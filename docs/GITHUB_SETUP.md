# GitHub Repository and Release Setup

## 1. Create the repository

Create `ai-subtitle-studio` as a private repository first. Do not initialize it
with a README, license or `.gitignore`; those files already exist locally.
Confirm the final GitHub owner before regenerating release artifacts because
the owner is embedded in every immutable runtime download URL.

Add the remote only after verifying the destination:

```powershell
git remote add origin https://github.com/<owner>/ai-subtitle-studio.git
git remote -v
git push -u origin main
```

Keep the repository private until source history, license policy, dependency
notices and the first draft release have been reviewed. Changing visibility is
a deliberate owner decision, not part of an automated workflow.

## 2. Protect `main`

Create a branch ruleset targeting the default branch:

- Require a pull request before merging.
- Require at least one approving review and dismiss stale approvals.
- Require conversation resolution.
- Require the `Source CI` checks for Python 3.11 and 3.13.
- Require the security checks that are supported by the repository plan.
- Block force pushes and branch deletion.
- Do not allow bypass except for a narrowly controlled repository owner or
  recovery role.

Enable private vulnerability reporting, Dependabot alerts and secret scanning
where the repository plan supports them. Treat dependency-review availability
as a repository-plan capability; do not weaken workflow permissions to work
around an unavailable feature.

## 3. Register the protected release runner

Register a dedicated Windows x64 self-hosted runner with all labels below:

```text
self-hosted
Windows
X64
ai-subtitle-release
```

The runner must be dedicated to this repository or a tightly scoped release
runner group. It must not accept pull-request jobs. Install and pin:

- Python 3.13.7 and the dependencies in
  `packaging/release-requirements.txt`.
- 7-Zip 24.09 or a reviewed replacement.
- Inno Setup 6.7.3 or a reviewed compatible update.
- Windows SDK SignTool.
- FFmpeg 8.0.1 x64 at a path discoverable by the release script.

Provision at least 40 GiB free disk space. Clear generated `build/`, `dist/`,
`release/` and `release-staging/` between unrelated release attempts, while
never deleting user data or signing material.

## 4. Create the protected environment

Create an environment named `windows-release`:

- Require an owner/release-manager approval.
- Restrict deployment branches/tags to protected release tags.
- Store `SIGNING_PFX_BASE64` and `SIGNING_PFX_PASSWORD` only in this
  environment.
- Prefer a hardware-backed or managed signing service when available. The PFX
  path is a compatibility fallback.

Pull-request and hosted CI workflows must never reference this environment or
these secrets. The release workflow creates a temporary certificate file under
`RUNNER_TEMP`, signs, verifies and removes it in an `always()` step.

## 5. Release procedure

1. Merge a version bump where `pyproject.toml`,
   `packaging/release-config.json` and version resources match.
2. Create an annotated tag `vX.Y.Z` on the reviewed commit.
3. Push the tag or manually dispatch the workflow with the same version.
4. Approve the `windows-release` environment deployment.
5. Inspect the draft release and download it to a clean Windows VM.
6. Run clean-install, corrupt-download, upgrade and uninstall scenarios.
7. Record the separate NVIDIA GPU/API acceptance.
8. Publish only after `verify-release.ps1 -GitHubDraft` passes.

Stable releases require valid Authenticode signatures. If signing or any
manual acceptance gate is unavailable, use a semantic pre-release version such
as `0.1.0-rc.1` and publish only as a pre-release. Never replace assets on an
already published tag.
