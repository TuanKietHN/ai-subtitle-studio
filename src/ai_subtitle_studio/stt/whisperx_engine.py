"""WhisperX STT engine wrapper with mandatory VAD and GPU lock."""

from __future__ import annotations

from contextlib import contextmanager
import importlib
import logging
import os
import subprocess
import time
from typing import Any, Callable
import wave

from .base import GpuUnavailableError, TranscriptionCanceled, TranscriptionFailed, TranscriptionRequest, TranscriptionResult
from .gpu_lock import GLOBAL_GPU_STT_LOCK, GPUSTTLock

logger = logging.getLogger(__name__)
ASR_PROGRESS_START = 35.0
ASR_PROGRESS_END = 70.0


def default_gpu_available() -> bool:
    try:
        import torch  # type: ignore
        if getattr(torch, "cuda", None) is not None and torch.cuda.is_available():
            return True
    except Exception:
        logger.debug("Torch CUDA availability check failed.", exc_info=True)
    try:
        subprocess.run(["nvidia-smi"], capture_output=True, check=True, timeout=5)
        return True
    except Exception:
        logger.debug("nvidia-smi availability check failed.", exc_info=True)
        return False


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _audio_duration_seconds(audio_path: str) -> float | None:
    try:
        with wave.open(audio_path, "rb") as audio:
            frame_count = audio.getnframes()
            frame_rate = audio.getframerate()
        if frame_count > 0 and frame_rate > 0:
            return frame_count / float(frame_rate)
    except Exception:
        logger.debug("Could not read WAV duration for ASR progress: %s", audio_path, exc_info=True)
    return None


