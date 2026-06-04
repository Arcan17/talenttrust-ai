"""Deterministic, offline mock providers.

Embeddings are reproducible (hashed bag-of-words → L2-normalized vector) so equal text
yields equal vectors and texts sharing words yield higher cosine similarity. Completions
are templated and report token counts derived from text length. No network, no cost.

This determinism underpins Constitution Principles III (offline CI) and V (reproducible
scoring): the same inputs always yield the same embeddings, hence the same score.
"""
from __future__ import annotations

import hashlib
import math
import re

from app.providers.base import EmbeddingProvider, LLMProvider, LLMResult

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


class MockEmbeddingProvider(EmbeddingProvider):
    name = "mock"

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = _tokens(text)
        for tok in tokens:
            h = int.from_bytes(hashlib.sha256(tok.encode()).digest()[:8], "big")
            idx = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            # empty/unknown text → stable non-zero unit vector
            vec[0] = 1.0
            return vec
        return [v / norm for v in vec]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]


class MockLLMProvider(LLMProvider):
    name = "mock"

    async def complete(
        self, prompt: str, *, system: str | None = None, **opts: object
    ) -> LLMResult:
        # Deterministic, grounded-looking reply that echoes provided context when present.
        context = str(opts.get("context", "")).strip()
        if context:
            body = f"Based on the provided evidence:\n\n{context}"
        else:
            body = (
                "This explanation is generated deterministically for offline testing and "
                "does not alter any computed score."
            )
        prompt_tokens = len(_tokens(prompt)) + (len(_tokens(system)) if system else 0)
        completion_tokens = len(_tokens(body))
        return LLMResult(
            text=body,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model="mock-1",
        )
