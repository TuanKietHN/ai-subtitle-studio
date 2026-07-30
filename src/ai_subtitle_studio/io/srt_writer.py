"""SRT writing with collision-safe output paths."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
from ai_subtitle_studio.domain.entities import SubtitleLine
from ai_subtitle_studio.domain.subtitle import format_srt_timestamp, validate_subtitle_line

class SRTWriteError(RuntimeError): pass

def unique_output_path(path: str | Path, overwrite: bool = False) -> Path:
    target = Path(path)
    if overwrite or not target.exists(): return target
    stem, suffix, parent = target.stem, target.suffix, target.parent
    index = 1
    while True:
        candidate = parent / f"{stem} ({index}){suffix}"
        if not candidate.exists(): return candidate
        index += 1

def default_output_paths(source_video: str | Path, output_dir: str | Path) -> dict[str, Path]:
    source = Path(source_video); base = Path(output_dir) / source.stem
    return {"english": base.with_suffix(".en.srt"), "vietnamese": base.with_suffix(".vi.srt"), "bilingual": base.with_suffix(".bilingual.srt")}

def render_srt(lines: Iterable[SubtitleLine], language: str = "source") -> str:
    chunks: list[str] = []
    for index, line in enumerate(lines, start=1):
        translated = language == "translated"
        status = validate_subtitle_line(line, translated=translated)
        if status != "valid": raise SRTWriteError(f"Invalid subtitle line {line.sequence_number}: {status}")
        text = line.translated_text if translated else line.source_text
        chunks.append(f"{index}\n{format_srt_timestamp(line.start_ms)} --> {format_srt_timestamp(line.end_ms)}\n{text.strip()}\n")
    return "\n".join(chunks)

def render_bilingual_srt(lines: Iterable[SubtitleLine]) -> str:
    chunks: list[str] = []
    for index, line in enumerate(lines, start=1):
        if validate_subtitle_line(line) != "valid" or validate_subtitle_line(line, translated=True) != "valid":
            raise SRTWriteError(f"Invalid bilingual subtitle line {line.sequence_number}")
        chunks.append(f"{index}\n{format_srt_timestamp(line.start_ms)} --> {format_srt_timestamp(line.end_ms)}\n{line.source_text.strip()}\n{line.translated_text.strip()}\n")
    return "\n".join(chunks)

class SRTWriter:
    def write_english(self, lines: Iterable[SubtitleLine], path: str | Path, overwrite: bool = False) -> Path:
        return self._write(render_srt(list(lines), language="source"), path, overwrite)
    def write_vietnamese(self, lines: Iterable[SubtitleLine], path: str | Path, overwrite: bool = False) -> Path:
        return self._write(render_srt(list(lines), language="translated"), path, overwrite)
    def write_bilingual(self, lines: Iterable[SubtitleLine], path: str | Path, overwrite: bool = False) -> Path:
        return self._write(render_bilingual_srt(list(lines)), path, overwrite)
    def _write(self, content: str, path: str | Path, overwrite: bool = False) -> Path:
        target = unique_output_path(path, overwrite=overwrite)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + ".tmp")
        try:
            temp.write_text(content, encoding="utf-8")
            temp.replace(target)
        finally:
            if temp.exists():
                try:
                    temp.unlink()
                except OSError:
                    pass
        return target
