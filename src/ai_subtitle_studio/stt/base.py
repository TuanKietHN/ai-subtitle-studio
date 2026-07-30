"""STT engine protocol and data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

@dataclass(slots=True)
class TranscriptionRequest:
    job_id: str
    audio_path: str
    model_id: str
    device: str = "cuda"
    compute_type: str = "float16"
    model_cache_dir: str | None = None
    gpu_id: str | None = None
    language_hint: str = "en"

@dataclass(slots=True)
class TranscriptionResult:
    language: str
    segments: list[dict[str, Any]]
    word_timings: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

class ProgressSink(Protocol):
    def __call__(self, percent: float, step: str, detail: str | None = None) -> None: ...

class CancelToken(Protocol):
    def is_cancel_requested(self) -> bool: ...

class STTEngine(Protocol):
    def transcribe(self, request: TranscriptionRequest, progress: ProgressSink | None = None, cancel: CancelToken | None = None) -> TranscriptionResult: ...

class STTError(RuntimeError): pass
class GpuUnavailableError(STTError): pass
class ModelUnavailableError(STTError): pass
class AudioReadError(STTError): pass
class TranscriptionCanceled(STTError): pass
class TranscriptionFailed(STTError): pass
