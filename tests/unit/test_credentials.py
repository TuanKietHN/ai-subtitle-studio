from ai_subtitle_studio.config.app_settings import AppSettingsStore, InMemorySettings
from ai_subtitle_studio.translation.base import KeyringCredentialStore


def test_credentials_use_secret_store_not_qsettings():
    settings = AppSettingsStore(InMemorySettings())
    try:
        settings.set_value("google_api_key", "secret")
        assert False, "secret key should be rejected"
    except ValueError:
        pass
    store = KeyringCredentialStore(); store.set_password("translation/google", "secret")
    assert store.get_password("translation/google") == "secret"