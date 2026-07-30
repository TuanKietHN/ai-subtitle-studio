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


def test_release_workflow_is_protected_and_never_runs_for_pull_requests():
    text = (WORKFLOWS / "release-windows.yml").read_text(encoding="utf-8")
    workflow = _load("release-windows.yml")
    triggers = workflow["on"]
    assert "pull_request" not in triggers
    assert "push" in triggers and "workflow_dispatch" in triggers
    job = workflow["jobs"]["build-draft"]
    assert job["runs-on"] == ["self-hosted", "Windows", "X64", "ai-subtitle-release"]
    assert job["environment"] == "windows-release"
    assert workflow["permissions"]["contents"] == "write"
    assert "--draft" in text
    assert "actions/attest-build-provenance@96b4a1ef7235a096b17240c259729fdd70c83d45" in text
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
        "draft release",
    ):
        assert required.lower() in setup.lower()
