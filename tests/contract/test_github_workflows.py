from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def _load(name):
    return yaml.load((WORKFLOWS / name).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_hosted_ci_is_read_only_and_tests_supported_python_versions():
    workflow = _load("ci.yml")
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["test"]["runs-on"] == "windows-latest"
    assert workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"] == ["3.11", "3.13"]
    assert "secrets." not in (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")


def test_security_workflow_has_no_write_permissions_or_release_environment():
    text = (WORKFLOWS / "security.yml").read_text(encoding="utf-8")
    workflow = _load("security.yml")
    assert workflow["permissions"] == {"contents": "read"}
    assert "windows-release" not in text
    assert "SIGNING_" not in text
    assert "dependency-review-action" in text
    assert "gitleaks" in text
    assert "gitleaks/gitleaks-action" not in text
    assert 'GITLEAKS_VERSION: "8.30.1"' in text
    assert 'GITLEAKS_LINUX_X64_SHA256: "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"' in text
    assert "fetch-depth: 0" in text
    assert '"${RUNNER_TEMP}/gitleaks" git' in text
    assert '--log-opts="--all"' in text
    assert "ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION" not in text


def test_release_bundle_workflow_is_protected_and_never_runs_for_pull_requests():
    text = (WORKFLOWS / "release-windows.yml").read_text(encoding="utf-8")
    workflow = _load("release-windows.yml")
    triggers = workflow["on"]
    assert "pull_request" not in triggers
    assert "push" in triggers and "workflow_dispatch" in triggers
    job = workflow["jobs"]["build-bundle"]
    assert job["runs-on"] == ["self-hosted", "Windows", "X64", "ai-subtitle-release"]
    assert job["environment"] == "windows-release"
    assert workflow["permissions"]["contents"] == "read"
    assert "gh release" not in text.lower()
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in text
    assert "actions/attest-build-provenance@0f67c3f4856b2e3261c31976d6725780e5e4c373" in text
    assert "github.event.repository.visibility == 'public'" in text
    assert "vars.ENABLE_PRIVATE_ATTESTATIONS == 'true'" in text
    assert text.index("Upload verified release bundle") < text.index(
        "Attest build provenance when supported"
    )
    assert "release/*" in text
    assert "SIGNING_PFX_BASE64" in text
    assert "pull_request_target" not in text


def test_all_workflow_actions_are_pinned_to_commit_shas():
    for path in WORKFLOWS.glob("*.yml"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped.startswith("uses:"):
                continue
            action_ref = stripped.split("#", 1)[0].split("@", 1)[-1].strip()
            assert len(action_ref) == 40
            assert all(character in "0123456789abcdef" for character in action_ref)


def test_release_tooling_has_no_github_cli_dependency():
    workflow = (WORKFLOWS / "release-windows.yml").read_text(encoding="utf-8").lower()
    verifier = (ROOT / "scripts" / "verify-release.ps1").read_text(encoding="utf-8").lower()
    quickstart = (ROOT / "specs" / "001-desktop-subtitle-studio" / "quickstart.md").read_text(
        encoding="utf-8"
    )
    assert "gh release" not in workflow
    assert "get-command gh" not in verifier
    assert "githubdraft" not in verifier
    assert "-GitHubDraft" not in quickstart


def test_release_naming_is_versioned_and_repository_setup_documents_gates():
    release_workflow = (WORKFLOWS / "release-windows.yml").read_text(encoding="utf-8")
    setup = (ROOT / "docs" / "GITHUB_SETUP.md").read_text(encoding="utf-8")
    assert "${{ steps.identity.outputs.tag }}" in release_workflow
    for required in (
        "private repository",
        "branch ruleset",
        "ai-subtitle-release",
        "windows-release",
        "SIGNING_PFX_BASE64",
        "giao diện web",
        "RELEASE_EXE.md",
    ):
        assert required.lower() in setup.lower()
