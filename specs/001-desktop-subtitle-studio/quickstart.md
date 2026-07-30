# Quickstart: Desktop Subtitle Studio Validation

## Prerequisites

- Windows machine with NVIDIA GPU and compatible CUDA/driver for STT validation.
- Python 3.13.7 for the reproducible Windows release builder. Hosted source CI
  also exercises Python 3.11.
- ffmpeg executable available or configured in Settings.
- Subtitle Edit installed only for the optional "Open with Subtitle Edit" validation.
- Google Cloud Translation API v3 key or DeepSeek API key for translation validation.
- At least two short `.mp4` English lecture samples.

## Setup

From the repository root after implementation exists:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev]
```

Dependency validation expected:

```powershell
python -c "import importlib.metadata as m; print(m.version('whisperx'))"
```

Expected result: `3.8.6` for builds following this plan.

## Run Automated Checks

```powershell
pytest tests/unit tests/contract tests/integration tests/gui
```

Expected results:
- After Gate G0, STT wrapper tests prove Pyannote VAD is mandatory through `vad_method="pyannote"` and no VAD field/toggle is public.
- Model catalog tests validate `resources/models.json` and default `large-v3`.
- Queue tests prove one active GPU STT job.
- Translation provider tests prove output count/order validation.
- System Info tests prove runtime version lookup and no hard-coded dependency versions.
- UI worker tests prove long-running jobs do not block the main window.

## Manual Scenario 1: Queue Two Videos

1. Start the app.
2. Configure ffmpeg path, output directory and model cache directory.
3. Drag two `.mp4` lecture videos into the main window.
4. Select `large-v3`.
5. Start processing.

Expected:
- Both videos appear in the queue.
- Only one job enters GPU STT at a time.
- If `large-v3` is missing, model download progress shows percent, speed and remaining bytes.
- English `.srt` output is created for each successful job. Vietnamese and bilingual outputs are created later by the translation/edit workflow.

## Manual Scenario 2: Translate and Edit

1. Select Google Cloud Translation API v3 or DeepSeek in Settings.
2. Enter provider API key.
3. Run translation for a generated English subtitle.
4. Edit one translated subtitle row in the table.
5. Export Vietnamese and bilingual SRT outputs.

Expected:
- API key is masked after entry.
- Translation preserves cue count, order and timestamps.
- Edited text appears in exported `.srt`.
- Bilingual output contains English and Vietnamese text in each cue.

## Manual Scenario 3: Pause, Cancel and Recovery

1. Queue three videos.
2. Pause one queued job.
3. Request pause on a running job.
4. Cancel another job.
5. Close and reopen the app while a job is active.

Expected:
- Queued job pauses immediately.
- Running job shows checkpoint-pending pause until the current step ends.
- Canceled job does not promote partial output.
- Queue and completed results restore after restart.
- Job active during shutdown appears as needing retry.

## Manual Scenario 4: System Info and GPU Failure

1. Open About/System Info.
2. Verify app version, WhisperX, faster-whisper, CUDA, GPU/driver, selected model and downloaded model size.
3. On a machine or configuration without valid NVIDIA/CUDA, try to start an STT job.

Expected:
- Version values reflect installed runtime packages.
- Missing GPU/CUDA is clearly shown as unavailable.
- STT job fails before transcribe with configuration error.
- Settings, About, model manager and subtitle table remain usable.

## Manual Scenario 5: Subtitle Edit Launch

1. Configure `SubtitleEdit.exe` path in Settings.
2. Generate or select an existing final `.srt` output.
3. Click "Open with Subtitle Edit".

Expected:
- Subtitle Edit opens the selected subtitle file.
- If path is invalid, the app shows a settings error and does not crash.

## Release Validation Prerequisites

- Clean Windows 10/11 x64 VM or Windows Sandbox without system Python.
- Separate Windows x64 machine with supported NVIDIA GPU for final STT acceptance.
- At least 40 GiB free on the full release builder.
- Inno Setup compiler and archive tool versions pinned by the release script.
- Authenticode signing access for stable releases.
- Two short English `.mp4` samples owned or licensed for testing.
- Test-only Google/DeepSeek credentials stored outside the repository.

## Source Validation

From a clean test environment:

```powershell
python -m compileall src tests
python -m pytest tests\unit tests\contract tests\integration tests\gui
python -m pip check
```

Expected:

- All tests pass.
- No dependency conflict is reported.
- No test requires a real API key or real Whisper model download.

Run repository hygiene checks before the first commit and every release:

```powershell
git status --short
git ls-files
```

Expected:

- No file under `outputs/`, model cache, SQLite database, `.env`, logs, `build/`, `dist/` or release staging is tracked.
- No generated installer/runtime archive is committed.
- Secret scan reports no credential.

## Frozen Runtime Build

The implementation phase will provide one entry point:

```powershell
.\scripts\build-release.ps1 -Version 0.1.0-rc.1 -Clean
```

Expected build stages:

1. Create/validate the Python 3.11 release environment.
2. Install pinned Torch CUDA 12.8 and locked runtime dependencies.
3. Verify versions and `pip check`.
4. Download/verify the pinned ffmpeg binary.
5. Run source tests.
6. Build PyInstaller `onedir`.
7. Run frozen smoke tests.
8. Produce inventory, dependency manifest and build identity.

Direct smoke validation:

```powershell
.\scripts\smoke-frozen.ps1 -DistPath .\dist\ai-subtitle-studio
```

Expected:

- Executable starts without system Python.
- `models.json` is readable.
- Writable data/model/log/output paths are outside the install directory.
- `whisperx`, Torch, Faster-Whisper, CTranslate2, Qt, httpx and keyring import.
- SQLite schema initializes in a temporary user-data directory.
- Bundled ffmpeg is discovered and returns version information.
- No Whisper model weight exists in `dist`.

## Package Runtime and Installer

```powershell
.\scripts\package-runtime.ps1 -Version 0.1.0-rc.1
.\scripts\generate-release-manifest.ps1 -Version 0.1.0-rc.1
.\scripts\verify-release.ps1 -Version 0.1.0-rc.1 -Local
```

Expected:

- Runtime is split into ordered `.7z.001`, `.7z.002`, ... volumes.
- Every volume is below 1.9 GiB.
- Manifest version/tag/commit match the source.
- `SHA256SUMS` contains every published asset.
- Installer download URLs point to the exact tag, not an unversioned branch.
- Installer contains no signing secret or API key.

Compile the Inno Setup online installer through the release script. Do not manually edit generated URLs/hashes.

## Clean-Machine Installer Scenarios

### Fresh Install

1. Start only `AI-Subtitle-Studio-Setup-v0.1.0-rc.1.exe`.
2. Confirm download and disk-space information.
3. Install without administrator elevation.
4. Launch from Start Menu.

Expected:

- Installer downloads every runtime volume with progress.
- SHA-256 verification occurs before extraction.
- App opens without terminal or Python installed.
- Add/Remove Programs contains one entry.
- Default data/model/log/output directories match `data-model.md`.

### Interrupted or Corrupt Download

1. Interrupt one runtime-volume download and retry.
2. Replace one test volume with invalid content in a controlled test release.

Expected:

- Retry does not corrupt the active installation.
- Invalid hash aborts before activation.
- Temporary files are cleaned after cancellation/failure.

### Upgrade

1. Install the previous release candidate.
2. Create settings, one queued job and a small test output.
3. Install the newer candidate without uninstalling.

Expected:

- One application/uninstall entry remains.
- Binary directory updates atomically.
- Settings, database, credentials, model cache and output remain.
- Database backup/migration behavior is logged.

### Uninstall

1. Uninstall through Windows Settings.
2. Inspect install and user-data directories.

Expected:

- Binaries and shortcuts are removed.
- User database, models, credentials and output are preserved by default.
- No release staging/download files remain.

## Clean NVIDIA GPU Acceptance

On a supported NVIDIA Windows machine:

1. Fresh-install the release candidate.
2. Open System Info and record app, WhisperX, Faster-Whisper, Torch CUDA and GPU driver versions.
3. Choose a model not already cached.
4. Queue two short videos and process them.
5. Exercise pause/cancel/retry and close/reopen recovery.
6. Translate with each provider using test credentials.
7. Edit one subtitle and export English, Vietnamese and bilingual SRT.

Expected:

- Model downloads to the configured model cache.
- Exactly one job enters GPU STT at a time.
- Bundled ffmpeg extracts audio.
- Output timestamps and cue grouping are valid.
- API keys are absent from logs.
- Queue and completed results survive restart.

## GitHub Draft Release Verification

Before publishing:

```powershell
.\scripts\verify-release.ps1 -Version 0.1.0-rc.1 -GitHubDraft
```

Expected:

- Draft release tag targets the expected commit.
- All required assets exist and are below GitHub limits.
- Downloaded asset hashes match both manifest and `SHA256SUMS`.
- Installer/application signatures validate for a stable release.
- SBOM/notices are present.
- README latest-download link resolves to the intended installer naming policy.

Publish as pre-release if signing or any stable gate is missing. Never replace an asset for an already published tag; create a new version/tag.

## Implementation Validation Notes

Last source validation run: 2026-07-30.

- Python: 3.13.7 local development environment.
- Final automated RC result: `131 passed` under pytest 9.0.3; `compileall`,
  `pip check`, repository hygiene and PowerShell syntax validation also passed.
- Installed versions observed: WhisperX 3.8.6, Torch 2.8.0+cu128, TorchVision 0.23.0+cu128, TorchAudio 2.8.0+cu128, PyInstaller 6.21.0 and PySide6 6.11.1.
- PyPI re-check: WhisperX 3.8.6 remains the latest stable; 3.8.7rc1 remains a pre-release.
- Local size audit: Torch package about 7.08 GiB total; runtime `.dll` files about 4.28 GiB; development `.lib` files about 2.68 GiB.
- Git metadata check: the local repository is initialized on branch `main`; no remote has been configured yet.
- PyInstaller `onedir` RC build completed at `dist/ai-subtitle-studio/`:
  7,391 files, 5,435,140,641 bytes.
- Frozen smoke validation passed with exit code 0. It imported PySide6, WhisperX and Torch, initialized SQLite/user paths in an isolated temporary profile, loaded `resources/models.json`, resolved bundled FFmpeg 8.0.1 and rejected cached Whisper/private data.
- Generated release evidence is under ignored `release-staging/build/`: dependency manifest, per-file SHA-256 runtime inventory and build identity.
- The required `whisperx/assets/pytorch_model.bin` is the packaged Pyannote VAD asset used by the mandatory VAD implementation; it is not a downloaded Whisper ASR model and is explicitly distinguished from forbidden model-cache weights by the smoke validator.
- Runtime packaging produced two RC volumes: 1,887,436,800 bytes
  (`a4ca6f...81da9`) and 551,568,654 bytes (`ae7531...3385`). Both are
  below the strict 1.9 GiB gate.
- Inno Setup 6.7.3 compiled
  `AI-Subtitle-Studio-Setup-v0.1.0-rc.1.exe` at 2,950,118 bytes
  (`d9e590...2d7a`). It is intentionally recorded as
  `unsigned_prerelease`.
- Local `verify-release.ps1` validation passed for five manifest payloads:
  two runtime volumes, installer, CycloneDX 1.6 SBOM (145 components) and
  third-party notices. `SHA256SUMS-v0.1.0-rc.1.txt` also passed.
- Frozen smoke validation passed again after the security/path hardening
  changes.
- The vbsec review found no remaining secret, SQL, command, SSRF or path
  traversal issue. It recorded two HIGH dependency findings inherited from
  WhisperX (Torch/Transformers). Twelve explicit advisory exceptions expire
  2026-09-30; CI fails on any new advisory and stable builds fail while the
  exception list is non-empty.
- GitHub Actions are pinned to full commit SHAs. Workflow contract tests passed
  for hosted Python 3.11/3.13 CI, read-only security jobs and the protected
  self-hosted Windows release environment.
- GitHub CLI 2.96.0 is installed locally, but no GitHub account is authenticated
  yet. Candidate URLs still use provisional owner `Kiet`; regenerate the
  manifest with the authenticated owner and source commit before upload.
- Clean-VM, NVIDIA GPU/API and GitHub draft-release scenarios remain unexecuted until the following release phases are completed.
