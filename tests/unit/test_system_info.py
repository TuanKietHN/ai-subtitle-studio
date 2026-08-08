from ai_subtitle_studio.config.system_info import (
    SystemInfoProvider,
    nvidia_smi_info,
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


def test_nvidia_inventory_parses_vram_without_claiming_torch_readiness(monkeypatch):
    class Result:
        stdout = "0, NVIDIA GeForce RTX 2050, 555.42, 4096 MiB, 3072 MiB\n"

    monkeypatch.setattr(
        "ai_subtitle_studio.config.system_info.subprocess.run",
        lambda *args, **kwargs: Result(),
    )

    driver, gpus = nvidia_smi_info()

    assert driver == "555.42"
    assert gpus[0]["memory_total_bytes"] == 4096 * 1024 * 1024
    assert gpus[0]["memory_free_bytes"] == 3072 * 1024 * 1024


def test_system_info_merges_torch_capability_and_compute_types(monkeypatch):
    monkeypatch.setattr(
        "ai_subtitle_studio.config.system_info.nvidia_smi_info",
        lambda: (
            "555.42",
            [
                {
                    "id": "0",
                    "name": "NVIDIA GeForce RTX 2050",
                    "driver_version": "555.42",
                    "memory_total_bytes": 4 * 1024**3,
                    "memory_free_bytes": 3 * 1024**3,
                }
            ],
        ),
    )
    monkeypatch.setattr(
        "ai_subtitle_studio.config.system_info.ctranslate2_compute_types",
        lambda gpu_id: ["float16", "int8_float16"],
    )

    snapshot = SystemInfoProvider(
        torch_capability_provider=lambda: (
            {"0": {"ready": True, "compute_capability": "8.6", "name": "NVIDIA GeForce RTX 2050"}},
            None,
        )
    ).collect()
    gpu = snapshot.detected_gpus[0]

    assert gpu.torch_cuda_ready is True
    assert gpu.compute_capability == "8.6"
    assert gpu.supported_compute_types == ["float16", "int8_float16"]


def test_system_info_sorts_numeric_and_diagnostic_gpu_ids_without_type_error(monkeypatch):
    monkeypatch.setattr(
        "ai_subtitle_studio.config.system_info.nvidia_smi_info",
        lambda: (
            "555.42",
            [
                {"id": "diagnostic", "name": "Unknown NVIDIA GPU", "driver_version": "555.42"},
                {"id": "10", "name": "GPU 10", "driver_version": "555.42"},
                {"id": "2", "name": "GPU 2", "driver_version": "555.42"},
            ],
        ),
    )
    snapshot = SystemInfoProvider(torch_capability_provider=lambda: ({}, "not ready")).collect()

    assert [gpu.gpu_id for gpu in snapshot.detected_gpus] == ["2", "10", "diagnostic"]
