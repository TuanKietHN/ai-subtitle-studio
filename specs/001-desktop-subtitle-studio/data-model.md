# Data Model: Desktop Subtitle Studio

## Overview

The application is local-first. QSettings stores user preferences; SQLite stores persisted queue/job history, generated subtitle metadata and recovery state. API key values are never stored in SQLite or QSettings; only provider key status and credential aliases are persisted.

## Entities

### VideoJob

Represents one source video in the processing queue.

**Fields**:
- `id`: Stable UUID generated when the video is added.
- `source_path`: Absolute path to the `.mp4` file.
- `source_fingerprint`: File identity derived from path, size and modified time for duplicate detection.
- `display_name`: File name shown in queue.
- `status`: Current `JobStatus`.
- `selected_model_id`: Whisper model id from `models.json`.
- `translation_provider_id`: `google_cloud_v3` or `deepseek_chat` when translation is requested.
- `gpu_id`: Selected GPU identifier at job start.
- `progress_percent`: 0-100 aggregate progress.
- `progress_label`: Current user-visible step.
- `pause_requested`: Boolean flag for pause at safe checkpoint.
- `cancel_requested`: Boolean flag for best-effort cancellation.
- `retry_required`: Boolean set when app closes mid-run or a recoverable job fails.
- `error_code`: Stable error category when failed.
- `error_message`: User-visible error summary.
- `created_at`, `started_at`, `completed_at`, `updated_at`: Timestamps.
- `audio_temp_path`: Extracted audio path while processing.
- `english_srt_path`, `vietnamese_srt_path`, `bilingual_srt_path`: Output paths when created.

**Relationships**:
- Has many `SubtitleLine` records.
- References one `WhisperModel` by `selected_model_id`.
- References one `TranslationProviderConfig` by `translation_provider_id`.

**Validation rules**:
- `source_path` must point to a readable `.mp4` before processing starts.
- STT states require valid NVIDIA/CUDA detection.
- Only one job can be in GPU STT states at a time.
- A canceled job cannot transition to completed.
- A job restored after app shutdown during processing must be `retry_required`.

### JobStatus

Canonical job states used by UI, persistence and worker contracts.

**Values**:
- `queued`: Waiting for processing.
- `paused`: Held by user before running.
- `waiting_for_model`: Needs model download before STT.
- `downloading_model`: Model download active.
- `extracting_audio`: ffmpeg extraction active.
- `waiting_for_gpu`: Ready for STT but waiting for GPU STT lock.
- `transcribing`: WhisperX transcription active.
- `aligning`: WhisperX forced alignment active.
- `translating`: Translation batch calls active.
- `ready_for_edit`: Generated subtitles loaded into editable table.
- `exporting`: Writing `.srt` files.
- `completed`: Final requested outputs written.
- `failed`: Job stopped with recoverable or terminal error.
- `canceled`: User canceled the job.
- `retry_required`: App shutdown or interruption requires explicit retry.

**State transitions**:
- `queued` -> `paused`, `waiting_for_model`, `extracting_audio`, `canceled`.
- `paused` -> `queued`, `canceled`.
- `waiting_for_model` -> `downloading_model`, `extracting_audio`, `failed`, `canceled`.
- `downloading_model` -> `extracting_audio`, `failed`, `canceled`.
- `extracting_audio` -> `waiting_for_gpu`, `failed`, `canceled`, `paused` at checkpoint.
- `waiting_for_gpu` -> `transcribing`, `paused`, `canceled`.
- `transcribing` -> `aligning`, `failed`, `canceled`, `paused` at checkpoint.
- `aligning` -> `translating` or `ready_for_edit`, `failed`, `canceled`, `paused` at checkpoint.
- `translating` -> `ready_for_edit`, `failed`, `canceled`, `paused` at batch checkpoint.
- `ready_for_edit` -> `exporting`, `queued` for retry, `canceled`.
- `exporting` -> `completed`, `failed`.
- any active state -> `retry_required` when restored after app shutdown.

### SubtitleLine

