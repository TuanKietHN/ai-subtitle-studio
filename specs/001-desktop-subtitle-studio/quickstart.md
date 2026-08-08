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
.\scripts\build-release.ps1 -Version 0.1.0-rc.5 -Clean
```

Expected build stages:

1. Create/validate the pinned Python 3.13.7 release environment.
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
.\scripts\package-runtime.ps1 -Version 0.1.0-rc.5
.\scripts\generate-release-manifest.ps1 -Version 0.1.0-rc.5
.\scripts\verify-release.ps1 -Version 0.1.0-rc.5
```

Expected:

- Runtime is split into ordered `.7z.001`, `.7z.002`, ... volumes.
- Every volume is below 1.9 GiB.
- Manifest, generated installer include and installed runtime marker contain the
  same deterministic `runtime_bundle_id`.
- Manifest version/tag/commit match the source.
- `SHA256SUMS` contains every published asset.
- Installer download URLs point to the exact tag, not an unversioned branch.
- Installer contains no signing secret or API key.

Compile the Inno Setup online installer through the release script. Do not manually edit generated URLs/hashes.

## Clean-Machine Installer Scenarios

### Fresh Install

1. On a clean machine, confirm that
   `%LOCALAPPDATA%\Programs\AI Subtitle Studio` does not exist.
2. Start only `AI-Subtitle-Studio-Setup-v0.1.0-rc.5.exe`.
3. Confirm Setup says this is a fresh install and shows download size,
   free-space requirement and destination.
4. Install without administrator elevation, then launch from Start Menu.

Expected:

- Setup explicitly creates `{app}` before activation and stages at
  `{app}\runtime.staging`; the RC4 `RenameFile` failure cannot recur.
- The download page shows current volume/source, total percent, transferred
  bytes, MiB/s and ETA rather than only changing a status label.
- SHA-256 verification occurs before extraction, and activation swaps runtime
  atomically on the same filesystem.
- App opens without terminal, Python, FFmpeg or 7-Zip installed system-wide.
- Start Menu contains application and uninstall shortcuts.
- Add/Remove Programs contains one entry.
- Default data/model/log/output directories match `data-model.md`.

### Local, Cached and Resumed Download Sources

Run each case from a clean or deliberately prepared VM:

1. Put all matching `.7z.00N` files beside Setup and install.
2. Remove those local files, seed the persistent installer cache with verified
   complete volumes and install again.
3. Interrupt a network download after a meaningful `.part` file exists, close
   Setup, and run the same Setup again.
4. Test where BITS range resume is unavailable so the Inno HTTPS fallback runs.

Expected:

- Source priority is `{src}` -> verified cache -> BITS -> Inno HTTPS fallback.
- Local and cached files still pass size and SHA-256 verification; filenames
  alone are never trusted.
- A valid partial BITS download resumes instead of restarting at byte zero.
- If BITS cannot operate, Setup explains the fallback and can complete through
  Inno download without modifying the active runtime.
- Complete verified files remain in
  `%LOCALAPPDATA%\AI Subtitle Studio\installer-cache\<runtime_bundle_id>` for
  retry; corrupt or wrong-identity files are rejected.

### Activation Failure and Retry

1. Install a valid older candidate.
2. Let RC5 download and extract successfully, then use the controlled test hook
   to fail activation before the staged runtime becomes active.
3. Verify the old application still launches, then rerun the same RC5 Setup.

Expected:

- `runtime.staging` is removed after failure, while the previously active
  runtime is preserved or restored from `runtime.previous`.
- Verified archives remain cached, so retry does not download the approximately
  2.33 GiB bundle again.
- The error identifies the failed lifecycle phase and log path.

### Running Application Detection

1. Start the installed application and keep it open.
2. Start the newer installer.

Expected:

- Setup detects the running application before runtime swap.
- The user is asked to close it and retry; Setup never swaps files while the
  old process is using them.

### Interrupted or Corrupt Download

1. Interrupt one runtime-volume download and retry.
2. Replace one test volume with invalid content in a controlled test release.

Expected:

- Retry does not corrupt the active installation.
- Invalid hash aborts before extraction or activation.
- Failed staging is cleaned, but resumable `.part` and verified cache files are
  preserved according to the cache contract.

### Upgrade

1. Install the previous release candidate.
2. Create settings, one queued job and a small test output.
3. Install RC5 without uninstalling.

Expected:

- Setup clearly says this is an upgrade and names old/new versions.
- One application/uninstall entry remains.
- Binary directory updates atomically.
- Settings, database, credentials, model cache and output remain.
- Database backup/migration behavior is logged.

Run a second upgrade using an installer whose active marker has the exact same
`runtime_bundle_id`.

Expected:

- Setup downloads and extracts zero runtime bytes, but may repair metadata and
  shortcuts.
- A missing, invalid or mismatched marker fails safe by performing a full
  verified runtime installation.

### Uninstall

Test these cases independently:

1. Default uninstall with every optional cleanup box off.
2. Select only “Xóa model, cache, log, lịch sử và API key”.
3. Select only “Xóa phụ đề/output đã tạo”.
4. Select both cleanup choices and confirm the full-clean warning.
5. Repeat output cleanup with a custom output directory that also contains
   source videos and unrelated user files.

