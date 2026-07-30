from ai_subtitle_studio.domain.entities import VideoJob
from ai_subtitle_studio.domain.job_state import JobStatus
from ai_subtitle_studio.workers.job_runner import JobRunner
from ai_subtitle_studio.workers.worker_events import WorkerControlToken


def test_worker_pause_checkpoint_and_cancel_events():
    runner = JobRunner()
    job = VideoJob("lecture.mp4", status=JobStatus.TRANSCRIBING)
    event = runner.request_pause(job)
    assert event.event_type == "pause.pending_checkpoint"
    assert job.pause_requested is True
    runner.cancel(job)
    assert job.status == JobStatus.CANCELED


def test_control_token_pause_cancel_flags():
    token = WorkerControlToken()
    token.request_pause()
    token.cancel()
    token.request_stop_after_current()
    assert token.is_pause_requested() is True
    assert token.is_cancel_requested() is True
    assert token.is_stop_after_current_requested() is True
    token.clear_cancel()
    assert token.is_cancel_requested() is False


def test_control_token_shutdown_requests_cancel_and_stop_after_current():
    token = WorkerControlToken()
    token.request_shutdown()
    assert token.is_shutdown_requested() is True
    assert token.is_cancel_requested() is True
    assert token.is_stop_after_current_requested() is True
