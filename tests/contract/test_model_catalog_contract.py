from ai_subtitle_studio.config.model_catalog import ModelCatalog


def test_model_catalog_default_and_unique_ids():
    catalog = ModelCatalog.load("resources/models.json")
    assert catalog.default().id == "large-v3"
    ids = [model.id for model in catalog.enabled_models()]
    assert len(ids) == len(set(ids))
    assert {"medium", "large-v3", "large-v3-turbo", "distil-large-v3"}.issubset(ids)