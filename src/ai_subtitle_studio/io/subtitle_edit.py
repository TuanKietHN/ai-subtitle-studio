"""Subtitle Edit subprocess launcher."""

from __future__ import annotations

import subprocess
from pathlib import Path

class SubtitleEditLaunchError(RuntimeError): pass

def open_with_subtitle_edit(executable_path: str | Path, subtitle_path: str | Path) -> subprocess.Popen:
    exe = Path(executable_path); subtitle = Path(subtitle_path)
    if not exe.exists() or not exe.is_file():
        raise SubtitleEditLaunchError(f"Subtitle Edit executable is invalid: {exe}")
    if not subtitle.exists() or not subtitle.is_file():
        raise SubtitleEditLaunchError(f"Subtitle file does not exist: {subtitle}")
    try:
        return subprocess.Popen([str(exe), str(subtitle)])
    except OSError as exc:
        raise SubtitleEditLaunchError(str(exc)) from exc