Expected:

- Default uninstall removes binaries, staging/previous runtime, shortcuts and
  registration, but preserves user data and outputs.
- Private-data cleanup removes database, model/cache/log files, QSettings and
  known Credential Manager aliases, and reports anything it could not remove.
- Output deletion is a separate opt-in, is off by default, displays the exact
  path and requires a second confirmation.
- Custom output cleanup deletes only app-recorded owned outputs; it never
  removes source videos, unrelated files or an arbitrary whole directory.
- The user can cancel at either warning without losing data.

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

## NVIDIA 4 GiB / RTX 2050 Acceptance

Use a real RTX 2050 4 GiB or another NVIDIA GPU with exactly 4 GiB VRAM. A
larger GPU with an artificial limit helps development but does not replace this
release gate.

1. Fresh-install RC5 and open System Info.
2. Confirm GPU name/index, driver, total VRAM, Torch CUDA readiness, compute
   capability and supported CTranslate2 compute types are shown.
3. Select the low-VRAM profile and `small.en` for two short English MP4 files.
4. Confirm the effective request shows `compute_type=int8_float16` and
   `batch_size=1`; mandatory Pyannote VAD remains internal and no VAD control
   appears in the UI.
5. Process both videos through extraction, ASR, alignment and SRT export.
6. Record peak VRAM by phase and confirm the ASR model is released before the
   alignment model is loaded.

Expected:

- Both jobs complete sequentially without CUDA OOM and produce valid English
  SRT files.
- The app never silently changes model/profile; an incompatible choice requires
  explicit user confirmation.
- Diagnostics record requested/effective model, compute type, batch size,
  selected GPU and VRAM, but no source text, subtitle text or API key.

Additional negative tests:

1. Make `nvidia-smi` succeed while Torch CUDA initialization fails.
2. Trigger a controlled CUDA OOM during ASR.

Expected:

- `nvidia-smi` alone cannot pass STT preflight; the app shows an actionable
  driver/Torch error.
- OOM cleanup retries at most once with documented safer parameters, never
  loops forever, and recommends a lighter model/profile if retry fails.

## GitHub Release Verification Without GitHub CLI

Create a draft Release in the GitHub web interface and upload every file from
`release/`. Download all assets again with the browser into a separate
directory, then run:

```powershell
.\scripts\verify-release.ps1 `
  -Version 0.1.0-rc.5 `
  -ReleaseDirectory "C:\Temp\ai-subtitle-studio-v0.1.0-rc.5"
```

Expected:

- The downloaded manifest records the expected tag and commit.
- All required assets exist and are below GitHub limits.
- Downloaded asset hashes match both manifest and `SHA256SUMS`.
- Installer/application signatures validate for a stable release.
- SBOM/notices are present.
- README latest-download link resolves to the intended installer naming policy.

Publish through the GitHub web interface as a pre-release if signing or any
stable gate is missing. Never replace an asset for an already published tag;
create a new version/tag.

## Implementation Validation Notes

Planning addendum checked: 2026-08-01.

- RC4 artifacts were built and published, but a clean install failed only after
  both runtime volumes passed download, hash verification and extraction.
  Setup log evidence identifies activation as the failure point: `{app}` did
  not exist when `RenameFile(StagedRuntime, ActiveRuntime)` ran.
- RC5 source implementation now includes forced `{app}` creation, same-volume
  staging/atomic rollback, local/cache/BITS/HTTPS source resolution, aggregate
  progress/speed/ETA, deterministic runtime identity, same-bundle skip,
  selective uninstall and a config-driven NVIDIA 4 GiB profile.
- Automated coverage passed for the lifecycle contracts, manifest/verifier,
  cleanup helper, GPU inventory/profile propagation, bounded OOM retry and UI
  diagnostics. Clean-machine network/resume/upgrade/uninstall and real RTX
  2050/4 GiB execution remain external release gates; source tests do not
  replace those runs.

Last RC5 source/build validation run: 2026-08-08.

- Lightweight automated result: `158 passed` in 4.81 seconds; the pinned release
  environment also passed `158` tests in 5.03 seconds. Python `compileall`, PowerShell parser
  validation and `git diff --check` passed.
- A first release-environment run exposed a 23.7-second synchronous Torch CUDA
  probe in System Info. RC5 now starts one cached daemon probe and returns UI
  diagnostics in under one second while persisted execution-profile parameters
  remain active; the definitive Torch preflight still runs before GPU STT.
- A clean PyInstaller 6.21.0 build produced a frozen runtime containing 7,391
  files / 5,435,164,732 bytes. Frozen smoke validation passed with bundled
  FFmpeg 8.0.1, PySide6, WhisperX and Torch CUDA imports.
- Runtime packaging produced two RC5 volumes: 1,887,436,800 bytes
  (`5e1583...9361`) and 551,605,321 bytes (`08cba2...1b1d`), both below the
  strict 1.9 GiB gate.
