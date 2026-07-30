"""SQLite schema migrations for local job history and queue recovery."""

from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 1
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS video_jobs (
 id TEXT PRIMARY KEY, source_path TEXT NOT NULL, source_fingerprint TEXT NOT NULL, display_name TEXT NOT NULL,
 status TEXT NOT NULL, selected_model_id TEXT NOT NULL, translation_provider_id TEXT, gpu_id TEXT,
 progress_percent REAL NOT NULL DEFAULT 0, progress_label TEXT NOT NULL DEFAULT '', pause_requested INTEGER NOT NULL DEFAULT 0,
 cancel_requested INTEGER NOT NULL DEFAULT 0, retry_required INTEGER NOT NULL DEFAULT 0, error_code TEXT, error_message TEXT,
 created_at TEXT NOT NULL, started_at TEXT, completed_at TEXT, updated_at TEXT NOT NULL, audio_temp_path TEXT,
 english_srt_path TEXT, vietnamese_srt_path TEXT, bilingual_srt_path TEXT
);
CREATE TABLE IF NOT EXISTS subtitle_lines (
 id TEXT PRIMARY KEY, job_id TEXT NOT NULL, sequence_number INTEGER NOT NULL, start_ms INTEGER NOT NULL, end_ms INTEGER NOT NULL,
 source_text TEXT NOT NULL, translated_text TEXT, word_timings_json TEXT, is_edited INTEGER NOT NULL DEFAULT 0,
 validation_status TEXT NOT NULL, UNIQUE(job_id, sequence_number), FOREIGN KEY(job_id) REFERENCES video_jobs(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS model_downloads (
 id TEXT PRIMARY KEY, model_id TEXT NOT NULL, status TEXT NOT NULL, percent REAL NOT NULL DEFAULT 0,
 bytes_downloaded INTEGER NOT NULL DEFAULT 0, bytes_total INTEGER, bytes_remaining INTEGER, speed_bytes_per_sec REAL NOT NULL DEFAULT 0,
 error_message TEXT
);
CREATE TABLE IF NOT EXISTS provider_status (
 provider_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, credential_alias TEXT NOT NULL, has_api_key INTEGER NOT NULL DEFAULT 0,
 last_validated_at TEXT, last_error TEXT
);
"""
ACTIVE_STATUS_NAMES = ("waiting_for_model", "downloading_model", "extracting_audio", "waiting_for_gpu", "transcribing", "aligning", "translating", "exporting")

def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_SQL)
    connection.execute("INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)", (SCHEMA_VERSION,))
    connection.commit()

def mark_active_jobs_retry_required(connection: sqlite3.Connection) -> int:
    placeholders = ",".join("?" for _ in ACTIVE_STATUS_NAMES)
    cursor = connection.execute(f"UPDATE video_jobs SET status='retry_required', retry_required=1, updated_at=CURRENT_TIMESTAMP WHERE status IN ({placeholders})", ACTIVE_STATUS_NAMES)
    connection.commit()
    return cursor.rowcount