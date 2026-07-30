from ai_subtitle_studio.config.model_catalog import ModelCatalog
from ai_subtitle_studio.ui.main_window import MainWindowController


def test_main_window_controller_adds_files_without_qt_blocking(tmp_path):
    video = tmp_path / "lecture.mp4"; video.write_bytes(b"1")
    catalog = ModelCatalog.load("resources/models.json")
    controller = MainWindowController(catalog)
    result = controller.add_files([video])
    assert len(result.added) == 1
    assert controller.model_options()[0]
    controller.select_model("medium")
    assert controller.selected_model_id == "medium"