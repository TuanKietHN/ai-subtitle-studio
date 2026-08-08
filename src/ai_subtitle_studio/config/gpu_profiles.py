"""Configurable GPU execution profiles and compatibility resolution."""

from __future__ import annotations

from dataclasses import dataclass

from ai_subtitle_studio.domain.entities import GpuCapabilitySnapshot

DEFAULT_PROFILE_ID = "default"
LOW_VRAM_PROFILE_ID = "low-vram-4gb"
KNOWN_PROFILE_IDS = {DEFAULT_PROFILE_ID, LOW_VRAM_PROFILE_ID}
LOW_VRAM_MODELS = {"small.en", "small"}


class GpuProfileError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class EffectiveGpuExecutionProfile:
    profile_id: str
    model_id: str
    compute_type: str
    batch_size: int
    requires_user_confirmation: bool = False
    recommended_profile_id: str | None = None
    warning: str | None = None


def configured_execution_profile(
    *,
    requested_model_id: str,
    requested_profile_id: str = DEFAULT_PROFILE_ID,
) -> EffectiveGpuExecutionProfile:
    """Resolve persisted profile parameters without performing a slow GPU probe."""
    if requested_profile_id not in KNOWN_PROFILE_IDS:
        raise GpuProfileError(f"Profile GPU không hợp lệ: {requested_profile_id}")
    if requested_profile_id == LOW_VRAM_PROFILE_ID:
        requires_confirmation = requested_model_id not in LOW_VRAM_MODELS
        return EffectiveGpuExecutionProfile(
            profile_id=LOW_VRAM_PROFILE_ID,
            model_id=requested_model_id,
            compute_type="int8_float16",
            batch_size=1,
            requires_user_confirmation=requires_confirmation,
            recommended_profile_id=LOW_VRAM_PROFILE_ID if requires_confirmation else None,
            warning=(
                "Profile 4 GiB nên dùng small.en hoặc small; xác nhận đổi model trước khi chạy."
                if requires_confirmation
                else None
            ),
        )
    return EffectiveGpuExecutionProfile(
        profile_id=DEFAULT_PROFILE_ID,
        model_id=requested_model_id,
        compute_type="float16",
        batch_size=16,
    )


def resolve_execution_profile(
    gpu: GpuCapabilitySnapshot,
    *,
    requested_model_id: str,
    requested_profile_id: str = DEFAULT_PROFILE_ID,
) -> EffectiveGpuExecutionProfile:
    if not gpu.torch_cuda_ready:
        raise GpuProfileError(gpu.torch_cuda_error or "Torch CUDA không khởi tạo được trên GPU đã chọn")
    if requested_profile_id not in KNOWN_PROFILE_IDS:
        raise GpuProfileError(f"Profile GPU không hợp lệ: {requested_profile_id}")

    total_gib = gpu.total_vram_bytes / float(1024**3) if gpu.total_vram_bytes else 0.0
    if requested_profile_id == LOW_VRAM_PROFILE_ID:
        if "int8_float16" not in gpu.supported_compute_types:
            raise GpuProfileError("GPU/CTranslate2 không hỗ trợ compute type int8_float16")
        return configured_execution_profile(
            requested_model_id=requested_model_id,
            requested_profile_id=requested_profile_id,
        )

    needs_low_vram = 0 < total_gib <= 4.5 and requested_model_id not in LOW_VRAM_MODELS
    return EffectiveGpuExecutionProfile(
        profile_id=DEFAULT_PROFILE_ID,
        model_id=requested_model_id,
        compute_type="float16",
        batch_size=16,
        requires_user_confirmation=needs_low_vram,
        recommended_profile_id=LOW_VRAM_PROFILE_ID if needs_low_vram else None,
        warning=(
            f"GPU chỉ có khoảng {total_gib:.1f} GiB VRAM; model {requested_model_id} có thể gây CUDA OOM."
            if needs_low_vram
            else None
        ),
    )
