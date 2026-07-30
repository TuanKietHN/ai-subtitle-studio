"""QSettings-backed non-secret application settings with fallback storage."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from ai_subtitle_studio.domain.entities import AppSettings

try:
    from PySide6.QtCore import QSettings  # type: ignore
except Exception:
    QSettings = None  # type: ignore

class InMemorySettings:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {}
    def value(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)
    def setValue(self, key: str, value: Any) -> None:
        self.values[key] = value
    def sync(self) -> None:
        return None

class AppSettingsStore:
    def __init__(self, backend: Any | None = None) -> None:
        if backend is not None:
            self.backend = backend
        elif QSettings is not None:
            self.backend = QSettings("AI Subtitle Studio", "AI Subtitle Studio")
        else:
            self.backend = InMemorySettings()
    def load(self) -> AppSettings:
        return AppSettings(selected_gpu_id=self._value("selected_gpu_id"), model_cache_dir=self._value("model_cache_dir"), ffmpeg_path=self._value("ffmpeg_path"), subtitle_edit_path=self._value("subtitle_edit_path"), default_output_dir=self._value("default_output_dir"), last_model_id=self._value("last_model_id", "large-v3") or "large-v3", last_translation_provider_id=self._value("last_translation_provider_id"))
    def save(self, settings: AppSettings) -> None:
        for key in ("selected_gpu_id", "model_cache_dir", "ffmpeg_path", "subtitle_edit_path", "default_output_dir", "last_model_id", "last_translation_provider_id"):
            self.backend.setValue(key, getattr(settings, key))
        self.backend.sync()
    def set_value(self, key: str, value: Any) -> None:
        if "api_key" in key.lower() or "secret" in key.lower():
            raise ValueError("Không được lưu secret/API key trong QSettings")
        self.backend.setValue(key, value)
        self.backend.sync()
    def _value(self, key: str, default: Any = None) -> Any:
        value = self.backend.value(key, default)
        return None if value == "" else value

def validate_existing_path(path: str | None, must_be_file: bool | None = None) -> tuple[bool, str | None]:
    if not path:
        return False, "Chưa cấu hình đường dẫn"
    p = Path(path)
    if not p.exists():
        return False, f"Đường dẫn không tồn tại: {path}"
    if must_be_file is True and not p.is_file():
        return False, f"Cần chọn đường dẫn file: {path}"
    if must_be_file is False and not p.is_dir():
        return False, f"Cần chọn đường dẫn thư mục: {path}"
    return True, None