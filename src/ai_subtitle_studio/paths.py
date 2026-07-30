"""Frozen-aware resource and persistent-data path resolution."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Mapping

APP_DIRECTORY_NAME = "AI Subtitle Studio"


def _default_resource_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root).resolve()
    return Path(__file__).resolve().parents[2]


def _default_local_data_root(env: Mapping[str, str], home: Path) -> Path:
    configured = env.get("LOCALAPPDATA")
    if configured:
        return Path(configured)
    if os.name == "nt":
        return home / "AppData" / "Local"
    return Path(env.get("XDG_DATA_HOME", home / ".local" / "share"))


def _default_documents_root(env: Mapping[str, str], home: Path) -> Path:
    profile = Path(env.get("USERPROFILE", home))
    return profile / "Documents"


@dataclass(frozen=True, slots=True)
class AppPaths:
    """All paths needed by source and PyInstaller builds."""

    resource_root: Path
    data_dir: Path
    model_cache_dir: Path
    log_dir: Path
    output_dir: Path

    @property
    def database_path(self) -> Path:
        return self.data_dir / "ai_subtitle_studio.sqlite3"

    @property
    def model_catalog_path(self) -> Path:
        return self.resource_root / "resources" / "models.json"

    @property
    def bundled_ffmpeg_path(self) -> Path:
        return self.resource_root / "bin" / "ffmpeg.exe"

    @classmethod
    def resolve(
        cls,
        *,
        resource_root: str | Path | None = None,
        model_cache_dir: str | Path | None = None,
        output_dir: str | Path | None = None,
        env: Mapping[str, str] | None = None,
        home: str | Path | None = None,
        create: bool = True,
    ) -> "AppPaths":
        values = os.environ if env is None else env
        home_path = Path(home) if home is not None else Path.home()
        resources = Path(resource_root).resolve() if resource_root is not None else _default_resource_root()
        local_root = _default_local_data_root(values, home_path)
        documents_root = _default_documents_root(values, home_path)

        data = Path(values.get("AI_SUBTITLE_DATA_DIR", local_root / APP_DIRECTORY_NAME))
        models = Path(
            values.get(
                "AI_SUBTITLE_MODEL_CACHE",
                model_cache_dir or data / "models",
            )
        )
        outputs = Path(
            values.get(
                "AI_SUBTITLE_OUTPUT_DIR",
                output_dir or documents_root / APP_DIRECTORY_NAME / "outputs",
            )
        )
        paths = cls(
            resource_root=resources,
            data_dir=data,
            model_cache_dir=models,
            log_dir=data / "logs",
            output_dir=outputs,
        )
        if create:
            for directory in (paths.data_dir, paths.model_cache_dir, paths.log_dir, paths.output_dir):
                directory.mkdir(parents=True, exist_ok=True)
        return paths
