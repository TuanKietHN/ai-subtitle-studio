"""Queue service and sequential job runner."""

from __future__ import annotations

from dataclasses import dataclass, field
import inspect
import logging
from pathlib import Path
from typing import Iterable

from ai_subtitle_studio.domain.entities import SubtitleLine, VideoJob, user_safe_error, utc_now_iso
from ai_subtitle_studio.domain.job_state import ACTIVE_STATUSES, JobStatus, require_transition
from ai_subtitle_studio.domain.subtitle import segments_to_subtitle_lines
from ai_subtitle_studio.io.audio_extractor import AudioExtractionCanceled
from ai_subtitle_studio.io.srt_writer import SRTWriter, default_output_paths
from ai_subtitle_studio.io.working_files import WorkingFileManager
from ai_subtitle_studio.persistence.repositories import source_fingerprint
from ai_subtitle_studio.stt.base import GpuOutOfMemoryError, GpuUnavailableError, TranscriptionCanceled, TranscriptionRequest
from ai_subtitle_studio.translation.base import TranslationBatchRequest, TranslationItem, validate_translation_shape
from ai_subtitle_studio.workers.worker_events import WorkerControlToken, WorkerEvent, error_event, pause_pending_event, progress_event

logger = logging.getLogger(__name__)

STEP_LABELS = {
    "start": "bắt đầu",
    "model": "kiểm tra model",
    "extracting_audio": "trích audio",
    "waiting_for_gpu": "chờ GPU",
    "loading_model": "tải model vào GPU",
    "detecting_speech": "phát hiện giọng nói",
    "transcribing": "nhận dạng",
    "aligning": "căn timestamp",
    "exporting": "xuất phụ đề",
}


def _step_label(step: str) -> str:
    return STEP_LABELS.get(step, step.replace("_", " "))


def _shutdown_retry_message(step: str | None = None) -> str:
    if step:
        return f"Đã dừng khi ứng dụng đóng (tại bước {_step_label(step)}). Bấm \"Bắt đầu xử lý\" để chạy lại từ đầu."
    return "App đã đóng khi job đang chạy. Bấm \"Bắt đầu xử lý\" để chạy lại từ đầu."


class _JobPaused(Exception):
    """Internal control-flow signal for a checkpoint pause."""


class _JobCanceled(Exception):
    """Internal control-flow signal for a checkpoint cancel."""


class _JobStopped(Exception):
    """Internal control-flow signal for app shutdown."""


class _JobCancelToken:
    def __init__(self, job: VideoJob, control: WorkerControlToken, runner: "JobRunner") -> None:
        self.job = job
        self.control = control
        self.runner = runner

    def is_cancel_requested(self) -> bool:
        return (
            self.control.is_cancel_requested()
            or self.control.is_shutdown_requested()
            or self.job.cancel_requested
            or self.job.status is JobStatus.CANCELED
        )

    def is_pause_requested(self) -> bool:
        return self.control.is_pause_requested() or self.job.pause_requested

    def wait_if_paused(self, step: str) -> None:
        if self.is_cancel_requested() or not self.is_pause_requested():
            return
        resume_status = self.job.status
        self.control.request_pause()
        self.job.pause_requested = False
        self.job.retry_required = True
        self.job.status = JobStatus.PAUSED
        self.job.progress_label = f"Đã tạm dừng tại bước {_step_label(step)}. Bấm \"Tiếp tục\" để chạy tiếp."
        self.runner._save(self.job)
        self.runner.emit(
            WorkerEvent(
                "job.status_changed",
                {"old_status": resume_status.value, "new_status": JobStatus.PAUSED.value, "message": self.job.progress_label},
                job_id=self.job.id,
            )
        )
        resumed = self.control.wait_while_paused(extra_stop=self.is_cancel_requested)
        if not resumed:
            return
        self.job.retry_required = False
        self.job.status = resume_status
        self.job.progress_label = f"Đang tiếp tục {_step_label(step)}"
        self.runner._save(self.job)
        self.runner.emit(
            WorkerEvent(
                "job.status_changed",
                {"old_status": JobStatus.PAUSED.value, "new_status": resume_status.value, "message": self.job.progress_label},
                job_id=self.job.id,
            )
        )


@dataclass
class QueueAddResult:
    added: list[VideoJob] = field(default_factory=list)
    rejected: list[tuple[str, str]] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)


