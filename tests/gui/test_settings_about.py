import time
from ai_subtitle_studio.config.app_settings import AppSettingsStore, InMemorySettings
from ai_subtitle_studio.config.system_info import SystemInfoProvider
from ai_subtitle_studio.domain.entities import AppSettings, GpuCapabilitySnapshot, SystemInfoSnapshot
from ai_subtitle_studio.ui.about_dialog import AboutController
from ai_subtitle_studio.ui.settings_dialog import SettingsController, SettingsDialog


class FakeSystemInfoProvider:
    def collect(self):
        gpu = GpuCapabilitySnapshot(
            gpu_id="0",
            name="NVIDIA GeForce RTX 2050",
            driver_version="555.42",
            total_vram_bytes=4 * 1024**3,
            free_vram_bytes=3 * 1024**3,
            compute_capability="8.6",
            torch_cuda_ready=True,
            supported_compute_types=["float16", "int8_float16"],
        )
        return SystemInfoSnapshot(
            app_version="0.1.0-rc.5",
            whisperx_version="test",
            faster_whisper_version="test",
            torch_cuda_version="12.8",
            gpu_driver_version="555.42",
            detected_gpus=[gpu],
            selected_model_id="small.en",
            downloaded_models_size_bytes=0,
            torch_cuda_ready=True,
        )


def test_settings_and_about_dialog_controllers_render_under_5s(tmp_path):
    ffmpeg = tmp_path / "ffmpeg.exe"; ffmpeg.write_text("exe")
    store = AppSettingsStore(InMemorySettings())
    settings = AppSettings(ffmpeg_path=str(ffmpeg), default_output_dir=str(tmp_path), model_cache_dir=str(tmp_path))
    controller = SettingsController(store)
    controller.save(settings)
    assert controller.validate_paths(settings)["ffmpeg_path"] is None
    start = time.monotonic()
    about = AboutController(SystemInfoProvider()).render_info(model_cache_dir=str(tmp_path))
    assert time.monotonic() - start < 5
    assert about["elapsed_seconds"] < 5


def test_settings_controller_reports_and_cleans_temp_files(tmp_path):
    working_dir = tmp_path / "outputs" / "_work"
    job_dir = working_dir / "job1"
    job_dir.mkdir(parents=True)
    (job_dir / "audio.wav").write_bytes(b"12345")
    store = AppSettingsStore(InMemorySettings())
    controller = SettingsController(store, working_dir=working_dir)

    assert controller.temp_files_size_bytes() == 5
    assert controller.cleanup_temp_files() == 5
    assert controller.temp_files_size_bytes() == 0
    assert not working_dir.exists()


def test_settings_cleanup_keeps_active_job_working_files(tmp_path):
    working_dir = tmp_path / "outputs" / "_work"
    active_dir = working_dir / "active"
    stale_dir = working_dir / "stale"
    active_dir.mkdir(parents=True)
    stale_dir.mkdir(parents=True)
    (active_dir / "audio.wav").write_bytes(b"active")
    (stale_dir / "audio.wav").write_bytes(b"stale")
    store = AppSettingsStore(InMemorySettings())
    controller = SettingsController(store, working_dir=working_dir, protected_job_ids=lambda: {"active"})

    assert controller.cleanup_temp_files() == len(b"stale")
    assert (active_dir / "audio.wav").exists()
    assert not stale_dir.exists()


def test_settings_dialog_shows_rtx_2050_capability_and_low_vram_profile(qtbot):
    settings = AppSettings(
        selected_gpu_id="0",
        last_model_id="small.en",
        last_compute_profile_id="low-vram-4gb",
    )
    store = AppSettingsStore(InMemorySettings())
    store.save(settings)
    controller = SettingsController(store, system_info_provider=FakeSystemInfoProvider())
    dialog = SettingsDialog(controller)
    qtbot.addWidget(dialog)

    assert dialog.gpu_combo.findData("0") >= 0
    assert dialog.profile_combo.currentData() == "low-vram-4gb"
    assert "RTX 2050" in dialog.gpu_combo.currentText()
    assert "4.0 GiB" in dialog.gpu_info_label.text()
    assert "8.6" in dialog.gpu_info_label.text()
    assert "int8_float16" in dialog.gpu_info_label.text()
    assert controller.validate_gpu_profile(settings) is None
