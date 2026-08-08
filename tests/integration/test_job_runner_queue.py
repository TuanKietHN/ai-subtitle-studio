import logging
from threading import Event, Thread
import time

from ai_subtitle_studio.domain.entities import VideoJob
from ai_subtitle_studio.domain.job_state import JobStatus
from ai_subtitle_studio.config.model_catalog import ModelCatalog
from ai_subtitle_studio.io.audio_extractor import AudioExtractionCanceled
from ai_subtitle_studio.stt.base import GpuOutOfMemoryError, TranscriptionCanceled, TranscriptionResult
from ai_subtitle_studio.ui.main_window import MainWindowController
from ai_subtitle_studio.workers.job_runner import JobRunner
from ai_subtitle_studio.workers.worker_events import WorkerControlToken


class FakeAudioExtractor:
    def extract(self, source, target):
        return target


class FakeSTT:
    def __init__(self):
        self.calls = []
    def transcribe(self, request, progress=None, cancel=None):
        self.calls.append(request.job_id)
        if progress: progress(50, "transcribing", None)
        return TranscriptionResult("en", [{"start": 0, "end": 1, "text": "Hello world.", "words": [{"word": "Hello", "start": 0, "end": 0.4}, {"word": "world.", "start": 0.4, "end": 1}]}])


class FailingSTT:
    def transcribe(self, request, progress=None, cancel=None):
        raise RuntimeError("worker stt exploded")


class OutOfMemorySTT:
    def transcribe(self, request, progress=None, cancel=None):
        raise GpuOutOfMemoryError("CUDA out of memory after one bounded retry")


def test_job_runner_processes_sequentially_and_writes_english_srt(tmp_path):
    v1 = tmp_path / "one.mp4"; v1.write_bytes(b"1")
    v2 = tmp_path / "two.mp4"; v2.write_bytes(b"2")
    stt = FakeSTT()
    runner = JobRunner(audio_extractor=FakeAudioExtractor(), stt_engine=stt, output_dir=tmp_path)
    jobs = [VideoJob(str(v1)), VideoJob(str(v2))]
    result = runner.process_queue(jobs, WorkerControlToken())
    assert [job.status for job in result] == [JobStatus.COMPLETED, JobStatus.COMPLETED]
    assert stt.calls == [jobs[0].id, jobs[1].id]
    assert (tmp_path / "one.en.srt").exists()
    assert (tmp_path / "two.en.srt").exists()
    assert sum(1 for e in runner.events if e.event_type == "job.output_ready") == 2


def test_job_runner_logs_worker_exception_traceback_before_failure(tmp_path, caplog):
    caplog.set_level(logging.ERROR)
    video = tmp_path / "broken.mp4"; video.write_bytes(b"1")
    job = VideoJob(str(video))
    runner = JobRunner(audio_extractor=FakeAudioExtractor(), stt_engine=FailingSTT(), output_dir=tmp_path)
    result = runner.process_job(job, WorkerControlToken())
    assert result.status == JobStatus.FAILED
    assert any(record.exc_info and f"Worker job {job.id} failed" in record.message for record in caplog.records)


def test_job_runner_exposes_stable_gpu_out_of_memory_error(tmp_path):
    video = tmp_path / "four-gib.mp4"
    video.write_bytes(b"1")
    job = VideoJob(str(video))
    runner = JobRunner(audio_extractor=FakeAudioExtractor(), stt_engine=OutOfMemorySTT(), output_dir=tmp_path)

    result = runner.process_job(job, WorkerControlToken())

    assert result.status == JobStatus.FAILED
    assert result.error_code == "gpu_out_of_memory"
    assert "không đủ VRAM" in result.error_message
    error_events = [event for event in runner.events if event.event_type == "job.error"]
    assert error_events[-1].payload["error_code"] == "gpu_out_of_memory"



class PausingOnceSTT(FakeSTT):
    def __init__(self, pause_job):
        super().__init__()
        self.pause_job = pause_job
        self.paused = False

    def transcribe(self, request, progress=None, cancel=None):
        self.calls.append(request.job_id)
        if request.job_id == self.pause_job.id and not self.paused:
            self.paused = True
            self.pause_job.pause_requested = True
        if progress:
            progress(50, "transcribing", None)
        return TranscriptionResult("en", [{"start": 0, "end": 1, "text": "Hello world.", "words": [{"word": "Hello", "start": 0, "end": 0.4}, {"word": "world.", "start": 0.4, "end": 1}]}])


