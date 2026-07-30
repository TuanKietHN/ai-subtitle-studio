from ai_subtitle_studio.config.model_catalog import ModelCatalog
from ai_subtitle_studio.ui.model_manager import ModelManagerController


def test_model_manager_lists_deletes_and_downloads(tmp_path):
    catalog = ModelCatalog.load("resources/models.json")
    manager = ModelManagerController(catalog, model_cache_dir=tmp_path)
    assert any(model.id == "large-v3" for model in manager.list_models())
    assert manager.delete_model("medium", active_model_ids={"large-v3"}) is True


def test_model_manager_only_deletes_descendants_of_model_cache(tmp_path):
    catalog = ModelCatalog.load("resources/models.json")
    cache = tmp_path / "cache"
    allowed = cache / "medium"
    allowed.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    model = catalog.get("medium")
    manager = ModelManagerController(catalog, model_cache_dir=cache)

    model.local_path = str(outside)
    assert manager.delete_model("medium") is False
    assert outside.is_dir()

    model.local_path = str(allowed)
    assert manager.delete_model("medium") is True
    assert not allowed.exists()
