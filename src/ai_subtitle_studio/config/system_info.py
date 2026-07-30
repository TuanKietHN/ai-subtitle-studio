"""Runtime system information for About/System Info."""

from __future__ import annotations

import importlib.metadata
import os
import re
import subprocess
from pathlib import Path
from ai_subtitle_studio import APP_VERSION
from ai_subtitle_studio.domain.entities import SystemInfoSnapshot

UNAVAILABLE = "unavailable"

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

def nvidia_smi_info() -> tuple[str, list[dict[str, str]]]:
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=index,name,driver_version", "--format=csv,noheader"], check=True, capture_output=True, text=True, timeout=5)
    except Exception:
        return UNAVAILABLE, []
    gpus: list[dict[str, str]] = []
    driver = UNAVAILABLE
    for line in result.stdout.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 3:
            driver = parts[2]
            gpus.append({"id": parts[0], "name": parts[1], "driver_version": parts[2]})
    return driver, gpus

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
    ) -> None:
        self.ffmpeg_path = str(ffmpeg_path) if ffmpeg_path else None
        self.data_dir = str(data_dir) if data_dir else None
        self.log_dir = str(log_dir) if log_dir else None

    def collect(self, selected_model_id: str = "large-v3", model_cache_dir: str | None = None) -> SystemInfoSnapshot:
        driver, gpus = nvidia_smi_info()
        return SystemInfoSnapshot(
            app_version=APP_VERSION,
            whisperx_version=package_version("whisperx"),
            faster_whisper_version=package_version("faster-whisper"),
            torch_cuda_version=torch_cuda_version(),
            gpu_driver_version=driver,
            detected_gpus=gpus,
            selected_model_id=selected_model_id,
            downloaded_models_size_bytes=directory_size(model_cache_dir),
            ffmpeg_path=self.ffmpeg_path,
            data_dir=self.data_dir,
            log_dir=self.log_dir,
        )
