import time
from ai_subtitle_studio.config.model_catalog import ModelCatalog
from ai_subtitle_studio.domain.entities import VideoJob
from ai_subtitle_studio.domain.job_state import JobStatus
from ai_subtitle_studio.ui.main_window import MainWindowController
from ai_subtitle_studio.workers.job_runner import JobRunner


def test_queue_controls_error_retry_and_pause_response_under_2s():
    controller = MainWindowController(ModelCatalog.load("resources/models.json"), job_runner=JobRunner())
    job = VideoJob("lecture.mp4", status=JobStatus.TRANSCRIBING)
    start = time.monotonic()
    event = controller.pause_job(job)
    elapsed = time.monotonic() - start
    assert elapsed < 2
    assert event.event_type == "pause.pending_checkpoint"
    controller.cancel_job(job)
    assert job.status == JobStatus.CANCELED
    controller.retry_job(job)
    assert job.status == JobStatus.QUEUED
