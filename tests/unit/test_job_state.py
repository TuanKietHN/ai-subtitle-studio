import pytest
from ai_subtitle_studio.domain.job_state import JobStatus, can_transition, cancel_target_for, restore_status_after_shutdown


def test_pause_resume_cancel_retry_transitions():
    assert can_transition(JobStatus.QUEUED, JobStatus.PAUSED)
    assert can_transition(JobStatus.PAUSED, JobStatus.QUEUED)
    assert cancel_target_for(JobStatus.TRANSCRIBING) == JobStatus.CANCELED
    assert can_transition(JobStatus.FAILED, JobStatus.QUEUED)
    assert can_transition(JobStatus.CANCELED, JobStatus.QUEUED)
    assert not can_transition(JobStatus.COMPLETED, JobStatus.CANCELED)


def test_active_job_restores_to_retry_required():
    assert restore_status_after_shutdown(JobStatus.TRANSCRIBING) == JobStatus.RETRY_REQUIRED
    assert restore_status_after_shutdown(JobStatus.COMPLETED) == JobStatus.COMPLETED
