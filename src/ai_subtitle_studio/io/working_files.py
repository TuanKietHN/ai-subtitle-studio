"""Managed working files for extracted audio and transient job artifacts."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import UUID

WORK_DIR_NAME = "_work"


class WorkingFileManager:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    @classmethod
    def for_output_dir(cls, output_dir: str | Path) -> "WorkingFileManager":
        return cls(Path(output_dir) / WORK_DIR_NAME)

    def job_dir(self, job_id: str) -> Path:
        try:
            safe_job_id = str(UUID(str(job_id)))
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValueError("job_id must be a UUID") from exc
        return self.root / safe_job_id

    def audio_path_for(self, job_id: str, source_path: str | Path) -> Path:
        stem = Path(source_path).stem or "audio"
        return self.job_dir(job_id) / f"{stem}.wav"

    def size_bytes(self) -> int:
        total = 0
        if self.root.exists():
            if self.root.is_file():
                total += self._path_size(self.root)
            else:
                total += self._path_size(self.root)
        for path in self._output_temp_paths():
            total += self._path_size(path)
        return total

    def cleanup_job(self, job_id: str) -> int:
        path = self.job_dir(job_id)
        bytes_before = self._path_size(path)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        return bytes_before

    def cleanup_all(self, protected_job_ids: set[str] | None = None) -> int:
        protected = set(protected_job_ids or ())
        removed_bytes = 0
        if not protected:
            for path in self._output_temp_paths():
                bytes_before = self._path_size(path)
                try:
                    path.unlink()
                except OSError:
                    continue
                removed_bytes += bytes_before
        if not self.root.exists():
            return removed_bytes
        if self.root.is_file():
            if protected:
                return removed_bytes
            bytes_before = self._path_size(self.root)
            try:
                self.root.unlink()
            except OSError:
                return removed_bytes
            return removed_bytes + bytes_before

        for path in self.root.iterdir():
            if path.name in protected:
                continue
            bytes_before = self._path_size(path)
            try:
                if path.is_symlink() or path.is_file():
                    path.unlink()
                else:
                    shutil.rmtree(path)
            except OSError:
                continue
            removed_bytes += bytes_before
        try:
            self.root.rmdir()
        except OSError:
            pass
        return removed_bytes

    def _output_temp_paths(self) -> list[Path]:
        output_dir = self.root.parent
        if not output_dir.exists() or not output_dir.is_dir():
            return []
        return [path for path in output_dir.glob("*.srt.tmp") if path.is_file()]

    @staticmethod
    def _path_size(path: Path) -> int:
        if not path.exists():
            return 0
        if path.is_file():
            try:
                return path.stat().st_size
            except OSError:
                return 0
        total = 0
        for dirpath, _, filenames in os.walk(path):
            for name in filenames:
                try:
                    total += (Path(dirpath) / name).stat().st_size
                except OSError:
                    pass
        return total
