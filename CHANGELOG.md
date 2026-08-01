# Changelog

All notable changes to AI Subtitle Studio are documented here.

The project follows Semantic Versioning. Release candidates use the
`MAJOR.MINOR.PATCH-rc.N` form.

## [Unreleased]

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
