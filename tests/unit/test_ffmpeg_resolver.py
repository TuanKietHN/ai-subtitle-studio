from pathlib import Path

import pytest

from ai_subtitle_studio.io.ffmpeg_resolver import FFmpegNotFoundError, find_ffmpeg, resolve_ffmpeg


def test_ffmpeg_resolution_prefers_explicit_then_bundle_then_path(tmp_path):
    explicit = tmp_path / "custom.exe"
    bundled = tmp_path / "ffmpeg.exe"
    on_path = tmp_path / "path-ffmpeg.exe"
    for path in (explicit, bundled, on_path):
        path.write_bytes(b"exe")

    assert resolve_ffmpeg(explicit, bundled, path_lookup=lambda _: str(on_path)) == str(explicit.resolve())
    explicit.unlink()
    assert resolve_ffmpeg(explicit, bundled, path_lookup=lambda _: str(on_path)) == str(bundled.resolve())
    bundled.unlink()
    assert resolve_ffmpeg(explicit, bundled, path_lookup=lambda _: str(on_path)) == str(on_path.resolve())


def test_ffmpeg_resolution_reports_missing_binary(tmp_path):
    assert find_ffmpeg(tmp_path / "missing.exe", path_lookup=lambda _: None) is None
    with pytest.raises(FFmpegNotFoundError, match="ffmpeg"):
        resolve_ffmpeg(tmp_path / "missing.exe", path_lookup=lambda _: None)
