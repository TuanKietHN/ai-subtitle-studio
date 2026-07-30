# Research: Desktop Subtitle Studio

## Decision: Pin WhisperX stable version

**Decision**: Pin `whisperx==3.8.6` in dependency metadata with the note `checked 2026-07-30`.

**Rationale**: PyPI lists `whisperx 3.8.6` as the latest release, released May 25, 2026. GitHub releases list `3.8.7rc1` as a pre-release and `v3.8.6` as the latest stable release. The constitution forbids rc/beta/dev builds, so `3.8.7rc1` is explicitly excluded.

**Alternatives considered**:
- `3.8.7rc1`: rejected because GitHub marks it pre-release and the constitution forbids rc builds.
- Installing from `main`: rejected because it is not a stable PyPI build and is not reproducible.
- Older stable releases: rejected because the project requires the latest stable release at build time.

**Sources checked**:
- PyPI project page: https://pypi.org/project/whisperx/
- PyPI JSON: https://pypi.org/pypi/whisperx/json
- GitHub releases: https://github.com/m-bain/whisperX/releases

## Decision: Python runtime and desktop framework

**Decision**: Use Python 3.11 with PySide6.

**Rationale**: The project is Windows desktop-first, and PySide6 provides native desktop widgets, QSettings, QThread/QThreadPool, signal/slot communication and packaging compatibility. Python 3.11 stays within WhisperX's published Python requirement range (`>=3.10,<3.14`) while avoiding edge compatibility risks from the newest Python minor.

**Alternatives considered**:
- Python 3.12: acceptable later, but 3.11 is lower-risk for ML and PyInstaller dependency compatibility.
- Python 3.13: rejected for initial implementation due dependency compatibility risk.
- Tkinter: rejected because the app needs richer tables, dialogs, worker signals and production desktop UX.

## Decision: WhisperX STT configuration

**Decision**: Implement `WhisperXEngine` with `model` selected at runtime, `device="cuda"`, `compute_type="float16"`, and hard-coded `vad_method="pyannote"` inside the wrapper. STT jobs fail clearly before transcribe if no valid NVIDIA/CUDA environment is detected.

**Rationale**: This matches the user's requested defaults and the constitution. Putting VAD inside the wrapper prevents UI/config bypasses. CUDA/float16 targets the user's NVIDIA GPU persona and avoids slow CPU fallback scope.

**Alternatives considered**:
- CPU fallback: rejected by clarification; non-STT UI remains usable, but STT requires NVIDIA/CUDA.
- Exposing VAD in settings: rejected by constitution.
- Calling WhisperX directly from UI or job runner: rejected because it would bypass invariants and make tests harder.

## Decision: Model catalog and downloads

**Decision**: Store supported models in `resources/models.json`, with `large-v3` as default and initial entries for `medium`, `large-v3`, `large-v3-turbo` and `distil-large-v3`. Validate this file at startup. Download models on first use or via the Model Manager; do not bundle models in PyInstaller output.

**Rationale**: Config-driven models satisfy the constitution and let future model additions avoid UI/transcribe code edits. Download-on-first-use keeps installer size reasonable.

**Alternatives considered**:
- Hard-code model list in UI: rejected by constitution.
- Bundle `large-v3`: rejected by user request and installer size concerns.
- Let users type arbitrary model IDs initially: deferred because validation, download progress and support expectations are clearer with a curated config file.

## Decision: Queue and worker execution

**Decision**: Use a persisted local job queue, QThread/QThreadPool workers and a process-local GPU STT semaphore. Pause requests apply immediately to queued jobs and at safe checkpoints for running jobs; cancel is best-effort and never promotes partial output to final output.

**Rationale**: Long video processing must not block the main UI thread. A GPU semaphore enforces the one-video-STT rule, while checkpoint pause avoids unsafe interruption in the middle of GPU inference or HTTP batches.

**Alternatives considered**:
- Python `threading` without Qt workers: rejected because PySide signal integration and UI-thread marshaling are cleaner with Qt worker patterns.
- Parallel STT jobs: rejected by constitution and VRAM risk.
- Immediate pause inside transcribe: rejected by clarification because it would require brittle interruption semantics.

## Decision: Translation integration

**Decision**: Implement direct REST translation providers with httpx: Google Cloud Translation API v3 and DeepSeek Chat API. Providers translate batches and must return the same number of lines as input; mismatches fail the job. Subtitle Edit is never used for automated translation.

**Rationale**: Direct provider contracts keep the app independent of Subtitle Edit for automation, preserve line/timestamp alignment and make provider errors testable.

