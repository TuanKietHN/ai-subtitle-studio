"""Resolve ffmpeg from user settings, the app bundle, or PATH."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Callable


class FFmpegNotFoundError(FileNotFoundError):
    """Raised when no usable ffmpeg executable can be found."""


def find_ffmpeg(
    explicit_path: str | Path | None = None,
    bundled_path: str | Path | None = None,
    *,
    path_lookup: Callable[[str], str | None] = shutil.which,
) -> str | None:
    if explicit_path:
        explicit = Path(explicit_path)
        if explicit.is_file():
            return str(explicit.resolve())
    if bundled_path:
        bundled = Path(bundled_path)
        if bundled.is_file():
            return str(bundled.resolve())
    discovered = path_lookup("ffmpeg")
    return str(Path(discovered).resolve()) if discovered else None


def resolve_ffmpeg(
    explicit_path: str | Path | None = None,
    bundled_path: str | Path | None = None,
    *,
    path_lookup: Callable[[str], str | None] = shutil.which,
) -> str:
    resolved = find_ffmpeg(explicit_path, bundled_path, path_lookup=path_lookup)
    if resolved:
        return resolved
    raise FFmpegNotFoundError(
        "Không tìm thấy ffmpeg. Hãy cài bản đầy đủ có ffmpeg đi kèm "
        "hoặc chọn ffmpeg.exe trong Cài đặt."
    )