def test_pause_checkpoint_keeps_job_paused_allows_resume_and_next_jobs(tmp_path):
    v1 = tmp_path / "one.mp4"; v1.write_bytes(b"1")
    v2 = tmp_path / "two.mp4"; v2.write_bytes(b"2")
    jobs = [VideoJob(str(v1)), VideoJob(str(v2))]
    stt = PausingOnceSTT(jobs[0])
    runner = JobRunner(audio_extractor=FakeAudioExtractor(), stt_engine=stt, output_dir=tmp_path)

    runner.process_queue(jobs, WorkerControlToken())

    assert jobs[0].status == JobStatus.PAUSED
    assert jobs[0].pause_requested is False
    assert jobs[0].error_code is None
    assert jobs[1].status == JobStatus.COMPLETED
    assert (tmp_path / "two.en.srt").exists()
    assert not [event for event in runner.events if event.job_id == jobs[0].id and event.event_type == "job.error"]

    runner.retry(jobs[0])
    assert jobs[0].status == JobStatus.QUEUED
    assert jobs[0].pause_requested is False

    runner.process_queue([jobs[0]], WorkerControlToken())

    assert jobs[0].status == JobStatus.COMPLETED
    assert (tmp_path / "one.en.srt").exists()


def test_control_token_pause_is_consumed_before_next_job(tmp_path):
    v1 = tmp_path / "one.mp4"; v1.write_bytes(b"1")
    v2 = tmp_path / "two.mp4"; v2.write_bytes(b"2")
    jobs = [VideoJob(str(v1)), VideoJob(str(v2))]
    stt = FakeSTT()
    runner = JobRunner(audio_extractor=FakeAudioExtractor(), stt_engine=stt, output_dir=tmp_path)
    control = WorkerControlToken()
    control.request_pause()

    runner.process_queue(jobs, control)

    assert jobs[0].status == JobStatus.PAUSED
    assert jobs[1].status == JobStatus.COMPLETED
    assert stt.calls == [jobs[1].id]
    assert control.is_pause_requested() is False

class CancelAwareSTT(FakeSTT):
    def __init__(self):
        super().__init__()
        self.first_started = Event()
        self.second_started = Event()

    def transcribe(self, request, progress=None, cancel=None):
        self.calls.append(request.job_id)
        if len(self.calls) == 1:
            self.first_started.set()
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if cancel and cancel.is_cancel_requested():
                    raise TranscriptionCanceled("canceled")
                time.sleep(0.01)
            raise AssertionError("cancel was not delivered to the active STT job")
        if len(self.calls) == 2:
            self.second_started.set()
        if progress:
            progress(50, "transcribing", None)
        return TranscriptionResult("en", [{"start": 0, "end": 1, "text": "Next job.", "words": []}])


def test_cancel_then_remove_running_job_does_not_stall_remaining_queue(tmp_path):
    videos = []
    for name in ("one.mp4", "two.mp4", "three.mp4"):
        path = tmp_path / name
        path.write_bytes(b"1")
        videos.append(path)
    jobs = [VideoJob(str(path)) for path in videos]
    stt = CancelAwareSTT()
    runner = JobRunner(audio_extractor=FakeAudioExtractor(), stt_engine=stt, output_dir=tmp_path)
    controller = MainWindowController(ModelCatalog.load("resources/models.json"), job_runner=runner)
    controller.queue_service.jobs = jobs
    controller.queue_service._fingerprints = {job.source_fingerprint for job in jobs if job.source_fingerprint}
    control = WorkerControlToken()

    thread = Thread(target=lambda: controller.start_queue(control), daemon=True)
    thread.start()
    assert stt.first_started.wait(1)

    controller.cancel_job(jobs[0])
    blocked = controller.remove_jobs([jobs[0].id])

    assert blocked == [jobs[0].id]
    assert jobs[0] in controller.queue_service.jobs
    assert stt.second_started.wait(2)

    thread.join(3)
    assert not thread.is_alive()
    controller.remove_jobs([jobs[0].id])

    assert [job.id for job in controller.queue_service.jobs] == [jobs[1].id, jobs[2].id]
    assert jobs[0].status == JobStatus.CANCELED
    assert jobs[1].status == JobStatus.COMPLETED
    assert jobs[2].status == JobStatus.COMPLETED
    assert stt.calls == [jobs[0].id, jobs[1].id, jobs[2].id]


class CooperativePauseSTT(FakeSTT):
    def __init__(self):
        super().__init__()
        self.first_progress = Event()
        self.allow_checkpoint = Event()
        self.resumed = Event()

    def transcribe(self, request, progress=None, cancel=None):
        self.calls.append(request.job_id)
        if progress:
            progress(40, "transcribing", "Nhận dạng 40.0%")
        self.first_progress.set()
        assert self.allow_checkpoint.wait(1)
        if cancel and hasattr(cancel, "wait_if_paused"):
            cancel.wait_if_paused("transcribing")
        if cancel and cancel.is_cancel_requested():
            raise TranscriptionCanceled("Đã hủy")
        self.resumed.set()
        if progress:
            progress(60, "transcribing", "Nhận dạng 60.0%")
        return TranscriptionResult("en", [{"start": 0, "end": 1, "text": "Paused safely.", "words": []}])


