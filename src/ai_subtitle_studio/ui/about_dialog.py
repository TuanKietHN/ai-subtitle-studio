"""About/System Info dialog adapter."""

from __future__ import annotations

import time

try:
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout  # type: ignore
    QT_AVAILABLE = True
except Exception:  # pragma: no cover
    QT_AVAILABLE = False
    QDialog = object  # type: ignore

class AboutController:
    def __init__(self, system_info_provider) -> None:
        self.system_info_provider = system_info_provider

    def render_info(self, selected_model_id: str = "large-v3", model_cache_dir: str | None = None) -> dict:
        start = time.monotonic()
        snapshot = self.system_info_provider.collect(selected_model_id=selected_model_id, model_cache_dir=model_cache_dir)
        return {"snapshot": snapshot, "elapsed_seconds": time.monotonic() - start}

if QT_AVAILABLE:
    class SystemInfoDialog(QDialog):
        def __init__(self, controller: AboutController, parent=None, selected_model_id: str = "large-v3", model_cache_dir: str | None = None) -> None:
            super().__init__(parent)
            self.setWindowTitle("Thông tin hệ thống")
            self.resize(520, 300)
            info = controller.render_info(selected_model_id=selected_model_id, model_cache_dir=model_cache_dir)
            snapshot = info["snapshot"]
            layout = QVBoxLayout(self)
            form = QFormLayout()
            form.addRow("App", QLabel(snapshot.app_version))
            form.addRow("WhisperX", QLabel(snapshot.whisperx_version))
            form.addRow("faster-whisper", QLabel(snapshot.faster_whisper_version))
            form.addRow("CUDA", QLabel(snapshot.torch_cuda_version))
            gpu_text = ", ".join(f"{gpu.get('id')}: {gpu.get('name')} ({gpu.get('driver_version')})" for gpu in snapshot.detected_gpus)
            form.addRow("GPU/Driver", QLabel(gpu_text or f"không khả dụng / driver {snapshot.gpu_driver_version}"))
            form.addRow("Model đang chọn", QLabel(snapshot.selected_model_id))
            form.addRow("Dung lượng model", QLabel(self._format_bytes(snapshot.downloaded_models_size_bytes)))
            form.addRow("FFmpeg", QLabel(snapshot.ffmpeg_path or "không tìm thấy"))
            form.addRow("Dữ liệu ứng dụng", QLabel(snapshot.data_dir or "không khả dụng"))
            form.addRow("Thư mục log", QLabel(snapshot.log_dir or "không khả dụng"))
            form.addRow("Thời gian đọc", QLabel(f"{info['elapsed_seconds']:.2f}s"))
            layout.addLayout(form)
            buttons = QDialogButtonBox(QDialogButtonBox.Ok)
            buttons.accepted.connect(self.accept)
            layout.addWidget(buttons)

        @staticmethod
        def _format_bytes(value: int) -> str:
            size = float(value)
            for unit in ("B", "KB", "MB", "GB", "TB"):
                if size < 1024 or unit == "TB":
                    return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
                size /= 1024
            return f"{value} B"
else:  # pragma: no cover
    SystemInfoDialog = None  # type: ignore
