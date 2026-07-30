import time
from ai_subtitle_studio.workers.model_download_worker import DownloadChunk, ModelDownloadWorker
from ai_subtitle_studio.workers.worker_events import CancelToken


def test_model_download_progress_percent_speed_remaining(tmp_path):
    events = []
    worker = ModelDownloadWorker("large-v3", tmp_path, chunks=[DownloadChunk(10), DownloadChunk(30)])
    result = worker.run(progress=events.append)
    assert result.status == "completed"
    assert result.percent == 100
    assert events[-1].bytes_remaining == 0
    assert events[-1].speed_bytes_per_sec > 0


def test_model_download_progress_appears_within_5_seconds(tmp_path):
    events = []
    start = time.monotonic()
    worker = ModelDownloadWorker("medium", tmp_path, chunks=[DownloadChunk(1)])
    worker.run(progress=events.append)
    assert events
    assert time.monotonic() - start < 5


def test_model_download_honors_cancel_control_during_delay(tmp_path):
    worker = ModelDownloadWorker("medium", tmp_path, chunks=[DownloadChunk(1, delay_seconds=2)])
    control = CancelToken()
    control.cancel()
    start = time.monotonic()

    result = worker.run(control=control)

    assert result.status == "canceled"
    assert time.monotonic() - start < 1
