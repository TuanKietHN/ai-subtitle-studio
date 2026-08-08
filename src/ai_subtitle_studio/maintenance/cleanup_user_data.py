"""Selective, auditable uninstall cleanup for user-owned application data."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Callable


KNOWN_CREDENTIAL_ALIASES = {
    "translation/google_cloud_v3",
    "translation/deepseek_chat",
}
OUTPUT_COLUMNS = ("english_srt_path", "vietnamese_srt_path", "bilingual_srt_path")


@dataclass(slots=True)
class CleanupReport:
    deleted_outputs: list[str] = field(default_factory=list)
    deleted_paths: list[str] = field(default_factory=list)
    deleted_credentials: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


def _database_owned_outputs(database_path: Path, report: CleanupReport) -> tuple[set[Path], set[str]]:
    outputs: set[Path] = set()
    aliases = set(KNOWN_CREDENTIAL_ALIASES)
    if not database_path.is_file():
        return outputs, aliases
    connection = None
    try:
        connection = sqlite3.connect(database_path)
        table_names = {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "video_jobs" in table_names:
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(video_jobs)")
            }
            selected = [column for column in OUTPUT_COLUMNS if column in columns]
            if selected:
                for row in connection.execute(f"SELECT {', '.join(selected)} FROM video_jobs"):
                    for value in row:
                        if value:
                            outputs.add(Path(str(value)).expanduser())
        if "provider_status" in table_names:
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(provider_status)")
            }
            if "credential_alias" in columns:
                aliases.update(
                    str(row[0])
                    for row in connection.execute(
                        "SELECT credential_alias FROM provider_status WHERE credential_alias IS NOT NULL"
                    )
                    if row[0]
                )
    except Exception as exc:
        report.failures.append(f"Không đọc được ownership database {database_path}: {exc}")
    finally:
        if connection is not None:
            connection.close()
    return outputs, aliases


def _delete_owned_outputs(paths: set[Path], report: CleanupReport) -> None:
    for path in sorted(paths, key=lambda item: str(item).lower()):
        try:
            resolved = path.resolve(strict=False)
            if resolved.suffix.lower() != ".srt":
                report.failures.append(f"Bỏ qua output không phải SRT: {resolved}")
                continue
            if resolved.is_file():
                resolved.unlink()
                report.deleted_outputs.append(str(resolved))
        except Exception as exc:
            report.failures.append(f"Không xóa được output {path}: {exc}")


def _default_settings_clearer() -> bool:
    from ai_subtitle_studio.config.app_settings import AppSettingsStore

    backend = AppSettingsStore().backend
    clear = getattr(backend, "clear", None)
    if callable(clear):
        clear()
    backend.sync()
    return True


def cleanup_user_data(
    *,
    data_dir: str | Path,
    cleanup_private_data: bool = False,
    cleanup_owned_outputs: bool = False,
    credential_store=None,
    clear_settings: Callable[[], bool] | None = None,
    model_cache_dir: str | Path | None = None,
) -> CleanupReport:
    data_root = Path(data_dir).resolve(strict=False)
    database_path = data_root / "ai_subtitle_studio.sqlite3"
    report = CleanupReport()
    owned_outputs, credential_aliases = _database_owned_outputs(database_path, report)

    if cleanup_owned_outputs:
        _delete_owned_outputs(owned_outputs, report)

    if not cleanup_private_data:
        return report

    if credential_store is None:
        from ai_subtitle_studio.translation.base import KeyringCredentialStore

        credential_store = KeyringCredentialStore()
    for alias in sorted(credential_aliases):
        try:
            credential_store.delete_password(alias)
            report.deleted_credentials.append(alias)
        except Exception as exc:
            report.failures.append(f"Không xóa được credential {alias}: {exc}")

    try:
        if not (clear_settings or _default_settings_clearer)():
            report.failures.append("QSettings không xác nhận đã xóa")
    except Exception as exc:
        report.failures.append(f"Không xóa được QSettings: {exc}")

    custom_model_root = Path(model_cache_dir).resolve(strict=False) if model_cache_dir else None
    if custom_model_root and custom_model_root != data_root and custom_model_root.exists():
        try:
            shutil.rmtree(custom_model_root)
            report.deleted_paths.append(str(custom_model_root))
        except Exception as exc:
            report.failures.append(f"Không xóa được model cache {custom_model_root}: {exc}")

    if data_root.exists():
        try:
            shutil.rmtree(data_root)
            report.deleted_paths.append(str(data_root))
        except Exception as exc:
            report.failures.append(f"Không xóa được dữ liệu ứng dụng {data_root}: {exc}")
    return report
