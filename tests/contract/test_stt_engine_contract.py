import logging
from dataclasses import fields
import sys
from threading import Thread
import time
from types import SimpleNamespace
import wave

import pytest

from ai_subtitle_studio.stt.base import GpuOutOfMemoryError, TranscriptionCanceled, TranscriptionFailed, TranscriptionRequest
from ai_subtitle_studio.stt.gpu_lock import GPUSTTLock
from ai_subtitle_studio.stt import whisperx_engine
from ai_subtitle_studio.stt.whisperx_engine import WhisperXEngine
from ai_subtitle_studio.workers.worker_events import CancelToken


class FakeModel:
    def __init__(self):
        self.kwargs = None
    def transcribe(self, path, **kwargs):
        self.kwargs = kwargs
        callback = kwargs.get("progress_callback")
        if callback:
            callback(50.0)
        return {"language": "en", "segments": [{"start": 0, "end": 1, "text": "Hello.", "words": [{"word": "Hello.", "start": 0, "end": 1}]}]}


class FakeVadModel:
    def merge_chunks(self, *args, **kwargs):
        return [{"start": 0, "end": 10}, {"start": 10, "end": 20}]


class TimedFakeModel(FakeModel):
    def __init__(self):
        super().__init__()
        self.vad_model = FakeVadModel()
    def transcribe(self, path, **kwargs):
        self.kwargs = kwargs
        self.vad_model.merge_chunks([], 30)
        callback = kwargs.get("progress_callback")
        if callback:
            callback(50.0)
            callback(100.0)
        return {"language": "en", "segments": [{"start": 0, "end": 20, "text": "Hello.", "words": []}]}


class ResettingVadModel:
    def __init__(self):
        self.calls = 0

    def merge_chunks(self, *args, **kwargs):
        self.calls += 1
        return [{"start": 0, "end": 10}]


class ResettingChunkFakeModel(FakeModel):
    def __init__(self):
        super().__init__()
        self.vad_model = ResettingVadModel()

    def transcribe(self, path, **kwargs):
        self.kwargs = kwargs
        callback = kwargs.get("progress_callback")
        self.vad_model.merge_chunks([], 30)
        if callback:
            callback(100.0)
        self.vad_model.merge_chunks([], 30)
        if callback:
            callback(100.0)
        return {"language": "en", "segments": [{"start": 0, "end": 20, "text": "Hello.", "words": []}]}


class FailingModel:
    def transcribe(self, path, **kwargs):
        raise RuntimeError("asr exploded")


class FakeWhisperX:
    def __init__(self, model=None):
        self.model = model or FakeModel()
        self.load_args = None
        self.load_kwargs = None
    def load_model(self, *args, **kwargs):
        self.load_args = args
        self.load_kwargs = kwargs
        return self.model
    def load_align_model(self, language_code, device):
        return object(), {"language": language_code}
    def align(self, segments, align_model, metadata, audio_path, device):
        return {"segments": segments}


def write_silent_wav(path, seconds):
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\0\0" * 16000 * seconds)


def test_transcription_request_has_no_vad_field():
    assert "vad_filter" not in {field.name for field in fields(TranscriptionRequest)}
    assert "vad" not in {field.name for field in fields(TranscriptionRequest)}


def test_whisperx_engine_configures_vad_when_loading_model():
    fake = FakeWhisperX()
    engine = WhisperXEngine(gpu_lock=GPUSTTLock(), gpu_available=lambda: True, whisperx_module=fake)
    result = engine.transcribe(TranscriptionRequest(job_id="j1", audio_path="a.wav", model_id="large-v3"))
    assert result.language == "en"
    assert fake.load_kwargs["vad_method"] == "pyannote"
    assert fake.load_kwargs["device_index"] == 0
    assert fake.model.kwargs == {"batch_size": 16}


def test_whisperx_engine_passes_effective_batch_size():
    fake = FakeWhisperX()
    engine = WhisperXEngine(gpu_lock=GPUSTTLock(), gpu_available=lambda: True, whisperx_module=fake)

    engine.transcribe(
        TranscriptionRequest(
            job_id="j1",
            audio_path="a.wav",
            model_id="small.en",
            compute_type="int8_float16",
            batch_size=1,
            execution_profile_id="low-vram-4gb",
        )
    )

    assert fake.load_kwargs["compute_type"] == "int8_float16"
    assert fake.model.kwargs["batch_size"] == 1


