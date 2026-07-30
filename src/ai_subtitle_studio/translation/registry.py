"""Translation provider registry."""

from __future__ import annotations

from .base import TranslationProvider

class TranslationProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, TranslationProvider] = {}
    def register(self, provider: TranslationProvider) -> None:
        self._providers[provider.provider_id] = provider
    def get(self, provider_id: str) -> TranslationProvider:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise KeyError(f"Unknown translation provider: {provider_id}") from exc
    def ids(self) -> list[str]:
        return sorted(self._providers)