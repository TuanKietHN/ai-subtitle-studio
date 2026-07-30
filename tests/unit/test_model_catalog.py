from ai_subtitle_studio.config.model_catalog import ModelCatalog
from ai_subtitle_studio.ui.main_window import MainWindowController


def test_default_fallback_and_ui_uses_catalog():
    catalog = ModelCatalog.load("resources/models.json")
    assert catalog.resolve_or_default("missing").id == "large-v3"
    controller = MainWindowController(catalog)
    assert controller.model_options() == [model.id for model in catalog.enabled_models()]
    assert "large-v3" in controller.model_options()