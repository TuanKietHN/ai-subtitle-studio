import pytest

from ai_subtitle_studio.domain.entities import VideoJob
from ai_subtitle_studio.persistence.repositories import JobRepository
from ai_subtitle_studio.persistence.sqlite_store import SQLiteStore


def test_sqlite_uses_durable_wal_settings_and_rolls_back_failed_transaction(tmp_path):
    store = SQLiteStore(tmp_path / "jobs.sqlite3")
    repo = JobRepository(store)
    job = VideoJob("lecture.mp4")
    repo.save(job)

    with store.connection() as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert conn.execute("PRAGMA synchronous").fetchone()[0] == 2
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000

    with pytest.raises(RuntimeError):
        with store.connection() as conn:
            conn.execute("UPDATE video_jobs SET progress_label='không được commit' WHERE id=?", (job.id,))
            raise RuntimeError("simulate crash before commit")

    assert repo.get(job.id).progress_label == "Chờ xử lý"
