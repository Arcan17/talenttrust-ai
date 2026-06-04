"""Anthropic adapter. The vendor SDK is imported lazily and only here.

Embeddings: Anthropic does not offer an embeddings API, so embedding generation should
use the OpenAI or mock provider; this module raises a clear error if asked to embed.
"""
from __future__ import annotations

from app.core.config import settings
from app.providers.base import EmbeddingProvider, LLMProvider, LLMResult


class AnthropicLLMProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        self.model = model

    def _client(self):
        try:
            from anthropic import AsyncAnthropic  # noqa: PLC0415 (lazy, isolated import)
        except ImportError as exc:  # pragma: no cover - exercised only without the SDK
            raise RuntimeError(
                "The 'anthropic' package is required for LLM_PROVIDER=anthropic. "
                "Install it or use LLM_PROVIDER=mock."
            ) from exc
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured.")
        return AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def complete(
        self, prompt: str, *, system: str | None = None, **opts: object
    ) -> LLMResult:  # pragma: no cover - requires live API, never run in CI
        client = self._client()
        msg = await client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system or "You explain candidate evaluations; you never assign scores.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in msg.content if block.type == "text")
        return LLMResult(
            text=text,
            prompt_tokens=msg.usage.input_tokens,
            completion_tokens=msg.usage.output_tokens,
            model=self.model,
        )


class AnthropicEmbeddingProvider(EmbeddingProvider):
    name = "anthropic"

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    async def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        raise RuntimeError(
            "Anthropic has no embeddings API; use EMBEDDING_PROVIDER=openai or mock."
        )
