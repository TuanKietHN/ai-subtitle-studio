import inspect
from ai_subtitle_studio.config import system_info


def test_system_info_uses_importlib_metadata_version():
    source = inspect.getsource(system_info.package_version)
    assert "importlib.metadata.version" in source


def test_no_hard_coded_dependency_versions_in_system_info_module():
    source = inspect.getsource(system_info)
    assert "3.8.6" not in source
    assert "faster-whisper==" not in source