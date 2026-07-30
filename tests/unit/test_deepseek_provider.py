from ai_subtitle_studio.translation.base import KeyringCredentialStore, TranslationBatchRequest, TranslationItem
from ai_subtitle_studio.translation.deepseek_provider import DeepSeekChatProvider

class Response:
    status_code = 200
    def json(self): return {"choices": [{"message": {"content": "1: Xin chao"}}]}
class Client:
    def __init__(self): self.headers = None
    def post(self, url, json=None, headers=None, timeout=None): self.headers = headers; return Response()

def test_deepseek_provider_request_response_shape():
    store = KeyringCredentialStore(); store.set_password("d", "secret")
    client = Client(); provider = DeepSeekChatProvider(store, client=client)
    req = TranslationBatchRequest("j", "deepseek_chat", "en", "vi", [TranslationItem(1, 0, 1, "Hello")], "d")
    result = provider.translate_batch(req)
    assert client.headers["Authorization"].startswith("Bearer ")
    assert result.items[0].translated_text == "Xin chao"