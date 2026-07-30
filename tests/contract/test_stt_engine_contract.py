import logging
from dataclasses import fields
from threading import Thread
import time
import wave

import pytest

from ai_subtitle_studio.stt.base import TranscriptionCanceled, TranscriptionFailed, TranscriptionRequest
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
    assert fake.model.kwargs == {}


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
