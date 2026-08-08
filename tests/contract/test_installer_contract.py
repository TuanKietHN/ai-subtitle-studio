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
        "runtime.staging",
        "runtime.previous",
        "RenameFile",
        "UninstallDelete",
        'WorkingDir: "{app}\\runtime"',
        "SetupLogging=yes",
        "CreateDownloadPage",
        "ForceDirectories(ExpandConstant('{app}'))",
        "ExpandConstant('{app}\\runtime.staging')",
        "RuntimeBundleId",
        ".runtime-bundle-id",
        "RegisterExtraCloseApplicationsResource",
        "{src}",
        "installer-cache",
        "bits-download.ps1",
        "GetSHA256OfFile",
        "ExtraDiskSpaceRequired={#TemporarySpaceBytes}",
        "CacheMetadataMatches",
        "ResetBitsJob",
        "UtcNowIso8601",
        "IsRepair",
    ):
        assert required in script
    assert "API_KEY=" not in script
    assert "credentials" not in script.lower()


def test_same_runtime_reuse_is_bound_to_bundle_identity_without_duplicate_version_check():
    script = (ROOT / "packaging" / "installer" / "ai-subtitle-studio.iss").read_text(encoding="utf-8")
    function_body = script.split("function SameRuntimeInstalled", 1)[1].split("procedure DownloadAndActivateRuntime", 1)[0]

    assert '"runtime_bundle_id":"{#RuntimeBundleId}"' in function_body
    assert '"volume_names":' in function_body
    assert '"volume_sha256":' in function_body
    assert '"app_version":"{#AppVersion}"' not in function_body


def test_installer_distinguishes_fresh_upgrade_repair_and_rollback_messages():
    script = (ROOT / "packaging" / "installer" / "ai-subtitle-studio.iss").read_text(encoding="utf-8")

    assert "Cài mới AI Subtitle Studio" in script
    assert "Nâng cấp AI Subtitle Studio" in script
    assert "Sửa chữa AI Subtitle Studio" in script
    assert "bản cũ đã được khôi phục" in script
    assert "lần cài đầu tiên" in script


def test_cache_metadata_invalidates_partial_bits_state():
    script = (ROOT / "packaging" / "installer" / "ai-subtitle-studio.iss").read_text(encoding="utf-8")

    assert "CacheMetadataJson(Name, Hash, Size)" in script
    assert "ResetBitsJob := not CacheMetadataMatches" in script
    assert "DeleteFile(PartPath)" in script
    assert "DeleteFile(StatusPath)" in script
    assert "-ResetExisting" in script


def test_recoverable_bits_failure_preserves_partial_for_next_run():
    script = (ROOT / "packaging" / "installer" / "ai-subtitle-studio.iss").read_text(encoding="utf-8")
    resolve_body = script.split("function ResolveVolume", 1)[1].split("function SameRuntimeInstalled", 1)[0]

    assert "BitsCompleted := TryBitsDownload" in resolve_body
    assert "if BitsCompleted and FileExists(PartPath)" in resolve_body
    assert "if FileExists(PartPath) then\n    DeleteFile(PartPath)" not in resolve_body


def test_installer_exposes_safe_uninstall_choices_and_shortcut():
    script = (ROOT / "packaging" / "installer" / "ai-subtitle-studio.iss").read_text(encoding="utf-8")

    assert 'Name: "{group}\\Gỡ cài đặt AI Subtitle Studio"' in script
    assert 'Filename: "{uninstallexe}"' in script
    assert "Xóa model, cache, log, lịch sử và API key" in script
    assert "Xóa phụ đề/output đã tạo" in script
    assert "--cleanup-private-data" in script
    assert "--cleanup-owned-outputs" in script
    assert "ConfirmOutputCleanup" in script


def test_bits_helper_is_resumable_foreground_and_never_skips_hash_gate():
    helper = (ROOT / "packaging" / "installer" / "bits-download.ps1").read_text(encoding="utf-8")

    for required in (
        "Start-BitsTransfer",
        "Get-BitsTransfer",
        "Resume-BitsTransfer",
        "Complete-BitsTransfer",
        "-Priority Foreground",
        "BytesTransferred",
        "BytesTotal",
        "ResetExisting",
        "Remove-BitsTransfer",
    ):
        assert required in helper
    assert "Get-FileHash" not in helper, "Inno owns the final SHA-256 promotion gate"


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