Represents one editable SRT cue, not one word.

**Fields**:
- `id`: Stable UUID.
- `job_id`: Parent `VideoJob`.
- `sequence_number`: 1-based cue order.
- `start_ms`, `end_ms`: Cue boundaries in milliseconds, refined from word-level alignment.
- `source_text`: English text.
- `translated_text`: Vietnamese text; nullable before translation.
- `word_timings_json`: Optional JSON of word-level alignment data for diagnostics/export decisions.
- `is_edited`: True after user edits either source or translated text.
- `validation_status`: `valid`, `empty_text`, `invalid_time_range`, `too_long`.

**Validation rules**:
- `sequence_number` unique within a job.
- `start_ms < end_ms`.
- Export requires non-empty text for requested language outputs.
- Translation export requires one translated cue per source cue.

### WhisperModel

Represents a supported and/or downloaded ASR model.

**Fields**:
- `id`: Canonical id from `models.json`, e.g. `large-v3`.
- `display_name`: UI label.
- `is_default`: True only for `large-v3` in initial catalog.
- `download_state`: `not_downloaded`, `downloading`, `downloaded`, `error`, `deleting`.
- `local_path`: Model cache directory when downloaded.
- `size_bytes`: Disk size when known.
- `last_verified_at`: Last local integrity/status check.
- `error_message`: Download or validation error.

**Validation rules**:
- Catalog must contain exactly one default model and it must be `large-v3`.
- Model ids must be unique.
- A model cannot be deleted while referenced by an active job.

### ModelDownload

Represents an active or historical model download operation.

**Fields**:
- `id`: Stable UUID.
- `model_id`: Target `WhisperModel`.
- `status`: `queued`, `downloading`, `completed`, `failed`, `canceled`.
- `percent`: 0-100 when known.
- `bytes_downloaded`, `bytes_total`, `bytes_remaining`: Download byte counters.
- `speed_bytes_per_sec`: Current speed estimate.
- `error_message`: User-visible failure reason.

### TranslationProviderConfig

Represents a translation provider selection and key availability, not the secret value.

**Fields**:
- `provider_id`: `google_cloud_v3` or `deepseek_chat`.
- `display_name`: UI label.
- `credential_alias`: Key name used in Windows Credential Manager.
- `has_api_key`: Boolean derived from secret store lookup.
- `last_validated_at`: Last successful provider validation.
- `last_error`: Last provider validation or translation error.

**Validation rules**:
- Provider calls require `has_api_key=true`.
- API key values must never be persisted in SQLite, QSettings, subtitle files, logs or normal error messages.

### AppSettings

Represents user preferences stored through QSettings.

**Fields**:
- `selected_gpu_id`: Optional GPU identifier.
- `model_cache_dir`: Directory for model downloads.
- `ffmpeg_path`: Path to ffmpeg executable.
- `subtitle_edit_path`: Path to Subtitle Edit executable.
- `default_output_dir`: Directory for generated subtitle files.
- `last_model_id`: Last selected model, defaults to `large-v3` if absent or invalid.
- `last_translation_provider_id`: Last selected translation provider.
- `last_compute_profile_id`: Last explicitly confirmed GPU execution profile; nullable so hardware detection can recommend a profile on first run.

**Validation rules**:
- Paths must exist and be usable before dependent operations run.
- Invalid settings produce per-job or settings-screen errors, not app crashes.

### SystemInfoSnapshot

Represents runtime diagnostics shown in About/System Info.

**Fields**:
- `app_version`: Installed app version.
- `whisperx_version`: `importlib.metadata.version("whisperx")` result or unavailable.
- `faster_whisper_version`: `importlib.metadata.version("faster-whisper")` result or unavailable.
- `torch_cuda_version`: `torch.version.cuda` result or unavailable.
- `gpu_driver_version`: `nvidia-smi` detected driver version or unavailable.
- `detected_gpus`: List of `GpuCapabilitySnapshot` records, not only id/name strings.
- `torch_cuda_ready`: Whether Torch can initialize CUDA on the selected device.
- `effective_compute_profile_id`: Profile that would be used for a new STT job.
- `selected_model_id`: Current model id.
- `downloaded_models_size_bytes`: Total local model cache size.

