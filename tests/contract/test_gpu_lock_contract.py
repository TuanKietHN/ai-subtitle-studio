import pytest
from ai_subtitle_studio.stt.gpu_lock import GPUSTTLock


def test_gpu_lock_allows_one_active_stt_section():
    lock = GPUSTTLock()
    with lock.acquire():
        assert lock.active_count == 1
        with pytest.raises(TimeoutError):
            with lock.acquire(blocking=False):
                pass
    assert lock.active_count == 0