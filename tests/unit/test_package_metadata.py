from ai_subtitle_studio import PACKAGE_NAME, UNKNOWN_VERSION, get_app_version


def test_app_version_comes_from_distribution_metadata(monkeypatch):
    monkeypatch.setattr("ai_subtitle_studio.importlib.metadata.version", lambda name: "9.8.7")
    assert PACKAGE_NAME == "ai-subtitle-studio"
    assert get_app_version() == "9.8.7"


def test_app_version_has_explicit_source_fallback(monkeypatch):
    def missing(_name):
        from importlib.metadata import PackageNotFoundError

        raise PackageNotFoundError

    monkeypatch.setattr("ai_subtitle_studio.importlib.metadata.version", missing)
    assert get_app_version() == UNKNOWN_VERSION
