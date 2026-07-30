from ai_subtitle_studio.translation.base import KeyringCredentialStore, TranslationBatchRequest, TranslationItem
from ai_subtitle_studio.translation.google_provider import GoogleCloudTranslationProvider

class Response:
    status_code = 200
    def json(self): return {"translations": [{"translatedText": "Xin chao"}]}
class Client:
    def __init__(self): self.payload = None
    def post(self, url, params=None, json=None, timeout=None): self.payload = json; return Response()

def test_google_provider_request_response_shape():
    store = KeyringCredentialStore(); store.set_password("g", "secret")
    client = Client(); provider = GoogleCloudTranslationProvider(store, client=client)
    req = TranslationBatchRequest("j", "google_cloud_v3", "en", "vi", [TranslationItem(1, 0, 1, "Hello")], "g")
    result = provider.translate_batch(req)
    assert client.payload["targetLanguageCode"] == "vi"
    assert result.items[0].translated_text == "Xin chao"