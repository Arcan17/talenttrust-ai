"""Provider interfaces for LLM completion and embeddings.

Business, scoring, parsing and dossier code depend ONLY on these abstractions
(Constitution Principle II). Concrete vendor SDKs are imported solely inside their
adapter modules. The numeric score is NEVER produced by an LLM (Principle IV).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class LLMResult:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = "unknown"


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def complete(
        self, prompt: str, *, system: str | None = None, **opts: object
    ) -> LLMResult:
        """Generate a completion for the given prompt."""


class EmbeddingProvider(ABC):
    name: str = "base"
    dim: int

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text (each of length ``dim``)."""
