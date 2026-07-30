"""Google Cloud Translation API v3 provider using direct REST calls."""

from __future__ import annotations

from .base import MissingCredentialError, ProviderAuthError, ProviderRateLimitError, ProviderTimeoutError, TranslatedItem, TranslationBatchRequest, TranslationBatchResult, validate_translation_shape

class GoogleCloudTranslationProvider:
    provider_id = "google_cloud_v3"
    endpoint = "https://translation.googleapis.com/v3/projects/{project_id}/locations/global:translateText"
    def __init__(self, credential_store, project_id: str = "local-project", client=None) -> None:
        self.credential_store = credential_store
        self.project_id = project_id
        self.client = client
    def translate_batch(self, request: TranslationBatchRequest, progress=None, cancel=None) -> TranslationBatchResult:
        api_key = self.credential_store.get_password(request.credential_alias)
        if not api_key:
            raise MissingCredentialError("Google Cloud Translation API key is missing")
        if cancel and cancel.is_cancel_requested():
            from .base import TranslationCanceled
            raise TranslationCanceled("Tác vụ dịch đã bị hủy")
        texts = [item.source_text for item in request.items]
        payload = {"contents": texts, "sourceLanguageCode": request.source_language, "targetLanguageCode": request.target_language, "mimeType": "text/plain"}
        url = self.endpoint.format(project_id=self.project_id)
        try:
            if self.client is not None:
                response = self.client.post(url, params={"key": api_key}, json=payload, timeout=30)
            else:
                import httpx
                response = httpx.post(url, params={"key": api_key}, json=payload, timeout=30)
        except TimeoutError as exc:
            raise ProviderTimeoutError("Google translation timed out") from exc
        status = getattr(response, "status_code", 200)
        if status in (401, 403): raise ProviderAuthError("Google API key rejected")
        if status == 429: raise ProviderRateLimitError("Google rate limit reached")
        data = response.json()
        translations = data.get("translations", [])
        result = TranslationBatchResult([TranslatedItem(item.sequence_number, translations[i].get("translatedText", "")) for i, item in enumerate(request.items) if i < len(translations)])
        validate_translation_shape(request, result)
        if progress: progress(100, "translated", "google_cloud_v3")
        return result