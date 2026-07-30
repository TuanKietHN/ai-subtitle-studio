"""Process-local GPU STT lock."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator

class GPUSTTLock:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active = 0
        self._counter_lock = threading.Lock()
    @contextmanager
    def acquire(self, blocking: bool = True) -> Iterator[None]:
        acquired = self._lock.acquire(blocking=blocking)
        if not acquired:
            raise TimeoutError("GPU STT lock is already held")
        with self._counter_lock:
            self._active += 1
            if self._active > 1:
                self._active -= 1
                self._lock.release()
                raise RuntimeError("More than one GPU STT job became active")
        try:
            yield
        finally:
            with self._counter_lock:
                self._active -= 1
            self._lock.release()
    @property
    def active_count(self) -> int:
        with self._counter_lock:
            return self._active

GLOBAL_GPU_STT_LOCK = GPUSTTLock()