import subprocess

import pytest

from ai_subtitle_studio.io.audio_extractor import AudioExtractionCanceled, AudioExtractor
from ai_subtitle_studio.workers.worker_events import CancelToken


class FakeProcess:
    def __init__(self, running=True):
        self.returncode = None if running else 0
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.returncode = -9

    def wait(self, timeout=None):
        return self.returncode

    def communicate(self, timeout=None):
        if self.returncode is None:
            raise subprocess.TimeoutExpired("ffmpeg", timeout)
        return "", ""


def test_audio_extractor_terminates_ffmpeg_when_canceled(tmp_path, monkeypatch):
    process = FakeProcess(running=True)
    monkeypatch.setattr("ai_subtitle_studio.io.audio_extractor.subprocess.Popen", lambda *args, **kwargs: process)
    token = CancelToken()
    token.cancel()

    with pytest.raises(AudioExtractionCanceled):
        AudioExtractor().extract(tmp_path / "video.mp4", tmp_path / "audio.wav", cancel=token)

    assert process.terminated is True


def test_audio_extractor_returns_target_after_success(tmp_path, monkeypatch):
    process = FakeProcess(running=False)
    monkeypatch.setattr("ai_subtitle_studio.io.audio_extractor.subprocess.Popen", lambda *args, **kwargs: process)
    target = tmp_path / "work" / "audio.wav"

    result = AudioExtractor().extract(tmp_path / "video.mp4", target)

    assert result == target
    assert target.parent.exists()