**Validation rules**:
- No version value may be hard-coded.
- Missing CUDA/GPU must be reported clearly without fake placeholders.
- `nvidia-smi` success alone must not set `torch_cuda_ready=true`.

### GpuCapabilitySnapshot

Represents one detected NVIDIA GPU and the evidence used for STT compatibility decisions.

**Fields**:
- `gpu_id`: Stable CUDA/NVIDIA index used by the current process.
- `name`: Device name reported by NVIDIA/Torch.
- `driver_version`: NVIDIA driver version.
- `total_vram_bytes`, `free_vram_bytes`: Capacity and currently available device memory at detection time.
- `compute_capability`: CUDA major/minor capability when Torch can query it.
- `torch_cuda_ready`: True only after Torch CUDA availability/device initialization succeeds.
- `ctranslate2_compute_types`: Supported compute types returned for the selected CUDA device.
- `compatibility`: `supported`, `low_vram`, `driver_error`, `cuda_unavailable`, or `unsupported_compute_type`.
- `diagnostic_message`: Non-secret actionable explanation shown in System Info/Settings.

**Validation rules**:
- A GPU can be listed for diagnostics while `torch_cuda_ready=false`, but cannot start STT.
- VRAM values must be byte counts internally and formatted only at the UI boundary.
- Selection uses `gpu_id`; no logic may branch on a hard-coded marketing name such as `RTX 2050`.

### GpuExecutionProfile

Config-driven STT resource profile resolved from GPU capability and the selected model.

**Fields**:
- `profile_id`: Stable id such as `low-vram-4gb`, `balanced-6gb`, or `quality-8gb-plus`.
- `minimum_vram_bytes`: Capacity floor for automatic recommendation.
- `recommended_model_ids`: Ordered model ids from `models.json`.
- `compute_type`: Effective CTranslate2 compute type.
- `batch_size`: Positive WhisperX transcription batch size.
- `allow_diarization`: False for the RC5 4 GiB profile.
- `oom_retry_batch_size`: Optional smaller batch used for the single bounded retry.
- `user_confirmation_required`: Whether applying the profile changes the user's selected model.

**RC5 4 GiB profile**:
- Recommends `small.en` for English input and `small` only when multilingual recognition is needed.
- Uses `int8_float16` when reported by CTranslate2 and `batch_size=1`.
- Does not change the catalog default away from `large-v3`.
- Does not expose or alter mandatory `vad_method="pyannote"`.

**Validation rules**:
- Model ids must resolve through `models.json`; the resolver cannot hard-code dropdown contents.
- The effective compute type must be supported by the selected device.
- `batch_size >= 1` and OOM retry count is at most one per STT attempt.
- A profile may recommend a different model but cannot silently replace the user's selection.

## SQLite Persistence Notes

Minimum tables:
- `video_jobs`
- `subtitle_lines`
- `model_downloads`
- `provider_status`
- `schema_migrations`

QSettings remains the source for current settings. SQLite stores snapshots needed for queue recovery and job history.

## Release and Installation Records

The following entities are build/release records, not SQLite application tables. They are serialized into release manifests, checksums, installer metadata and CI artifacts.

### BuildIdentity

Identifies one reproducible Windows build.

**Fields**:
- `app_version`: Semantic version sourced from `pyproject.toml`.
- `git_commit`: Full commit SHA.
- `git_tag`: Release or release-candidate tag.
- `built_at_utc`: Build timestamp in UTC.
- `python_version`: Exact release interpreter version.
- `platform`: `windows-x64`.
- `whisperx_version`: Exact stable version included.
- `torch_version`: Exact Torch version and CUDA wheel suffix.
- `cuda_runtime_version`: CUDA runtime family bundled by Torch.
- `pyinstaller_version`: Exact packager version.
- `dependency_manifest_sha256`: Digest of the complete dependency inventory.