def _format_timestamp(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _segment_value_seconds(segment: Any, key: str) -> float | None:
    value = segment.get(key) if isinstance(segment, dict) else getattr(segment, key, None)
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        logger.debug("Could not parse VAD segment %s time for ASR progress.", key, exc_info=True)
        return None


def _segment_end_seconds(segment: Any) -> float | None:
    return _segment_value_seconds(segment, "end")


def _segment_start_seconds(segment: Any) -> float | None:
    return _segment_value_seconds(segment, "start")


def _segment_index(raw_percent: float, segments: list[Any]) -> int | None:
    if not segments:
        return None
    completed = int(round((_clamp(raw_percent, 0.0, 100.0) / 100.0) * len(segments)))
    completed = max(1, min(len(segments), completed))
    return completed - 1


def _eta_text(started_at: float, processed_seconds: float, duration_seconds: float, paused_seconds: float = 0.0) -> str:
    elapsed = time.monotonic() - started_at - paused_seconds
    remaining = max(0.0, duration_seconds - processed_seconds)
    if elapsed < 1.0 or processed_seconds <= 0 or remaining <= 0:
        return ""
    rate = processed_seconds / elapsed
    if rate <= 0:
        return ""
    return f" (còn khoảng {_format_timestamp(remaining / rate)})"


def _synchronize_cuda_before_pause() -> None:
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            torch.cuda.synchronize()
    except Exception:
        logger.debug("Could not synchronize CUDA at pause checkpoint.", exc_info=True)


def _control_checkpoint(control: Any | None, step: str) -> float:
    if control is None:
        return 0.0
    if control.is_cancel_requested():
        raise TranscriptionCanceled("Tác vụ nhận dạng đã bị hủy")
    wait_if_paused = getattr(control, "wait_if_paused", None)
    paused_at = None
    if callable(wait_if_paused):
        is_pause_requested = getattr(control, "is_pause_requested", None)
        if callable(is_pause_requested) and is_pause_requested():
            _synchronize_cuda_before_pause()
            paused_at = time.monotonic()
        wait_if_paused(step)
    if control.is_cancel_requested():
        raise TranscriptionCanceled("Tác vụ nhận dạng đã bị hủy")
    return max(0.0, time.monotonic() - paused_at) if paused_at is not None else 0.0


@contextmanager
def _acquire_gpu_interruptibly(gpu_lock: GPUSTTLock, control: Any | None):
    context = None
    while context is None:
        _control_checkpoint(control, "waiting_for_gpu")
        candidate = gpu_lock.acquire(blocking=False)
        try:
            candidate.__enter__()
        except TimeoutError:
            time.sleep(0.1)
        else:
            context = candidate
    try:
        yield
    finally:
        context.__exit__(None, None, None)


@contextmanager
def _capture_vad_segments(model: Any, checkpoint: Callable[[str], None] | None = None):
    captured: dict[str, Any] = {
        "segments": None,
        "chunk_offset_seconds": 0.0,
        "merge_call_count": 0,
        "last_local_end_seconds": None,
        "last_global_end_seconds": 0.0,
    }
    vad_model = getattr(model, "vad_model", None)
    original_merge_chunks = getattr(vad_model, "merge_chunks", None)
    if vad_model is None or original_merge_chunks is None:
        yield captured
        return

    def merge_chunks_with_capture(*args, **kwargs):
        if checkpoint:
            checkpoint("detecting_speech")
        chunks = original_merge_chunks(*args, **kwargs)
        if checkpoint:
            checkpoint("detecting_speech")
        try:
            segments = chunks if isinstance(chunks, list) else list(chunks)
            captured["segments"] = segments
            captured["merge_call_count"] = int(captured["merge_call_count"]) + 1
            local_ends = [_segment_end_seconds(segment) for segment in segments]
            local_starts = [_segment_start_seconds(segment) for segment in segments]
            local_ends = [value for value in local_ends if value is not None]
            local_starts = [value for value in local_starts if value is not None]
            if local_ends:
                local_end = max(local_ends)
                local_start = min(local_starts) if local_starts else 0.0
                previous_local_end = captured.get("last_local_end_seconds")
                previous_global_end = float(captured.get("last_global_end_seconds") or 0.0)
                offset = 0.0
                if previous_local_end is not None and (local_end <= float(previous_local_end) + 0.001 or local_start < previous_global_end <= local_end + 0.001):
                    offset = previous_global_end
                captured["chunk_offset_seconds"] = offset
                captured["last_local_end_seconds"] = local_end
                captured["last_global_end_seconds"] = max(previous_global_end, offset + local_end)
                if captured["merge_call_count"] > 1:
                    logger.info(
                        "WhisperX VAD chunk %s captured: local %.2fs..%.2fs, offset %.2fs, global processed %.2fs.",
                        captured["merge_call_count"],
                        local_start,
                        local_end,
                        offset,
                        captured["last_global_end_seconds"],
                    )
            return segments
        except Exception:
            logger.exception("WhisperX VAD chunk capture failed; ASR progress will use callback percent.")
            return chunks

    try:
        setattr(vad_model, "merge_chunks", merge_chunks_with_capture)
    except Exception:
        logger.debug("Could not attach WhisperX VAD chunk capture; ASR progress will use callback percent.", exc_info=True)
        yield captured
        return

    try:
        yield captured
    finally:
        try:
            setattr(vad_model, "merge_chunks", original_merge_chunks)
        except Exception:
            logger.exception("Could not restore WhisperX VAD merge_chunks after transcription.")


class WhisperXEngine:
    def __init__(self, gpu_lock: GPUSTTLock | None = None, gpu_available: Callable[[], bool] = default_gpu_available, whisperx_module: Any | None = None) -> None:
        self.gpu_lock = gpu_lock or GLOBAL_GPU_STT_LOCK
        self.gpu_available = gpu_available
        self._whisperx = whisperx_module
        self._configured_gpu_id: str | None = None

    @property
    def whisperx(self) -> Any:
        if self._whisperx is None:
            self._whisperx = importlib.import_module("whisperx")
        return self._whisperx

    def transcribe(self, request: TranscriptionRequest, progress=None, cancel=None) -> TranscriptionResult:
        self._configure_gpu(request.gpu_id)
        if request.device != "cuda" or not self.gpu_available():
            raise GpuUnavailableError("Không phát hiện NVIDIA/CUDA GPU hợp lệ")
        _control_checkpoint(cancel, "waiting_for_gpu")
        if progress:
            progress(5, "waiting_for_gpu", None)
        with _acquire_gpu_interruptibly(self.gpu_lock, cancel):
            try:
                _control_checkpoint(cancel, "loading_model")
                if progress:
                    progress(15, "loading_model", request.model_id)
                model = self.whisperx.load_model(request.model_id, request.device, compute_type=request.compute_type, download_root=request.model_cache_dir, language=request.language_hint, vad_method="pyannote")
                _control_checkpoint(cancel, "detecting_speech")
                if progress:
                    progress(ASR_PROGRESS_START, "transcribing", None)
                duration_seconds = _audio_duration_seconds(request.audio_path) if progress else None
                started_at = time.monotonic()
                paused_seconds = 0.0
                last_asr_progress = ASR_PROGRESS_START
                last_audio_seconds = 0.0

                def transcription_checkpoint(step: str) -> None:
                    nonlocal paused_seconds
                    paused_seconds += _control_checkpoint(cancel, step)

                def asr_progress_callback(raw_percent: float) -> None:
                    nonlocal last_asr_progress, last_audio_seconds
                    transcription_checkpoint("transcribing")
                    if not progress:
                        return
                    ratio = _clamp(float(raw_percent) / 100.0, 0.0, 1.0)
                    detail = f"Nhận dạng {ratio * 100.0:.1f}%"
                    segments = captured_vad.get("segments") or []
                    segment_index = _segment_index(float(raw_percent), segments)
                    if duration_seconds and segment_index is not None:
                        segment_end = _segment_end_seconds(segments[segment_index])
                        if segment_end is not None:
                            chunk_offset = float(captured_vad.get("chunk_offset_seconds") or 0.0)
                            processed_seconds = _clamp(chunk_offset + segment_end, 0.0, duration_seconds)
                            processed_seconds = max(last_audio_seconds, processed_seconds)
                            last_audio_seconds = processed_seconds
                            ratio = _clamp(processed_seconds / duration_seconds, 0.0, 1.0)
                            detail = f"Nhận dạng {_format_timestamp(processed_seconds)} / {_format_timestamp(duration_seconds)}{_eta_text(started_at, processed_seconds, duration_seconds, paused_seconds)}"
                    percent = ASR_PROGRESS_START + (ASR_PROGRESS_END - ASR_PROGRESS_START) * ratio
                    percent = max(last_asr_progress, percent)
                    last_asr_progress = percent
                    progress(percent, "transcribing", detail)

                transcribe_kwargs = {"progress_callback": asr_progress_callback} if progress else {}
                with _capture_vad_segments(model, transcription_checkpoint) as captured_vad:
                    # WhisperX runs Pyannote VAD inside transcribe(); any long-audio chunking observed here comes from WhisperX/VAD merge_chunks.
                    raw = model.transcribe(request.audio_path, **transcribe_kwargs)
                _control_checkpoint(cancel, "aligning")
                segments = raw.get("segments", []) if isinstance(raw, dict) else []
                language = raw.get("language", request.language_hint) if isinstance(raw, dict) else request.language_hint
                if progress:
                    progress(ASR_PROGRESS_END, "aligning", None)
                aligned_segments = segments
                if hasattr(self.whisperx, "load_align_model") and hasattr(self.whisperx, "align") and segments:
                    _control_checkpoint(cancel, "aligning")
                    align_model, metadata = self.whisperx.load_align_model(language_code=language, device=request.device)
                    _control_checkpoint(cancel, "aligning")
                    aligned = self.whisperx.align(segments, align_model, metadata, request.audio_path, request.device)
                    _control_checkpoint(cancel, "aligning")
                    aligned_segments = aligned.get("segments", segments)
                word_timings = []
                for segment in aligned_segments:
                    word_timings.extend(segment.get("words", []) or [])
                if progress:
                    progress(100, "aligned", None)
                return TranscriptionResult(language=language, segments=aligned_segments, word_timings=word_timings)
            except TranscriptionCanceled:
                logger.info("WhisperX transcription canceled for job %s.", request.job_id, exc_info=True)
                raise
            except Exception as exc:
                logger.exception("WhisperX transcription failed for job %s.", request.job_id)
                raise TranscriptionFailed(str(exc)) from exc

    def _configure_gpu(self, gpu_id: str | None) -> None:
        if gpu_id is None or gpu_id == "":
            return
        normalized = str(gpu_id)
        if self._configured_gpu_id is not None and self._configured_gpu_id != normalized:
            raise GpuUnavailableError(
                "GPU đã thay đổi sau khi runtime CUDA được khởi tạo; hãy khởi động lại ứng dụng"
            )
        if self._configured_gpu_id is None:
            os.environ["CUDA_VISIBLE_DEVICES"] = normalized
            self._configured_gpu_id = normalized
            logger.info("Configured CUDA_VISIBLE_DEVICES=%s for the STT runtime.", normalized)
