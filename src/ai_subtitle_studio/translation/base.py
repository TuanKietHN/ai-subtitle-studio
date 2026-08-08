"""Translation provider protocol, credential storage, and shared errors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

@dataclass(slots=True)
class TranslationItem:
    sequence_number: int
    start_ms: int
    end_ms: int
    source_text: str

@dataclass(slots=True)
class TranslatedItem:
    sequence_number: int
    translated_text: str

@dataclass(slots=True)
class TranslationBatchRequest:
    job_id: str
    provider_id: str
    source_language: str
    target_language: str
    items: list[TranslationItem]
    credential_alias: str

@dataclass(slots=True)
class TranslationBatchResult:
    items: list[TranslatedItem]
    provider_usage: dict | None = None
    warnings: list[str] = field(default_factory=list)

class TranslationProvider(Protocol):
    provider_id: str
    def translate_batch(self, request: TranslationBatchRequest, progress=None, cancel=None) -> TranslationBatchResult: ...

class TranslationError(RuntimeError): pass
class MissingCredentialError(TranslationError): pass
class ProviderAuthError(TranslationError): pass
class ProviderRateLimitError(TranslationError): pass
class ProviderTimeoutError(TranslationError): pass
class TranslationShapeError(TranslationError): pass
class TranslationCanceled(TranslationError): pass

class CredentialStore:
    def get_password(self, alias: str) -> str | None: ...
    def set_password(self, alias: str, value: str) -> None: ...
    def delete_password(self, alias: str) -> None: ...

class KeyringCredentialStore(CredentialStore):
    service_name = "AI Subtitle Studio"
    def __init__(self) -> None:
        try:
            import keyring  # type: ignore
            self._keyring = keyring
            self._memory: dict[str, str] = {}
        except Exception:
            self._keyring = None
            self._memory = {}
    def get_password(self, alias: str) -> str | None:
        if self._keyring is None:
            return self._memory.get(alias)
        return self._keyring.get_password(self.service_name, alias)
    def set_password(self, alias: str, value: str) -> None:
        if self._keyring is None:
            self._memory[alias] = value
        else:
            self._keyring.set_password(self.service_name, alias, value)
    def delete_password(self, alias: str) -> None:
        if self._keyring is None:
            self._memory.pop(alias, None)
        else:
            if self._keyring.get_password(self.service_name, alias) is not None:
                self._keyring.delete_password(self.service_name, alias)

def validate_translation_shape(request: TranslationBatchRequest, result: TranslationBatchResult) -> None:
    expected = [item.sequence_number for item in request.items]
    actual = [item.sequence_number for item in result.items]
    if expected != actual or len(result.items) != len(request.items):
        raise TranslationShapeError("Provider returned mismatched translation count or order")
