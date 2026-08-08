# Changelog

All notable changes to AI Subtitle Studio are documented here.

The project follows Semantic Versioning. Release candidates use the
`MAJOR.MINOR.PATCH-rc.N` form.

## [Unreleased]

## [0.1.0-rc.5] - Unreleased

### Added

- Added a configuration-driven 4 GiB NVIDIA GPU profile for hardware such as
  RTX 2050, including `small.en`/`small`, `int8_float16`, batch size 1, GPU
  inventory, VRAM/capability diagnostics and an explicit model-change prompt.
- Added safe uninstall choices for private application data and application-
  owned subtitle outputs, with both choices disabled by default.
- Added a persistent, runtime-identity-scoped installer cache with local-volume
  reuse, resumable BITS transfer and verified HTTPS fallback.

### Changed

- Runtime activation now stages on the installation volume, smoke-tests before
  activation and atomically rolls back to the previous runtime on failure.
- Release manifests now bind every runtime volume and dependency identity to a
  deterministic `runtime_bundle_id`.
- WhisperX now propagates compute type and batch size, releases ASR memory
  before alignment, reports peak GPU memory and retries CUDA OOM at most once.

### Fixed

- Fixed the RC4 fresh-install failure caused by activating the runtime before
  the per-user application directory existed.
- Prevented repair/retry of the exact same runtime bundle from downloading and
  extracting the already active payload again.

### Known issues and release gates

- RC5 is unsigned and must remain a GitHub pre-release; Windows SmartScreen may
  warn until Authenticode signing is available.
- Added a time-limited prerelease exception for `PYSEC-2026-3624` in transitive
  `lightning==2.6.5`. WhisperX reaches the affected checkpoint loader through
  mandatory Pyannote VAD, but RC5 only permits the pinned and release-hashed
  bundled VAD checkpoint and exposes no user Lightning checkpoint selector;
  stable remains blocked until a patched Lightning release is pinned.
- Clean-Windows install/resume/upgrade/uninstall, real NVIDIA 4 GiB and real
  Google/DeepSeek acceptance remain required before publication claims are
  expanded.
- Locally generated assets whose manifest records `git_commit=uncommitted` are
  validation-only and must be rebuilt from the clean tagged commit.

## [0.1.0-rc.4] - 2026-08-01

### Fixed

- Skipped GitHub artifact attestation when it is unavailable for a private
  repository while preserving verified bundle upload; Enterprise Cloud private
  repositories can explicitly enable the step with a repository variable.

## [0.1.0-rc.3] - 2026-08-01

### Fixed

- Replaced the Node 20 Gitleaks action with a checksum-pinned Gitleaks CLI scan
  that handles the repository's root commit and scans the complete history.
- Updated official GitHub Actions to Node 24-compatible releases while keeping
  every action reference pinned to an immutable commit SHA.

## [0.1.0-rc.2] - 2026-08-01

### Changed

- Expanded source-only ignore rules for Python caches, generated binaries,
  release archives, user media/subtitles, local databases and signing material.
- Replaced GitHub CLI release operations with browser-based publication and a
  verified Actions artifact bundle.
- Added a Vietnamese manual for building the Windows EXE/online installer,
  pushing with Git and creating a GitHub Release from the web interface, with
  beginner-friendly explanations, validation steps and troubleshooting.
- Scoped SHA-256 checksum generation and verification to the current version's
  manifest and assets so files from older releases cannot leak into a bundle.

## [0.1.0-rc.1] - 2026-07-30

### Added

- Windows PyInstaller `onedir` runtime, online Inno Setup installer, split
  hash-verified runtime volumes, SBOM and third-party notices.
- GitHub CI, security scanning, protected Windows release workflow and build
  provenance attestation.
- Constitution 1.0.1 clarification for mandatory Pyannote VAD through
  `vad_method="pyannote"`.

### Changed

- Frozen-safe resource/data/model/log/output paths and rotating credential-
  redacted logs.
- Release workflow actions are pinned to immutable commit SHAs.
- File cleanup is restricted to UUID work directories and the configured model
  cache.

### Security

- Dependency audit records temporary prerelease-only exceptions for Torch 2.8.0
  and Transformers 4.57.6 inherited from WhisperX 3.8.6.
- Stable builds are blocked while any vulnerability exception is active.
- PFX passwords are not forwarded to SignTool command-line arguments.

### Known issues and release gates

- This candidate is unsigned and Windows SmartScreen may warn.
- Clean-machine installer and real Google/DeepSeek credential acceptance still
  require external test environments.
- Real Subtitle Edit 5.1.0 portable launch acceptance passed locally with an
  English SRT produced by the NVIDIA GPU scenario.
- WhisperX 3.8.6 constrains Torch to 2.8.x and Hugging Face Hub below 1.0;
  upgrade before a stable release when upstream compatibility is available.