def test_whisperx_engine_selects_requested_torch_and_faster_whisper_gpu(monkeypatch):
    selected = []
    fake_cuda = SimpleNamespace(
        is_available=lambda: True,
        device_count=lambda: 2,
        set_device=lambda index: selected.append(index),
    )
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=fake_cuda))
    monkeypatch.setattr(whisperx_engine, "_reset_peak_cuda_memory", lambda: None)
    monkeypatch.setattr(whisperx_engine, "_log_peak_cuda_memory", lambda phase: None)
    monkeypatch.setattr(whisperx_engine, "release_cuda_resources", lambda: None)
    fake = FakeWhisperX()
    engine = WhisperXEngine(gpu_lock=GPUSTTLock(), gpu_available=lambda: True, whisperx_module=fake)

    engine.transcribe(
        TranscriptionRequest(job_id="j1", audio_path="a.wav", model_id="small.en", gpu_id="1")
    )
    engine.transcribe(
        TranscriptionRequest(job_id="j2", audio_path="b.wav", model_id="small.en", gpu_id=None)
    )

    assert selected == [1]
    assert fake.load_kwargs["device_index"] == 1


def test_nvidia_smi_does_not_make_torch_unavailable_gpu_ready(monkeypatch):
    monkeypatch.setattr(whisperx_engine, "torch_cuda_ready", lambda: (False, "Torch CUDA failed"))

    assert whisperx_engine.default_gpu_available() is False


class OomThenSuccessModel(FakeModel):
    def __init__(self, always_fail=False):
        super().__init__()
        self.calls = 0
        self.always_fail = always_fail

    def transcribe(self, path, **kwargs):
        self.calls += 1
        if self.always_fail or self.calls == 1:
            raise RuntimeError("CUDA out of memory")
        return super().transcribe(path, **kwargs)


def test_cuda_oom_retries_once_with_same_model():
    model = OomThenSuccessModel()
    fake = FakeWhisperX(model=model)
    engine = WhisperXEngine(gpu_lock=GPUSTTLock(), gpu_available=lambda: True, whisperx_module=fake)

    result = engine.transcribe(
        TranscriptionRequest(job_id="j1", audio_path="a.wav", model_id="small.en", batch_size=2)
    )

    assert result.language == "en"
    assert model.calls == 2
    assert model.kwargs["batch_size"] == 1
    assert fake.load_args[0] == "small.en"


def test_second_cuda_oom_maps_to_stable_error():
    model = OomThenSuccessModel(always_fail=True)
    engine = WhisperXEngine(
        gpu_lock=GPUSTTLock(),
        gpu_available=lambda: True,
        whisperx_module=FakeWhisperX(model=model),
    )

    with pytest.raises(GpuOutOfMemoryError, match="GPU 4 GiB"):
        engine.transcribe(
            TranscriptionRequest(job_id="j1", audio_path="a.wav", model_id="small.en", batch_size=1)
        )

    assert model.calls == 2


def test_asr_model_is_released_before_alignment(monkeypatch):
    import gc
    import weakref

    released = []

    class EphemeralWhisperX:
        def load_model(self, *args, **kwargs):
            model = FakeModel()
            self.ref = weakref.ref(model)
            return model

        def load_align_model(self, language_code, device):
            gc.collect()
            released.append(self.ref() is None)
            return object(), {"language": language_code}

        def align(self, segments, align_model, metadata, audio_path, device):
            return {"segments": segments}

    engine = WhisperXEngine(
        gpu_lock=GPUSTTLock(),
        gpu_available=lambda: True,
        whisperx_module=EphemeralWhisperX(),
    )
    monkeypatch.setattr(whisperx_engine, "release_cuda_resources", lambda: None)

    engine.transcribe(TranscriptionRequest(job_id="j1", audio_path="a.wav", model_id="small.en"))

    assert released == [True]


def test_asr_resources_are_released_when_canceled_after_model_load(monkeypatch):
    token = CancelToken()
    released = []

    class CancelAfterLoadWhisperX:
        def load_model(self, *args, **kwargs):
            token.cancel()
            return FakeModel()

    engine = WhisperXEngine(
        gpu_lock=GPUSTTLock(),
        gpu_available=lambda: True,
        whisperx_module=CancelAfterLoadWhisperX(),
    )
    monkeypatch.setattr(whisperx_engine, "release_cuda_resources", lambda: released.append(True))

    with pytest.raises(TranscriptionCanceled):
        engine.transcribe(
            TranscriptionRequest(job_id="j1", audio_path="a.wav", model_id="small.en"),
            cancel=token,
        )

    assert released == [True]


