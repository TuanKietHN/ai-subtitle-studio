"""DeepSeek Chat API provider using direct REST calls."""

from __future__ import annotations

from .base import MissingCredentialError, ProviderAuthError, ProviderRateLimitError, ProviderTimeoutError, TranslatedItem, TranslationBatchRequest, TranslationBatchResult, TranslationShapeError, validate_translation_shape

class DeepSeekChatProvider:
    provider_id = "deepseek_chat"
    endpoint = "https://api.deepseek.com/chat/completions"
    def __init__(self, credential_store, client=None) -> None:
        self.credential_store = credential_store
        self.client = client
    def translate_batch(self, request: TranslationBatchRequest, progress=None, cancel=None) -> TranslationBatchResult:
        api_key = self.credential_store.get_password(request.credential_alias)
        if not api_key:
            raise MissingCredentialError("DeepSeek API key is missing")
        if cancel and cancel.is_cancel_requested():
            from .base import TranslationCanceled
            raise TranslationCanceled("Tác vụ dịch đã bị hủy")
        numbered = "\n".join(f"{item.sequence_number}: {item.source_text}" for item in request.items)
        payload = {"model": "deepseek-chat", "messages": [{"role": "system", "content": "Translate each numbered English subtitle line to Vietnamese. Return one line per input as '<number>: <translation>'."}, {"role": "user", "content": numbered}], "temperature": 0.2}
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            if self.client is not None:
                response = self.client.post(self.endpoint, json=payload, headers=headers, timeout=60)
            else:
                import httpx
                response = httpx.post(self.endpoint, json=payload, headers=headers, timeout=60)
        except TimeoutError as exc:
            raise ProviderTimeoutError("DeepSeek translation timed out") from exc
        status = getattr(response, "status_code", 200)
        if status in (401, 403): raise ProviderAuthError("DeepSeek API key rejected")
        if status == 429: raise ProviderRateLimitError("DeepSeek rate limit reached")
        content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        by_number: dict[int, str] = {}
        for line in content.splitlines():
            if ":" not in line: continue
            left, right = line.split(":", 1)
            try: by_number[int(left.strip())] = right.strip()
            except ValueError: continue
        result = TranslationBatchResult([TranslatedItem(item.sequence_number, by_number.get(item.sequence_number, "")) for item in request.items])
        if any(not item.translated_text for item in result.items):
            raise TranslationShapeError("DeepSeek response did not contain one translation per cue")
        validate_translation_shape(request, result)
        if progress: progress(100, "translated", "deepseek_chat")
        return result