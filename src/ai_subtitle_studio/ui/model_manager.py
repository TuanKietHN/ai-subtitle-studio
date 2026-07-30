"""Model manager UI-facing service."""

from __future__ import annotations

from pathlib import Path
import shutil

class ModelManagerController:
    def __init__(
        self,
        catalog,
        repository=None,
        downloader_factory=None,
        model_cache_dir: str | Path | None = None,
    ) -> None:
        self.catalog = catalog
        self.repository = repository
        self.downloader_factory = downloader_factory
        self.model_cache_dir = Path(model_cache_dir).resolve() if model_cache_dir else None

    def list_models(self):
        return self.catalog.enabled_models()

    def delete_model(self, model_id: str, active_model_ids: set[str] | None = None) -> bool:
        if active_model_ids and model_id in active_model_ids:
            return False
        model = self.catalog.get(model_id)
        if model.local_path:
            target = self._safe_model_directory(model.local_path)
            if target is None:
                return False
            if target.exists():
                shutil.rmtree(target)
        model.download_state = "not_downloaded"
        model.local_path = None
        model.size_bytes = 0
        return True

    def download_model(self, model_id: str, cache_dir: str, progress=None):
        if not self.downloader_factory:
            raise RuntimeError("Chưa cấu hình bộ tải model")
        worker = self.downloader_factory(model_id, cache_dir)
        return worker.run(progress=progress)

    def _safe_model_directory(self, local_path: str | Path) -> Path | None:
        if self.model_cache_dir is None:
            return None
        target = Path(local_path)
        if target.is_symlink() or (target.exists() and not target.is_dir()):
            return None
        try:
            resolved = target.resolve()
            resolved.relative_to(self.model_cache_dir)
        except (OSError, ValueError):
            return None
        if resolved == self.model_cache_dir:
            return None
        return resolved
