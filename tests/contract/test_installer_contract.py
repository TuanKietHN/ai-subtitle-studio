from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_installer_is_per_user_hash_verified_and_upgrade_safe():
    script = (ROOT / "packaging" / "installer" / "ai-subtitle-studio.iss").read_text(encoding="utf-8")
    for required in (
        "PrivilegesRequired=lowest",
        r"DefaultDirName={localappdata}\Programs\AI Subtitle Studio",
        "DownloadTemporaryFile",
        "RuntimeVolume1Sha256",
        "7z.exe",
        "runtime-staging",
        "runtime.previous",
        "RenameFile",
        "UninstallDelete",
        'WorkingDir: "{app}\\runtime"',
        "SetupLogging=yes",
    ):
        assert required in script
    assert "API key" not in script
    assert "credentials" not in script.lower()


def test_installer_build_enforces_signed_stable_or_unsigned_prerelease():
    script = (ROOT / "scripts" / "build-installer.ps1").read_text(encoding="utf-8")
    assert "Stable installer builds require" in script
    assert "unsigned_prerelease" in script
    assert "sign-release.ps1" in script


def test_signing_password_is_not_forwarded_on_signtool_command_line():
    script = (ROOT / "scripts" / "sign-release.ps1").read_text(encoding="utf-8")

    assert "Import-PfxCertificate" in script
    assert "AI_SUBTITLE_SIGNING_PASSWORD" in script
    assert "Remove-Item Env:AI_SUBTITLE_SIGNING_PASSWORD" in script
    assert "'/p'" not in script
    assert "verify /pa /all" in script
