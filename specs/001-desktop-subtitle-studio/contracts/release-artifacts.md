# Contract: Windows Release Artifacts

## Purpose

Define the immutable files, naming rules, integrity metadata and installer behavior required for one AI Subtitle Studio GitHub Release.

## Required Assets

For version `X.Y.Z`, a stable release contains:

```text
AI-Subtitle-Studio-Setup-vX.Y.Z.exe
AI-Subtitle-Studio-Runtime-vX.Y.Z.7z.001
AI-Subtitle-Studio-Runtime-vX.Y.Z.7z.002
...additional contiguous runtime volumes
release-manifest-vX.Y.Z.json
SHA256SUMS-vX.Y.Z.txt
SBOM-vX.Y.Z.json
THIRD-PARTY-NOTICES-vX.Y.Z.txt
```

Release candidates use the complete semantic version in every filename, for example `v0.1.0-rc.1`.

## Size Contract

- Every GitHub Release asset MUST be smaller than 2 GiB.
- Every runtime volume MUST be smaller than 1.9 GiB.
- Runtime packaging SHOULD target 1.8 GiB per volume to leave operational margin.
- The online installer SHOULD remain small and MUST NOT embed the full Torch CUDA runtime.
- Whisper model weights MUST NOT be present in any release artifact.

## Manifest Contract

`release-manifest-vX.Y.Z.json` has this logical shape:

```json
{
  "schema_version": 1,
  "release": {
    "app_version": "X.Y.Z",
    "git_commit": "<40-character-sha>",
    "git_tag": "vX.Y.Z",
    "built_at_utc": "<ISO-8601 UTC>",
    "python_version": "<exact-version>",
    "platform": "windows-x64",
    "whisperx_version": "3.8.6",
    "torch_version": "<exact-cu128-version>",
    "cuda_runtime_version": "12.8",
    "pyinstaller_version": "<exact-version>",
    "dependency_manifest_sha256": "<sha256>"
  },
  "channel": "stable",
  "minimum_windows_version": "10",
  "architecture": "x64",
  "install_scope": "current_user",
  "installed_size_bytes": 0,
  "temporary_space_bytes": 0,
  "artifacts": [
    {
      "name": "AI-Subtitle-Studio-Runtime-vX.Y.Z.7z.001",
      "kind": "runtime_volume",
      "size_bytes": 0,
      "sha256": "<sha256>",
      "download_url": "https://github.com/<owner>/<repo>/releases/download/vX.Y.Z/<asset>",
      "required": true,
      "volume_index": 1,
      "signature_status": "not_applicable"
    }
  ]
}
```

The implementation MAY add optional fields, but MUST NOT reinterpret existing fields without incrementing `schema_version`.

## Installer Contract

The installer MUST:

1. Run as a current-user installer without requiring administrator rights.
2. Display version, expected download size and required temporary/installed disk space before downloading.
3. Download only HTTPS URLs tied to the exact release tag.
4. Verify SHA-256 for every downloaded archive before extraction.
5. Abort without modifying the active installation if an asset is missing, truncated or hash-invalid.
6. Extract into a staging directory before replacing the active install directory.
7. Preserve SQLite, credentials, settings, logs, model cache and subtitle output during upgrade.
8. Create Start Menu and optional desktop shortcuts with working directory set to the install directory.
9. Register an uninstaller using a stable application ID.
10. Remove temporary download/staging files after success, cancellation or handled failure.
11. Write an installer log that does not contain API keys or user subtitle contents.

The installer SHOULD retry transient network failures and SHOULD reuse a previously downloaded volume only after its SHA-256 has been verified.

## Frozen Runtime Contract

The installed runtime MUST:

- Start without system Python or a pre-existing virtual environment.
- Include required Qt platform plugins and native DLLs.
- Import `whisperx`, `torch`, `faster_whisper`, `ctranslate2`, `httpx` and the selected keyring backend.
- Include `resources/models.json`.
- Include a working ffmpeg executable resolved after any explicit user setting and before PATH fallback.
- Read package versions at runtime for System Info.
- Store persistent data only in the user-data paths defined in `data-model.md`.
- Exclude Whisper model weights, tests, caches, local databases, sample outputs and development `.lib` files.

## Signing Contract

- Stable installer and application executable MUST have a valid Authenticode signature.
- Release verification MUST validate the signature after all packaging/signing steps.
- If signing is unavailable, the release MUST be marked pre-release and `signature_status` MUST be `unsigned_prerelease`.
- Signing credentials MUST NOT be available to pull-request workflows or committed to the repository.

## Publication Contract

- A release starts as draft.
- All assets are uploaded before verification.
- The owner downloads draft assets with the browser and runs the local verifier
  to check names, sizes, SHA-256, manifest consistency and signatures.
- Manual Windows/GPU acceptance is recorded before stable publication.
- Published assets are immutable; fixes use a new tag/version.
- README's latest download link points to:

```text
https://github.com/<owner>/<repo>/releases/latest/download/AI-Subtitle-Studio-Setup-vX.Y.Z.exe
```

If versioned installer names make a stable `/latest/download/` URL impractical, the release workflow MAY also upload one immutable-content alias named `AI-Subtitle-Studio-Setup-latest.exe`, whose hash is recorded in the same manifest.
