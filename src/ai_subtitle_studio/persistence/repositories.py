"""Repository layer for jobs, subtitles, model downloads, and providers."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable
from ai_subtitle_studio.domain.entities import ModelDownload, SubtitleLine, TranslationProviderConfig, VideoJob, utc_now_iso
from ai_subtitle_studio.domain.job_state import JobStatus, restore_status_after_shutdown
from .sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)

def source_fingerprint(path: str | Path) -> str:
    p = Path(path)
    try:
        stat = p.stat()
        return f"{p.resolve()}::{stat.st_size}::{int(stat.st_mtime)}"
    except OSError:
        return f"{p.resolve()}::missing"

class JobRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
    def save(self, job: VideoJob) -> VideoJob:
        if not job.source_fingerprint:
            job.source_fingerprint = source_fingerprint(job.source_path)
        job.updated_at = utc_now_iso()
        with self.store.connection() as conn:
            conn.execute("""INSERT OR REPLACE INTO video_jobs (id, source_path, source_fingerprint, display_name, status, selected_model_id, translation_provider_id, gpu_id, progress_percent, progress_label, pause_requested, cancel_requested, retry_required, error_code, error_message, created_at, started_at, completed_at, updated_at, audio_temp_path, english_srt_path, vietnamese_srt_path, bilingual_srt_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (job.id, job.source_path, job.source_fingerprint, job.display_name, job.status.value, job.selected_model_id, job.translation_provider_id, job.gpu_id, job.progress_percent, job.progress_label, int(job.pause_requested), int(job.cancel_requested), int(job.retry_required), job.error_code, job.error_message, job.created_at, job.started_at, job.completed_at, job.updated_at, job.audio_temp_path, job.english_srt_path, job.vietnamese_srt_path, job.bilingual_srt_path))
        return job
    def list_jobs(self) -> list[VideoJob]:
        with self.store.connection() as conn:
            rows = conn.execute("SELECT * FROM video_jobs ORDER BY created_at, rowid").fetchall()
        return [self._row_to_job(row) for row in rows]
    def get(self, job_id: str) -> VideoJob | None:
        with self.store.connection() as conn:
            row = conn.execute("SELECT * FROM video_jobs WHERE id=?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None
    def delete(self, job_id: str) -> None:
        with self.store.connection() as conn:
            conn.execute("DELETE FROM subtitle_lines WHERE job_id=?", (job_id,))
            conn.execute("DELETE FROM video_jobs WHERE id=?", (job_id,))
    def update_status(self, job_id: str, status: JobStatus, label: str | None = None) -> None:
        with self.store.connection() as conn:
            conn.execute("UPDATE video_jobs SET status=?, progress_label=COALESCE(?, progress_label), updated_at=? WHERE id=?", (status.value, label, utc_now_iso(), job_id))
    def recover_active_jobs(self) -> int:
        count = 0
        for job in self.list_jobs():
            restored = restore_status_after_shutdown(job.status)
            if job.status is JobStatus.PAUSED and job.retry_required:
                restored = JobStatus.RETRY_REQUIRED
            if restored is not job.status:
                old_status = job.status
                job.status = restored
                job.retry_required = True
                job.cancel_requested = False
                job.pause_requested = False
                job.progress_label = "App đã đóng khi job đang chạy. Bấm \"Bắt đầu xử lý\" để chạy lại từ đầu."
                self.save(job)
                count += 1
                logger.info("Recovered job %s from %s to retry_required after shutdown.", job.id, old_status.value)
        return count
    def _row_to_job(self, row) -> VideoJob:
        return VideoJob(id=row["id"], source_path=row["source_path"], source_fingerprint=row["source_fingerprint"], display_name=row["display_name"], status=JobStatus(row["status"]), selected_model_id=row["selected_model_id"], translation_provider_id=row["translation_provider_id"], gpu_id=row["gpu_id"], progress_percent=row["progress_percent"], progress_label=row["progress_label"], pause_requested=bool(row["pause_requested"]), cancel_requested=bool(row["cancel_requested"]), retry_required=bool(row["retry_required"]), error_code=row["error_code"], error_message=row["error_message"], created_at=row["created_at"], started_at=row["started_at"], completed_at=row["completed_at"], updated_at=row["updated_at"], audio_temp_path=row["audio_temp_path"], english_srt_path=row["english_srt_path"], vietnamese_srt_path=row["vietnamese_srt_path"], bilingual_srt_path=row["bilingual_srt_path"])

class SubtitleRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
    def replace_for_job(self, job_id: str, lines: Iterable[SubtitleLine]) -> None:
        with self.store.connection() as conn:
            conn.execute("DELETE FROM subtitle_lines WHERE job_id=?", (job_id,))
            for line in lines:
                conn.execute("""INSERT INTO subtitle_lines (id, job_id, sequence_number, start_ms, end_ms, source_text, translated_text, word_timings_json, is_edited, validation_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (line.id, job_id, line.sequence_number, line.start_ms, line.end_ms, line.source_text, line.translated_text, line.word_timings_json, int(line.is_edited), line.validation_status))
    def list_for_job(self, job_id: str) -> list[SubtitleLine]:
        with self.store.connection() as conn:
            rows = conn.execute("SELECT * FROM subtitle_lines WHERE job_id=? ORDER BY sequence_number", (job_id,)).fetchall()
        return [SubtitleLine(row["sequence_number"], row["start_ms"], row["end_ms"], row["source_text"], id=row["id"], job_id=row["job_id"], translated_text=row["translated_text"], word_timings_json=row["word_timings_json"], is_edited=bool(row["is_edited"]), validation_status=row["validation_status"]) for row in rows]
    def delete_for_job(self, job_id: str) -> None:
        with self.store.connection() as conn:
            conn.execute("DELETE FROM subtitle_lines WHERE job_id=?", (job_id,))

class ModelRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
    def save_download(self, download: ModelDownload) -> ModelDownload:
        with self.store.connection() as conn:
            conn.execute("INSERT OR REPLACE INTO model_downloads VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (download.id, download.model_id, download.status, download.percent, download.bytes_downloaded, download.bytes_total, download.bytes_remaining, download.speed_bytes_per_sec, download.error_message))
        return download
    def model_size(self, path: str | Path) -> int:
        root = Path(path)
        if not root.exists(): return 0
        if root.is_file(): return root.stat().st_size
        total = 0
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                try: total += (Path(dirpath) / name).stat().st_size
                except OSError: pass
        return total

class ProviderStatusRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
    def save(self, config: TranslationProviderConfig) -> TranslationProviderConfig:
        with self.store.connection() as conn:
            conn.execute("INSERT OR REPLACE INTO provider_status VALUES (?, ?, ?, ?, ?, ?)", (config.provider_id, config.display_name, config.credential_alias, int(config.has_api_key), config.last_validated_at, config.last_error))
        return config