- Inno Setup 6.7.3 compiled
  `AI-Subtitle-Studio-Setup-v0.1.0-rc.5.exe` at 2,956,277 bytes
  (`82451d...1da1`). It is intentionally `unsigned_prerelease`.
- Local release verification passed for five manifest payloads and a
  deterministic runtime identity
  `a7be9704f1d9798ae0dcb1d69675601613ef38fa036e512526a71f9eebf34656`.
- This validation build correctly records `git_commit=uncommitted` because the
  RC5 changes are still in the working tree. It MUST NOT be uploaded; after the
  user commits, the official workflow must rebuild so manifest/tag/commit and
  artifacts are immutable and identical.
- Repository metadata observed locally: branch `main`, remote
  `https://github.com/TuanKietHN/ai-subtitle-studio.git`, latest published local
  tag `v0.1.0-rc.4` at the start of RC5 work.
- Plan completion audit on 2026-08-08 found the current GPU is NVIDIA GeForce
  RTX 5060 with 8,151 MiB VRAM and driver 610.88; it cannot satisfy the real
  4 GiB gate. `WindowsSandbox.exe` is not installed, so this machine cannot
  supply the separate clean-Windows evidence.
- Presence-only keyring checks returned false for both
  `translation/google_cloud_v3` and `translation/deepseek_chat`; no credential
  values were printed or copied. Real-provider acceptance remains blocked until
  the owner supplies dedicated test credentials and explicitly authorizes API
  calls that may consume quota.
- `Get-AuthenticodeSignature` reports the RC5 Setup as `NotSigned`, which is
  consistent with `unsigned_prerelease` but blocks stable publication.
- Versioned RC5 notes are prepared in
  `docs/RELEASE_NOTES_v0.1.0-rc.5.md`. GitHub environment/ruleset/runner state,
  final Actions runs and draft Release cannot be inferred from local source and
  remain unchecked in `docs/GITHUB_SETUP.md`.
- Final local plan-validation rerun passed all 158 tests, Python `compileall`,
  `pip check`, parsing of every PowerShell script, `git diff --check` and
  `verify-release.ps1`. The verifier confirmed five RC5 payloads and runtime
  identity `a7be9704f1d9798ae0dcb1d69675601613ef38fa036e512526a71f9eebf34656`;
  the manifest remains correctly blocked from publication by
  `git_commit=uncommitted`.

Previous full runtime validation run: 2026-07-30.

- Python: 3.13.7 local development environment.
- Final automated result: `132 passed` under pytest 9.0.3; `compileall`,
  `pip check`, repository hygiene and PowerShell syntax validation also passed.
- Installed versions observed: WhisperX 3.8.6, Torch 2.8.0+cu128, TorchVision 0.23.0+cu128, TorchAudio 2.8.0+cu128, PyInstaller 6.21.0 and PySide6 6.11.1.
- PyPI re-check: WhisperX 3.8.6 remains the latest stable; 3.8.7rc1 remains a pre-release.
- Local size audit: Torch package about 7.08 GiB total; runtime `.dll` files about 4.28 GiB; development `.lib` files about 2.68 GiB.
- The historical run was performed before the current GitHub remote/tag state;
  use the RC5 metadata recorded above for new release work.
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
- Candidate URLs currently use provisional owner `Kiet`; regenerate the
  installer and manifest with the final GitHub owner/repository and source
  commit before upload.
- NVIDIA acceptance ran on an RTX 5060 8 GiB (driver 610.88) with two
  synthetic English MP4 files and the `medium` model. The isolated model cache
  downloaded 9 files / 1,530,571,775 bytes; WhisperX logged mandatory Pyannote
  VAD for both jobs; the queue completed sequentially and produced two
  timestamped English SRT files with the expected text. The Python GPU process
  exited and released its VRAM afterward.
- A second real-GPU control run used a 30-second synthetic MP4 and the same
  isolated model cache. Cancel acknowledgement changed the active job to
  `canceled` in 0.005 seconds without promoting an output; retry then completed
  and wrote a valid English SRT. A running transcription reached a safe pause
  checkpoint in 0.160 seconds, remained blocked until resume and then completed.
  A separate shutdown during GPU processing persisted `retry_required`; a new
  SQLite repository instance restored that state and the retried job completed
  with a valid English SRT.
- Real Subtitle Edit integration passed with the official portable Subtitle
  Edit 5.1.0 x64 build. The application launcher opened
  `sample-1.en.srt` from the GPU acceptance output; the process remained alive
  during the observation window and was then closed by the validation command.
- Windows Sandbox is not installed on this builder, so a distinct clean
  Windows VM or machine is still required for fresh-install, interrupted
  download, upgrade and uninstall evidence.
- Pyannote emitted its known TorchCodec built-in decoder warning because the
  packaged FFmpeg is 8.x while TorchCodec probes 4-7. The real acceptance still
  passed because this application first extracts a 16 kHz mono WAV through its
  own FFmpeg pipeline before WhisperX/VAD processing.
- Clean-install persistence, user-owned video quality and real API providers
  remain manual gates; automated contract/integration coverage for their state
  transitions is passing.
- Clean-VM, real-video/API and GitHub draft-release scenarios remain unexecuted
  until external test inputs, environments and authentication are available.
