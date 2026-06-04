"""Provider selection from configuration. Defaults to the deterministic mock."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.providers.base import EmbeddingProvider, LLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    provider = settings.llm_provider.lower()
    if provider == "anthropic":
        from app.providers.anthropic import AnthropicLLMProvider

        return AnthropicLLMProvider()
    if provider == "openai":
        from app.providers.openai import OpenAILLMProvider

        return OpenAILLMProvider()
    from app.providers.mock import MockLLMProvider

    return MockLLMProvider()


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    provider = settings.embedding_provider.lower()
    if provider == "openai":
        from app.providers.openai import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(dim=settings.embedding_dim)
    if provider == "anthropic":
        from app.providers.anthropic import AnthropicEmbeddingProvider

        return AnthropicEmbeddingProvider(dim=settings.embedding_dim)
    from app.providers.mock import MockEmbeddingProvider

    return MockEmbeddingProvider(dim=settings.embedding_dim)
