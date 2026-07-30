from pathlib import Path

from ai_subtitle_studio.paths import AppPaths


def test_source_resources_are_separate_from_windows_user_data(tmp_path):
    source = tmp_path / "source"
    local = tmp_path / "LocalAppData"
    profile = tmp_path / "profile"

    paths = AppPaths.resolve(
        resource_root=source,
        env={"LOCALAPPDATA": str(local), "USERPROFILE": str(profile)},
    )

    assert paths.resource_root == source.resolve()
    assert paths.data_dir == local / "AI Subtitle Studio"
    assert paths.database_path.parent == paths.data_dir
    assert paths.model_cache_dir == paths.data_dir / "models"
    assert paths.log_dir == paths.data_dir / "logs"
    assert paths.output_dir == profile / "Documents" / "AI Subtitle Studio" / "outputs"
    assert paths.resource_root not in paths.data_dir.parents


def test_environment_and_saved_settings_overrides_are_deterministic(tmp_path):
    env_output = tmp_path / "env-output"
    env_model = tmp_path / "env-model"
    paths = AppPaths.resolve(
        resource_root=tmp_path / "bundle",
        model_cache_dir=tmp_path / "saved-model",
        output_dir=tmp_path / "saved-output",
        env={
            "LOCALAPPDATA": str(tmp_path / "local"),
            "USERPROFILE": str(tmp_path / "profile"),
            "AI_SUBTITLE_MODEL_CACHE": str(env_model),
            "AI_SUBTITLE_OUTPUT_DIR": str(env_output),
        },
    )
    assert paths.model_cache_dir == env_model
    assert paths.output_dir == env_output
    assert all(path.is_dir() for path in (paths.data_dir, paths.model_cache_dir, paths.log_dir, paths.output_dir))
