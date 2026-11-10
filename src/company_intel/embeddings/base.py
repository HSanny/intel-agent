"""Embedding provider interface and factory.

The provider is the swappable seam behind Decision D3: the rest of the system
depends only on this protocol, so the embedding model can change later (change
config, recreate the chunks table at the new dimension, re-embed).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Turns text into vectors. ``dim`` must match the DB ``vector(dim)`` column."""

    name: str
    dim: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed documents (passages)."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Embed a search query (some models add a query instruction prefix)."""
        ...


def get_provider(name: str | None = None) -> EmbeddingProvider:
    """Build the configured embedding provider (lazy-imports heavy deps)."""
    from ..config import get_settings

    settings = get_settings()
    name = name or settings.embedding_provider

    if name in ("local_bge", "bge", "local"):
        from .local_bge import LocalBGEProvider

        return LocalBGEProvider(settings.embedding_model)
    if name == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(settings.embedding_model)

    raise ValueError(f"unknown embedding provider: {name}")
