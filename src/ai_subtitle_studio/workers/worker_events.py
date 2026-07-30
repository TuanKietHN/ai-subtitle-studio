"""Worker event dataclasses and control tokens."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Condition, Event
from typing import Any, Callable
from uuid import uuid4

@dataclass(slots=True)
class WorkerEvent:
    event_type: str
    payload: dict[str, Any]
    job_id: str | None = None
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CancelToken:
    def __init__(self) -> None:
        self._event = Event()
    def cancel(self) -> None:
        self._event.set()
    def clear_cancel(self) -> None:
        self._event.clear()
    def is_cancel_requested(self) -> bool:
        return self._event.is_set()

class WorkerControlToken(CancelToken):
    def __init__(self) -> None:
        super().__init__()
        self._pause = Event()
        self._stop_after_current = Event()
        self._shutdown = Event()
        self._condition = Condition()

    def request_pause(self) -> None:
        with self._condition:
            self._pause.set()
            self._condition.notify_all()

    def clear_pause(self) -> None:
        with self._condition:
            self._pause.clear()
            self._condition.notify_all()

    def resume(self) -> None:
        self.clear_pause()

    def is_pause_requested(self) -> bool:
        return self._pause.is_set()

    def cancel(self) -> None:
        with self._condition:
            super().cancel()
            self._condition.notify_all()

    def wait_while_paused(self, extra_stop: Callable[[], bool] | None = None) -> bool:
        """Block at a safe worker checkpoint until resume, cancel, or shutdown."""
        with self._condition:
            while (
                self._pause.is_set()
                and not self.is_cancel_requested()
                and not self.is_shutdown_requested()
                and not (extra_stop and extra_stop())
            ):
                self._condition.wait(timeout=0.1)
        return not self.is_cancel_requested() and not self.is_shutdown_requested() and not (extra_stop and extra_stop())

    def request_stop_after_current(self) -> None:
        self._stop_after_current.set()
    def is_stop_after_current_requested(self) -> bool:
        return self._stop_after_current.is_set()
    def request_shutdown(self) -> None:
        self._shutdown.set()
        self.request_stop_after_current()
        self.cancel()
    def is_shutdown_requested(self) -> bool:
        return self._shutdown.is_set()

def progress_event(job_id: str, percent: float, step: str, detail: str | None = None) -> WorkerEvent:
    return WorkerEvent("job.progress", {"percent": percent, "step": step, "detail": detail}, job_id=job_id)

def error_event(job_id: str, error_code: str, message: str, recoverable: bool = True, retry_allowed: bool = True) -> WorkerEvent:
    return WorkerEvent("job.error", {"error_code": error_code, "message": message, "recoverable": recoverable, "retry_allowed": retry_allowed}, job_id=job_id)

def pause_pending_event(job_id: str, current_step: str) -> WorkerEvent:
    return WorkerEvent("pause.pending_checkpoint", {"current_step": current_step, "message": "Tạm dừng sẽ được áp dụng sau điểm kiểm tra an toàn hiện tại."}, job_id=job_id)