def _wait_for_status(job, status, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if job.status is status:
            return True
        time.sleep(0.01)
    return False


def _wait_for(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_active_transcription_really_blocks_until_resume(tmp_path):
    video = tmp_path / "pause.mp4"
    video.write_bytes(b"1")
    job = VideoJob(str(video))
    stt = CooperativePauseSTT()
    runner = JobRunner(audio_extractor=FakeAudioExtractor(), stt_engine=stt, output_dir=tmp_path)
    control = WorkerControlToken()
    thread = Thread(target=lambda: runner.process_job(job, control), daemon=True)
    thread.start()
    assert stt.first_progress.wait(1)

    runner.request_pause(job)
    control.request_pause()
    stt.allow_checkpoint.set()

    assert _wait_for_status(job, JobStatus.PAUSED)
    assert _wait_for(lambda: any(event.event_type == "job.status_changed" for event in runner.events))
    event_count = len(runner.events)
    time.sleep(0.1)
    assert thread.is_alive()
    assert job.status is JobStatus.PAUSED
    assert len(runner.events) == event_count
    assert not stt.resumed.is_set()

    runner.resume_active(job)
    control.resume()
    thread.join(2)

    assert not thread.is_alive()
    assert stt.resumed.is_set()
    assert job.status is JobStatus.COMPLETED


def test_shutdown_while_transcription_is_paused_unblocks_and_requires_retry(tmp_path):
    video = tmp_path / "shutdown.mp4"
    video.write_bytes(b"1")
    job = VideoJob(str(video))
    stt = CooperativePauseSTT()
    runner = JobRunner(audio_extractor=FakeAudioExtractor(), stt_engine=stt, output_dir=tmp_path)
    control = WorkerControlToken()
    thread = Thread(target=lambda: runner.process_job(job, control), daemon=True)
    thread.start()
    assert stt.first_progress.wait(1)
    runner.request_pause(job)
    control.request_pause()
    stt.allow_checkpoint.set()
    assert _wait_for_status(job, JobStatus.PAUSED)

    control.request_shutdown()
    thread.join(2)

    assert not thread.is_alive()
    assert job.status is JobStatus.RETRY_REQUIRED
    assert job.retry_required is True
    assert "Bắt đầu xử lý" in job.progress_label


class BlockingAudioExtractor:
    def __init__(self):
        self.started = Event()

    def extract(self, source, target, cancel=None):
        target.write_bytes(b"partial")
        self.started.set()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if cancel and cancel.is_cancel_requested():
                raise AudioExtractionCanceled("Đã hủy trích audio")
            time.sleep(0.01)
        raise AssertionError("shutdown was not delivered to audio extraction")


def test_shutdown_during_audio_extraction_requires_retry_and_cleans_partial_file(tmp_path):
    video = tmp_path / "extracting.mp4"
    video.write_bytes(b"1")
    job = VideoJob(str(video))
    extractor = BlockingAudioExtractor()
    runner = JobRunner(audio_extractor=extractor, stt_engine=FakeSTT(), output_dir=tmp_path)
    control = WorkerControlToken()
    thread = Thread(target=lambda: runner.process_job(job, control), daemon=True)
    thread.start()
    assert extractor.started.wait(1)

    control.request_shutdown()
    thread.join(2)

    assert not thread.is_alive()
    assert job.status is JobStatus.RETRY_REQUIRED
    assert "Bắt đầu xử lý" in job.progress_label
    assert job.audio_temp_path is None
    assert not runner.working_files.job_dir(job.id).exists()


class WritingAudioExtractor:
    def extract(self, source, target):
        target.write_bytes(b"temporary audio")
        return target


def test_job_runner_cleans_managed_audio_temp_after_job_finishes(tmp_path):
    video = tmp_path / "one.mp4"
    video.write_bytes(b"1")
    job = VideoJob(str(video))
    runner = JobRunner(audio_extractor=WritingAudioExtractor(), stt_engine=FakeSTT(), output_dir=tmp_path)

    runner.process_job(job, WorkerControlToken())

    assert job.status == JobStatus.COMPLETED
    assert job.audio_temp_path is None
    assert not runner.working_files.job_dir(job.id).exists()
    assert (tmp_path / "one.en.srt").exists()


def test_running_job_keeps_output_and_working_directory_snapshot(tmp_path):
    old_output = tmp_path / "old"
    new_output = tmp_path / "new"
    video = tmp_path / "switch.mp4"
    video.write_bytes(b"1")
    job = VideoJob(str(video))

    class SwitchingSTT(FakeSTT):
        def transcribe(self, request, progress=None, cancel=None):
            runner.set_output_dir(new_output)
            return super().transcribe(request, progress=progress, cancel=cancel)

    runner = JobRunner(audio_extractor=WritingAudioExtractor(), output_dir=old_output)
    runner.stt_engine = SwitchingSTT()
    old_working_files = runner.working_files

    runner.process_job(job, WorkerControlToken())

    assert job.status is JobStatus.COMPLETED
    assert (old_output / "switch.en.srt").exists()
    assert not (new_output / "switch.en.srt").exists()
    assert not old_working_files.job_dir(job.id).exists()
