"""Editable subtitle table abstraction with PySide fallback."""

from __future__ import annotations

from ai_subtitle_studio.domain.entities import SubtitleLine
from ai_subtitle_studio.domain.subtitle import mark_validation

class SubtitleTableModel:
    def __init__(self, lines: list[SubtitleLine] | None = None) -> None:
        self.lines = list(lines or [])
    def load(self, lines: list[SubtitleLine]) -> None:
        self.lines = list(lines)
    def edit_source(self, sequence_number: int, text: str) -> SubtitleLine:
        line = self._line(sequence_number); line.source_text = text; line.is_edited = True; line.validation_status = mark_validation(line).validation_status; return line
    def edit_translation(self, sequence_number: int, text: str) -> SubtitleLine:
        line = self._line(sequence_number); line.translated_text = text; line.is_edited = True; line.validation_status = mark_validation(line, translated=True).validation_status; return line
    def _line(self, sequence_number: int) -> SubtitleLine:
        for line in self.lines:
            if line.sequence_number == sequence_number: return line
        raise KeyError(sequence_number)