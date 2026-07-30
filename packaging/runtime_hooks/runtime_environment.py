"""Initialize writable caches and native DLL search paths before app imports."""

from __future__ import annotations

import os
from pathlib import Path
import sys

APP_DIRECTORY_NAME = "AI Subtitle Studio"
_DLL_HANDLES: list[object] = []


def _user_data_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_DIRECTORY_NAME
    return Path.home() / "AppData" / "Local" / APP_DIRECTORY_NAME


def _configure_caches() -> None:
    cache_root = _user_data_dir() / "models"
    cache_root.mkdir(parents=True, exist_ok=True)
    defaults = {
        "HF_HOME": cache_root / "huggingface",
        "TORCH_HOME": cache_root / "torch",
        "PYANNOTE_CACHE": cache_root / "pyannote",
        "XDG_CACHE_HOME": cache_root,
    }
    for name, path in defaults.items():
        os.environ.setdefault(name, str(path))


def _configure_windows_dll_search() -> None:
    if os.name != "nt" or not hasattr(os, "add_dll_directory"):
        return
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    candidates = (
        bundle_root,
        bundle_root / "_internal",
        bundle_root / "torch" / "lib",
        bundle_root / "_internal" / "torch" / "lib",
        bundle_root / "ctranslate2",
        bundle_root / "_internal" / "ctranslate2",
    )
    for directory in candidates:
        if directory.is_dir():
            _DLL_HANDLES.append(os.add_dll_directory(str(directory)))


_configure_caches()
_configure_windows_dll_search()
