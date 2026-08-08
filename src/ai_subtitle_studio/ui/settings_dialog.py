"""Settings controller and Qt dialog."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from ai_subtitle_studio.config.app_settings import AppSettingsStore, validate_existing_path
from ai_subtitle_studio.config.gpu_profiles import DEFAULT_PROFILE_ID, LOW_VRAM_PROFILE_ID, GpuProfileError, resolve_execution_profile
from ai_subtitle_studio.domain.entities import AppSettings
from ai_subtitle_studio.io.working_files import WorkingFileManager

try:
    from PySide6.QtWidgets import (  # type: ignore
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )
    QT_AVAILABLE = True
except Exception:  # pragma: no cover
    QT_AVAILABLE = False
    QDialog = object  # type: ignore

PROVIDER_LABELS = {
    "google_cloud_v3": "Google Cloud Translation API v3",
    "deepseek_chat": "DeepSeek",
}

class SettingsController:
    def __init__(
        self,
        store: AppSettingsStore,
        credential_store=None,
        working_dir: str | Path | None = None,
        protected_job_ids: Callable[[], set[str]] | None = None,
        system_info_provider=None,
    ) -> None:
        self.store = store
        self.credential_store = credential_store
        self.working_dir = Path(working_dir) if working_dir else None
        self.protected_job_ids = protected_job_ids or (lambda: set())
        self.system_info_provider = system_info_provider

    def load(self) -> AppSettings:
        return self.store.load()

    def save(self, settings: AppSettings) -> None:
        self.store.save(settings)

    def validate_paths(self, settings: AppSettings) -> dict[str, str | None]:
        return {
            "ffmpeg_path": validate_existing_path(settings.ffmpeg_path, must_be_file=True)[1],
            "subtitle_edit_path": validate_existing_path(settings.subtitle_edit_path, must_be_file=True)[1] if settings.subtitle_edit_path else None,
            "model_cache_dir": validate_existing_path(settings.model_cache_dir, must_be_file=False)[1] if settings.model_cache_dir else None,
            "default_output_dir": validate_existing_path(settings.default_output_dir, must_be_file=False)[1] if settings.default_output_dir else None,
        }

    def save_api_key(self, provider_id: str, value: str) -> str:
        if not self.credential_store:
            raise RuntimeError("Chưa cấu hình kho lưu API key")
        alias = f"translation/{provider_id}"
        self.credential_store.set_password(alias, value)
        return alias

    def temp_files_size_bytes(self) -> int:
        return self._working_files().size_bytes()

    def cleanup_temp_files(self) -> int:
        return self._working_files().cleanup_all(protected_job_ids=self.protected_job_ids())

    def gpu_inventory(self):
        if self.system_info_provider is None:
            return []
        return self.system_info_provider.collect().detected_gpus

    def validate_gpu_profile(self, settings: AppSettings) -> str | None:
        inventory = self.gpu_inventory()
        selected = next(
            (gpu for gpu in inventory if gpu.gpu_id == settings.selected_gpu_id),
            inventory[0] if inventory else None,
        )
        if selected is None:
            return (
                "Không tìm thấy GPU NVIDIA/Torch CUDA để áp dụng profile 4 GiB."
                if settings.last_compute_profile_id == LOW_VRAM_PROFILE_ID
                else None
            )
        try:
            result = resolve_execution_profile(
                selected,
                requested_model_id=settings.last_model_id,
                requested_profile_id=settings.last_compute_profile_id,
            )
        except GpuProfileError as exc:
            return str(exc)
        return result.warning

    def _working_files(self) -> WorkingFileManager:
        if self.working_dir is not None:
            return WorkingFileManager(self.working_dir)
        settings = self.load()
        output_dir = Path(settings.default_output_dir or ".")
        return WorkingFileManager.for_output_dir(output_dir)

if QT_AVAILABLE:
    class SettingsDialog(QDialog):
        def __init__(self, controller: SettingsController, parent=None, provider_ids: list[str] | None = None) -> None:
            super().__init__(parent)
            self.controller = controller
            self._settings = controller.load()
            self.provider_ids = provider_ids or ["google_cloud_v3", "deepseek_chat"]
            self.setWindowTitle("Cài đặt")
            self.resize(620, 430)
            self._build_ui()
            self._load_values()

        def settings(self) -> AppSettings:
            return self._settings

        def _build_ui(self) -> None:
            root = QVBoxLayout(self)
            self.tabs = QTabWidget(self)
            root.addWidget(self.tabs)
            self._build_stt_tab()
            self._build_translation_tab()
            self._build_paths_tab()
            self._build_other_tab()
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            root.addWidget(buttons)

        def _build_stt_tab(self) -> None:
            tab = QWidget()
            layout = QFormLayout(tab)
            self.gpu_combo = QComboBox()
            self.gpu_combo.addItem("Mặc định", "")
            layout.addRow("GPU", self.gpu_combo)
            self.profile_combo = QComboBox()
            self.profile_combo.addItem("Mặc định (float16)", DEFAULT_PROFILE_ID)
            self.profile_combo.addItem("GPU 4 GiB (int8_float16, batch 1)", LOW_VRAM_PROFILE_ID)
            layout.addRow("Profile GPU", self.profile_combo)
            self.gpu_info_label = QLabel("Chưa đọc thông tin GPU")
            self.gpu_info_label.setWordWrap(True)
            layout.addRow("Khả năng", self.gpu_info_label)
            self.model_cache_edit = self._path_row(layout, "Thư mục model", directory=True)
            self.tabs.addTab(tab, "STT")

        def _build_translation_tab(self) -> None:
            tab = QWidget()
            layout = QFormLayout(tab)
            self.provider_combo = QComboBox()
            for provider_id in self.provider_ids:
                self.provider_combo.addItem(PROVIDER_LABELS.get(provider_id, provider_id), provider_id)
            layout.addRow("Provider mặc định", self.provider_combo)
            self.google_key_edit = QLineEdit()
            self.google_key_edit.setEchoMode(QLineEdit.Password)
            self.google_key_edit.setPlaceholderText("Nhập API key mới nếu muốn cập nhật")
            layout.addRow("Google API key", self.google_key_edit)
            self.deepseek_key_edit = QLineEdit()
            self.deepseek_key_edit.setEchoMode(QLineEdit.Password)
            self.deepseek_key_edit.setPlaceholderText("Nhập API key mới nếu muốn cập nhật")
            layout.addRow("DeepSeek API key", self.deepseek_key_edit)
            self.tabs.addTab(tab, "Dịch")
        def _build_paths_tab(self) -> None:
            tab = QWidget()
            layout = QFormLayout(tab)
            self.ffmpeg_edit = self._path_row(layout, "ffmpeg executable", directory=False)
            self.subtitle_edit_edit = self._path_row(layout, "Subtitle Edit executable", directory=False)
            self.output_dir_edit = self._path_row(layout, "Thư mục output", directory=True)
            self.tabs.addTab(tab, "Đường dẫn công cụ")

        def _build_other_tab(self) -> None:
            tab = QWidget()
            layout = QFormLayout(tab)
            self.last_model_label = QLabel("-")
            self.last_provider_label = QLabel("-")
            self.temp_size_label = QLabel("-")
            cleanup_button = QPushButton("Dọn dẹp file tạm")
            cleanup_button.clicked.connect(self._cleanup_temp_files)
            layout.addRow("Model gần nhất", self.last_model_label)
            layout.addRow("Provider gần nhất", self.last_provider_label)
            layout.addRow("File tạm/làm việc", self.temp_size_label)
            layout.addRow(cleanup_button)
            layout.addRow(QLabel("API key được lưu bằng kho bí mật của hệ điều hành, không lưu trong QSettings."))
            self.tabs.addTab(tab, "Khác")

        def _path_row(self, layout: QFormLayout, label: str, directory: bool) -> QLineEdit:
            edit = QLineEdit()
            button = QPushButton("Chọn")
            button.clicked.connect(lambda: self._browse_path(edit, directory))
            row = QHBoxLayout()
            row.addWidget(edit, 1)
            row.addWidget(button)
            layout.addRow(label, row)
            return edit

        def _load_values(self) -> None:
            settings = self._settings
            inventory = self.controller.gpu_inventory()
            for gpu in inventory:
                total_gib = gpu.total_vram_bytes / float(1024**3) if gpu.total_vram_bytes else 0.0
                readiness = "Torch CUDA sẵn sàng" if gpu.torch_cuda_ready else "Torch CUDA lỗi"
                self.gpu_combo.addItem(f"{gpu.gpu_id}: {gpu.name} ({total_gib:.1f} GiB, {readiness})", gpu.gpu_id)
            self._set_combo_data(self.gpu_combo, settings.selected_gpu_id or "")
            self._set_combo_data(self.profile_combo, settings.last_compute_profile_id or DEFAULT_PROFILE_ID)
            selected_gpu = next((gpu for gpu in inventory if gpu.gpu_id == settings.selected_gpu_id), inventory[0] if inventory else None)
            if selected_gpu:
                compute_types = ", ".join(selected_gpu.supported_compute_types) or "không đọc được"
                self.gpu_info_label.setText(
                    f"VRAM {selected_gpu.total_vram_bytes / float(1024**3):.1f} GiB; "
                    f"compute capability {selected_gpu.compute_capability or '-'}; "
                    f"CTranslate2: {compute_types}"
                )
            self.model_cache_edit.setText(settings.model_cache_dir or "")
            self.ffmpeg_edit.setText(settings.ffmpeg_path or "")
            self.subtitle_edit_edit.setText(settings.subtitle_edit_path or "")
            self.output_dir_edit.setText(settings.default_output_dir or "")
            self._set_combo_data(self.provider_combo, settings.last_translation_provider_id or "")
            self.last_model_label.setText(settings.last_model_id or "large-v3")
            self.last_provider_label.setText(settings.last_translation_provider_id or "-")
            self._refresh_temp_size()

        def _refresh_temp_size(self) -> None:
            self.temp_size_label.setText(self._format_bytes(self.controller.temp_files_size_bytes()))

        def _cleanup_temp_files(self) -> None:
            removed = self.controller.cleanup_temp_files()
            self._refresh_temp_size()
            QMessageBox.information(
                self,
                "Đã dọn file tạm",
                f"Đã dọn {self._format_bytes(removed)} file tạm/làm việc. File của job đang chạy được giữ lại.",
            )

        def accept(self) -> None:  # noqa: D401 - Qt override
            settings = AppSettings(
                selected_gpu_id=self.gpu_combo.currentData() or None,
                model_cache_dir=self.model_cache_edit.text().strip() or None,
                ffmpeg_path=self.ffmpeg_edit.text().strip() or None,
                subtitle_edit_path=self.subtitle_edit_edit.text().strip() or None,
                default_output_dir=self.output_dir_edit.text().strip() or None,
                last_model_id=self._settings.last_model_id or "large-v3",
                last_translation_provider_id=self.provider_combo.currentData() or None,
                last_compute_profile_id=self.profile_combo.currentData() or DEFAULT_PROFILE_ID,
            )
            if settings.last_compute_profile_id == LOW_VRAM_PROFILE_ID and settings.last_model_id not in {"small.en", "small"}:
                answer = QMessageBox.question(
                    self,
                    "Xác nhận đổi model",
                    "Profile GPU 4 GiB cần model nhẹ. Đổi model đang chọn sang small.en?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
                settings.last_model_id = "small.en"
            profile_warning = self.controller.validate_gpu_profile(settings)
            if profile_warning:
                answer = QMessageBox.question(
                    self,
                    "Cảnh báo tương thích GPU",
                    profile_warning + "\n\nBạn vẫn muốn lưu cấu hình này?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
            errors = {key: message for key, message in self.controller.validate_paths(settings).items() if message}
            if errors:
                QMessageBox.warning(self, "Settings chưa hợp lệ", "\n".join(errors.values()))
                return
            try:
                if self.google_key_edit.text().strip():
                    self.controller.save_api_key("google_cloud_v3", self.google_key_edit.text().strip())
                if self.deepseek_key_edit.text().strip():
                    self.controller.save_api_key("deepseek_chat", self.deepseek_key_edit.text().strip())
            except Exception as exc:
                QMessageBox.warning(self, "Không thể lưu API key", str(exc))
                return
            self.controller.save(settings)
            self._settings = settings
            super().accept()

        def _browse_path(self, edit: QLineEdit, directory: bool) -> None:
            if directory:
                value = QFileDialog.getExistingDirectory(self, "Chọn thư mục", edit.text() or "")
            else:
                value, _ = QFileDialog.getOpenFileName(self, "Chọn file", edit.text() or "")
            if value:
                edit.setText(value)

        @staticmethod
        def _set_combo_data(combo: QComboBox, value: str) -> None:
            index = combo.findData(value)
            if index >= 0:
                combo.setCurrentIndex(index)

        @staticmethod
        def _format_bytes(value: int) -> str:
            size = float(value)
            for unit in ("B", "KB", "MB", "GB", "TB"):
                if size < 1024 or unit == "TB":
                    return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
                size /= 1024
            return f"{value} B"
else:  # pragma: no cover
    SettingsDialog = None  # type: ignore
