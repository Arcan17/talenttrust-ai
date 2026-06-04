"""OpenAI adapter. The vendor SDK is imported lazily and only here."""
from __future__ import annotations

from app.core.config import settings
from app.providers.base import EmbeddingProvider, LLMProvider, LLMResult


def _client():
    try:
        from openai import AsyncOpenAI  # noqa: PLC0415 (lazy, isolated import)
    except ImportError as exc:  # pragma: no cover - exercised only without the SDK
        raise RuntimeError(
            "The 'openai' package is required for the OpenAI provider. "
            "Install it or use the mock provider."
        ) from exc
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    return AsyncOpenAI(api_key=settings.openai_api_key)


class OpenAILLMProvider(LLMProvider):
    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model

    async def complete(
        self, prompt: str, *, system: str | None = None, **opts: object
    ) -> LLMResult:  # pragma: no cover - requires live API, never run in CI
        client = _client()
        resp = await client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system
                    or "You explain candidate evaluations; you never assign scores.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        usage = resp.usage
        return LLMResult(
            text=resp.choices[0].message.content or "",
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            model=self.model,
        )


class OpenAIEmbeddingProvider(EmbeddingProvider):
    name = "openai"

    def __init__(self, dim: int = 384, model: str = "text-embedding-3-small") -> None:
        self.dim = dim
        self.model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        client = _client()
        resp = await client.embeddings.create(
            model=self.model, input=texts, dimensions=self.dim
        )
        return [item.embedding for item in resp.data]
