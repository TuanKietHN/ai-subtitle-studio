# Translation Provider Contract

## Purpose

Define translation provider behavior for Google Cloud Translation API v3 and DeepSeek Chat API through direct REST calls with httpx.

## Interface

`TranslationProvider` is implemented as a Python `Protocol` or abstract base class.

```text
translate_batch(request: TranslationBatchRequest, progress: ProgressSink, cancel: CancelToken) -> TranslationBatchResult
```

## TranslationBatchRequest

- `job_id`: Video job id.
- `provider_id`: `google_cloud_v3` or `deepseek_chat`.
- `source_language`: `en` for this feature.
- `target_language`: `vi` for this feature.
- `items`: Ordered list of source cue records:
  - `sequence_number`
  - `start_ms`
  - `end_ms`
  - `source_text`
- `credential_alias`: Secret-store alias for provider API key.

## Required Behavior

- Use httpx for direct REST calls.
- Read API key from Windows Credential Manager or equivalent OS secret store.
- Never log, persist or display API key values.
- Translate multiple subtitle lines per request where provider limits allow.
- Preserve item count and order.
- Return one translated text per input item.
- If provider returns fewer, more or reordered lines, fail the job instead of exporting mismatched subtitles.
- Pause requests take effect at batch checkpoints.
- Cancel requests stop best-effort and mark job canceled without final output promotion.

## Result

`TranslationBatchResult` contains:
- `items`: Ordered list of translated cue records with `sequence_number` and `translated_text`.
- `provider_usage`: Optional request/token/character counters if available.
- `warnings`: Non-fatal provider notices.

## Errors

- `MissingCredentialError`: No API key stored for provider.
- `ProviderAuthError`: API key rejected or expired.
- `ProviderRateLimitError`: Quota/rate limit reached.
- `ProviderTimeoutError`: Provider did not respond in configured timeout.
- `TranslationShapeError`: Output count/order cannot be matched to input.
- `TranslationCanceled`: User canceled translation.
