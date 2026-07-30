# Tasks: Desktop Subtitle Studio

**Input**: Design documents from `/specs/001-desktop-subtitle-studio/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are included because the constitution gates require explicit verification for WhisperX pinning, VAD invariants, config-driven models, runtime System Info versions, worker execution, and single-GPU STT scheduling.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize Python desktop project structure, dependencies, packaging scaffolding, and model catalog resource.

- [X] T001 Create Python package directory structure from plan in `src/ai_subtitle_studio/` and test directories in `tests/`
- [X] T002 Create `pyproject.toml` with Python 3.11 project metadata, pytest config, package discovery, and dev extras
- [X] T003 Pin runtime dependencies in `pyproject.toml` including `whisperx==3.8.6` with `checked 2026-07-30` note, PySide6, httpx, torch, keyring, and PyInstaller
- [X] T004 [P] Create package marker and application metadata in `src/ai_subtitle_studio/__init__.py`
- [X] T005 [P] Create initial model catalog in `resources/models.json` with default `large-v3` plus `medium`, `large-v3-turbo`, and `distil-large-v3`
- [X] T006 [P] Create PyInstaller onedir spec scaffold in `packaging/ai-subtitle-studio.spec` including `resources/models.json` and excluding Whisper model weights
- [X] T007 Create project ignore file `.gitignore` for Python, PyInstaller, local SQLite, model cache, logs, temp files, and IDE artifacts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core contracts, persistence, settings, worker, STT, translation, and runtime diagnostics infrastructure that all user stories depend on.

**CRITICAL**: No user story work can begin until this phase is complete.

### Constitution Gate Tests

- [X] T008 [P] Add dependency pin test for `pyproject.toml` containing `whisperx==3.8.6` and `checked 2026-07-30` note in `tests/contract/test_dependency_pins.py`
- [X] T009 [P] Add model catalog contract tests for `large-v3` default and unique config-driven model IDs in `tests/contract/test_model_catalog_contract.py`
- [X] T010 [P] Add STT contract tests proving `TranscriptionRequest` has no VAD field and `WhisperXEngine` passes `vad_method="pyannote"` in `tests/contract/test_stt_engine_contract.py`
- [X] T011 [P] Add translation provider contract tests for line count/order preservation and API key redaction in `tests/contract/test_translation_provider_contract.py`
- [X] T012 [P] Add worker event contract tests for progress, error, pause checkpoint, and output-ready payloads in `tests/contract/test_worker_events_contract.py`
- [X] T013 [P] Add System Info contract tests for `importlib.metadata.version()` and non-hard-coded CUDA/GPU values in `tests/contract/test_system_info_contract.py`
- [X] T014 [P] Add GPU STT lock contract test allowing one active STT section in `tests/contract/test_gpu_lock_contract.py`

### Foundational Implementation

- [X] T015 Create domain job state enum and transition helpers in `src/ai_subtitle_studio/domain/job_state.py`
- [X] T016 Create domain entities for VideoJob, SubtitleLine, WhisperModel, ModelDownload, TranslationProviderConfig, AppSettings, and SystemInfoSnapshot in `src/ai_subtitle_studio/domain/entities.py`
- [X] T017 [P] Create subtitle validation and cue model helpers in `src/ai_subtitle_studio/domain/subtitle.py`
- [X] T018 Create SQLite schema migrations for video jobs, subtitle lines, model downloads, provider status, and schema migrations in `src/ai_subtitle_studio/persistence/migrations.py`
- [X] T019 Create SQLite connection/store abstraction in `src/ai_subtitle_studio/persistence/sqlite_store.py`
- [X] T020 Create repository layer for jobs, subtitle lines, model downloads, and provider status in `src/ai_subtitle_studio/persistence/repositories.py`
- [X] T021 Create QSettings wrapper for non-secret settings in `src/ai_subtitle_studio/config/app_settings.py`
- [X] T022 Create model catalog loader and validator for `resources/models.json` in `src/ai_subtitle_studio/config/model_catalog.py`
- [X] T023 Create System Info provider with runtime package/CUDA/GPU detection in `src/ai_subtitle_studio/config/system_info.py`
- [X] T024 Create STT Protocol, request/result/error types without VAD argument in `src/ai_subtitle_studio/stt/base.py`
- [X] T025 Create process-local GPU STT semaphore/lock in `src/ai_subtitle_studio/stt/gpu_lock.py`
- [X] T026 Create WhisperX engine wrapper with `device="cuda"`, `compute_type="float16"`, runtime model id, GPU preflight, and hard-coded `vad_method="pyannote"` in `src/ai_subtitle_studio/stt/whisperx_engine.py`
- [X] T027 Create TranslationProvider Protocol, request/result/error types, and credential abstraction in `src/ai_subtitle_studio/translation/base.py`
- [X] T028 Create translation provider registry/factory in `src/ai_subtitle_studio/translation/registry.py`
- [X] T029 Create worker event dataclasses and cancel/progress token types in `src/ai_subtitle_studio/workers/worker_events.py`
- [X] T030 Create Qt worker runner skeleton using QThread/QThreadPool signals in `src/ai_subtitle_studio/workers/job_runner.py`
- [X] T031 Create audio extraction service shelling out to configured ffmpeg path in `src/ai_subtitle_studio/io/audio_extractor.py`
- [X] T032 Create English SRT writer foundation and reusable collision-safe output path helpers in `src/ai_subtitle_studio/io/srt_writer.py`
- [X] T033 Create Subtitle Edit launcher using subprocess and configured executable path in `src/ai_subtitle_studio/io/subtitle_edit.py`
- [X] T034 Create application bootstrap and dependency wiring in `src/ai_subtitle_studio/app.py`

**Checkpoint**: Foundation ready; all story work can depend on tested contracts, persistence, settings, model catalog, workers, STT wrapper, translation interfaces, and I/O services.

---

## Phase 3: User Story 1 - Tạo phụ đề tiếng Anh từ hàng đợi video (Priority: P1) MVP

**Goal**: User can add multiple `.mp4` files, process them sequentially, and generate aligned English SRT output without command-line use.

**Independent Test**: Add two valid `.mp4` files, start processing, and verify each job runs sequentially, creates a usable English SRT output, and isolates per-job errors without depending on translation features.

### Tests for User Story 1

- [X] T035 [P] [US1] Add queue add/reject duplicate/non-mp4 tests in `tests/unit/test_video_queue.py`
- [X] T036 [P] [US1] Add job runner sequential processing and per-job error isolation tests in `tests/integration/test_job_runner_queue.py`
- [X] T037 [P] [US1] Add English SRT output contract tests for readable cue grouping, aligned timestamp format, and automatic unique filenames on collisions in `tests/contract/test_output_files_contract.py`
- [X] T038 [P] [US1] Add GUI smoke test for adding files and starting queue without blocking UI in `tests/gui/test_main_window_queue.py`

### Implementation for User Story 1

- [X] T039 [US1] Implement queue service for adding `.mp4` files, rejecting invalid files, detecting duplicates, and preserving add order in `src/ai_subtitle_studio/workers/job_runner.py`
- [X] T040 [US1] Implement VideoJob persistence and queue recovery integration in `src/ai_subtitle_studio/persistence/repositories.py`
- [X] T041 [US1] Implement ffmpeg audio extraction execution and error mapping in `src/ai_subtitle_studio/io/audio_extractor.py`
- [X] T042 [US1] Implement WhisperX transcribe and alignment flow with GPU lock acquisition in `src/ai_subtitle_studio/stt/whisperx_engine.py`
- [X] T043 [US1] Implement cue grouping from word-level timings into readable SubtitleLine records in `src/ai_subtitle_studio/domain/subtitle.py`
- [X] T044 [US1] Implement English SRT file writing with automatic unique filename suffixes for collisions and no silent overwrite in `src/ai_subtitle_studio/io/srt_writer.py`
- [X] T045 [US1] Implement default queue processing pipeline from audio extraction through STT and English SRT export in `src/ai_subtitle_studio/workers/job_runner.py`
- [X] T046 [US1] Implement main window queue table, file picker, drag-drop `.mp4` support, and start action in `src/ai_subtitle_studio/ui/main_window.py`
- [X] T047 [US1] Wire application startup to open main window and initialize stores/services in `src/ai_subtitle_studio/app.py`

**Checkpoint**: US1 is independently testable as the MVP queue-to-English-SRT workflow.

---

## Phase 4: User Story 2 - Chọn, tải và quản lý model nhận dạng (Priority: P1)

**Goal**: User can select `large-v3` by default, see supported models from config, download missing models with progress, and manage downloaded model storage.

**Independent Test**: Start without selected model downloaded, select a model, see download progress, then manage downloaded models in Model Manager.

### Tests for User Story 2

- [X] T048 [P] [US2] Add model catalog service tests for default fallback and no UI hard-coded model list in `tests/unit/test_model_catalog.py`
- [X] T049 [P] [US2] Add model download progress worker tests for percent, speed, and remaining bytes in `tests/unit/test_model_download_worker.py`
- [X] T050 [P] [US2] Add GUI tests for model dropdown and Model Manager actions in `tests/gui/test_model_manager.py`

### Implementation for User Story 2

- [X] T051 [US2] Implement model catalog lookup, default fallback, and validation errors in `src/ai_subtitle_studio/config/model_catalog.py`
- [X] T052 [US2] Implement model download worker progress, failure, cancel, and cache path handling in `src/ai_subtitle_studio/workers/model_download_worker.py`
- [X] T053 [US2] Implement model download persistence and disk size refresh in `src/ai_subtitle_studio/persistence/repositories.py`
- [X] T054 [US2] Implement Model Manager UI with downloaded model list, size, delete, and download actions in `src/ai_subtitle_studio/ui/model_manager.py`
- [X] T055 [US2] Connect model dropdown in main window to model catalog service without hard-coded model IDs in `src/ai_subtitle_studio/ui/main_window.py`
- [X] T056 [US2] Integrate missing-model auto-download before job execution in `src/ai_subtitle_studio/workers/job_runner.py`

**Checkpoint**: US2 is independently testable through model selection/download/management without requiring translation/edit workflows.

---

## Phase 5: User Story 3 - Dịch, chỉnh sửa và xuất phụ đề cuối cùng (Priority: P1)

**Goal**: User can choose Google Cloud Translation API v3 or DeepSeek, store provider API keys securely, translate English subtitle batches, edit subtitle rows, and export Vietnamese or bilingual SRT.

**Independent Test**: Load an English SRT generated by US1, translate through a selected provider, edit a row, export Vietnamese and bilingual SRT, and verify cue count/timestamps are preserved.

### Tests for User Story 3

- [X] T057 [P] [US3] Add Google provider httpx request/response shape tests in `tests/unit/test_google_provider.py`
- [X] T058 [P] [US3] Add DeepSeek provider httpx request/response shape tests in `tests/unit/test_deepseek_provider.py`
- [X] T059 [P] [US3] Add secure credential storage/redaction tests in `tests/unit/test_credentials.py`
- [X] T060 [P] [US3] Add subtitle table edit and export tests in `tests/gui/test_subtitle_table.py`
- [X] T061 [P] [US3] Add translation and Vietnamese/bilingual export integration tests preserving line count/order/timestamps in `tests/integration/test_translation_export.py`

### Implementation for User Story 3

- [X] T062 [US3] Implement Windows Credential Manager or keyring-backed credential storage in `src/ai_subtitle_studio/translation/base.py`
- [X] T063 [US3] Implement Google Cloud Translation API v3 provider using httpx in `src/ai_subtitle_studio/translation/google_provider.py`
- [X] T064 [US3] Implement DeepSeek Chat API provider using httpx in `src/ai_subtitle_studio/translation/deepseek_provider.py`
- [X] T065 [US3] Implement provider registry wiring for Google and DeepSeek in `src/ai_subtitle_studio/translation/registry.py`
- [X] T066 [US3] Implement translation batch orchestration, shape validation, pause checkpoints, and provider error mapping in `src/ai_subtitle_studio/workers/job_runner.py`
- [X] T067 [US3] Implement editable subtitle table with validation status for source and translated text in `src/ai_subtitle_studio/ui/subtitle_table.py`
- [X] T068 [US3] Implement Vietnamese and bilingual export from edited subtitle rows in `src/ai_subtitle_studio/io/srt_writer.py`
- [X] T069 [US3] Add provider selection and masked API key entry to Settings UI in `src/ai_subtitle_studio/ui/settings_dialog.py`
- [X] T070 [US3] Connect translation actions and subtitle table loading in `src/ai_subtitle_studio/ui/main_window.py`

**Checkpoint**: US3 is independently testable with mocked providers or valid user API keys after US1-generated English subtitles exist.

---

## Phase 6: User Story 4 - Điều khiển hàng đợi và phục hồi lỗi (Priority: P2)

**Goal**: User can pause, resume, cancel, retry jobs, recover queue state after restart, and see clear per-job errors without app-wide crashes.

**Independent Test**: Add three videos, pause a queued job, request pause on a running job, cancel another job, force one job error, restart the app, and verify queue state and recovery semantics.

### Tests for User Story 4

- [X] T071 [P] [US4] Add job state transition tests for pause/resume/cancel/retry in `tests/unit/test_job_state.py`
- [X] T072 [P] [US4] Add queue recovery tests for active job becoming retry_required after restart in `tests/integration/test_queue_recovery.py`
- [X] T073 [P] [US4] Add worker pause checkpoint and cancel event tests in `tests/unit/test_worker_control.py`
- [X] T074 [P] [US4] Add GUI tests for per-job error display and retry action in `tests/gui/test_queue_controls.py`

### Implementation for User Story 4

- [X] T075 [US4] Implement pause/resume/cancel/retry state transition enforcement in `src/ai_subtitle_studio/domain/job_state.py`
- [X] T076 [US4] Implement worker control tokens and pause checkpoint event emission in `src/ai_subtitle_studio/workers/worker_events.py`
- [X] T077 [US4] Implement pause/resume/cancel/retry handling in job runner without promoting partial outputs in `src/ai_subtitle_studio/workers/job_runner.py`
- [X] T078 [US4] Implement queue restore on startup and active-job-to-retry_required migration in `src/ai_subtitle_studio/persistence/repositories.py`
- [X] T079 [US4] Implement queue row controls, checkpoint-pending state, per-job error display, and retry action in `src/ai_subtitle_studio/ui/main_window.py`
- [X] T080 [US4] Add user-safe error code/message mapping for audio, STT, model, translation, output, and settings failures in `src/ai_subtitle_studio/domain/entities.py`

**Checkpoint**: US4 is independently testable with simulated workers and persistence without requiring full real GPU/API execution.

---

## Phase 7: User Story 5 - Cấu hình công cụ, thông tin hệ thống và mở Subtitle Edit (Priority: P2)

**Goal**: User can configure paths/GPU/output, view runtime System Info, and open generated subtitle files in Subtitle Edit.

**Independent Test**: Configure ffmpeg, Subtitle Edit, model/output paths and GPU; open About; generate/select an SRT; launch Subtitle Edit or see clear configuration errors.

### Tests for User Story 5

- [X] T081 [P] [US5] Add QSettings wrapper tests for ffmpeg, model cache, Subtitle Edit, output dir, GPU, and provider settings in `tests/unit/test_app_settings.py`
- [X] T082 [P] [US5] Add System Info provider tests for package versions, torch CUDA, nvidia-smi fallback, missing GPU display, and model size in `tests/unit/test_system_info.py`
- [X] T083 [P] [US5] Add Subtitle Edit subprocess launcher tests for valid and invalid executable paths in `tests/unit/test_subtitle_edit_launcher.py`
- [X] T084 [P] [US5] Add GUI tests for Settings and About dialogs in `tests/gui/test_settings_about.py`

### Implementation for User Story 5

- [X] T085 [US5] Implement Settings dialog for GPU, model cache directory, ffmpeg path, Subtitle Edit path, output directory, and provider settings in `src/ai_subtitle_studio/ui/settings_dialog.py`
- [X] T086 [US5] Implement path validation and QSettings persistence for Settings fields in `src/ai_subtitle_studio/config/app_settings.py`
- [X] T087 [US5] Implement runtime System Info snapshot collection with importlib.metadata, torch CUDA, nvidia-smi fallback, selected model, and model size in `src/ai_subtitle_studio/config/system_info.py`
- [X] T088 [US5] Implement About/System Info dialog rendering unavailable GPU/CUDA values clearly in `src/ai_subtitle_studio/ui/about_dialog.py`
- [X] T089 [US5] Implement Subtitle Edit subprocess launch and configuration error handling in `src/ai_subtitle_studio/io/subtitle_edit.py`
- [X] T090 [US5] Wire Settings, About, Model Manager, and Open with Subtitle Edit actions into main window menus/buttons in `src/ai_subtitle_studio/ui/main_window.py`

**Checkpoint**: US5 is independently testable using mocked runtime version/GPU probes and mocked subprocess launch.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validation, packaging, documentation, and constitution compliance proof across all stories.

- [X] T091 Run full automated test suite and record results in `specs/001-desktop-subtitle-studio/quickstart.md`
- [X] T092 Verify no UI, config, dataclass, or persistence field exposes VAD toggle and document evidence in `specs/001-desktop-subtitle-studio/quickstart.md`
- [X] T093 Verify `pyproject.toml` pins `whisperx==3.8.6` with `checked 2026-07-30` note and no `requirements.txt` dependency pin is used for WhisperX
- [X] T094 Verify `resources/models.json` drives all model UI choices and no model list is hard-coded in UI or transcribe logic in `src/ai_subtitle_studio/ui/main_window.py`
- [X] T095 Verify System Info reads runtime package versions and contains no hard-coded WhisperX or faster-whisper version strings in `src/ai_subtitle_studio/config/system_info.py`
- [X] T096 Verify one-GPU-STT lock behavior under 10 queued jobs in `tests/integration/test_job_runner_queue.py`
- [X] T097 Verify PyInstaller onedir build includes `models.json` and excludes Whisper model weights using `packaging/ai-subtitle-studio.spec`
- [ ] T098 Run manual quickstart scenarios and update validation notes in `specs/001-desktop-subtitle-studio/quickstart.md`
- [X] T099 Add explicit SC-004 timing assertion that model download progress appears within 5 seconds in `tests/unit/test_model_download_worker.py`
- [X] T100 Add explicit SC-005 timing assertion that pause/cancel acknowledgement appears within 2 seconds in `tests/gui/test_queue_controls.py`
- [X] T101 Add explicit SC-008 timing assertion that About/System Info renders required fields within 5 seconds in `tests/gui/test_settings_about.py`

---

## Phase 9: Gate G0 — Constitution and STT Contract Reconciliation

**Purpose**: Make governance, specifications, contracts and implementation describe the same mandatory Pyannote VAD API.

- [X] T102 Amend Mandatory VAD principle to `vad_method="pyannote"` and bump constitution to 1.0.1 in `.specify/memory/constitution.md`
- [X] T103 [P] Propagate VAD wording and stable check date through `.specify/templates/`, `README.md`, `pyproject.toml`, and `specs/001-desktop-subtitle-studio/`
- [X] T104 Run VAD/dependency contract tests in `tests/contract/test_stt_engine_contract.py` and `tests/contract/test_dependency_pins.py`

**Checkpoint**: Constitution Check is PASS and 11 focused contract tests pass.

---

## Phase 10: Release Foundation R0 — Repository Hygiene and Governance

**Purpose**: Create a source-only, privacy-safe repository foundation before GitHub publication.

- [X] T105 Update source/release ignore rules and preserve an empty output directory in `.gitignore`, `.dockerignore`, and `outputs/.gitkeep`
- [X] T106 [P] Add release history and contributor/security policies in `CHANGELOG.md`, `CONTRIBUTING.md`, and `SECURITY.md`
- [X] T107 [P] Add third-party runtime/license inventory in `THIRD_PARTY_NOTICES.md`
- [X] T108 Update user-facing install, data-path, privacy, support, and release guidance in `README.md`
- [X] T109 Centralize application version lookup from installed metadata with source fallback in `src/ai_subtitle_studio/__init__.py` and `tests/unit/test_package_metadata.py`
- [X] T110 Add repository hygiene contract tests for ignored private/generated files and single-source versioning in `tests/contract/test_repository_hygiene.py`
- [X] T111 Initialize the local `main` Git repository and verify the source-only index using `.git/`, `.gitignore`, and `scripts/verify-repository.ps1`

**Checkpoint**: Local Git repository is valid, source-only, private-ready, and passes hygiene tests.

---

## Phase 11: Runtime Correctness R1 — Paths, ffmpeg, Logging and Smoke Mode

**Purpose**: Ensure source and frozen builds use immutable resources plus safe user-writable directories.

### Tests for R1

- [X] T112 [P] Add source/frozen resource and Windows user-data path tests in `tests/unit/test_paths.py`
- [X] T113 [P] Add model cache/GPU propagation tests in `tests/integration/test_runtime_settings_propagation.py`
- [X] T114 [P] Add explicit/bundled/PATH ffmpeg resolution tests in `tests/unit/test_ffmpeg_resolver.py`
- [X] T115 [P] Add rolling log and secret-redaction tests in `tests/unit/test_logging_config.py`
- [X] T116 [P] Add non-blocking application smoke-mode contract tests in `tests/contract/test_smoke_mode.py`

### Implementation for R1

- [X] T117 Implement frozen-aware resource and Windows user-data paths in `src/ai_subtitle_studio/paths.py`
- [X] T118 Implement rolling file logging and credential redaction in `src/ai_subtitle_studio/logging_config.py`
- [X] T119 Implement explicit/bundled/PATH ffmpeg discovery in `src/ai_subtitle_studio/io/ffmpeg_resolver.py`
- [X] T120 Propagate model cache and selected GPU into STT requests in `src/ai_subtitle_studio/workers/job_runner.py` and `src/ai_subtitle_studio/stt/base.py`
- [X] T121 Wire safe paths, logging, ffmpeg resolution, metadata, and `--smoke-test` into `src/ai_subtitle_studio/app.py`
- [X] T122 Expose ffmpeg/log/data diagnostics in `src/ai_subtitle_studio/config/system_info.py`, `src/ai_subtitle_studio/domain/entities.py`, and `src/ai_subtitle_studio/ui/about_dialog.py`
- [X] T123 Add “Open logs” action and actionable startup error handling in `src/ai_subtitle_studio/ui/main_window.py` and `src/ai_subtitle_studio/app.py`

**Checkpoint**: Full source tests pass; smoke mode exits deterministically; persistent writes never target the bundle.

---

## Phase 12: Reproducible Runtime R2 — PyInstaller and Build Tooling

**Purpose**: Produce a deterministic PyInstaller `onedir` runtime with dynamic ML imports, ffmpeg, metadata and no model weights.

### Tests for R2

- [X] T124 [P] Add PyInstaller spec/hook/resource exclusion contract tests in `tests/contract/test_packaging_contract.py`
- [X] T125 [P] Add release build configuration/version consistency tests in `tests/contract/test_release_build_config.py`

### Implementation for R2

- [X] T126 Define pinned release build inputs in `packaging/release-requirements.txt` and `packaging/release-config.json`
- [X] T127 Implement WhisperX dynamic import/data/metadata collection in `packaging/hooks/hook-whisperx.py`
- [X] T128 Implement frozen environment initialization in `packaging/runtime_hooks/runtime_environment.py`
- [X] T129 Complete onedir spec with icon, metadata, ffmpeg, notices, hooks, exclusions, `upx=False`, and no model weights in `packaging/ai-subtitle-studio.spec`
- [X] T130 Add Windows application icon and version resources in `packaging/assets/app.ico` and `packaging/assets/version-info.txt`
- [X] T131 Implement clean release build orchestration, dependency checks, ffmpeg verification and inventory generation in `scripts/build-release.ps1`
- [X] T132 Implement frozen runtime verification in `scripts/smoke-frozen.ps1`
- [X] T133 Build and validate the local PyInstaller runtime in `dist/ai-subtitle-studio/` and record evidence in `specs/001-desktop-subtitle-studio/quickstart.md`

**Checkpoint**: Frozen app starts without system Python, imports WhisperX, finds resources/ffmpeg, and contains no model/private data.

---

## Phase 13: Delivery R3 — Manifest, Runtime Volumes and Online Installer

**Purpose**: Turn the onedir runtime into integrity-checked GitHub Release assets installable from one Setup executable.

### Tests for R3

- [X] T134 [P] Add release manifest schema/generation tests in `tests/contract/test_release_manifest.py`
- [X] T135 [P] Add installer contract/static validation tests in `tests/contract/test_installer_contract.py`
- [X] T136 [P] Add release verifier negative tests for missing, oversized and corrupt assets in `tests/unit/test_release_verifier.py`

### Implementation for R3

- [X] T137 Implement the release manifest JSON Schema in `packaging/release-manifest.schema.json`
- [X] T138 Implement versioned manifest, SHA256SUMS and build identity generation in `scripts/generate-release-manifest.ps1`
- [X] T139 Implement multi-volume runtime packaging with a strict 1.9 GiB gate in `scripts/package-runtime.ps1`
- [X] T140 Implement local/draft asset, checksum, size and signature verification in `scripts/verify-release.ps1`
- [X] T141 Implement per-user online installer downloads, SHA-256 checks, extraction, upgrade and uninstall preservation in `packaging/installer/ai-subtitle-studio.iss`
- [X] T142 Implement generated Inno Setup release values in `packaging/installer/generated-release-values.iss`
- [X] T143 Implement Authenticode sign/verify helpers without embedded secrets in `scripts/sign-release.ps1`
- [X] T144 Implement installer build orchestration and unsigned-prerelease fallback in `scripts/build-installer.ps1`
- [X] T145 Produce local runtime volumes, manifest, checksums and installer candidate under `release/`

**Checkpoint**: One Setup executable can obtain hash-verified runtime parts below 1.9 GiB and preserve user data across upgrade/uninstall.

---

## Phase 14: Automation R4 — GitHub CI/CD and Supply-Chain Controls

**Purpose**: Make tests and releases repeatable without exposing write/signing authority to untrusted pull requests.

- [X] T146 Add lightweight test dependencies for hosted CI in `pyproject.toml`
- [X] T147 Implement Windows Python 3.11/3.13 source CI in `.github/workflows/ci.yml`
- [X] T148 [P] Configure dependency updates in `.github/dependabot.yml`
- [X] T149 [P] Configure generated release notes in `.github/release.yml`
- [X] T150 [P] Configure source secret/dependency review in `.github/workflows/security.yml`
- [X] T151 Implement protected self-hosted Windows tag/manual release workflow in `.github/workflows/release-windows.yml`
- [X] T152 Add SBOM/provenance generation and upload steps in `.github/workflows/release-windows.yml` and `scripts/build-release.ps1`
- [X] T153 Add GitHub repository setup/branch protection instructions in `docs/GITHUB_SETUP.md`
- [X] T154 Validate workflow syntax, permissions, immutable naming and untrusted-runner separation in `tests/contract/test_github_workflows.py`

**Checkpoint**: Hosted CI is safe/green and protected release workflow creates a verifiable draft release from a tag.

---

## Phase 15: Acceptance R5 — Clean Machine, GPU, Signing and Publication

**Purpose**: Prove the downloadable artifact works for the target user before publication.

- [X] T155 Run source, packaging, repository and workflow contract suites and update `specs/001-desktop-subtitle-studio/quickstart.md`
- [ ] T156 Run clean Windows fresh install/interrupted download/upgrade/uninstall scenarios and record evidence in `specs/001-desktop-subtitle-studio/quickstart.md`
- [X] T157 Run NVIDIA two-video/model-download/queue/cancel/retry/recovery acceptance and record evidence in `specs/001-desktop-subtitle-studio/quickstart.md`
- [ ] T158 Run Google/DeepSeek/edit/English-Vietnamese-bilingual export acceptance and record evidence in `specs/001-desktop-subtitle-studio/quickstart.md`
- [ ] T159 Run no-GPU, Subtitle Edit, logging redaction, SmartScreen and signature acceptance and record evidence in `specs/001-desktop-subtitle-studio/quickstart.md`
- [ ] T160 Prepare versioned release notes and known issues in `CHANGELOG.md` and GitHub draft release
- [ ] T161 Create/push the private GitHub repository, configure protected environment/secrets/branch rules, and verify Actions in `docs/GITHUB_SETUP.md`
- [ ] T162 Create `v0.1.0-rc.1`, verify the downloaded draft assets, and publish pre-release or stable according to signing/acceptance gates

**Checkpoint**: All release gates pass and the GitHub installer is downloadable; otherwise the release remains a draft/pre-release with evidence of the missing external gate.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; must complete before foundational code.
- **Foundational (Phase 2)**: Depends on Setup; blocks all user stories.
- **User Stories (Phase 3-7)**: Depend on Foundation. US1, US2, and US3 are P1 and should be completed before P2 stories for MVP maturity.
- **Polish (Phase 8)**: Depends on all desired stories being complete.
- **G0 (Phase 9)**: Completed; blocks all release work.
- **R0 (Phase 10)**: Depends on G0 and creates the repository/documentation foundation.
- **R1 (Phase 11)**: Depends on R0 source conventions; blocks packaging.
- **R2 (Phase 12)**: Depends on R1 runtime correctness; produces the frozen runtime.
- **R3 (Phase 13)**: Depends on R2 runtime output; produces installer/release assets.
- **R4 (Phase 14)**: Depends on reproducible R2/R3 scripts; automates CI/release.
- **R5 (Phase 15)**: Depends on R0-R4 and requires clean Windows/GPU/API/signing/GitHub external state.

### User Story Dependencies

- **US1 (P1)**: Starts after Foundation; provides core queue/STT/SRT workflow.
- **US2 (P1)**: Starts after Foundation; can run alongside US1 after shared model catalog exists.
- **US3 (P1)**: Starts after Foundation; full manual test benefits from US1-generated English subtitles, but provider/export code can be developed independently.
- **US4 (P2)**: Starts after Foundation; integrates with US1 job runner and persistence.
- **US5 (P2)**: Starts after Foundation; settings/about/subprocess launch can be developed independently and then wired to US1/US2/US3.

### Within Each User Story

- Tests listed for a story MUST be written before the implementation tasks in that story.
- Domain and persistence changes precede worker/UI wiring when in the same story.
- UI tasks depending on services should follow service implementation.
- Story checkpoint must pass before moving to lower-priority stories unless work is intentionally parallelized by different contributors.

## Parallel Opportunities

- Setup tasks T004-T006 can run after T001 creates directories.
- Foundational tests T008-T014 can run in parallel.
- Foundational independent modules T017, T021-T025, T027-T029, T031-T033 can run in parallel after entities/contracts exist.
- Story test tasks marked [P] can run in parallel within their story.
- US2 and US5 can progress in parallel after Foundation because they mostly touch separate model/settings/about files.
- US3 provider implementations T063 and T064 can run in parallel after T062 and T065 contract wiring expectations are clear.

## Parallel Example: User Story 1

```bash
Task: "T035 [P] [US1] Add queue add/reject duplicate/non-mp4 tests in tests/unit/test_video_queue.py"
Task: "T036 [P] [US1] Add job runner sequential processing and per-job error isolation tests in tests/integration/test_job_runner_queue.py"
Task: "T037 [P] [US1] Add English SRT output contract tests for readable cue grouping, aligned timestamp format, and automatic unique filenames on collisions in tests/contract/test_output_files_contract.py"
Task: "T038 [P] [US1] Add GUI smoke test for adding files and starting queue without blocking UI in tests/gui/test_main_window_queue.py"
```

## Parallel Example: User Story 3

```bash
Task: "T057 [P] [US3] Add Google provider httpx request/response shape tests in tests/unit/test_google_provider.py"
Task: "T058 [P] [US3] Add DeepSeek provider httpx request/response shape tests in tests/unit/test_deepseek_provider.py"
Task: "T059 [P] [US3] Add secure credential storage/redaction tests in tests/unit/test_credentials.py"
Task: "T060 [P] [US3] Add subtitle table edit and export tests in tests/gui/test_subtitle_table.py"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 Setup.
2. Complete Phase 2 Foundation and constitution gate tests.
3. Complete Phase 3 US1 to deliver queue-to-English-SRT workflow.
4. Validate US1 independently with two `.mp4` files and no translation dependency.

### Incremental Delivery

1. Add US2 model selection/download/management.
2. Add US3 translation/edit/export completeness.
3. Add US4 pause/cancel/retry/recovery controls.
4. Add US5 settings/about/Subtitle Edit integration.
5. Run Phase 8 validation and packaging checks.

### Validation Gates

- Stop if any constitution gate test fails.
- Stop if UI thread responsiveness tests fail for long-running job simulations, including SC-005 pause/cancel acknowledgement within 2 seconds.
- Stop if translation provider shape validation allows mismatched line counts.
- Stop if System Info uses hard-coded dependency version strings.
- Stop if more than one GPU STT job can enter the locked region.
- Stop release work if any G0 constitution/contract wording diverges from the stable WhisperX API.
- Stop publication if a runtime asset is at least 1.9 GiB, checksum/signature verification fails, or clean-machine evidence is missing.
- Keep unsigned artifacts as pre-release only.

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks.
- [Story] label maps task to a user story phase.
- All user story tasks include exact file paths for implementability.
- Tasks intentionally include tests where constitution gates require proof.
- Subtitle Edit is only launched for manual editing; it is not part of automatic translation.