class VideoQueueService:
    def __init__(self) -> None:
        self.jobs: list[VideoJob] = []
        self._fingerprints: set[str] = set()

    def add_files(self, paths: Iterable[str | Path], selected_model_id: str = "large-v3") -> QueueAddResult:
        result = QueueAddResult()
        for raw in paths:
            path = Path(raw)
            if path.suffix.lower() != ".mp4":
                result.rejected.append((str(path), "Chỉ hỗ trợ file .mp4"))
                continue
            fingerprint = source_fingerprint(path)
            if fingerprint in self._fingerprints:
                result.duplicates.append(str(path))
                continue
            job = VideoJob(source_path=str(path), source_fingerprint=fingerprint, selected_model_id=selected_model_id)
            self.jobs.append(job)
            self._fingerprints.add(fingerprint)
            result.added.append(job)
        return result

    def pending_jobs(self) -> list[VideoJob]:
        return [job for job in self.jobs if job.status in {JobStatus.QUEUED, JobStatus.RETRY_REQUIRED}]


class JobRunner:
    def __init__(
        self,
        audio_extractor=None,
        stt_engine=None,
        srt_writer: SRTWriter | None = None,
        output_dir: str | Path | None = None,
        job_repository=None,
        subtitle_repository=None,
        model_catalog=None,
        model_downloader_factory=None,
        translation_registry=None,
        working_files: WorkingFileManager | None = None,
        model_cache_dir: str | Path | None = None,
        selected_gpu_id: str | None = None,
        compute_type: str = "float16",
        batch_size: int = 16,
        execution_profile_id: str = "default",
    ) -> None:
        self.audio_extractor = audio_extractor
        self.stt_engine = stt_engine
        self.srt_writer = srt_writer or SRTWriter()
        self.output_dir = Path(output_dir or ".")
        self.working_files = working_files or WorkingFileManager.for_output_dir(self.output_dir)
        self.working_dir = self.working_files.root
        self.job_repository = job_repository
        self.subtitle_repository = subtitle_repository
        self.model_catalog = model_catalog
        self.model_downloader_factory = model_downloader_factory
        self.translation_registry = translation_registry
        self.model_cache_dir = Path(model_cache_dir) if model_cache_dir else None
        self.selected_gpu_id = selected_gpu_id
        self.compute_type = compute_type
        self.batch_size = batch_size
        self.execution_profile_id = execution_profile_id
        self.events: list[WorkerEvent] = []
        self.current_job_id: str | None = None

    def set_output_dir(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)
        self.working_files = WorkingFileManager.for_output_dir(self.output_dir)
        self.working_dir = self.working_files.root

    def set_runtime_settings(
        self,
        *,
        model_cache_dir: str | Path | None = None,
        selected_gpu_id: str | None = None,
        compute_type: str | None = None,
        batch_size: int | None = None,
        execution_profile_id: str | None = None,
    ) -> None:
        self.model_cache_dir = Path(model_cache_dir) if model_cache_dir else None
        self.selected_gpu_id = selected_gpu_id
        if compute_type is not None:
            self.compute_type = compute_type
        if batch_size is not None:
            if batch_size < 1:
                raise ValueError("batch_size must be positive")
            self.batch_size = batch_size
        if execution_profile_id is not None:
            self.execution_profile_id = execution_profile_id

    def emit(self, event: WorkerEvent) -> None:
        self.events.append(event)

    def process_queue(self, jobs: Iterable[VideoJob], control: WorkerControlToken | None = None) -> list[VideoJob]:
        queue_control = control or WorkerControlToken()
        processed: list[VideoJob] = []
        for job in jobs:
            if queue_control.is_shutdown_requested():
                break
            if job.status in {JobStatus.PAUSED, JobStatus.CANCELED, JobStatus.COMPLETED}:
                continue
            processed.append(self.process_job(job, control=queue_control))
            if queue_control.is_stop_after_current_requested() or queue_control.is_shutdown_requested():
                break
        return processed

    def process_job(self, job: VideoJob, control: WorkerControlToken) -> VideoJob:
        self.current_job_id = job.id
        job_output_dir = self.output_dir
        job_working_files = self.working_files
        if job.status is JobStatus.RETRY_REQUIRED:
            job.retry_required = False
            job.error_code = None
            job.error_message = None
        if not job.started_at:
            job.started_at = utc_now_iso()
        job_control = _JobCancelToken(job, control, self)
        try:
            self._checkpoint(job, control, "start")
            self._ensure_model_available(job, job_control, output_dir=job_output_dir)
            self._checkpoint(job, control, "model")
            job.status = JobStatus.EXTRACTING_AUDIO
            job.progress_label = "Đang trích audio"
            self._save(job)
            self.emit(progress_event(job.id, 10, "extracting_audio"))

            audio_path = self._prepare_audio(job, job_control, working_files=job_working_files)
            self._checkpoint(job, control, "extracting_audio")

            job.status = JobStatus.TRANSCRIBING
            job.progress_label = "Đang nhận dạng"
            self._save(job)
            if not self.stt_engine:
                raise RuntimeError("Chưa cấu hình bộ nhận dạng giọng nói")
            request = TranscriptionRequest(
                job_id=job.id,
                audio_path=audio_path,
                model_id=job.selected_model_id,
                model_cache_dir=str(self.model_cache_dir) if self.model_cache_dir else None,
                gpu_id=job.gpu_id or self.selected_gpu_id,
                compute_type=self.compute_type,
                batch_size=self.batch_size,
                execution_profile_id=self.execution_profile_id,
            )
            result = self.stt_engine.transcribe(
                request,
                progress=lambda p, s, d=None: self.emit(progress_event(job.id, p, s, d)),
                cancel=job_control,
            )
            lines = segments_to_subtitle_lines(result.segments)
            self._checkpoint(job, control, "aligning")

            if self.subtitle_repository:
                self.subtitle_repository.replace_for_job(job.id, lines)
            paths = default_output_paths(job.source_path, job_output_dir)
            job.status = JobStatus.EXPORTING
            job.progress_label = "Đang xuất phụ đề"
            self._save(job)
            job.english_srt_path = str(self.srt_writer.write_english(lines, paths["english"]))
            job.status = JobStatus.COMPLETED
            job.progress_percent = 100
            job.progress_label = "Hoàn tất"
            job.completed_at = utc_now_iso()
            self._save(job)
            self.emit(WorkerEvent("job.output_ready", {"english_srt_path": job.english_srt_path, "vietnamese_srt_path": job.vietnamese_srt_path, "bilingual_srt_path": job.bilingual_srt_path}, job_id=job.id))
        except _JobPaused:
            pass
        except _JobStopped:
            pass
        except _JobCanceled:
            self._mark_canceled(job)
        except AudioExtractionCanceled:
            if control.is_shutdown_requested():
                self._mark_retry_required(job, _shutdown_retry_message("extracting_audio"))
            else:
                self._mark_canceled(job)
        except TranscriptionCanceled:
            if control.is_shutdown_requested():
                self._mark_retry_required(job, _shutdown_retry_message("transcribing"))
            else:
                self._mark_canceled(job)
        except Exception as exc:
            logger.exception("Worker job %s failed while status=%s.", job.id, job.status.value)
            if job.status is not JobStatus.CANCELED:
                if isinstance(exc, GpuOutOfMemoryError):
                    error_code = "gpu_out_of_memory"
                elif isinstance(exc, GpuUnavailableError):
                    error_code = "gpu"
                else:
                    error_code = "stt"
                info = user_safe_error(error_code, str(exc))
                job.status = JobStatus.FAILED
                job.error_code = info.code
                job.error_message = info.message
                job.completed_at = utc_now_iso()
                self._save(job)
                self.emit(error_event(job.id, info.code, info.message))
        finally:
            self.current_job_id = None
            self._cleanup_job_temp(job, working_files=job_working_files)
            self.emit(WorkerEvent("job.finished", {"status": job.status.value}, job_id=job.id))
        return job

    def translate_lines(self, job: VideoJob, lines: list[SubtitleLine], provider_id: str, credential_alias: str, control: WorkerControlToken | None = None) -> list[SubtitleLine]:
        if not self.translation_registry:
            raise RuntimeError("Chưa cấu hình bộ dịch")
        provider = self.translation_registry.get(provider_id)
        request = TranslationBatchRequest(job_id=job.id, provider_id=provider_id, source_language="en", target_language="vi", credential_alias=credential_alias, items=[TranslationItem(l.sequence_number, l.start_ms, l.end_ms, l.source_text) for l in lines])
        result = provider.translate_batch(request, progress=lambda p, s, d=None: self.emit(progress_event(job.id, p, s, d)), cancel=control)
        validate_translation_shape(request, result)
        by_seq = {item.sequence_number: item.translated_text for item in result.items}
        for line in lines:
            line.translated_text = by_seq[line.sequence_number]
        return lines

    def request_pause(self, job: VideoJob) -> WorkerEvent:
        if job.status is JobStatus.QUEUED:
            job.status = JobStatus.PAUSED
            job.pause_requested = False
            self._save(job)
            return WorkerEvent("job.status_changed", {"old_status": "queued", "new_status": "paused", "message": "Đã tạm dừng"}, job_id=job.id)
        job.pause_requested = True
        job.progress_label = "Đang chờ điểm dừng an toàn để tạm dừng"
        self._save(job)
        event = pause_pending_event(job.id, job.status.value)
        self.emit(event)
        return event

    def resume_active(self, job: VideoJob) -> None:
        if self.current_job_id != job.id or job.status is not JobStatus.PAUSED:
            raise ValueError("Job không tạm dừng trong worker hiện tại")
        job.pause_requested = False
        job.progress_label = "Đang tiếp tục xử lý"
        self._save(job)

    def cancel(self, job: VideoJob) -> None:
        if job.status is JobStatus.COMPLETED:
            return
        job.cancel_requested = True
        job.pause_requested = False
        job.status = JobStatus.CANCELED
        job.progress_label = "Đã yêu cầu hủy"
        self._save(job)

    def retry(self, job: VideoJob) -> None:
        require_transition(job.status, JobStatus.QUEUED)
        job.status = JobStatus.QUEUED
        job.pause_requested = False
        job.cancel_requested = False
        job.retry_required = False
        job.error_code = None
        job.error_message = None
        job.progress_percent = 0
        job.progress_label = "Chờ xử lý"
        job.started_at = None
        job.completed_at = None
        self._save(job)

    def _prepare_audio(self, job: VideoJob, cancel=None, working_files: WorkingFileManager | None = None) -> str:
        if not self.audio_extractor:
            fallback = str(Path(job.source_path).with_suffix(".wav"))
            job.audio_temp_path = fallback if Path(fallback).exists() else None
            self._save(job)
            return fallback
        manager = working_files or self.working_files
        audio_target = manager.audio_path_for(job.id, job.source_path)
        audio_target.parent.mkdir(parents=True, exist_ok=True)
        job.audio_temp_path = str(audio_target)
        self._save(job)
        extract = self.audio_extractor.extract
        try:
            supports_cancel = "cancel" in inspect.signature(extract).parameters
        except (TypeError, ValueError):
            supports_cancel = False
        if supports_cancel:
            extracted = self.audio_extractor.extract(job.source_path, audio_target, cancel=cancel)
        else:
            extracted = self.audio_extractor.extract(job.source_path, audio_target)
        job.audio_temp_path = str(extracted)
        self._save(job)
        return str(extracted)

    def _ensure_model_available(self, job: VideoJob, control=None, output_dir: str | Path | None = None) -> None:
        if not self.model_catalog or not self.model_downloader_factory:
            return
        model = self.model_catalog.resolve_or_default(job.selected_model_id)
        local_path = getattr(model, "local_path", None)
        if local_path and Path(local_path).exists():
            return
        job.status = JobStatus.DOWNLOADING_MODEL
        self._save(job)
        cache_dir = self.model_cache_dir or Path(output_dir or self.output_dir) / "model_cache"
        worker = self.model_downloader_factory(model.id, cache_dir)
        run = worker.run
        progress = lambda state: self.emit(WorkerEvent("model.download_progress", {"model_id": state.model_id, "percent": state.percent, "speed_bytes_per_sec": state.speed_bytes_per_sec, "bytes_remaining": state.bytes_remaining}, job_id=job.id))
        try:
            supports_control = "control" in inspect.signature(run).parameters
        except (TypeError, ValueError):
            supports_control = False
        if supports_control:
            run(progress=progress, control=control)
        else:
            run(progress=progress)

    def _checkpoint(self, job: VideoJob, control: WorkerControlToken, step: str) -> None:
        if control.is_shutdown_requested():
            self._mark_retry_required(job, _shutdown_retry_message(step))
            raise _JobStopped()
        if control.is_cancel_requested() or job.cancel_requested or job.status is JobStatus.CANCELED:
            self._mark_canceled(job)
            raise _JobCanceled()
        if control.is_pause_requested() or job.pause_requested:
            job.status = JobStatus.PAUSED
            job.pause_requested = False
            job.progress_label = f"Đã tạm dừng sau bước {_step_label(step)}"
            control.clear_pause()
            self._save(job)
            raise _JobPaused()

    def _mark_canceled(self, job: VideoJob) -> None:
        job.status = JobStatus.CANCELED
        job.retry_required = False
        job.cancel_requested = False
        job.pause_requested = False
        job.progress_label = "Đã hủy"
        job.completed_at = utc_now_iso()
        self._save(job)

    def _mark_retry_required(self, job: VideoJob, label: str) -> None:
        job.status = JobStatus.RETRY_REQUIRED
        job.retry_required = True
        job.cancel_requested = False
        job.pause_requested = False
        job.progress_label = label
        self._save(job)
        logger.info("Job %s stopped and marked retry_required: %s", job.id, label)

    def _cleanup_job_temp(self, job: VideoJob, working_files: WorkingFileManager | None = None) -> None:
        manager = working_files or self.working_files
        had_temp = bool(job.audio_temp_path) or manager.job_dir(job.id).exists()
        if not had_temp:
            return
        try:
            removed_bytes = manager.cleanup_job(job.id)
            if removed_bytes:
                logger.info("Cleaned %s bytes of temporary working files for job %s.", removed_bytes, job.id)
        except Exception:
            logger.exception("Could not clean temporary working files for job %s.", job.id)
            return
        if job.audio_temp_path:
            job.audio_temp_path = None
            self._save(job)

    def _save(self, job: VideoJob) -> None:
        if self.job_repository:
            self.job_repository.save(job)
