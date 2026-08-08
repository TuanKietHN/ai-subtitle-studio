"""Config-driven Whisper model catalog."""

from __future__ import annotations

import json
from pathlib import Path
from ai_subtitle_studio.domain.entities import WhisperModel
from ai_subtitle_studio.config.gpu_profiles import KNOWN_PROFILE_IDS

DEFAULT_MODEL_ID = "large-v3"

class ModelCatalogError(ValueError):
    pass

class ModelCatalog:
    def __init__(self, models: list[WhisperModel], default_model: str = DEFAULT_MODEL_ID) -> None:
        self.models = models
        self.default_model = default_model
        self._by_id = {m.id: m for m in models}
        self.validate()

    @classmethod
    def load(cls, path: str | Path) -> "ModelCatalog":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        models = [WhisperModel(id=item["id"], display_name=item["display_name"], is_default=item["id"] == data.get("default_model", DEFAULT_MODEL_ID), enabled=bool(item.get("enabled", True)), description=item.get("description", ""), recommended_vram_gb=item.get("recommended_vram_gb"), execution_profile_ids=list(item.get("execution_profile_ids", []))) for item in data.get("models", [])]
        return cls(models=models, default_model=data.get("default_model", DEFAULT_MODEL_ID))

    def validate(self) -> None:
        ids = [m.id for m in self.models]
        if len(ids) != len(set(ids)):
            raise ModelCatalogError("Model ids must be unique")
        if self.default_model != DEFAULT_MODEL_ID:
            raise ModelCatalogError("Default model must be large-v3")
        defaults = [m for m in self.models if m.is_default]
        if len(defaults) != 1 or defaults[0].id != DEFAULT_MODEL_ID:
            raise ModelCatalogError("Catalog must contain exactly one default large-v3 model")
        for model in self.models:
            unknown = set(model.execution_profile_ids) - KNOWN_PROFILE_IDS
            if unknown:
                raise ModelCatalogError(f"Model {model.id} references unknown execution profiles: {sorted(unknown)}")

    def enabled_models(self) -> list[WhisperModel]:
        return [m for m in self.models if m.enabled]

    def get(self, model_id: str) -> WhisperModel:
        try:
            return self._by_id[model_id]
        except KeyError as exc:
            raise ModelCatalogError(f"Unsupported model id: {model_id}") from exc

    def default(self) -> WhisperModel:
        return self.get(self.default_model)

    def resolve_or_default(self, model_id: str | None) -> WhisperModel:
        if model_id and model_id in self._by_id:
            return self._by_id[model_id]
        return self.default()
