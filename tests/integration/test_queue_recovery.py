from ai_subtitle_studio.config.model_catalog import ModelCatalog
from ai_subtitle_studio.domain.entities import VideoJob
from ai_subtitle_studio.domain.job_state import JobStatus
from ai_subtitle_studio.persistence.repositories import JobRepository
from ai_subtitle_studio.persistence.sqlite_store import SQLiteStore
from ai_subtitle_studio.ui.main_window import MainWindowController
from ai_subtitle_studio.workers.job_runner import JobRunner


def test_queue_recovery_marks_active_job_retry_required(tmp_path):
    repo = JobRepository(SQLiteStore(tmp_path / "jobs.sqlite3"))
    job = VideoJob("lecture.mp4", status=JobStatus.TRANSCRIBING)
    repo.save(job)
    assert repo.recover_active_jobs() == 1
    restored = repo.get(job.id)
    assert restored.status == JobStatus.RETRY_REQUIRED
    assert restored.retry_required is True
    assert "Bắt đầu xử lý" in restored.progress_label


def test_startup_recovers_active_job_and_removes_stale_working_files(tmp_path):
    repo = JobRepository(SQLiteStore(tmp_path / "jobs.sqlite3"))
    job = VideoJob("lecture.mp4", status=JobStatus.TRANSCRIBING, audio_temp_path="stale.wav")
    repo.save(job)
    output_dir = tmp_path / "outputs"
    runner = JobRunner(output_dir=output_dir, job_repository=repo)
    stale_dir = runner.working_files.job_dir(job.id)
    stale_dir.mkdir(parents=True)
    (stale_dir / "lecture.wav").write_bytes(b"partial")
    stale_srt_temp = output_dir / "lecture.en.srt.tmp"
    stale_srt_temp.write_bytes(b"partial subtitle")

    controller = MainWindowController(ModelCatalog.load("resources/models.json"), job_runner=runner)

    restored = controller.get_job(job.id)
    assert restored is not None
    assert restored.status is JobStatus.RETRY_REQUIRED
    assert "Bắt đầu xử lý" in restored.progress_label
    assert restored.audio_temp_path is None
    assert not stale_dir.exists()
    assert not stale_srt_temp.exists()


def test_recovery_distinguishes_in_place_pause_from_queued_pause(tmp_path):
    repo = JobRepository(SQLiteStore(tmp_path / "jobs.sqlite3"))
    in_place_pause = VideoJob("active-pause.mp4", status=JobStatus.PAUSED, retry_required=True)
    queued_pause = VideoJob("queued-pause.mp4", status=JobStatus.PAUSED, retry_required=False)
    repo.save(in_place_pause)
    repo.save(queued_pause)

    assert repo.recover_active_jobs() == 1
    assert repo.get(in_place_pause.id).status is JobStatus.RETRY_REQUIRED
    assert repo.get(queued_pause.id).status is JobStatus.PAUSED


def test_startup_keeps_temp_reference_when_cleanup_fails(tmp_path):
    class FailingWorkingFiles:
        def cleanup_all(self):
            raise OSError("locked")

    repo = JobRepository(SQLiteStore(tmp_path / "jobs.sqlite3"))
    job = VideoJob("lecture.mp4", status=JobStatus.TRANSCRIBING, audio_temp_path="locked.wav")
    repo.save(job)
    runner = JobRunner(output_dir=tmp_path / "outputs", job_repository=repo)
    runner.working_files = FailingWorkingFiles()

    controller = MainWindowController(ModelCatalog.load("resources/models.json"), job_runner=runner)

    restored = controller.get_job(job.id)
    assert restored.status is JobStatus.RETRY_REQUIRED
    assert restored.audio_temp_path == "locked.wav"
