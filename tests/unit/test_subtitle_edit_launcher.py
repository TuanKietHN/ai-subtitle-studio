from unittest.mock import patch
import pytest
from ai_subtitle_studio.io.subtitle_edit import SubtitleEditLaunchError, open_with_subtitle_edit


def test_subtitle_edit_launcher_valid_and_invalid_paths(tmp_path):
    exe = tmp_path / "SubtitleEdit.exe"; exe.write_text("exe")
    subtitle = tmp_path / "a.srt"; subtitle.write_text("1")
    with patch("subprocess.Popen") as popen:
        open_with_subtitle_edit(exe, subtitle)
        assert popen.called
    with pytest.raises(SubtitleEditLaunchError):
        open_with_subtitle_edit(tmp_path / "missing.exe", subtitle)