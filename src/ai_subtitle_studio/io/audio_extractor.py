"""ffmpeg audio extraction service."""

from __future__ import annotations

import subprocess
from pathlib import Path

class AudioExtractionError(RuntimeError): pass
class AudioExtractionCanceled(AudioExtractionError): pass

class AudioExtractor:
    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        self.ffmpeg_path = ffmpeg_path
    def extract(self, video_path: str | Path, output_audio_path: str | Path, cancel=None) -> Path:
        video = Path(video_path); output = Path(output_audio_path)
        if video.suffix.lower() != ".mp4":
            raise AudioExtractionError("Chỉ hỗ trợ đầu vào .mp4")
        output.parent.mkdir(parents=True, exist_ok=True)
        command = [self.ffmpeg_path, "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(output)]
        process = None
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout = ""
            stderr = ""
            while True:
                if cancel is not None and cancel.is_cancel_requested():
                    process.terminate()
                    try:
                        process.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.communicate(timeout=5)
                    raise AudioExtractionCanceled("Đã hủy trích audio")
                try:
                    stdout, stderr = process.communicate(timeout=0.1)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if process.returncode:
                detail = (stderr or stdout or "").strip()
                raise AudioExtractionError(detail or "ffmpeg chạy thất bại")
        except FileNotFoundError as exc:
            raise AudioExtractionError("Không tìm thấy ffmpeg executable") from exc
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                process.wait()
        return output
