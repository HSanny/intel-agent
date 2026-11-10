"""Dense (semantic) retrieval over pgvector."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .types import Hit, hit_from_row

if TYPE_CHECKING:
    from ..embeddings.base import EmbeddingProvider
    from ..store.db import DB


def vector_search(
    db: DB,
    provider: EmbeddingProvider,
    query: str,
    k: int = 20,
    ticker: str | None = None,
) -> list[Hit]:
    """Embed the query and return the k nearest chunks by cosine similarity."""
    embedding = provider.embed_query(query)
    rows = db.vector_search(embedding, k=k, ticker=ticker)
    return [hit_from_row(row, float(row["score"])) for row in rows]
