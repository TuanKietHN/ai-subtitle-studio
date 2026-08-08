"""Runtime system information for About/System Info."""

from __future__ import annotations

import importlib.metadata
import os
import re
import subprocess
from threading import Event, Lock, Thread
from typing import Callable
from pathlib import Path
from ai_subtitle_studio import APP_VERSION
from ai_subtitle_studio.domain.entities import GpuCapabilitySnapshot, SystemInfoSnapshot

UNAVAILABLE = "unavailable"
_TORCH_PROBE_LOCK = Lock()
_TORCH_PROBE_READY = Event()
_TORCH_PROBE_STARTED = False
_TORCH_PROBE_RESULT: tuple[dict[str, dict[str, object]], str | None] | None = None

def package_version(package_name: str) -> str:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return UNAVAILABLE

def torch_cuda_version() -> str:
    version = package_version("torch")
    match = re.search(r"\+cu(\d{2,3})", version)
    if not match:
        return UNAVAILABLE
    digits = match.group(1)
    return f"{digits[:-1]}.{digits[-1]}"

def _memory_mib_to_bytes(value: str) -> int:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", value)
    return int(float(match.group(1)) * 1024 * 1024) if match else 0


def nvidia_smi_info() -> tuple[str, list[dict[str, object]]]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,driver_version,memory.total,memory.free",
                "--format=csv,noheader",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return UNAVAILABLE, []
    gpus: list[dict[str, object]] = []
    driver = UNAVAILABLE
    for line in result.stdout.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 5:
            driver = parts[2]
            gpus.append(
                {
                    "id": parts[0],
                    "name": parts[1],
                    "driver_version": parts[2],
                    "memory_total_bytes": _memory_mib_to_bytes(parts[3]),
                    "memory_free_bytes": _memory_mib_to_bytes(parts[4]),
                }
            )
    return driver, gpus


def torch_gpu_capabilities() -> tuple[dict[str, dict[str, object]], str | None]:
    try:
        import torch  # type: ignore

        cuda = getattr(torch, "cuda", None)
        if cuda is None or not cuda.is_available():
            return {}, "Torch CUDA báo không khả dụng"
        devices: dict[str, dict[str, object]] = {}
        original_device = int(cuda.current_device())
        try:
            for index in range(cuda.device_count()):
                properties = cuda.get_device_properties(index)
                cuda.set_device(index)
                cuda.init()
                free_bytes = 0
                try:
                    free_bytes = int(cuda.mem_get_info(index)[0])
                except Exception:
                    pass
                devices[str(index)] = {
                    "ready": True,
                    "name": str(getattr(properties, "name", f"CUDA GPU {index}")),
                    "total_vram_bytes": int(getattr(properties, "total_memory", 0)),
                    "free_vram_bytes": free_bytes,
                    "compute_capability": f"{int(properties.major)}.{int(properties.minor)}",
                }
        finally:
            cuda.set_device(original_device)
        if not devices:
            return {}, "Torch CUDA không tìm thấy thiết bị"
        return devices, None
    except Exception as exc:
        return {}, f"Torch CUDA khởi tạo thất bại: {exc}"


def torch_cuda_ready() -> tuple[bool, str | None]:
    devices, error = torch_gpu_capabilities()
    return bool(devices), error


def _run_background_torch_probe() -> None:
    global _TORCH_PROBE_RESULT
    try:
        _TORCH_PROBE_RESULT = torch_gpu_capabilities()
    finally:
        _TORCH_PROBE_READY.set()


def cached_torch_gpu_capabilities(
    wait_seconds: float = 0.25,
) -> tuple[dict[str, dict[str, object]], str | None]:
    """Return cached Torch inventory without blocking the UI on first CUDA init."""
    global _TORCH_PROBE_STARTED
    with _TORCH_PROBE_LOCK:
        if not _TORCH_PROBE_STARTED:
            _TORCH_PROBE_STARTED = True
            Thread(target=_run_background_torch_probe, name="torch-gpu-probe", daemon=True).start()
    _TORCH_PROBE_READY.wait(timeout=max(0.0, wait_seconds))
    if _TORCH_PROBE_READY.is_set() and _TORCH_PROBE_RESULT is not None:
        return _TORCH_PROBE_RESULT
    return {}, "Torch CUDA đang khởi tạo ở nền; mở lại System Info sau ít phút"


