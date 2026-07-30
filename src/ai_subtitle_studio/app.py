"""Application bootstrap and dependency wiring."""

from __future__ import annotations

import argparse
import importlib
import logging
from pathlib import Path
import shutil
import sys
from typing import Callable

from ai_subtitle_studio.config.app_settings import AppSettingsStore
from ai_subtitle_studio.config.model_catalog import ModelCatalog
from ai_subtitle_studio.config.system_info import SystemInfoProvider
from ai_subtitle_studio.io.audio_extractor import AudioExtractor
from ai_subtitle_studio.io.ffmpeg_resolver import find_ffmpeg
from ai_subtitle_studio.io.srt_writer import SRTWriter
from ai_subtitle_studio.logging_config import configure_logging
from ai_subtitle_studio.paths import AppPaths
from ai_subtitle_studio.persistence.repositories import JobRepository, SubtitleRepository
from ai_subtitle_studio.persistence.sqlite_store import SQLiteStore
from ai_subtitle_studio.stt.whisperx_engine import WhisperXEngine
from ai_subtitle_studio.translation.base import KeyringCredentialStore
from ai_subtitle_studio.translation.deepseek_provider import DeepSeekChatProvider
from ai_subtitle_studio.translation.google_provider import GoogleCloudTranslationProvider
from ai_subtitle_studio.translation.registry import TranslationProviderRegistry
from ai_subtitle_studio.ui.main_window import MainWindow, MainWindowController
from ai_subtitle_studio.workers.job_runner import JobRunner

ROOT = Path(__file__).resolve().parents[2]


def _saved_path_outside_bundle(value: str | None, resource_root: Path) -> str | None:
    if not value:
        return None
    try:
        candidate = Path(value).resolve()
        candidate.relative_to(resource_root.resolve())
    except ValueError:
        return value
    except OSError:
        return value
    logging.getLogger(__name__).warning(
        "Ignoring legacy persistent path inside the application bundle: %s",
        value,
    )
    return None


def build_services(
    root: Path | None = None,
    *,
    app_paths: AppPaths | None = None,
    settings_store: AppSettingsStore | None = None,
    ffmpeg_lookup: Callable[[str], str | None] = shutil.which,
) -> dict:
    settings_store = settings_store or AppSettingsStore()
    settings = settings_store.load()
    resource_root = Path(root).resolve() if root is not None else None
    if app_paths is None:
        effective_root = resource_root or AppPaths.resolve(create=False).resource_root
        app_paths = AppPaths.resolve(
            resource_root=effective_root,
            model_cache_dir=_saved_path_outside_bundle(settings.model_cache_dir, effective_root),
            output_dir=_saved_path_outside_bundle(settings.default_output_dir, effective_root),
        )
    catalog = ModelCatalog.load(app_paths.model_catalog_path)

    settings.model_cache_dir = str(app_paths.model_cache_dir)
    settings.default_output_dir = str(app_paths.output_dir)
    settings_store.save(settings)

    ffmpeg_path = find_ffmpeg(
        settings.ffmpeg_path,
        app_paths.bundled_ffmpeg_path,
        path_lookup=ffmpeg_lookup,
    )
    if not ffmpeg_path:
        ffmpeg_path = "ffmpeg"
        logging.getLogger(__name__).warning(
            "ffmpeg was not found during startup; audio extraction will fail until it is configured."
        )

    store = SQLiteStore(app_paths.database_path)
    job_repo = JobRepository(store)
    subtitle_repo = SubtitleRepository(store)
    credentials = KeyringCredentialStore()
    registry = TranslationProviderRegistry()
    registry.register(GoogleCloudTranslationProvider(credentials))
    registry.register(DeepSeekChatProvider(credentials))
    runner = JobRunner(
        audio_extractor=AudioExtractor(ffmpeg_path),
        stt_engine=WhisperXEngine(),
        srt_writer=SRTWriter(),
        output_dir=app_paths.output_dir,
        job_repository=job_repo,
        subtitle_repository=subtitle_repo,
        model_catalog=catalog,
        translation_registry=registry,
        model_cache_dir=app_paths.model_cache_dir,
        selected_gpu_id=settings.selected_gpu_id,
    )
    system_info_provider = SystemInfoProvider(
        ffmpeg_path=ffmpeg_path,
        data_dir=app_paths.data_dir,
        log_dir=app_paths.log_dir,
    )
    controller = MainWindowController(
        model_catalog=catalog,
        job_runner=runner,
        settings_store=settings_store,
        credential_store=credentials,
        translation_registry=registry,
        system_info_provider=system_info_provider,
    )
    return {
        "settings_store": settings_store,
        "catalog": catalog,
        "store": store,
        "job_repository": job_repo,
        "subtitle_repository": subtitle_repo,
        "credential_store": credentials,
        "translation_registry": registry,
        "job_runner": runner,
        "main_controller": controller,
        "system_info_provider": system_info_provider,
        "paths": app_paths,
        "ffmpeg_path": ffmpeg_path,
    }


def run_smoke_test(
    app_paths: AppPaths,
    *,
    importer: Callable[[str], object] = importlib.import_module,
    services_builder: Callable[[AppPaths], dict] | None = None,
) -> int:
    """Exercise packaged imports and service wiring without starting the event loop."""
    builder = services_builder or (lambda paths: build_services(app_paths=paths))
    try:
        for module_name in ("PySide6", "whisperx", "torch"):
            importer(module_name)
        services = builder(app_paths)
        if not services:
            raise RuntimeError("Service container is empty")
        if getattr(sys, "frozen", False) and not app_paths.bundled_ffmpeg_path.is_file():
            raise RuntimeError(f"Bundled ffmpeg is missing: {app_paths.bundled_ffmpeg_path}")
        logging.getLogger(__name__).info(
            "Smoke test passed (resources=%s, data=%s, models=%s).",
            app_paths.resource_root,
            app_paths.data_dir,
            app_paths.model_cache_dir,
        )
        return 0
    except Exception:
        logging.getLogger(__name__).exception("Application smoke test failed.")
        return 1


def _show_startup_error(message: str) -> None:
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox  # type: ignore

        app = QApplication.instance() or QApplication([])
        QMessageBox.critical(None, "AI Subtitle Studio không thể khởi động", message)
        if QApplication.instance() is app:
            app.processEvents()
    except Exception:
        logging.getLogger(__name__).exception("Could not display the startup error dialog.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-subtitle-studio")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Validate packaged dependencies and service wiring without opening the UI.",
    )
    args = parser.parse_args(argv)
    paths = AppPaths.resolve()
    log_path = configure_logging(paths.log_dir, console=not getattr(sys, "frozen", False))
    if args.smoke_test:
        return run_smoke_test(paths)

    try:
        from PySide6.QtWidgets import QApplication  # type: ignore

        services = build_services(app_paths=paths)
        app = QApplication(sys.argv[:1])
        window = MainWindow(services["main_controller"])
        window.show()
        return app.exec()
    except Exception as exc:
        logging.exception("AI Subtitle Studio failed during desktop UI startup.")
        _show_startup_error(
            "Ứng dụng không thể khởi động.\n\n"
            f"{exc}\n\n"
            f"Log kỹ thuật: {log_path}"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
