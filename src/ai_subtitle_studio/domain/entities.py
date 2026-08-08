"""Core domain dataclasses shared by UI, workers, and persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .job_state import JobStatus


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ErrorInfo:
    code: str
    message: str
    recoverable: bool = True
    retry_allowed: bool = True


ERROR_MESSAGES = {
    "audio": "Không trích được audio. Hãy kiểm tra đường dẫn ffmpeg và file video đầu vào.",
    "stt": "Nhận dạng giọng nói thất bại. Hãy kiểm tra CUDA/GPU và cài đặt WhisperX.",
    "gpu": "Không phát hiện NVIDIA/CUDA GPU hợp lệ để chạy nhận dạng.",
    "gpu_out_of_memory": "GPU không đủ VRAM để hoàn tất nhận dạng. Hãy chọn profile/model nhẹ hơn.",
    "model": "Model Whisper đã chọn chưa sẵn sàng hoặc tải xuống thất bại.",
    "translation": "Provider dịch thất bại. Hãy kiểm tra cài đặt provider và API key.",
    "output": "Không ghi được file phụ đề đầu ra.",
    "settings": "Cài đặt ứng dụng chưa đầy đủ hoặc chưa hợp lệ.",
}

DETAIL_TRANSLATIONS = {
    "No valid NVIDIA/CUDA GPU detected": "Không phát hiện NVIDIA/CUDA GPU hợp lệ.",
    "Transcription canceled": "Tác vụ nhận dạng đã bị hủy.",
    "Transcription canceled before start": "Tác vụ nhận dạng đã bị hủy trước khi bắt đầu.",
    "STT engine is not configured": "Chưa cấu hình bộ nhận dạng giọng nói.",
    "ffmpeg executable was not found": "Không tìm thấy ffmpeg executable.",
    "ffmpeg failed": "ffmpeg chạy thất bại.",
}


def _localized_detail(detail: str | None) -> str | None:
    if not detail:
        return None
    return DETAIL_TRANSLATIONS.get(detail, "Chi tiết kỹ thuật đã được ghi trong log.")


def user_safe_error(code: str, detail: str | None = None) -> ErrorInfo:
    base = ERROR_MESSAGES.get(code, "Job thất bại do lỗi không xác định.")
    localized = _localized_detail(detail)
    return ErrorInfo(code=code, message=f"{base} {localized}".strip() if localized else base)


@dataclass(slots=True)
class VideoJob:
    source_path: str
    selected_model_id: str = "large-v3"
    id: str = field(default_factory=lambda: str(uuid4()))
    source_fingerprint: str = ""
    display_name: str = ""
    status: JobStatus = JobStatus.QUEUED
    translation_provider_id: str | None = None
    gpu_id: str | None = None
    progress_percent: float = 0.0
    progress_label: str = "Chờ xử lý"
    pause_requested: bool = False
    cancel_requested: bool = False
    retry_required: bool = False
    error_code: str | None = None
    error_message: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    started_at: str | None = None
    completed_at: str | None = None
    updated_at: str = field(default_factory=utc_now_iso)
    audio_temp_path: str | None = None
    english_srt_path: str | None = None
    vietnamese_srt_path: str | None = None
    bilingual_srt_path: str | None = None

    def __post_init__(self) -> None:
        if not self.display_name:
            self.display_name = Path(self.source_path).name


@dataclass(slots=True)
class SubtitleLine:
    sequence_number: int
    start_ms: int
    end_ms: int
    source_text: str
    id: str = field(default_factory=lambda: str(uuid4()))
    job_id: str | None = None
    translated_text: str | None = None
    word_timings_json: str | None = None
    is_edited: bool = False
    validation_status: str = "valid"


@dataclass(slots=True)
class WhisperModel:
    id: str
    display_name: str
    is_default: bool = False
    download_state: str = "not_downloaded"
    local_path: str | None = None
    size_bytes: int | None = None
    last_verified_at: str | None = None
    error_message: str | None = None
    enabled: bool = True
    description: str = ""
    recommended_vram_gb: float | None = None
    execution_profile_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ModelDownload:
    model_id: str
    id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "queued"
    percent: float = 0.0
    bytes_downloaded: int = 0
    bytes_total: int | None = None
    bytes_remaining: int | None = None
    speed_bytes_per_sec: float = 0.0
    error_message: str | None = None


@dataclass(slots=True)
class TranslationProviderConfig:
    provider_id: str
    display_name: str
    credential_alias: str
    has_api_key: bool = False
    last_validated_at: str | None = None
    last_error: str | None = None


@dataclass(slots=True)
class AppSettings:
    selected_gpu_id: str | None = None
    model_cache_dir: str | None = None
    ffmpeg_path: str | None = None
    subtitle_edit_path: str | None = None
    default_output_dir: str | None = None
    last_model_id: str = "large-v3"
    last_translation_provider_id: str | None = None
    last_compute_profile_id: str = "default"


@dataclass(slots=True)
class GpuCapabilitySnapshot:
    gpu_id: str
    name: str
    driver_version: str
    total_vram_bytes: int = 0
    free_vram_bytes: int = 0
    compute_capability: str | None = None
    torch_cuda_ready: bool = False
    torch_cuda_error: str | None = None
    supported_compute_types: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SystemInfoSnapshot:
    app_version: str
    whisperx_version: str
    faster_whisper_version: str
    torch_cuda_version: str
    gpu_driver_version: str
    detected_gpus: list[GpuCapabilitySnapshot]
    selected_model_id: str
    downloaded_models_size_bytes: int
    torch_cuda_ready: bool = False
    torch_cuda_error: str | None = None
    selected_gpu_id: str | None = None
    effective_profile_id: str | None = None
    effective_compute_type: str | None = None
    effective_batch_size: int | None = None
    ffmpeg_path: str | None = None
    data_dir: str | None = None
    log_dir: str | None = None