**Validation rules**:
- `app_version`, tag and installer version must match.
- `git_commit` must be the commit targeted by `git_tag`.
- A published tag may map to only one immutable `BuildIdentity`.
- Stable builds may not include a WhisperX pre-release.

### ReleaseArtifact

Represents one file attached to a GitHub Release.

**Fields**:
- `name`: Stable filename including app version.
- `kind`: `online_installer`, `runtime_volume`, `manifest`, `checksums`, `sbom`, `notices`.
- `size_bytes`: Exact uploaded size.
- `sha256`: Lowercase SHA-256 digest.
- `download_url`: Version-specific HTTPS GitHub Release URL.
- `required`: Whether installation requires this artifact.
- `volume_index`: Optional 1-based runtime volume position.
- `signature_status`: `signed`, `unsigned_prerelease`, or `not_applicable`.

**Validation rules**:
- Every artifact must be below 2 GiB; runtime volumes use a stricter release limit below 1.9 GiB.
- Names, sizes and hashes must match the uploaded file exactly.
- Required runtime volume indices must be contiguous and unique.
- Stable installer/app executables must have `signature_status=signed`.
- An artifact cannot be replaced after its tag has been published.

### ReleaseManifest

Machine-readable contract used by verification tooling and as the source for installer download metadata.

**Fields**:
- `schema_version`: Manifest schema version.
- `release`: One `BuildIdentity`.
- `channel`: `rc`, `prerelease`, or `stable`.
- `minimum_windows_version`: Minimum supported Windows version.
- `architecture`: `x64`.
- `install_scope`: `current_user`.
- `installed_size_bytes`: Required disk space after extraction.
- `temporary_space_bytes`: Required temporary disk space during install.
- `runtime_bundle_id`: Deterministic identity for the complete ordered runtime payload.
- `artifacts`: Ordered list of `ReleaseArtifact`.

**Validation rules**:
- Stable channel requires all stable release gates to pass.
- All required artifacts must be present and hash-valid before publish.
- Installer-embedded URLs/hashes must be generated from the same manifest.
- Manifest validation must fail closed on missing or unknown required fields.
- `runtime_bundle_id` must change when any ordered runtime volume hash/size or frozen build identity changes.

### RuntimeBundleIdentity

Identifies whether a verified cached or installed runtime can be reused independently from its release filename.

**Fields**:
- `schema_version`: Runtime marker schema.
- `runtime_bundle_id`: Lowercase digest derived from ordered volume hashes/sizes and `BuildIdentity` runtime fields.
- `volume_names`: Ordered source asset names.
- `volume_sha256`: Ordered SHA-256 values.
- `installed_at_utc`: Successful activation time for the local marker.
- `app_version`: Release that activated the marker.

**Validation rules**:
- Same-runtime upgrade skip is allowed only after the installed marker parses and its `runtime_bundle_id` equals the new manifest.
- Missing, malformed or mismatched markers trigger a full verified install.
- A partial cache or filename match can never substitute for the identity/hash checks.

### InstallerDownloadCacheEntry

Represents one versioned runtime volume in persistent installer cache.

**Fields**:
- `runtime_bundle_id`: Parent runtime identity.
- `volume_index`, `asset_name`, `download_url`: Expected release metadata.
- `expected_size_bytes`, `expected_sha256`: Integrity contract.
- `local_path`: Final cache file path.
- `partial_path`: `.part` path used by resumable transfer.
- `bits_job_id`: Optional persisted BITS job id.
- `bytes_downloaded`: Current partial size/progress.
- `state`: `missing`, `partial`, `transferring`, `verified`, `invalid`, `expired`.
- `last_attempt_at_utc`, `verified_at_utc`: Cache lifecycle timestamps.

**Validation rules**:
- Only `verified` entries may be extraction inputs.
- Wrong bundle id/hash/size invalidates and removes the cache entry before retry.
- Cancel/network failure preserves a valid `.part`; extraction/activation failure preserves verified complete cache.
- Retention cleanup may remove expired installer cache but never model cache or subtitle output.

