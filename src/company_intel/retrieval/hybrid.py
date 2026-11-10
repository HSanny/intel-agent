"""Combine dense and lexical rankings with Reciprocal Rank Fusion (RRF).

RRF ignores each retriever's raw score (which live on different scales) and uses
only the *rank* a document got in each list. A document's fused score is the sum
over lists of ``1 / (k + rank)``. Ranking well in both retrievers beats ranking
first in only one, which is exactly the hybrid behaviour we want.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .bm25 import bm25_search
from .types import Hit
from .vector import vector_search

if TYPE_CHECKING:
    from ..embeddings.base import EmbeddingProvider
    from ..store.db import DB


def reciprocal_rank_fusion(rankings: list[list[Hit]], k: int = 60) -> list[Hit]:
    """Fuse several ranked Hit lists into one, by RRF. ``score`` becomes the RRF score."""
    scores: dict[int, float] = {}
    hit_by_id: dict[int, Hit] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking):
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (k + rank + 1)
            hit_by_id[hit.chunk_id] = hit

    ordered = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
    return [replace(hit_by_id[cid], score=score) for cid, score in ordered]


def hybrid_search(
    db: DB,
    provider: EmbeddingProvider,
    query: str,
    k_each: int = 20,
    k_final: int = 20,
    ticker: str | None = None,
) -> list[Hit]:
    """Run dense + lexical retrieval and fuse them with RRF."""
    dense = vector_search(db, provider, query, k=k_each, ticker=ticker)
    lexical = bm25_search(db, query, k=k_each, ticker=ticker)
    return reciprocal_rank_fusion([dense, lexical])[:k_final]
