from ai_subtitle_studio.config.app_settings import AppSettingsStore, InMemorySettings
from ai_subtitle_studio.domain.entities import AppSettings


def test_qsettings_wrapper_persists_non_secret_fields():
    backend = InMemorySettings(); store = AppSettingsStore(backend)
    store.save(AppSettings(selected_gpu_id="0", model_cache_dir="models", ffmpeg_path="ffmpeg.exe", subtitle_edit_path="SubtitleEdit.exe", default_output_dir="out", last_model_id="medium", last_translation_provider_id="deepseek_chat", last_compute_profile_id="low-vram-4gb"))
    loaded = store.load()
    assert loaded.selected_gpu_id == "0"
    assert loaded.last_model_id == "medium"
    assert loaded.last_translation_provider_id == "deepseek_chat"
    assert loaded.last_compute_profile_id == "low-vram-4gb"
