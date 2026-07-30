from ai_subtitle_studio.domain.entities import SubtitleLine
from ai_subtitle_studio.io.srt_writer import SRTWriter, default_output_paths, render_srt, unique_output_path


def test_english_srt_readable_timestamp_format():
    content = render_srt([SubtitleLine(1, 0, 1234, "Hello world.")])
    assert "00:00:00,000 --> 00:00:01,234" in content
    assert "Hello world." in content


def test_collision_uses_automatic_unique_suffix(tmp_path):
    target = tmp_path / "Lecture 01.en.srt"
    target.write_text("old", encoding="utf-8")
    assert unique_output_path(target).name == "Lecture 01.en (1).srt"


def test_default_output_paths_are_source_related(tmp_path):
    paths = default_output_paths(tmp_path / "Lecture 01.mp4", tmp_path)
    assert paths["english"].name == "Lecture 01.en.srt"
    assert paths["vietnamese"].name == "Lecture 01.vi.srt"