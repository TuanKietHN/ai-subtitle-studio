# UI Contract

## Main Window

The main window must expose these user actions:
- Add `.mp4` files via file picker.
- Add `.mp4` files via drag and drop.
- Start queue processing.
- Pause, resume, cancel and retry individual jobs.
- Select Whisper model from model catalog.
- Select translation provider.
- Open Settings.
- Open Model Manager.
- Open About/System Info.

## Queue Table

Each row displays:
- Video name.
- Status.
- Current step/progress.
- Selected model.
- Translation provider.
- Output status.
- Error summary if present.
- Row actions: pause/resume, cancel, retry, open output when available.

Rules:
- Multiple selected files are added in selection/drop order.
- Invalid non-`.mp4` files are rejected or marked invalid before processing.
- Duplicate source videos are surfaced to the user before adding another job.
- Only one job can show GPU STT active at a time.

## Subtitle Table

Columns:
- Sequence number.
- Timestamp.
- Source text.
- Translated text.
- Validation status.

Rules:
- Source and translated text are editable.
- Empty export text or invalid timestamp shows row-level warning.
- Edits are used on subsequent exports.
- Rows represent readable cue groups, not one word per row.

## Settings

Settings must allow:
- Select GPU when multiple GPUs are detected.
- Choose model cache directory.
- Choose ffmpeg executable.
- Choose Subtitle Edit executable.
- Choose default output directory.
- Enter/update API key for Google Cloud Translation API v3.
- Enter/update API key for DeepSeek Chat API.

Rules:
- API key fields are masked after entry.
- API key values are stored in OS secret storage, not QSettings.
- Invalid executable/path settings show actionable errors.

## About/System Info

Displays:
- App version.
- Installed WhisperX version.
- Installed faster-whisper version.
- CUDA version.
- GPU/driver information.
- Selected model.
- Total downloaded model size.

Rules:
- Version values are read at runtime.
- Missing GPU/CUDA data is shown as unavailable, not faked.