**Alternatives considered**:
- Driving Subtitle Edit automation for translation: rejected by user request.
- Unofficial Google Translate scraping: rejected due reliability and terms risk.
- One HTTP request per subtitle line: rejected due latency and rate-limit pressure.

## Decision: Settings, credentials and job persistence

**Decision**: Use QSettings for non-secret settings, Windows Credential Manager or equivalent OS secret store for API keys, and SQLite via stdlib `sqlite3` for job history, queue recovery and subtitle metadata.

**Rationale**: This keeps the app local-first without a server database. QSettings fits desktop preferences, SQLite handles structured job state and queue recovery, and OS credential storage avoids plaintext API keys.

**Alternatives considered**:
- Plain JSON settings for everything: rejected because API keys must not be plaintext and structured job history needs queries.
- External database server: rejected by user request and unnecessary for single-user desktop.
- Prompt for API key every session: rejected because it hurts the target user's workflow.

## Decision: System Info runtime detection

**Decision**: About/System Info reads `importlib.metadata.version("whisperx")`, `importlib.metadata.version("faster-whisper")`, CUDA via `torch.version.cuda`, and GPU/driver via `nvidia-smi` subprocess fallback. Missing values are displayed as detected-unavailable states, never fake versions.

**Rationale**: Runtime metadata is required by the constitution and helps diagnose installation/GPU issues.

**Alternatives considered**:
- Hard-code dependency versions: rejected by constitution.
- Only use `nvidia-smi`: rejected because it may not be available even when torch can report CUDA build information.
- Hide missing GPU fields: rejected because clear diagnostics are part of the product value.

## Decision: Packaging

**Decision**: Package with PyInstaller `--onedir`, include app resources such as `models.json`, exclude Whisper model weights, and document first-use model downloads.

**Rationale**: `--onedir` is easier to debug and safer for ML/native dependencies than single-file extraction. Excluding model weights keeps package size manageable and satisfies user request.

**Alternatives considered**:
- PyInstaller `--onefile`: rejected for initial build due startup/extraction complexity with heavy native dependencies.
- Bundling default model: rejected by user request.
- MSI installer as first deliverable: deferred until core app packaging is validated.

# Release Readiness Research Addendum

**Checked**: 2026-07-30

## Decision: Stable WhisperX release remains 3.8.6

**Decision**: Keep `whisperx==3.8.6` for the `v0.1.0` release candidate and update the checked-date note to 2026-07-30 during implementation.

**Rationale**: PyPI lists `3.8.6` as the latest stable release and `3.8.7rc1` as a pre-release. This satisfies the constitution requirement to use the latest stable production release and exclude RC builds.

**Alternatives considered**:
- `3.8.7rc1`: rejected because the constitution prohibits pre-release/RC dependencies for production.
- Unpinned `whisperx`: rejected because it makes ML/native builds non-reproducible.

**Source**: https://pypi.org/project/whisperx/

## Decision: Reconcile the mandatory VAD invariant with the current WhisperX API

**Decision**: Constitution 1.0.1 and dependent artifacts express the mandatory invariant as `vad_method="pyannote"` at `whisperx.load_model()` for WhisperX 3.8.6, with no public VAD field or toggle. The behavior remains mandatory; only the obsolete literal API expression changed.

**Rationale**: Current source and contract tests intentionally use `vad_method="pyannote"` and verify that `vad_filter` is not passed to `model.transcribe()`. Constitution 1.0.1 and dependent artifacts now describe that same stable API truthfully.

**Alternatives considered**:
- Pretend the current code passes the literal constitution: rejected because it would hide a release-blocking inconsistency.
- Add an unsupported `vad_filter=True` call only to satisfy wording: rejected because it may break the stable WhisperX API and duplicates VAD configuration.
- Make VAD configurable: rejected because it weakens the product invariant and violates the intended constitution principle.

## Decision: Use PyInstaller onedir with explicit hooks

**Decision**: Keep PyInstaller `onedir`, add custom hooks for dynamically imported WhisperX and its package metadata/native dependencies, and add a frozen smoke mode that imports every runtime-critical package.

**Rationale**: The current engine loads WhisperX through `importlib.import_module("whisperx")`, which static analysis does not reliably discover. PyInstaller officially supports hidden imports, collecting submodules/data/binaries and custom hooks. `onedir` is easier to inspect, validate and repair than extracting a multi-gigabyte `onefile` payload on every launch.

