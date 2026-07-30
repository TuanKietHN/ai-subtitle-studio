from ai_subtitle_studio.app import run_smoke_test
from ai_subtitle_studio.paths import AppPaths


def test_smoke_mode_builds_services_and_imports_dependencies_without_ui(tmp_path):
    paths = AppPaths.resolve(
        resource_root=tmp_path / "bundle",
        env={
            "LOCALAPPDATA": str(tmp_path / "local"),
            "USERPROFILE": str(tmp_path / "profile"),
        },
    )
    imported = []
    built = []

    exit_code = run_smoke_test(
        paths,
        importer=lambda name: imported.append(name),
        services_builder=lambda app_paths: built.append(app_paths) or {"store": object()},
    )

    assert exit_code == 0
    assert built == [paths]
    assert imported == ["PySide6", "whisperx", "torch"]


def test_smoke_mode_returns_failure_when_a_critical_import_fails(tmp_path):
    paths = AppPaths.resolve(
        resource_root=tmp_path,
        env={"LOCALAPPDATA": str(tmp_path / "local"), "USERPROFILE": str(tmp_path)},
    )

    def fail_import(_name):
        raise ImportError("missing dependency")

    assert run_smoke_test(paths, importer=fail_import, services_builder=lambda _: {}) == 1
