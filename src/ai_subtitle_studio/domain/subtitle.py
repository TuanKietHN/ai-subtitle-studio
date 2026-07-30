"""Subtitle validation, cue grouping, and timestamp helpers."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Iterable

from .entities import SubtitleLine

_SENTENCE_END = re.compile(r"[.!?][\"')\]]*$")


def format_srt_timestamp(ms: int) -> str:
    if ms < 0:
        raise ValueError("Timestamp cannot be negative")
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def validate_subtitle_line(line: SubtitleLine, translated: bool = False) -> str:
    text = line.translated_text if translated else line.source_text
    if line.start_ms >= line.end_ms:
        return "invalid_time_range"
    if text is None or not text.strip():
        return "empty_text"
    if "\x00" in text:
        return "invalid_text"
    if len(text) > 500:
        return "too_long"
    return "valid"


def mark_validation(line: SubtitleLine, translated: bool = False) -> SubtitleLine:
    return replace(line, validation_status=validate_subtitle_line(line, translated=translated))


def group_words_into_cues(words: Iterable[dict], max_words: int = 18) -> list[SubtitleLine]:
    cues: list[SubtitleLine] = []
    current: list[dict] = []

    def flush() -> None:
        if not current:
            return
        text = " ".join(str(w.get("word", "")).strip() for w in current).strip()
        start = int(float(current[0].get("start", 0)) * 1000)
        end = int(float(current[-1].get("end", current[-1].get("start", 0))) * 1000)
        cues.append(SubtitleLine(sequence_number=len(cues) + 1, start_ms=start, end_ms=max(end, start + 1), source_text=text))
        current.clear()

    for word in words:
        current.append(word)
        token = str(word.get("word", "")).strip()
        if len(current) >= max_words or _SENTENCE_END.search(token):
            flush()
    flush()
    return [mark_validation(cue) for cue in cues]


def segments_to_subtitle_lines(segments: Iterable[dict]) -> list[SubtitleLine]:
    lines: list[SubtitleLine] = []
    for segment in segments:
        words = segment.get("words") or []
        if words:
            grouped = group_words_into_cues(words)
            for line in grouped:
                line.sequence_number = len(lines) + 1
                lines.append(line)
            continue
        start = int(float(segment.get("start", 0)) * 1000)
        end = int(float(segment.get("end", segment.get("start", 0))) * 1000)
        text = str(segment.get("text", "")).strip()
        lines.append(mark_validation(SubtitleLine(len(lines) + 1, start, max(end, start + 1), text)))
    return lines