import pytest
from ai_subtitle_studio.translation.base import TranslationBatchRequest, TranslationBatchResult, TranslationItem, TranslatedItem, TranslationShapeError, validate_translation_shape


def request():
    return TranslationBatchRequest(job_id="j", provider_id="p", source_language="en", target_language="vi", credential_alias="alias", items=[TranslationItem(1, 0, 100, "A"), TranslationItem(2, 100, 200, "B")])

def test_translation_shape_preserves_count_and_order():
    validate_translation_shape(request(), TranslationBatchResult([TranslatedItem(1, "A vi"), TranslatedItem(2, "B vi")]))

def test_translation_shape_rejects_mismatch():
    with pytest.raises(TranslationShapeError):
        validate_translation_shape(request(), TranslationBatchResult([TranslatedItem(2, "B vi")]))

def test_api_key_value_not_in_error_message():
    secret = "super-secret-key"
    try:
        raise RuntimeError("Provider failed")
    except RuntimeError as exc:
        assert secret not in str(exc)