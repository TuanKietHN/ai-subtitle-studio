"""Model download worker with progress accounting."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
from ai_subtitle_studio.domain.entities import ModelDownload

ProgressCallback = Callable[[ModelDownload], None]

@dataclass(slots=True)
class DownloadChunk:
    bytes_count: int
    delay_seconds: float = 0.0

class ModelDownloadWorker:
    def __init__(self, model_id: str, cache_dir: str | Path, chunks: Iterable[DownloadChunk] | None = None) -> None:
        self.model_id = model_id
        self.cache_dir = Path(cache_dir)
        self.chunks = list(chunks or [DownloadChunk(1_000_000)])
        self.canceled = False
    def cancel(self) -> None:
        self.canceled = True
    def run(self, progress: ProgressCallback | None = None, control=None) -> ModelDownload:
        total = sum(chunk.bytes_count for chunk in self.chunks)
        state = ModelDownload(model_id=self.model_id, status="downloading", bytes_total=total, bytes_remaining=total)
        start = time.monotonic()
        if progress: progress(state)
        downloaded = 0
        for chunk in self.chunks:
            wait_if_paused = getattr(control, "wait_if_paused", None)
            if callable(wait_if_paused):
                wait_if_paused("downloading_model")
            if self.canceled or (control is not None and control.is_cancel_requested()):
                state.status = "canceled"; break
            if chunk.delay_seconds:
                deadline = time.monotonic() + chunk.delay_seconds
                while time.monotonic() < deadline:
                    if self.canceled or (control is not None and control.is_cancel_requested()):
                        state.status = "canceled"
                        break
                    time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
                if state.status == "canceled":
                    break
            downloaded += chunk.bytes_count
            elapsed = max(time.monotonic() - start, 0.001)
            state.bytes_downloaded = downloaded
            state.bytes_remaining = max(total - downloaded, 0)
            state.percent = 100.0 if total == 0 else min(100.0, downloaded / total * 100)
            state.speed_bytes_per_sec = downloaded / elapsed
            if progress: progress(state)
        if state.status != "canceled":
            state.status = "completed"; state.percent = 100.0; state.bytes_remaining = 0
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        return state
