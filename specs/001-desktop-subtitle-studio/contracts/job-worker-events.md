# Job Worker Events Contract

## Purpose

Define messages emitted from background workers to the PySide6 UI. Heavy work must never update widgets directly; workers emit events/signals and UI consumes them on the main thread.

## Event Envelope

Every event has:
- `event_id`: Stable UUID.
- `job_id`: Related VideoJob id, nullable for app-level events.
- `event_type`: One of the event types below.
- `timestamp`: ISO timestamp.
- `payload`: Event-specific object.

## Event Types

### `job.status_changed`

Payload:
- `old_status`
- `new_status`
- `message`

### `job.progress`

Payload:
- `percent`: 0-100.
- `step`: User-visible current step.
- `detail`: Optional detail such as current batch or file name.

### `job.error`

Payload:
- `error_code`
- `message`: User-safe reason.
- `recoverable`: Boolean.
- `retry_allowed`: Boolean.

### `job.output_ready`

Payload:
- `english_srt_path`
- `vietnamese_srt_path`
- `bilingual_srt_path`

### `model.download_progress`

Payload:
- `model_id`
- `percent`
- `speed_bytes_per_sec`
- `bytes_remaining`

### `pause.pending_checkpoint`

Payload:
- `current_step`
- `message`: Must explain that pause will apply after the current safe checkpoint.

### `system.info_ready`

Payload:
- `whisperx_version`
- `faster_whisper_version`
- `torch_cuda_version`
- `gpu_driver_version`
- `detected_gpus`
- `selected_model_id`
- `downloaded_models_size_bytes`
- `app_version`

## Rules

- Worker events must not include API key values.
- A job can emit progress while paused is pending, but UI must show checkpoint-pending state.
- `job.output_ready` must only be emitted after all requested final outputs are valid.
- Failed or canceled jobs must not emit final output as completed.
- GPU STT worker must emit `waiting_for_gpu` if another STT job holds the lock.
