import json
from datetime import date
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def _project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'(?m)^version\s*=\s*"([^"]+)"', text).group(1)


def test_release_versions_are_consistent_and_direct_inputs_are_pinned():
    config = json.loads((ROOT / "packaging" / "release-config.json").read_text(encoding="utf-8"))
    version_info = (ROOT / "packaging" / "assets" / "version-info.txt").read_text(encoding="utf-8")
    requirements = (ROOT / "packaging" / "release-requirements.txt").read_text(encoding="utf-8")

    assert config["app_version"] == _project_version()
    assert f"StringStruct('FileVersion', '{_project_version()}')" in version_info
    assert f"StringStruct('ProductVersion', '{_project_version()}')" in version_info
    for line in requirements.splitlines():
        if line and not line.startswith("#"):
            assert "==" in line and not any(operator in line for operator in (">=", "~=", "<="))
    assert f"whisperx=={config['whisperx_version']}" in requirements
    assert f"pyinstaller=={config['pyinstaller_version']}" in requirements


def test_build_script_verifies_dependencies_ffmpeg_smoke_and_inventory():
    script = (ROOT / "scripts" / "build-release.ps1").read_text(encoding="utf-8")
    for required in (
        "python -m pip check",
        "python -m pytest",
        "python -m PyInstaller",
        "smoke-frozen.ps1",
        "runtime-inventory.json",
        "dependency-manifest.txt",
        "ffmpeg_sha256",
        "audit-dependencies.ps1",
    ):
        assert required in script


def test_vulnerability_exceptions_are_explicit_unique_and_time_limited():
    policy = json.loads(
        (ROOT / "packaging" / "vulnerability-allowlist.json").read_text(encoding="utf-8")
    )
    advisories = policy["advisories"]
    ids = [item["id"] for item in advisories]

    assert advisories
    assert len(ids) == len(set(ids))
    for item in advisories:
        assert item["package"] in {"torch", "transformers"}
        assert item["affected_version"]
        assert item["rationale"]
        expiry = date.fromisoformat(item["expires_on"])
        assert date(2026, 7, 30) < expiry <= date(2026, 12, 31)


def test_stable_installer_is_blocked_by_active_vulnerability_exceptions():
    script = (ROOT / "scripts" / "build-installer.ps1").read_text(encoding="utf-8")

    assert "audit-dependencies.ps1" in script
    assert "-FailOnAllowlisted" in script