### InstallerLifecycleState

Ephemeral state used to make fresh install, upgrade and rollback messages/actions deterministic.

**Fields**:
- `mode`: `fresh_install`, `upgrade_same_runtime`, `upgrade_new_runtime`, or `repair`.
- `app_dir_created`: Whether `{app}` exists and is writable.
- `application_running`: Whether Restart Manager/app mutex reports the old app active.
- `active_runtime_path`: `{app}\runtime`.
- `staging_runtime_path`: `{app}\runtime.staging`.
- `previous_runtime_path`: `{app}\runtime.previous`.
- `download_source`: `setup_directory`, `verified_cache`, `bits`, `inno_fallback`, or `skipped_same_runtime`.
- `activation_state`: `not_started`, `staged`, `previous_saved`, `active`, `rolled_back`, `failed`.

**Validation rules**:
- `{app}` must be created before staging or rename.
- All three runtime paths must resolve under the exact install directory and on the same volume.
- A running old app stops the lifecycle before mutation unless it closes successfully.
- Fresh-install errors must not claim an old runtime was preserved.
- `runtime.staging` is removed after success, cancellation, handled failure and uninstall.

### UninstallSelection

Records explicit user choices for one uninstall session; it is not persisted as an opt-out default.

**Fields**:
- `remove_application`: Always true for normal uninstall.
- `remove_private_app_data`: Checkbox for model, installer cache, logs, SQLite history, QSettings and API keys; default false.
- `remove_outputs`: Separate checkbox for generated subtitle outputs; default false.
- `output_path_display`: Exact path shown before destructive confirmation.
- `owned_output_files`: Files known from application metadata when output is custom.
- `output_confirmation_granted`: Second confirmation required before output deletion.
- `cleanup_failures`: Items that could not be removed and must be reported/logged.

**Validation rules**:
- The two optional checkboxes are independent and unchecked by default.
- Credential cleanup runs through the app/keyring before runtime deletion.
- Custom output cleanup deletes only `owned_output_files`, never the entire arbitrary directory.
- Source video paths are never uninstall targets.

### InstallationLayout

Defines ownership boundaries between application binaries and user data.

**Paths**:
- `install_dir`: `%LOCALAPPDATA%\Programs\AI Subtitle Studio`
- `data_root`: `%LOCALAPPDATA%\AI Subtitle Studio`
- `database_path`: `%LOCALAPPDATA%\AI Subtitle Studio\ai_subtitle_studio.sqlite3`
- `model_cache_dir`: `%LOCALAPPDATA%\AI Subtitle Studio\models`
- `log_dir`: `%LOCALAPPDATA%\AI Subtitle Studio\logs`
- `installer_cache_dir`: `%LOCALAPPDATA%\AI Subtitle Studio\installer-cache\<runtime_bundle_id>`
- `default_output_dir`: `%USERPROFILE%\Documents\AI Subtitle Studio\outputs`
- `active_runtime_dir`: `%LOCALAPPDATA%\Programs\AI Subtitle Studio\runtime`
- `staging_runtime_dir`: `%LOCALAPPDATA%\Programs\AI Subtitle Studio\runtime.staging`
- `previous_runtime_dir`: `%LOCALAPPDATA%\Programs\AI Subtitle Studio\runtime.previous`

**Validation rules**:
- Installer owns only `install_dir`, shortcuts and uninstall registration.
- Upgrade may replace `install_dir` but must preserve all user-data paths.
- Installer may read/write `installer_cache_dir` for verified download reuse, but default uninstall preserves it with other user data.
- Uninstall must preserve database, model cache, settings, credentials and output by default.
- Optional private-data cleanup may remove `data_root` only after credential/QSettings cleanup and must not imply output deletion.
- Optional output cleanup follows `UninstallSelection` ownership and double-confirmation rules.
- The app must not write persistent data inside PyInstaller `_internal`, `_MEIPASS` or a protected system directory.