**Alternatives considered**:
- Current spec with `hiddenimports=[]`: rejected because UI startup can pass while STT fails only when first used.
- `onefile`: rejected due extraction/startup/antivirus cost for the CUDA runtime.
- Nuitka migration: rejected for `v0.1.0` because it changes the release toolchain before the existing PyInstaller scaffold has been validated.

**Sources**:
- https://pyinstaller.org/en/stable/usage.html
- https://pyinstaller.org/en/stable/hooks.html
- https://pyinstaller.org/en/latest/spec-files.html

## Decision: Separate immutable resources from user-writable data

**Decision**: Introduce one path resolver. Packaged resources resolve from the frozen bundle; SQLite, logs, model cache and output resolve to Windows user directories.

**Rationale**: A frozen application may be installed under a read-only location. Persisting data beside the executable risks permission failures, accidental loss on upgrade and mixing private data with binaries. User directories also make backup, cleanup and uninstall semantics explicit.

**Alternatives considered**:
- Continue using the source/bundle root: rejected because it is not a safe writable contract.
- Require the user to configure every path before first run: rejected because the primary workflow must not require technical setup.
- Portable mode only: deferred; it can be added later through an explicit flag without becoming the default.

## Decision: Bundle ffmpeg but not Whisper models

**Decision**: Download a pinned Windows x64 ffmpeg build during the protected release workflow, verify its SHA-256, bundle the executable and include applicable license/source notices. Continue downloading Whisper models at first use.

**Rationale**: ffmpeg is required for every STT job and is small enough to bundle relative to the CUDA runtime. Whisper models add gigabytes per model and are already selected/configured dynamically.

**Alternatives considered**:
- Require ffmpeg on PATH: rejected as the default because the target user should not need command-line setup.
- Commit ffmpeg to Git: rejected because generated/vendor binaries do not belong in source history.
- Bundle `large-v3`: rejected because it makes release delivery and model updates unnecessarily large.

## Decision: Deliver a small online installer backed by release archives

**Decision**: Publish a small Inno Setup online installer as the primary download. It downloads one or more versioned runtime archives from the same GitHub Release, verifies SHA-256 and extracts them per user. Each runtime asset must be below 1.9 GiB.

**Rationale**: GitHub requires each Release asset to be under 2 GiB, while the installed Torch CUDA runtime alone contains several gigabytes of DLLs. Inno Setup supports HTTPS downloads, required SHA-256 verification, archive extraction, progress UI, non-admin installation and uninstall. The user still starts with one Setup executable.

**Alternatives considered**:
- One offline installer: rejected because it may exceed GitHub's per-asset limit.
- Ask users to download and join split files manually: rejected because it violates the non-command-line target experience.
- Git LFS for installers: rejected because release binaries should be attached to versioned releases, not source history.
- External object storage for `v0.1.0`: deferred; GitHub Release volumes are sufficient and keep source/release ownership together.

**Sources**:
- https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
- https://jrsoftware.org/ishelp/topic_isxfunc_downloadtemporaryfile.htm
- https://jrsoftware.org/ishelp/topic_filessection.htm
- https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm

## Decision: Build full releases on a protected self-hosted Windows runner

**Decision**: Run lightweight source CI on GitHub-hosted Windows runners; run full CUDA packaging only on a clean protected self-hosted Windows x64 runner with at least 40 GiB free.

**Rationale**: The local dependency audit found approximately 4.28 GiB of Torch CUDA DLLs and 2.68 GiB of development `.lib` files. Full install/build/archive/sign/verify stages need more disk and tighter control than routine pull-request tests. A protected runner also permits controlled access to signing material.

**Alternatives considered**:
- Install full Torch CUDA on every PR: rejected due cost, time and low additional test signal.
- Run untrusted PR code on the self-hosted runner: rejected as a security risk.
- Build stable releases manually on a developer workstation: rejected because it is not auditable or reproducible.

## Decision: Private-first repository and signed stable releases

**Decision**: Initialize and push the repository as private. Public visibility requires an explicit source-license decision and completed third-party notices. Authenticode signing is mandatory for a stable/latest release; unsigned artifacts may only be pre-releases.

**Rationale**: The repository owner has not selected an open-source license, and Windows SmartScreen trust materially affects installation usability. Private-first prevents accidental publication with ambiguous rights; a pre-release path still allows validation before a signing certificate is available.

**Alternatives considered**:
- Assume MIT license: rejected because licensing is an owner/legal decision, not an implementation default.
- Publish public source without a license: rejected because reuse rights would be ambiguous.
- Call an unsigned installer stable: rejected because it undermines the requested easy-download experience.
