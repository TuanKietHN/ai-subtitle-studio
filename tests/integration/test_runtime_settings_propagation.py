from ai_subtitle_studio.domain.entities import VideoJob
from ai_subtitle_studio.stt.base import TranscriptionResult
from ai_subtitle_studio.workers.job_runner import JobRunner
from ai_subtitle_studio.workers.worker_events import WorkerControlToken


class CapturingSTT:
    def __init__(self):
        self.request = None

    def transcribe(self, request, progress=None, cancel=None):
        self.request = request
        return TranscriptionResult("en", [])


class FakeAudioExtractor:
    def extract(self, source, target):
        return target


def test_runner_propagates_model_cache_and_selected_gpu(tmp_path):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"video")
    stt = CapturingSTT()
    runner = JobRunner(
        audio_extractor=FakeAudioExtractor(),
        stt_engine=stt,
        output_dir=tmp_path / "outputs",
        model_cache_dir=tmp_path / "models",
        selected_gpu_id="2",
        compute_type="int8_float16",
        batch_size=1,
        execution_profile_id="low-vram-4gb",
    )

    runner.process_job(VideoJob(str(source)), WorkerControlToken())

    assert stt.request.model_cache_dir == str(tmp_path / "models")
    assert stt.request.gpu_id == "2"
    assert stt.request.compute_type == "int8_float16"
    assert stt.request.batch_size == 1
    assert stt.request.execution_profile_id == "low-vram-4gb"


def test_job_gpu_override_wins_over_runtime_setting(tmp_path):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"video")
    stt = CapturingSTT()
    runner = JobRunner(
        audio_extractor=FakeAudioExtractor(),
        stt_engine=stt,
        output_dir=tmp_path / "outputs",
        selected_gpu_id="0",
    )
    job = VideoJob(str(source), gpu_id="1")

    runner.process_job(job, WorkerControlToken())

    assert stt.request.gpu_id == "1"
