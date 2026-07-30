# STT Engine Contract

## Purpose

Define the core STT boundary so the app can use WhisperX today and add other engines later without changing queue, UI or export logic.

## Interface

`STTEngine` is implemented as a Python `Protocol` or abstract base class.

```text
transcribe(request: TranscriptionRequest, progress: ProgressSink, cancel: CancelToken) -> TranscriptionResult
```

## TranscriptionRequest

- `job_id`: Video job id.
- `audio_path`: Extracted audio path.
- `model_id`: Runtime-selected model id from validated `models.json`.
- `device`: Must be `cuda` for WhisperX implementation.
- `compute_type`: Must be `float16` for WhisperX implementation.
- `model_cache_dir`: Directory for model download/cache.
- `language_hint`: Defaults to English for this feature.

No VAD field is allowed in this request.

## WhisperX Invariants

- Implementation must call WhisperX only through `WhisperXEngine`.
- `vad_method="pyannote"` is hard-coded inside `WhisperXEngine` when loading the model.
- No VAD field or toggle may be accepted from UI, config, CLI, request models or job persistence.
- `model.transcribe()` must not receive the obsolete `vad_filter` keyword for WhisperX 3.8.6.
- STT must fail before transcribe if no valid NVIDIA/CUDA GPU is available.
- GPU STT must acquire the global STT lock before WhisperX transcribe/alignment.
- Model id must come from validated model catalog, not UI hard-coding.

## Result

`TranscriptionResult` contains:
- `language`: Detected or selected language.
- `segments`: Sentence/cue-level segments suitable for SRT.
- `word_timings`: Word-level timing data used to refine cue start/end times.
- `warnings`: Non-fatal alignment warnings.

## Errors

- `GpuUnavailableError`: No valid NVIDIA/CUDA runtime.
- `ModelUnavailableError`: Selected model cannot be loaded/downloaded.
- `AudioReadError`: Extracted audio cannot be read.
- `TranscriptionCanceled`: User canceled job.
- `TranscriptionFailed`: WhisperX returned an unrecoverable failure.
