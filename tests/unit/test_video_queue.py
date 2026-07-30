from ai_subtitle_studio.workers.job_runner import VideoQueueService


def test_queue_add_rejects_non_mp4_and_duplicates(tmp_path):
    video = tmp_path / "lecture.mp4"
    video.write_bytes(b"video")
    note = tmp_path / "note.txt"
    note.write_text("x")
    queue = VideoQueueService()
    result = queue.add_files([video, note, video])
    assert len(result.added) == 1
    assert result.rejected[0][0].endswith("note.txt")
    assert result.duplicates == [str(video)]
    assert queue.jobs[0].display_name == "lecture.mp4"