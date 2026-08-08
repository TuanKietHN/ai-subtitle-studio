"""Main window and UI controller for AI Subtitle Studio."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ai_subtitle_studio.config.app_settings import AppSettingsStore
from ai_subtitle_studio.config.gpu_profiles import GpuProfileError, configured_execution_profile, resolve_execution_profile
from ai_subtitle_studio.config.system_info import SystemInfoProvider
from ai_subtitle_studio.domain.entities import AppSettings, SubtitleLine, VideoJob
from ai_subtitle_studio.domain.job_state import ACTIVE_STATUSES, JobStatus
from ai_subtitle_studio.io.srt_writer import SRTWriter, default_output_paths
from ai_subtitle_studio.io.subtitle_edit import open_with_subtitle_edit
from ai_subtitle_studio.translation.base import TranslationError
from ai_subtitle_studio.ui.about_dialog import AboutController, SystemInfoDialog
from ai_subtitle_studio.ui.settings_dialog import SettingsController, SettingsDialog
from ai_subtitle_studio.ui.subtitle_table import SubtitleTableModel
from ai_subtitle_studio.workers.job_runner import VideoQueueService
from ai_subtitle_studio.workers.worker_events import WorkerControlToken

try:
    from PySide6.QtCore import QObject, Qt, QThread, QTimer, QUrl, Signal, Slot  # type: ignore
    from PySide6.QtGui import QDesktopServices  # type: ignore
    from PySide6.QtWidgets import (  # type: ignore
        QAbstractItemView, QComboBox, QDialog, QFileDialog, QFormLayout, QGroupBox,
        QHBoxLayout, QHeaderView, QLabel, QMainWindow, QMessageBox, QPushButton,
        QProgressBar, QSplitter, QStyle, QTableWidget, QTableWidgetItem,
        QVBoxLayout, QWidget,
    )
    QT_AVAILABLE = True
except Exception:  # pragma: no cover
    QMainWindow = object  # type: ignore
    QT_AVAILABLE = False

logger = logging.getLogger(__name__)

PROVIDER_LABELS = {
    "google_cloud_v3": "Google Cloud Translation API v3",
    "deepseek_chat": "DeepSeek",
}


PROGRESS_STEP_LABELS = {
    "extracting_audio": "Đang trích audio",
    "waiting_for_gpu": "Đang chờ GPU",
    "loading_model": "Đang tải model",
    "transcribing": "Đang nhận dạng",
    "aligning": "Đang căn timestamp",
    "aligned": "Đã căn timestamp",
    "translated": "Đã dịch",
    "exporting": "Đang xuất phụ đề",
}

STATUS_LABELS = {
    JobStatus.QUEUED: "Chờ xử lý",
    JobStatus.PAUSED: "Tạm dừng",
    JobStatus.WAITING_FOR_MODEL: "Chờ model",
    JobStatus.DOWNLOADING_MODEL: "Đang tải model",
    JobStatus.EXTRACTING_AUDIO: "Trích audio",
    JobStatus.WAITING_FOR_GPU: "Chờ GPU",
    JobStatus.TRANSCRIBING: "Nhận dạng",
    JobStatus.ALIGNING: "Căn timestamp",
    JobStatus.TRANSLATING: "Đang dịch",
    JobStatus.READY_FOR_EDIT: "Sẵn sàng sửa",
    JobStatus.EXPORTING: "Đang xuất",
    JobStatus.COMPLETED: "Hoàn tất",
    JobStatus.FAILED: "Lỗi",
    JobStatus.CANCELED: "Đã hủy",
    JobStatus.RETRY_REQUIRED: "Cần chạy lại",
}


@dataclass(frozen=True, slots=True)
class QueueToolbarState:
    start: bool = False
    pause: bool = False
    resume: bool = False
    cancel: bool = False
    retry: bool = False
    remove: bool = False


def queue_toolbar_state(
    selected_jobs: Iterable[VideoJob],
    *,
    queue_running: bool,
    has_pending_jobs: bool,
    running_job_id: str | None,
) -> QueueToolbarState:
    """Return one deterministic toolbar state for the complete selection."""
    selected = list(selected_jobs)
    start = not queue_running and has_pending_jobs
    if len(selected) != 1:
        return QueueToolbarState(start=start, remove=bool(selected))

    job = selected[0]
    is_current_worker_job = job.id == running_job_id
    is_active = job.status in ACTIVE_STATUSES and is_current_worker_job
    is_active_pause = job.status is JobStatus.PAUSED and is_current_worker_job
    return QueueToolbarState(
        start=start,
        pause=(job.status is JobStatus.QUEUED or is_active) and not job.pause_requested,
        resume=job.status is JobStatus.PAUSED,
        cancel=is_active or is_active_pause,
        retry=job.status in {JobStatus.FAILED, JobStatus.CANCELED},
        remove=True,
    )


class MainWindowController:
    def __init__(
        self,
        model_catalog,
        job_runner=None,
        queue_service: VideoQueueService | None = None,
        settings_store: AppSettingsStore | None = None,
        credential_store=None,
        translation_registry=None,
        system_info_provider: SystemInfoProvider | None = None,
        subtitle_edit_launcher=open_with_subtitle_edit,
    ) -> None:
        self.model_catalog = model_catalog
        self.job_runner = job_runner
        self.queue_service = queue_service or VideoQueueService()
        self.settings_store = settings_store
        self.credential_store = credential_store
        self.translation_registry = translation_registry or getattr(job_runner, "translation_registry", None)
        self.system_info_provider = system_info_provider
        self.subtitle_edit_launcher = subtitle_edit_launcher
        self.settings = settings_store.load() if settings_store else AppSettings()
        self.selected_model_id = self._resolve_model_id(self.settings.last_model_id)
        self.translation_provider_id: str | None = self.settings.last_translation_provider_id
        if self.translation_provider_id not in self.provider_options():
            self.translation_provider_id = self.provider_options()[0] if self.provider_options() else None
        self.subtitle_lines: list[SubtitleLine] = []
        self._subtitle_job_id: str | None = None
        self.last_errors: list[str] = []
        self._event_cursor = 0
        self._load_persisted_jobs()

    def model_options(self) -> list[str]:
        return [model.id for model in self.model_catalog.enabled_models()]

    def model_items(self):
        return list(self.model_catalog.enabled_models())

    def select_model(self, model_id: str) -> None:
        self.selected_model_id = self._resolve_model_id(model_id)
        self._save_last_choices()

    def model_compatibility_warning(self, model_id: str) -> str | None:
        if not self.system_info_provider or not self.model_catalog:
            return None
        settings = self.settings_store.load() if self.settings_store else self.settings
        snapshot = self.system_info_provider.collect(selected_gpu_id=settings.selected_gpu_id)
        gpu = next(
            (item for item in snapshot.detected_gpus if item.gpu_id == settings.selected_gpu_id),
            snapshot.detected_gpus[0] if snapshot.detected_gpus else None,
        )
        if gpu is None or not gpu.total_vram_bytes:
            return None
        model = self.model_catalog.get(model_id)
        available_gib = gpu.total_vram_bytes / float(1024**3)
        if model.recommended_vram_gb and model.recommended_vram_gb > available_gib:
            return (
                f"{model.display_name} khuyến nghị {model.recommended_vram_gb:g} GiB VRAM, "
                f"nhưng GPU đang chọn có {available_gib:.1f} GiB. Model này có thể gây CUDA OOM."
            )
        return None

    def add_files(self, paths) -> object:
        result = self.queue_service.add_files(paths, selected_model_id=self.selected_model_id)
        for job in result.added:
            job.translation_provider_id = self.translation_provider_id
            self._save_job(job)
        return result
    def remove_jobs(self, job_ids: Iterable[str], allow_running: bool = False) -> list[str]:
        selected = set(job_ids)
        running_job_id = self.running_job_id()
        blocked_running: list[str] = []
        remaining: list[VideoJob] = []
        for job in self.queue_service.jobs:
            if job.id not in selected:
                remaining.append(job)
                continue
            if job.id == running_job_id and not allow_running:
                if self.job_runner:
                    self.job_runner.cancel(job)
                blocked_running.append(job.id)
                remaining.append(job)
                continue
            if self.job_runner and job.status not in {JobStatus.COMPLETED, JobStatus.CANCELED}:
                try:
                    self.job_runner.cancel(job)
                except Exception:
                    pass
            repo = getattr(self.job_runner, "job_repository", None)
            if repo and hasattr(repo, "delete"):
                repo.delete(job.id)
            subtitle_repo = getattr(self.job_runner, "subtitle_repository", None)
            if subtitle_repo and hasattr(subtitle_repo, "delete_for_job"):
                subtitle_repo.delete_for_job(job.id)
        self.queue_service.jobs = remaining
        self.queue_service._fingerprints = {job.source_fingerprint for job in remaining if job.source_fingerprint}
        return blocked_running

    def start_queue(self, control: WorkerControlToken | None = None):
        if not self.job_runner:
            return []
        return self.job_runner.process_queue(self.queue_service.pending_jobs(), control=control)

    def select_translation_provider(self, provider_id: str) -> None:
        self.translation_provider_id = provider_id or None
        for job in self.queue_service.jobs:
            if job.status in {JobStatus.QUEUED, JobStatus.PAUSED, JobStatus.RETRY_REQUIRED}:
                job.translation_provider_id = self.translation_provider_id
        self._save_last_choices()

    def load_subtitle_lines(self, lines) -> None:
        self.subtitle_lines = list(lines)

    def load_subtitles_for_job(self, job: VideoJob | None) -> list[SubtitleLine]:
        if job is None:
            self.subtitle_lines = []
            self._subtitle_job_id = None
            return []
        if self._subtitle_job_id == job.id:
            return self.subtitle_lines
        repo = getattr(self.job_runner, "subtitle_repository", None)
        self.subtitle_lines = repo.list_for_job(job.id) if repo else []
        self._subtitle_job_id = job.id
        return self.subtitle_lines

    def update_subtitle_line(self, job: VideoJob | None, sequence_number: int, source_text: str, translated_text: str) -> SubtitleLine | None:
        if job is None:
            return None
        model = SubtitleTableModel(self.subtitle_lines)
        try:
            line = model.edit_source(sequence_number, source_text)
            line = model.edit_translation(sequence_number, translated_text)
        except KeyError:
            return None
        repo = getattr(self.job_runner, "subtitle_repository", None)
        if repo:
            repo.replace_for_job(job.id, self.subtitle_lines)
        return line

    def translate_loaded_subtitles(self, job, credential_alias: str):
        if not self.job_runner:
            raise RuntimeError("Chưa cấu hình bộ xử lý job")
        if not self.translation_provider_id:
            raise RuntimeError("Chưa chọn provider dịch")
        try:
            self.subtitle_lines = self.job_runner.translate_lines(job, self.subtitle_lines, self.translation_provider_id, credential_alias)
        except TranslationError as exc:
            logger.exception("Translation failed for job %s.", job.id)
            raise RuntimeError("Không thể dịch phụ đề. Kiểm tra API key, kết nối mạng và log kỹ thuật.") from exc
        repo = getattr(self.job_runner, "subtitle_repository", None)
        if repo:
            repo.replace_for_job(job.id, self.subtitle_lines)
        return self.subtitle_lines

    def export_subtitles(self, job: VideoJob, lines: list[SubtitleLine] | None = None) -> dict[str, Path]:
        lines = list(lines if lines is not None else self.subtitle_lines)
        if not lines:
            raise RuntimeError("Chưa tải phụ đề cho job đang chọn")
        writer = getattr(self.job_runner, "srt_writer", None) or SRTWriter()
        output_dir = getattr(self.job_runner, "output_dir", Path.cwd())
        paths = default_output_paths(job.source_path, output_dir)
        written: dict[str, Path] = {}
        written["english"] = writer.write_english(lines, paths["english"])
        job.english_srt_path = str(written["english"])
        if all((line.translated_text or "").strip() for line in lines):
            written["vietnamese"] = writer.write_vietnamese(lines, paths["vietnamese"])
            written["bilingual"] = writer.write_bilingual(lines, paths["bilingual"])
            job.vietnamese_srt_path = str(written["vietnamese"])
            job.bilingual_srt_path = str(written["bilingual"])
        self._save_job(job)
        return written

    def pause_job(self, job):
        if not self.job_runner:
            raise RuntimeError("Chưa cấu hình bộ xử lý job")
        return self.job_runner.request_pause(job)

    def cancel_job(self, job):
        if not self.job_runner:
            raise RuntimeError("Chưa cấu hình bộ xử lý job")
        return self.job_runner.cancel(job)

    def retry_job(self, job):
        if not self.job_runner:
            raise RuntimeError("Chưa cấu hình bộ xử lý job")
        return self.job_runner.retry(job)

    def resume_active_job(self, job):
        if not self.job_runner:
            raise RuntimeError("Chưa cấu hình bộ xử lý job")
        return self.job_runner.resume_active(job)

    def open_output_path(self, job) -> str | None:
        return job.bilingual_srt_path or job.vietnamese_srt_path or job.english_srt_path

    def open_selected_in_subtitle_edit(self, job: VideoJob) -> None:
        settings = self.settings_store.load() if self.settings_store else self.settings
        if not settings.subtitle_edit_path:
            raise RuntimeError("Chưa cấu hình đường dẫn Subtitle Edit")
        subtitle_path = self.open_output_path(job)
        if not subtitle_path:
            raise RuntimeError("Job đang chọn chưa có file phụ đề đầu ra")
        self.subtitle_edit_launcher(settings.subtitle_edit_path, subtitle_path)

    def settings_controller(self) -> SettingsController:
        store = self.settings_store or AppSettingsStore()
        working_dir = getattr(self.job_runner, "working_dir", None)
        return SettingsController(
            store,
            credential_store=self.credential_store,
            working_dir=working_dir,
            protected_job_ids=lambda: {job_id} if (job_id := self.running_job_id()) else set(),
            system_info_provider=self.system_info_provider,
        )

    def apply_settings(self, settings: AppSettings) -> None:
        self.settings = settings
        if self.settings_store:
            self.settings_store.save(settings)
        if settings.last_model_id:
            self.selected_model_id = self._resolve_model_id(settings.last_model_id)
        if settings.last_translation_provider_id:
            self.translation_provider_id = settings.last_translation_provider_id
        if self.job_runner and settings.default_output_dir:
            if hasattr(self.job_runner, "set_output_dir"):
                self.job_runner.set_output_dir(Path(settings.default_output_dir))
            else:
                self.job_runner.output_dir = Path(settings.default_output_dir)
        audio_extractor = getattr(self.job_runner, "audio_extractor", None)
        if audio_extractor and settings.ffmpeg_path:
            audio_extractor.ffmpeg_path = settings.ffmpeg_path
        if self.job_runner and hasattr(self.job_runner, "set_runtime_settings"):
            try:
                configured_profile = configured_execution_profile(
                    requested_model_id=settings.last_model_id,
                    requested_profile_id=settings.last_compute_profile_id,
                )
            except GpuProfileError as exc:
                logger.warning("Invalid persisted GPU profile after settings update: %s", exc)
                configured_profile = configured_execution_profile(requested_model_id=settings.last_model_id)
            compute_type = configured_profile.compute_type
            batch_size = configured_profile.batch_size
            profile_id = configured_profile.profile_id
            if self.system_info_provider:
                snapshot = self.system_info_provider.collect(selected_gpu_id=settings.selected_gpu_id)
                ready_gpus = [gpu for gpu in snapshot.detected_gpus if gpu.torch_cuda_ready]
                gpu = next(
                    (item for item in ready_gpus if item.gpu_id == settings.selected_gpu_id),
                    ready_gpus[0] if ready_gpus else None,
                )
                if gpu is not None:
                    try:
                        profile = resolve_execution_profile(
                            gpu,
                            requested_model_id=settings.last_model_id,
                            requested_profile_id=settings.last_compute_profile_id,
                        )
                        compute_type = profile.compute_type
                        batch_size = profile.batch_size
                        profile_id = profile.profile_id
                    except GpuProfileError as exc:
                        logger.warning("GPU profile remains unavailable after settings update: %s", exc)
            self.job_runner.set_runtime_settings(
                model_cache_dir=settings.model_cache_dir,
                selected_gpu_id=settings.selected_gpu_id,
                compute_type=compute_type,
                batch_size=batch_size,
                execution_profile_id=profile_id,
            )

    def logs_directory(self) -> str | None:
        provider = self.system_info_provider
        return getattr(provider, "log_dir", None) if provider else None

    def provider_options(self) -> list[str]:
        if self.translation_registry:
            ids = self.translation_registry.ids()
            if ids:
                return ids
        return ["google_cloud_v3", "deepseek_chat"]

    def provider_label(self, provider_id: str) -> str:
        return PROVIDER_LABELS.get(provider_id, provider_id)

    def collect_system_info(self):
        if not self.system_info_provider:
            return None
        settings = self.settings_store.load() if self.settings_store else self.settings
        return AboutController(self.system_info_provider).render_info(
            selected_model_id=self.selected_model_id,
            model_cache_dir=settings.model_cache_dir,
            selected_gpu_id=settings.selected_gpu_id,
            effective_profile_id=getattr(self.job_runner, "execution_profile_id", None),
            effective_compute_type=getattr(self.job_runner, "compute_type", None),
            effective_batch_size=getattr(self.job_runner, "batch_size", None),
        )

    def drain_worker_events(self):
        runner = self.job_runner
        events = getattr(runner, "events", []) if runner else []
        new_events = events[self._event_cursor :]
        self._event_cursor = len(events)
        for event in new_events:
            job = self.get_job(event.job_id)
            if job is None:
                continue
            if event.event_type == "job.progress":
                job.progress_percent = float(event.payload.get("percent", job.progress_percent))
                job.progress_label = self._progress_label_for_event(event, job.progress_label)
            elif event.event_type == "job.error":
                job.status = JobStatus.FAILED
                job.error_code = str(event.payload.get("error_code") or "error")
                job.error_message = str(event.payload.get("message") or "Job thất bại")
            elif event.event_type == "job.output_ready":
                for key in ("english_srt_path", "vietnamese_srt_path", "bilingual_srt_path"):
                    value = event.payload.get(key)
                    if value:
                        setattr(job, key, value)
        return new_events

    def get_job(self, job_id: str | None) -> VideoJob | None:
        if not job_id:
            return None
        for job in self.queue_service.jobs:
            if job.id == job_id:
                return job
        return None

    def _progress_label_for_event(self, event, current_label: str) -> str:
        step = str(event.payload.get("step") or "")
        detail = event.payload.get("detail")
        step_label = PROGRESS_STEP_LABELS.get(step, "Đang xử lý" if step else "")
        if detail:
            detail_text = str(detail)
            if step == "loading_model":
                return f"{step_label}: {detail_text}"
            if step == "transcribing" and detail_text.startswith("Nhận dạng"):
                return detail_text
            if step == "translated":
                provider_label = PROVIDER_LABELS.get(detail_text, detail_text)
                return f"{step_label}: {provider_label}"
            if step in PROGRESS_STEP_LABELS:
                return f"{step_label}: {detail_text}" if step_label else detail_text
            return step_label or current_label
        return step_label or current_label

    def running_job_id(self) -> str | None:
        return getattr(self.job_runner, "current_job_id", None)

    def _resolve_model_id(self, model_id: str | None) -> str:
        if not self.model_catalog:
            return model_id or "large-v3"
        return self.model_catalog.resolve_or_default(model_id).id

    def _save_job(self, job: VideoJob) -> None:
        repo = getattr(self.job_runner, "job_repository", None)
        if repo:
            repo.save(job)

    def _save_last_choices(self) -> None:
        if not self.settings_store:
            return
        settings = self.settings_store.load()
        settings.last_model_id = self.selected_model_id
        settings.last_translation_provider_id = self.translation_provider_id
        self.settings_store.save(settings)
        self.settings = settings

    def _load_persisted_jobs(self) -> None:
        repo = getattr(self.job_runner, "job_repository", None)
        if not repo:
            return
        recovered = repo.recover_active_jobs() if hasattr(repo, "recover_active_jobs") else 0
        if recovered:
            logger.info("Đã khôi phục %s job đang chạy sang retry_required. Người dùng cần bấm Bắt đầu xử lý để chạy lại từ đầu.", recovered)
        working_files = getattr(self.job_runner, "working_files", None)
        working_cleanup_succeeded = False
        if working_files is not None:
            try:
                removed_bytes = working_files.cleanup_all()
                working_cleanup_succeeded = True
                if removed_bytes:
                    logger.info("Đã dọn %s byte file tạm còn lại từ lần chạy trước.", removed_bytes)
            except Exception:
                logger.exception("Không thể dọn file tạm còn lại từ lần chạy trước.")
        jobs = repo.list_jobs()
        for job in jobs:
            if working_cleanup_succeeded and job.audio_temp_path:
                job.audio_temp_path = None
                repo.save(job)
        if jobs:
            self.queue_service.jobs = jobs
            self.queue_service._fingerprints = {job.source_fingerprint for job in jobs if job.source_fingerprint}

if QT_AVAILABLE:
    class _QueueWorker(QObject):
        finished = Signal(object)
        failed = Signal(str)

        def __init__(self, controller: MainWindowController, control: WorkerControlToken) -> None:
            super().__init__()
            self.controller = controller
            self.control = control

        @Slot()
        def run(self) -> None:
            try:
                self.finished.emit(self.controller.start_queue(self.control))
            except Exception as exc:  # pragma: no cover
                self.failed.emit(str(exc))

class MainWindow(QMainWindow):
    def __init__(self, controller: MainWindowController | None = None) -> None:
        try:
            super().__init__()
        except Exception:  # pragma: no cover
            pass
        self.controller = controller
        if not QT_AVAILABLE:
            return
        if controller is None:
            raise ValueError("MainWindow requires a MainWindowController")
        self._jobs_by_id: dict[str, VideoJob] = {}
        self._current_job_id: str | None = None
        self._loading_subtitles = False
        self._queue_thread: QThread | None = None
        self._queue_worker: _QueueWorker | None = None
        self._queue_control: WorkerControlToken | None = None
        self._restart_queue_when_idle = False
        self._closing = False
        self._event_timer = QTimer(self)
        self._event_timer.setInterval(500)
        self._event_timer.timeout.connect(self._refresh_from_worker_events)
        self._build_ui()
        self._refresh_models()
        self._refresh_providers()
        self.refresh_queue()
        self.refresh_system_info()
    def _build_ui(self) -> None:
        self.setWindowTitle("AI Subtitle Studio")
        self.resize(1200, 760)
        self.setAcceptDrops(True)
        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)
        self.setCentralWidget(central)

        controls = QHBoxLayout()
        self.add_button = QPushButton("Thêm video")
        self.add_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        self.add_button.clicked.connect(self._pick_videos)
        controls.addWidget(self.add_button)
        self.remove_button = QPushButton("Xóa")
        self.remove_button.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        self.remove_button.clicked.connect(self._remove_selected_jobs)
        controls.addWidget(self.remove_button)
        self.start_button = QPushButton("Bắt đầu xử lý")
        self.start_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.start_button.clicked.connect(self._start_queue)
        controls.addWidget(self.start_button)
        self.pause_button = QPushButton("Tạm dừng")
        self.pause_button.setToolTip(
            "Tạm dừng tại điểm kiểm tra an toàn gần nhất; tác vụ GPU đang chạy sẽ hoàn tất trước khi dừng."
        )
        self.pause_button.clicked.connect(self._pause_selected_job)
        controls.addWidget(self.pause_button)
        self.resume_button = QPushButton("Tiếp tục")
        self.resume_button.setToolTip("Tiếp tục job đang tạm dừng từ checkpoint hiện tại.")
        self.resume_button.clicked.connect(self._resume_selected_job)
        controls.addWidget(self.resume_button)
        self.cancel_button = QPushButton("Hủy")
        self.cancel_button.clicked.connect(self._cancel_selected_job)
        controls.addWidget(self.cancel_button)
        self.retry_button = QPushButton("Thử lại")
        self.retry_button.clicked.connect(self._retry_selected_job)
        controls.addWidget(self.retry_button)
        controls.addSpacing(12)
        controls.addWidget(QLabel("Model"))
        self.model_combo = QComboBox()
        self.model_combo.currentIndexChanged.connect(self._model_changed)
        controls.addWidget(self.model_combo, 1)
        controls.addWidget(QLabel("Provider dịch"))
        self.provider_combo = QComboBox()
        self.provider_combo.currentIndexChanged.connect(self._provider_changed)
        controls.addWidget(self.provider_combo, 1)
        self.settings_button = QPushButton("Cài đặt")
        self.settings_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.settings_button.clicked.connect(self._open_settings)
        controls.addWidget(self.settings_button)
        self.about_button = QPushButton("Thông tin hệ thống")
        self.about_button.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation))
        self.about_button.clicked.connect(self._open_system_info_dialog)
        controls.addWidget(self.about_button)
        self.logs_button = QPushButton("Mở log")
        self.logs_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.logs_button.clicked.connect(self._open_logs_folder)
        controls.addWidget(self.logs_button)
        root.addLayout(controls)

        self.main_splitter = QSplitter(Qt.Vertical)
        root.addWidget(self.main_splitter, 1)
        queue_box = QGroupBox("Hàng đợi video")
        queue_layout = QVBoxLayout(queue_box)
        self.queue_table = QTableWidget(0, 4)
        self.queue_table.setHorizontalHeaderLabels(["Tên file", "Thời lượng", "Trạng thái", "Tiến trình %"])
        self.queue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.queue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.queue_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.queue_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.queue_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.queue_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.queue_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.queue_table.itemSelectionChanged.connect(self._queue_selection_changed)
        queue_layout.addWidget(self.queue_table)
        self.main_splitter.addWidget(queue_box)

        lower = QSplitter(Qt.Horizontal)
        subtitle_box = QGroupBox("Chi tiết phụ đề")
        subtitle_layout = QVBoxLayout(subtitle_box)
        self.subtitle_table = QTableWidget(0, 3)
        self.subtitle_table.setHorizontalHeaderLabels(["Timestamp", "Text gốc", "Text dịch"])
        self.subtitle_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.subtitle_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.subtitle_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.subtitle_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.subtitle_table.itemChanged.connect(self._subtitle_item_changed)
        subtitle_layout.addWidget(self.subtitle_table, 1)
        subtitle_actions = QHBoxLayout()
        self.open_subtitle_edit_button = QPushButton("Mở bằng Subtitle Edit")
        self.open_subtitle_edit_button.clicked.connect(self._open_with_subtitle_edit)
        subtitle_actions.addWidget(self.open_subtitle_edit_button)
        self.export_button = QPushButton("Xuất SRT")
        self.export_button.clicked.connect(self._export_srt)
        subtitle_actions.addWidget(self.export_button)
        self.open_folder_button = QPushButton("Mở thư mục chứa file")
        self.open_folder_button.clicked.connect(self._open_output_folder)
        subtitle_actions.addWidget(self.open_folder_button)
        subtitle_actions.addStretch(1)
        subtitle_layout.addLayout(subtitle_actions)
        lower.addWidget(subtitle_box)

        system_box = QGroupBox("Thông tin hệ thống")
        system_layout = QFormLayout(system_box)
        self.info_labels = {
            "app_version": QLabel("-"), "whisperx_version": QLabel("-"),
            "faster_whisper_version": QLabel("-"), "cuda": QLabel("-"),
            "gpu": QLabel("-"), "selected_model": QLabel("-"),
            "downloaded_size": QLabel("-"), "ffmpeg": QLabel("-"),
            "data_dir": QLabel("-"), "log_dir": QLabel("-"),
        }
        system_layout.addRow("App", self.info_labels["app_version"])
        system_layout.addRow("WhisperX", self.info_labels["whisperx_version"])
        system_layout.addRow("faster-whisper", self.info_labels["faster_whisper_version"])
        system_layout.addRow("CUDA", self.info_labels["cuda"])
        system_layout.addRow("GPU/Driver", self.info_labels["gpu"])
        system_layout.addRow("Model đang chọn", self.info_labels["selected_model"])
        system_layout.addRow("Dung lượng model", self.info_labels["downloaded_size"])
        system_layout.addRow("FFmpeg", self.info_labels["ffmpeg"])
        system_layout.addRow("Dữ liệu", self.info_labels["data_dir"])
        system_layout.addRow("Log", self.info_labels["log_dir"])
        refresh_info = QPushButton("Cập nhật")
        refresh_info.clicked.connect(self.refresh_system_info)
        system_layout.addRow(refresh_info)
        lower.addWidget(system_box)
        lower.setSizes([850, 300])
        self.main_splitter.addWidget(lower)
        self.main_splitter.setSizes([300, 430])
        self.statusBar().showMessage("Sẵn sàng")
    def _refresh_models(self) -> None:
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for model in self.controller.model_items():
            label = f"{model.display_name} ({model.id})" if model.display_name != model.id else model.id
            self.model_combo.addItem(label, model.id)
        index = self.model_combo.findData(self.controller.selected_model_id)
        self.model_combo.setCurrentIndex(max(index, 0))
        self.model_combo.blockSignals(False)

    def _refresh_providers(self) -> None:
        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()
        for provider_id in self.controller.provider_options():
            self.provider_combo.addItem(self.controller.provider_label(provider_id), provider_id)
        index = self.provider_combo.findData(self.controller.translation_provider_id)
        self.provider_combo.setCurrentIndex(max(index, 0))
        self.provider_combo.blockSignals(False)
        current = self.provider_combo.currentData()
        if current:
            self.controller.select_translation_provider(str(current))

    def refresh_queue(self) -> None:
        selected_id = self._current_job_id
        self._jobs_by_id = {job.id: job for job in self.controller.queue_service.jobs}
        self.queue_table.blockSignals(True)
        self.queue_table.setRowCount(len(self.controller.queue_service.jobs))
        for row, job in enumerate(self.controller.queue_service.jobs):
            name_item = QTableWidgetItem(job.display_name)
            name_item.setData(Qt.UserRole, job.id)
            if job.error_message:
                name_item.setToolTip(job.error_message)
            self.queue_table.setItem(row, 0, name_item)
            self.queue_table.setItem(row, 1, QTableWidgetItem(self._duration_text(job)))
            status_item = QTableWidgetItem(self._status_text(job))
            tooltip = self._status_tooltip(job)
            if tooltip:
                status_item.setToolTip(tooltip)
            self.queue_table.setItem(row, 2, status_item)
            progress = QProgressBar()
            progress.setRange(0, 100)
            progress.setValue(max(0, min(100, int(job.progress_percent))))
            progress.setFormat("%p%")
            self.queue_table.setCellWidget(row, 3, progress)
        self.queue_table.blockSignals(False)
        if selected_id and selected_id in self._jobs_by_id:
            self._select_job_id(selected_id)
        elif self.controller.queue_service.jobs:
            self.queue_table.selectRow(0)
        else:
            self._current_job_id = None
            self._load_subtitle_table([])
        self._update_action_state()

    def refresh_system_info(self) -> None:
        info = self.controller.collect_system_info()
        if not info:
            self.info_labels["selected_model"].setText(self.controller.selected_model_id)
            return
        snapshot = info["snapshot"]
        self.info_labels["app_version"].setText(snapshot.app_version)
        self.info_labels["whisperx_version"].setText(snapshot.whisperx_version)
        self.info_labels["faster_whisper_version"].setText(snapshot.faster_whisper_version)
        self.info_labels["cuda"].setText(snapshot.torch_cuda_version)
        gpu_text = ", ".join(
            f"{gpu.gpu_id}: {gpu.name} ({gpu.total_vram_bytes / float(1024**3):.1f} GiB, {gpu.driver_version})"
            for gpu in snapshot.detected_gpus
        )
        self.info_labels["gpu"].setText(gpu_text or f"không khả dụng / driver {snapshot.gpu_driver_version}")
        self.info_labels["selected_model"].setText(snapshot.selected_model_id)
        self.info_labels["downloaded_size"].setText(self._format_bytes(snapshot.downloaded_models_size_bytes))
        self.info_labels["ffmpeg"].setText(snapshot.ffmpeg_path or "không tìm thấy")
        self.info_labels["data_dir"].setText(snapshot.data_dir or "không khả dụng")
        self.info_labels["log_dir"].setText(snapshot.log_dir or "không khả dụng")

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        self._add_paths(paths)

    def _pick_videos(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Chọn video", "", "Video MP4 (*.mp4)")
        self._add_paths(paths)

    def _add_paths(self, paths: list[str]) -> None:
        if not paths:
            return
        result = self.controller.add_files(paths)
        messages: list[str] = []
        if result.rejected:
            messages.extend(f"Từ chối {Path(path).name}: {reason}" for path, reason in result.rejected)
        if result.duplicates:
            messages.extend(f"Bỏ qua trùng: {Path(path).name}" for path in result.duplicates)
        self.refresh_queue()
        if messages:
            QMessageBox.warning(self, "Không thể thêm một số file", "\n".join(messages))
        self.statusBar().showMessage(f"Đã thêm {len(result.added)} video", 4000)

    def _remove_selected_jobs(self) -> None:
        ids = self._selected_job_ids()
        if not ids:
            return
        running_job_id = self.controller.running_job_id()
        if running_job_id in ids:
            running_job = self.controller.get_job(running_job_id)
            if running_job is not None:
                self.controller.cancel_job(running_job)
            self._request_queue_stop_after_current()
        blocked = self.controller.remove_jobs(ids)
        if blocked:
            if not self._wait_for_queue_thread(30000):
                QMessageBox.warning(self, "Chưa thể xóa", "Job đang chạy chưa dừng xong. Vui lòng thử lại sau khi worker kết thúc checkpoint hiện tại.")
                self.refresh_queue()
                return
            self.controller.remove_jobs(ids, allow_running=True)
            self._current_job_id = None
            self.refresh_queue()
            self._start_queue_if_pending()
            return
        self._current_job_id = None
        self.refresh_queue()

    def _start_queue(self) -> None:
        if self._queue_thread is not None:
            return
        self.start_button.setEnabled(False)
        self.statusBar().showMessage("Đang xử lý hàng đợi...")
        self._queue_control = WorkerControlToken()
        self._queue_thread = QThread(self)
        self._queue_worker = _QueueWorker(self.controller, self._queue_control)
        self._queue_worker.moveToThread(self._queue_thread)
        self._queue_thread.started.connect(self._queue_worker.run)
        self._queue_worker.finished.connect(self._queue_finished)
        self._queue_worker.failed.connect(self._queue_failed)
        self._queue_worker.finished.connect(self._queue_thread.quit)
        self._queue_worker.failed.connect(self._queue_thread.quit)
        self._queue_worker.finished.connect(self._queue_worker.deleteLater)
        self._queue_worker.failed.connect(self._queue_worker.deleteLater)
        self._queue_thread.finished.connect(self._queue_thread.deleteLater)
        self._queue_thread.finished.connect(lambda thread=self._queue_thread: self._clear_queue_thread(thread))
        self._event_timer.start()
        self._queue_thread.start()

    def _queue_finished(self, _jobs) -> None:
        self._refresh_from_worker_events()
        self.refresh_queue()
        self.statusBar().showMessage("Hoàn tất xử lý hàng đợi", 5000)

    def _queue_failed(self, message: str) -> None:
        self._refresh_from_worker_events()
        logger.error("Queue worker failed outside normal job handling: %s", message)
        QMessageBox.critical(self, "Lỗi xử lý", "Worker hàng đợi dừng ngoài dự kiến. Chi tiết kỹ thuật đã được ghi trong log.")
        self.statusBar().showMessage("Hàng đợi dừng vì lỗi", 5000)

    def _clear_queue_thread(self, expected_thread=None) -> None:
        if expected_thread is not None and self._queue_thread is not expected_thread:
            return
        self._event_timer.stop()
        self._queue_thread = None
        self._queue_worker = None
        self._queue_control = None
        self.start_button.setEnabled(True)
        self.refresh_queue()
        restart = self._restart_queue_when_idle
        self._restart_queue_when_idle = False
        if restart and not self._closing and self.controller.queue_service.pending_jobs():
            QTimer.singleShot(0, self._start_queue)

    def _request_queue_stop_after_current(self) -> None:
        if self._queue_control is not None:
            self._queue_control.request_stop_after_current()
            self._queue_control.resume()
        if self._queue_thread is not None:
            self._queue_thread.requestInterruption()
            self._queue_thread.quit()

    def _wait_for_queue_thread(self, timeout_ms: int) -> bool:
        thread = self._queue_thread
        if thread is None:
            return True
        thread.quit()
        stopped = thread.wait(timeout_ms)
        if stopped:
            self._refresh_from_worker_events()
            self._clear_queue_thread(thread)
        return bool(stopped)

    def _start_queue_if_pending(self) -> None:
        if self._queue_thread is None and self.controller.queue_service.pending_jobs():
            self._start_queue()

    def _refresh_from_worker_events(self) -> None:
        self.controller.drain_worker_events()
        self.refresh_queue()
    def _pause_selected_job(self) -> None:
        job = self.current_job()
        if not job:
            return
        try:
            self.controller.pause_job(job)
            if self._queue_control is not None and self.controller.running_job_id() == job.id:
                self._queue_control.request_pause()
        except Exception as exc:
            QMessageBox.warning(self, "Không thể tạm dừng", str(exc))
        self.refresh_queue()

    def _resume_selected_job(self) -> None:
        job = self.current_job()
        if not job:
            return
        try:
            if self._queue_control is not None and self.controller.running_job_id() == job.id:
                self.controller.resume_active_job(job)
                self._queue_control.resume()
            else:
                self.controller.retry_job(job)
                if self._queue_thread is None:
                    self._start_queue_if_pending()
                else:
                    self._restart_queue_when_idle = True
        except Exception as exc:
            QMessageBox.warning(self, "Không thể tiếp tục", str(exc))
        self.refresh_queue()

    def _cancel_selected_job(self) -> None:
        job = self.current_job()
        if not job:
            return
        try:
            self.controller.cancel_job(job)
            if self._queue_control is not None and self.controller.running_job_id() == job.id:
                self._queue_control.resume()
        except Exception as exc:
            QMessageBox.warning(self, "Không thể hủy", str(exc))
        self.refresh_queue()

    def _retry_selected_job(self) -> None:
        job = self.current_job()
        if not job:
            return
        try:
            self.controller.retry_job(job)
            if self._queue_thread is None:
                self._start_queue_if_pending()
            else:
                self._restart_queue_when_idle = True
        except Exception as exc:
            QMessageBox.warning(self, "Không thể thử lại", str(exc))
        self.refresh_queue()
    def _model_changed(self) -> None:
        model_id = self.model_combo.currentData()
        if model_id:
            previous_model_id = self.controller.selected_model_id
            warning = self.controller.model_compatibility_warning(str(model_id))
            if warning:
                answer = QMessageBox.question(
                    self,
                    "Cảnh báo VRAM",
                    warning + "\n\nBạn vẫn muốn chọn model này?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    self.model_combo.blockSignals(True)
                    self.model_combo.setCurrentIndex(max(0, self.model_combo.findData(previous_model_id)))
                    self.model_combo.blockSignals(False)
                    return
            self.controller.select_model(str(model_id))
            self.refresh_system_info()

    def _provider_changed(self) -> None:
        provider_id = self.provider_combo.currentData()
        if provider_id:
            self.controller.select_translation_provider(str(provider_id))

    def _queue_selection_changed(self) -> None:
        ids = self._selected_job_ids()
        self._current_job_id = ids[0] if ids else None
        job = self.current_job()
        lines = self.controller.load_subtitles_for_job(job)
        self._load_subtitle_table(lines)
        self._update_action_state()

    def _load_subtitle_table(self, lines: list[SubtitleLine]) -> None:
        self._loading_subtitles = True
        self.subtitle_table.setRowCount(len(lines))
        for row, line in enumerate(lines):
            timestamp = f"{self._format_ms(line.start_ms)} --> {self._format_ms(line.end_ms)}"
            timestamp_item = QTableWidgetItem(timestamp)
            timestamp_item.setData(Qt.UserRole, line.sequence_number)
            timestamp_item.setFlags(timestamp_item.flags() & ~Qt.ItemIsEditable)
            self.subtitle_table.setItem(row, 0, timestamp_item)
            source_item = QTableWidgetItem(line.source_text)
            source_item.setToolTip(line.validation_status)
            self.subtitle_table.setItem(row, 1, source_item)
            translated_item = QTableWidgetItem(line.translated_text or "")
            translated_item.setToolTip(line.validation_status)
            self.subtitle_table.setItem(row, 2, translated_item)
        self._loading_subtitles = False

    def _subtitle_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading_subtitles or item.column() not in {1, 2}:
            return
        row = item.row()
        seq_item = self.subtitle_table.item(row, 0)
        if not seq_item:
            return
        sequence_number = int(seq_item.data(Qt.UserRole))
        source = self.subtitle_table.item(row, 1).text() if self.subtitle_table.item(row, 1) else ""
        translated = self.subtitle_table.item(row, 2).text() if self.subtitle_table.item(row, 2) else ""
        line = self.controller.update_subtitle_line(self.current_job(), sequence_number, source, translated)
        if line:
            for column in (1, 2):
                cell = self.subtitle_table.item(row, column)
                if cell:
                    cell.setToolTip(line.validation_status)

    def _export_srt(self) -> None:
        job = self.current_job()
        if not job:
            return
        try:
            written = self.controller.export_subtitles(job, self.controller.subtitle_lines)
        except Exception as exc:
            logger.exception("Subtitle export failed for job %s: %s", job.id, exc)
            QMessageBox.critical(self, "Không thể xuất SRT", "Không thể ghi file phụ đề. Kiểm tra dữ liệu, quyền ghi thư mục output và log kỹ thuật.")
            return
        self.refresh_queue()
        QMessageBox.information(self, "Đã xuất SRT", "\n".join(str(path) for path in written.values()))

    def _open_with_subtitle_edit(self) -> None:
        job = self.current_job()
        if not job:
            return
        try:
            self.controller.open_selected_in_subtitle_edit(job)
        except Exception as exc:
            logger.exception("Could not open Subtitle Edit for job %s: %s", job.id, exc)
            QMessageBox.critical(self, "Không thể mở Subtitle Edit", "Không thể mở Subtitle Edit. Kiểm tra đường dẫn ứng dụng, file phụ đề và log kỹ thuật.")

    def _open_output_folder(self) -> None:
        job = self.current_job()
        if not job:
            return
        output = self.controller.open_output_path(job)
        if not output:
            QMessageBox.information(self, "Chưa có output", "Job đang chọn chưa có file phụ đề để mở thư mục.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(output).parent)))

    def _open_logs_folder(self) -> None:
        log_dir = self.controller.logs_directory()
        if not log_dir:
            QMessageBox.warning(self, "Không thể mở log", "Chưa xác định được thư mục log.")
            return
        path = Path(log_dir)
        path.mkdir(parents=True, exist_ok=True)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            QMessageBox.warning(self, "Không thể mở log", f"Không thể mở thư mục:\n{path}")

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.controller.settings_controller(), parent=self, provider_ids=self.controller.provider_options())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.controller.apply_settings(dialog.settings())
            self._refresh_models()
            self._refresh_providers()
            self.refresh_system_info()

    def _open_system_info_dialog(self) -> None:
        if self.controller.system_info_provider and SystemInfoDialog is not None:
            model_cache_dir = self.controller.settings_store.load().model_cache_dir if self.controller.settings_store else None
            settings = self.controller.settings_store.load() if self.controller.settings_store else self.controller.settings
            dialog = SystemInfoDialog(
                AboutController(self.controller.system_info_provider),
                self,
                selected_model_id=self.controller.selected_model_id,
                model_cache_dir=model_cache_dir,
                selected_gpu_id=settings.selected_gpu_id,
                effective_profile_id=getattr(self.controller.job_runner, "execution_profile_id", None),
                effective_compute_type=getattr(self.controller.job_runner, "compute_type", None),
                effective_batch_size=getattr(self.controller.job_runner, "batch_size", None),
            )
            dialog.exec()
        else:
            self.refresh_system_info()

    def current_job(self) -> VideoJob | None:
        return self._jobs_by_id.get(self._current_job_id or "")

    def _selected_job_ids(self) -> list[str]:
        rows = sorted({index.row() for index in self.queue_table.selectionModel().selectedRows()})
        ids: list[str] = []
        for row in rows:
            item = self.queue_table.item(row, 0)
            if item:
                ids.append(str(item.data(Qt.UserRole)))
        return ids

    def _select_job_id(self, job_id: str) -> None:
        for row in range(self.queue_table.rowCount()):
            item = self.queue_table.item(row, 0)
            if item and item.data(Qt.UserRole) == job_id:
                self.queue_table.selectRow(row)
                return

    def _update_action_state(self) -> None:
        selected_jobs = [
            job
            for job_id in self._selected_job_ids()
            if (job := self.controller.get_job(job_id)) is not None
        ]
        toolbar = queue_toolbar_state(
            selected_jobs,
            queue_running=self._queue_thread is not None,
            has_pending_jobs=bool(self.controller.queue_service.pending_jobs()),
            running_job_id=self.controller.running_job_id(),
        )
        job = self.current_job()
        has_job = job is not None
        has_output = bool(job and self.controller.open_output_path(job))
        self.start_button.setEnabled(toolbar.start)
        self.remove_button.setEnabled(toolbar.remove)
        self.export_button.setEnabled(has_job and bool(self.controller.subtitle_lines))
        self.open_subtitle_edit_button.setEnabled(has_output)
        self.open_folder_button.setEnabled(has_output)
        self.pause_button.setEnabled(toolbar.pause)
        self.resume_button.setEnabled(toolbar.resume)
        self.cancel_button.setEnabled(toolbar.cancel)
        self.retry_button.setEnabled(toolbar.retry)

    def _duration_text(self, job: VideoJob) -> str:
        return str(getattr(job, "duration", None) or "-")

    def _status_text(self, job: VideoJob) -> str:
        return STATUS_LABELS.get(job.status, job.status.value if hasattr(job.status, "value") else str(job.status))

    def _status_tooltip(self, job: VideoJob) -> str | None:
        if job.error_message:
            return job.error_message
        if job.progress_label and job.progress_label != self._status_text(job):
            return job.progress_label
        return None

    def closeEvent(self, event) -> None:  # noqa: N802
        self._closing = True
        self._restart_queue_when_idle = False
        if self._queue_thread is not None:
            if self._queue_control is not None:
                self._queue_control.request_shutdown()
            self._queue_thread.requestInterruption()
            self._queue_thread.quit()
            if not self._wait_for_queue_thread(30000):
                self._closing = False
                QMessageBox.warning(self, "Chưa thể đóng", "Worker đang chạy chưa dừng xong. Vui lòng thử lại sau khi checkpoint hiện tại kết thúc.")
                event.ignore()
                return
            logger.info("Queue thread stopped cleanly before application close.")
        event.accept()

    @staticmethod
    def _format_ms(value: int) -> str:
        total_seconds, ms = divmod(int(value), 1000)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"

    @staticmethod
    def _format_bytes(value: int) -> str:
        size = float(value)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
            size /= 1024
        return f"{value} B"
