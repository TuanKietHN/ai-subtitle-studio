"""Job state machine for queue, workers, and persistence."""

from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    PAUSED = "paused"
    WAITING_FOR_MODEL = "waiting_for_model"
    DOWNLOADING_MODEL = "downloading_model"
    EXTRACTING_AUDIO = "extracting_audio"
    WAITING_FOR_GPU = "waiting_for_gpu"
    TRANSCRIBING = "transcribing"
    ALIGNING = "aligning"
    TRANSLATING = "translating"
    READY_FOR_EDIT = "ready_for_edit"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    RETRY_REQUIRED = "retry_required"


ACTIVE_STATUSES = {
    JobStatus.WAITING_FOR_MODEL,
    JobStatus.DOWNLOADING_MODEL,
    JobStatus.EXTRACTING_AUDIO,
    JobStatus.WAITING_FOR_GPU,
    JobStatus.TRANSCRIBING,
    JobStatus.ALIGNING,
    JobStatus.TRANSLATING,
    JobStatus.EXPORTING,
}

TERMINAL_STATUSES = {JobStatus.COMPLETED, JobStatus.CANCELED}

TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.QUEUED: {JobStatus.PAUSED, JobStatus.WAITING_FOR_MODEL, JobStatus.EXTRACTING_AUDIO, JobStatus.CANCELED},
    JobStatus.PAUSED: {JobStatus.QUEUED, JobStatus.CANCELED},
    JobStatus.WAITING_FOR_MODEL: {JobStatus.DOWNLOADING_MODEL, JobStatus.EXTRACTING_AUDIO, JobStatus.FAILED, JobStatus.CANCELED},
    JobStatus.DOWNLOADING_MODEL: {JobStatus.EXTRACTING_AUDIO, JobStatus.FAILED, JobStatus.CANCELED, JobStatus.PAUSED},
    JobStatus.EXTRACTING_AUDIO: {JobStatus.WAITING_FOR_GPU, JobStatus.FAILED, JobStatus.CANCELED, JobStatus.PAUSED},
    JobStatus.WAITING_FOR_GPU: {JobStatus.TRANSCRIBING, JobStatus.PAUSED, JobStatus.CANCELED, JobStatus.FAILED},
    JobStatus.TRANSCRIBING: {JobStatus.ALIGNING, JobStatus.FAILED, JobStatus.CANCELED, JobStatus.PAUSED},
    JobStatus.ALIGNING: {JobStatus.TRANSLATING, JobStatus.READY_FOR_EDIT, JobStatus.FAILED, JobStatus.CANCELED, JobStatus.PAUSED},
    JobStatus.TRANSLATING: {JobStatus.READY_FOR_EDIT, JobStatus.FAILED, JobStatus.CANCELED, JobStatus.PAUSED},
    JobStatus.READY_FOR_EDIT: {JobStatus.EXPORTING, JobStatus.QUEUED, JobStatus.CANCELED},
    JobStatus.EXPORTING: {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELED},
    JobStatus.FAILED: {JobStatus.QUEUED, JobStatus.RETRY_REQUIRED},
    JobStatus.CANCELED: {JobStatus.QUEUED},
    JobStatus.COMPLETED: set(),
    JobStatus.RETRY_REQUIRED: {JobStatus.QUEUED, JobStatus.CANCELED},
}


def normalize_status(status: JobStatus | str) -> JobStatus:
    return status if isinstance(status, JobStatus) else JobStatus(status)


def can_transition(current: JobStatus | str, target: JobStatus | str) -> bool:
    current_status = normalize_status(current)
    target_status = normalize_status(target)
    if current_status in ACTIVE_STATUSES and target_status is JobStatus.RETRY_REQUIRED:
        return True
    return target_status in TRANSITIONS.get(current_status, set())


def require_transition(current: JobStatus | str, target: JobStatus | str) -> JobStatus:
    if not can_transition(current, target):
        raise ValueError(f"Invalid job transition: {normalize_status(current).value} -> {normalize_status(target).value}")
    return normalize_status(target)


def pause_target_for(status: JobStatus | str) -> JobStatus:
    current = normalize_status(status)
    if current is JobStatus.QUEUED:
        return JobStatus.PAUSED
    if current in ACTIVE_STATUSES:
        return JobStatus.PAUSED
    raise ValueError(f"Cannot pause job in {current.value}")


def cancel_target_for(status: JobStatus | str) -> JobStatus:
    current = normalize_status(status)
    if current in {JobStatus.COMPLETED, JobStatus.CANCELED}:
        raise ValueError(f"Cannot cancel job in {current.value}")
    return JobStatus.CANCELED


def restore_status_after_shutdown(status: JobStatus | str) -> JobStatus:
    current = normalize_status(status)
    return JobStatus.RETRY_REQUIRED if current in ACTIVE_STATUSES else current