def ctranslate2_compute_types(gpu_id: str) -> list[str]:
    try:
        import ctranslate2  # type: ignore

        values = ctranslate2.get_supported_compute_types("cuda", int(gpu_id))
        return sorted(str(value) for value in values)
    except Exception:
        return []


def _gpu_sort_key(item: tuple[str, dict[str, object]]) -> tuple[int, int | str]:
    gpu_id = item[0]
    return (0, int(gpu_id)) if gpu_id.isdigit() else (1, gpu_id.casefold())

def directory_size(path: str | Path | None) -> int:
    if not path:
        return 0
    root = Path(path)
    if not root.exists():
        return 0
    total = 0
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            try:
                total += (Path(dirpath) / filename).stat().st_size
            except OSError:
                pass
    return total

class SystemInfoProvider:
    def __init__(
        self,
        *,
        ffmpeg_path: str | Path | None = None,
        data_dir: str | Path | None = None,
        log_dir: str | Path | None = None,
        torch_capability_provider: Callable[[], tuple[dict[str, dict[str, object]], str | None]] | None = None,
    ) -> None:
        self.ffmpeg_path = str(ffmpeg_path) if ffmpeg_path else None
        self.data_dir = str(data_dir) if data_dir else None
        self.log_dir = str(log_dir) if log_dir else None
        self.torch_capability_provider = torch_capability_provider or cached_torch_gpu_capabilities

    def collect(
        self,
        selected_model_id: str = "large-v3",
        model_cache_dir: str | None = None,
        *,
        selected_gpu_id: str | None = None,
        effective_profile_id: str | None = None,
        effective_compute_type: str | None = None,
        effective_batch_size: int | None = None,
    ) -> SystemInfoSnapshot:
        driver, nvidia_gpus = nvidia_smi_info()
        torch_devices, torch_error = self.torch_capability_provider()
        inventory: dict[str, dict[str, object]] = {
            str(item["id"]): dict(item) for item in nvidia_gpus
        }
        for gpu_id, torch_info in torch_devices.items():
            inventory.setdefault(
                gpu_id,
                {"id": gpu_id, "name": torch_info.get("name", f"CUDA GPU {gpu_id}"), "driver_version": driver},
            ).update(
                {
                    key: value
                    for key, value in torch_info.items()
                    if key in {"name", "total_vram_bytes", "free_vram_bytes", "compute_capability"}
                    and value not in (None, 0, "")
                }
            )
        gpus = [
            GpuCapabilitySnapshot(
                gpu_id=gpu_id,
                name=str(item.get("name") or f"NVIDIA GPU {gpu_id}"),
                driver_version=str(item.get("driver_version") or driver),
                total_vram_bytes=int(item.get("memory_total_bytes") or item.get("total_vram_bytes") or 0),
                free_vram_bytes=int(item.get("memory_free_bytes") or item.get("free_vram_bytes") or 0),
                compute_capability=str(item.get("compute_capability")) if item.get("compute_capability") else None,
                torch_cuda_ready=bool(torch_devices.get(gpu_id, {}).get("ready")),
                torch_cuda_error=None if gpu_id in torch_devices else torch_error,
                supported_compute_types=ctranslate2_compute_types(gpu_id) if gpu_id in torch_devices else [],
            )
            for gpu_id, item in sorted(inventory.items(), key=_gpu_sort_key)
        ]
        return SystemInfoSnapshot(
            app_version=APP_VERSION,
            whisperx_version=package_version("whisperx"),
            faster_whisper_version=package_version("faster-whisper"),
            torch_cuda_version=torch_cuda_version(),
            gpu_driver_version=driver,
            detected_gpus=gpus,
            selected_model_id=selected_model_id,
            downloaded_models_size_bytes=directory_size(model_cache_dir),
            torch_cuda_ready=bool(torch_devices),
            torch_cuda_error=torch_error,
            selected_gpu_id=selected_gpu_id,
            effective_profile_id=effective_profile_id,
            effective_compute_type=effective_compute_type,
            effective_batch_size=effective_batch_size,
            ffmpeg_path=self.ffmpeg_path,
            data_dir=self.data_dir,
            log_dir=self.log_dir,
        )
