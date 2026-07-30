from ai_subtitle_studio.workers.worker_events import WorkerEvent, error_event, pause_pending_event, progress_event


def test_worker_event_envelope_and_payloads():
    event = progress_event("job1", 20, "extracting_audio", "clip")
    assert event.event_id
    assert event.job_id == "job1"
    assert event.event_type == "job.progress"
    assert event.payload["percent"] == 20
    assert "api_key" not in str(event.payload).lower()

def test_error_and_pause_events():
    err = error_event("job1", "audio", "failed")
    pause = pause_pending_event("job1", "transcribing")
    assert err.payload["retry_allowed"] is True
    assert pause.event_type == "pause.pending_checkpoint"
    assert "điểm kiểm tra" in pause.payload["message"].lower()