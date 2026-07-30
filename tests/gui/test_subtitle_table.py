from ai_subtitle_studio.domain.entities import SubtitleLine
from ai_subtitle_studio.io.srt_writer import SRTWriter
from ai_subtitle_studio.ui.subtitle_table import SubtitleTableModel


def test_subtitle_table_edit_and_export(tmp_path):
    model = SubtitleTableModel([SubtitleLine(1, 0, 1000, "Hello")])
    line = model.edit_translation(1, "Xin chao")
    assert line.is_edited is True
    out = SRTWriter().write_vietnamese(model.lines, tmp_path / "out.vi.srt")
    assert "Xin chao" in out.read_text(encoding="utf-8")