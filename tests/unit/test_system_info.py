from ai_subtitle_studio.config.system_info import (
    SystemInfoProvider,
    package_version,
    torch_cuda_version,
)


def test_system_info_provider_returns_required_fields(tmp_path):
    (tmp_path / "m.bin").write_bytes(b"123")
    snapshot = SystemInfoProvider().collect(selected_model_id="large-v3", model_cache_dir=tmp_path)
    assert snapshot.app_version
    assert snapshot.whisperx_version
    assert snapshot.faster_whisper_version
    assert snapshot.selected_model_id == "large-v3"
    assert snapshot.downloaded_models_size_bytes == 3


def test_package_version_unavailable_for_missing_package():
    assert package_version("definitely-missing-package-ai-subtitle-studio") == "unavailable"


def test_torch_cuda_version_uses_distribution_local_version(monkeypatch):
    monkeypatch.setattr(
        "ai_subtitle_studio.config.system_info.package_version",
        lambda package: "2.8.0+cu128",
    )

    assert torch_cuda_version() == "12.8"
