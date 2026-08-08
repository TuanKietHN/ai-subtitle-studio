import pytest

from ai_subtitle_studio.config.gpu_profiles import (
    DEFAULT_PROFILE_ID,
    LOW_VRAM_PROFILE_ID,
    GpuProfileError,
    configured_execution_profile,
    resolve_execution_profile,
)
from ai_subtitle_studio.domain.entities import GpuCapabilitySnapshot


def _gpu(*, total_gib=4.0, ready=True, compute_types=("float16", "int8_float16")):
    return GpuCapabilitySnapshot(
        gpu_id="0",
        name="NVIDIA GeForce RTX 2050",
        driver_version="555.0",
        total_vram_bytes=int(total_gib * 1024**3),
        free_vram_bytes=int((total_gib - 0.5) * 1024**3),
        compute_capability="8.6",
        torch_cuda_ready=ready,
        supported_compute_types=list(compute_types),
    )


def test_resolver_selects_config_driven_4gb_profile_after_user_choice():
    result = resolve_execution_profile(
        _gpu(),
        requested_model_id="small.en",
        requested_profile_id=LOW_VRAM_PROFILE_ID,
    )

    assert result.profile_id == LOW_VRAM_PROFILE_ID
    assert result.model_id == "small.en"
    assert result.compute_type == "int8_float16"
    assert result.batch_size == 1


def test_persisted_low_vram_profile_parameters_do_not_wait_for_gpu_probe():
    result = configured_execution_profile(
        requested_model_id="small.en",
        requested_profile_id=LOW_VRAM_PROFILE_ID,
    )

    assert result.compute_type == "int8_float16"
    assert result.batch_size == 1


def test_resolver_never_silently_replaces_large_v3():
    result = resolve_execution_profile(_gpu(), requested_model_id="large-v3")

    assert result.profile_id == DEFAULT_PROFILE_ID
    assert result.model_id == "large-v3"
    assert result.requires_user_confirmation is True
    assert result.recommended_profile_id == LOW_VRAM_PROFILE_ID


def test_resolver_rejects_unready_torch_and_unsupported_compute_type():
    with pytest.raises(GpuProfileError, match="Torch CUDA"):
        resolve_execution_profile(_gpu(ready=False), requested_model_id="small.en", requested_profile_id=LOW_VRAM_PROFILE_ID)

    with pytest.raises(GpuProfileError, match="int8_float16"):
        resolve_execution_profile(
            _gpu(compute_types=("float16",)),
            requested_model_id="small.en",
            requested_profile_id=LOW_VRAM_PROFILE_ID,
        )
