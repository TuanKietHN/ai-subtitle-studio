import time
from ai_subtitle_studio.config.app_settings import AppSettingsStore, InMemorySettings
from ai_subtitle_studio.config.system_info import SystemInfoProvider
from ai_subtitle_studio.domain.entities import AppSettings
from ai_subtitle_studio.ui.about_dialog import AboutController
from ai_subtitle_studio.ui.settings_dialog import SettingsController


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