def test_whisperx_engine_uses_progress_callback_without_vad_filter():
    fake = FakeWhisperX()
    events = []
    engine = WhisperXEngine(gpu_lock=GPUSTTLock(), gpu_available=lambda: True, whisperx_module=fake)
    engine.transcribe(TranscriptionRequest(job_id="j1", audio_path="a.wav", model_id="large-v3"), progress=lambda p, s, d=None: events.append((p, s, d)))
    assert "vad_filter" not in fake.model.kwargs
    assert callable(fake.model.kwargs["progress_callback"])
    assert (52.5, "transcribing", "Nhận dạng 50.0%") in events


def test_whisperx_engine_maps_asr_progress_to_vad_end_time(tmp_path):
    audio_path = tmp_path / "a.wav"
    write_silent_wav(audio_path, seconds=40)
    fake = FakeWhisperX(model=TimedFakeModel())
    events = []
    engine = WhisperXEngine(gpu_lock=GPUSTTLock(), gpu_available=lambda: True, whisperx_module=fake)
    engine.transcribe(TranscriptionRequest(job_id="j1", audio_path=str(audio_path), model_id="large-v3"), progress=lambda p, s, d=None: events.append((p, s, d)))
    assert (43.75, "transcribing", "Nhận dạng 00:10 / 00:40") in events
    assert (52.5, "transcribing", "Nhận dạng 00:20 / 00:40") in events


def test_whisperx_engine_logs_transcription_traceback(caplog):
    caplog.set_level(logging.ERROR)
    fake = FakeWhisperX(model=FailingModel())
    engine = WhisperXEngine(gpu_lock=GPUSTTLock(), gpu_available=lambda: True, whisperx_module=fake)
    with pytest.raises(TranscriptionFailed):
        engine.transcribe(TranscriptionRequest(job_id="j1", audio_path="a.wav", model_id="large-v3"))
    assert any(record.exc_info and "WhisperX transcription failed for job j1" in record.message for record in caplog.records)


def test_whisperx_engine_checks_cancel_between_gpu_stages():
    fake = FakeWhisperX()
    token = CancelToken()
    engine = WhisperXEngine(gpu_lock=GPUSTTLock(), gpu_available=lambda: True, whisperx_module=fake)

    with pytest.raises(TranscriptionCanceled):
        engine.transcribe(
            TranscriptionRequest(job_id="j1", audio_path="a.wav", model_id="large-v3"),
            progress=lambda *_: token.cancel(),
            cancel=token,
        )

    assert fake.load_args is None


def test_whisperx_engine_cancel_interrupts_wait_for_gpu_lock():
    fake = FakeWhisperX()
    token = CancelToken()
    lock = GPUSTTLock()
    engine = WhisperXEngine(gpu_lock=lock, gpu_available=lambda: True, whisperx_module=fake)
    errors = []

    with lock.acquire():
        thread = Thread(
            target=lambda: _capture_exception(
                errors,
                lambda: engine.transcribe(
                    TranscriptionRequest(job_id="j1", audio_path="a.wav", model_id="large-v3"),
                    cancel=token,
                ),
            ),
            daemon=True,
        )
        thread.start()
        time.sleep(0.05)
        token.cancel()
        thread.join(1)

    assert not thread.is_alive()
    assert len(errors) == 1
    assert isinstance(errors[0], TranscriptionCanceled)
    assert fake.load_args is None


def _capture_exception(errors, operation):
    try:
        operation()
    except Exception as exc:
        errors.append(exc)


def test_whisperx_engine_accumulates_progress_when_vad_chunk_timestamps_reset(tmp_path):
    audio_path = tmp_path / "a.wav"
    write_silent_wav(audio_path, seconds=20)
    fake = FakeWhisperX(model=ResettingChunkFakeModel())
    events = []
    engine = WhisperXEngine(gpu_lock=GPUSTTLock(), gpu_available=lambda: True, whisperx_module=fake)
    engine.transcribe(TranscriptionRequest(job_id="j1", audio_path=str(audio_path), model_id="large-v3"), progress=lambda p, s, d=None: events.append((p, s, d)))
    assert (52.5, "transcribing", "Nhận dạng 00:10 / 00:20") in events
    assert (70.0, "transcribing", "Nhận dạng 00:20 / 00:20") in events


def test_eta_excludes_time_spent_paused(monkeypatch):
    monkeypatch.setattr(whisperx_engine.time, "monotonic", lambda: 100.0)

    without_pause_adjustment = whisperx_engine._eta_text(0.0, 50.0, 100.0)
    with_pause_adjustment = whisperx_engine._eta_text(0.0, 50.0, 100.0, paused_seconds=50.0)

    assert without_pause_adjustment == " (còn khoảng 01:40)"
    assert with_pause_adjustment == " (còn khoảng 00:50)"
