"""The filing-search tool: a query -> ranked passages, each with a citation.

This is the unit the Filings Researcher agent will call in Milestone 3. It ties
the whole retrieval pipeline together: hybrid search -> rerank -> cited results.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from ..retrieval.hybrid import hybrid_search

if TYPE_CHECKING:
    from ..embeddings.base import EmbeddingProvider
    from ..retrieval.rerank import Reranker
    from ..store.db import DB


@dataclass
class Citation:
    """Where a passage came from — enough to verify it in the source filing."""

    ticker: str
    form: str
    item: str
    filed_date: date | None
    accession_no: str
    chunk_idx: int


@dataclass
class SearchResult:
    text: str
    score: float
    citation: Citation


def filing_search(
    query: str,
    ticker: str | None = None,
    top_k: int = 5,
    *,
    db: DB,
    provider: EmbeddingProvider,
    reranker: Reranker,
    k_each: int = 20,
) -> list[SearchResult]:
    """Hybrid-search the filings, rerank, and return cited passages."""
    hits = hybrid_search(db, provider, query, k_each=k_each, k_final=k_each, ticker=ticker)
    hits = reranker.rerank(query, hits, top_k=top_k)
    return [
        SearchResult(
            text=hit.text,
            score=hit.score,
            citation=Citation(
                ticker=hit.ticker,
                form=hit.form,
                item=hit.item,
                filed_date=hit.filed_date,
                accession_no=hit.accession_no,
                chunk_idx=hit.chunk_idx,
            ),
        )
        for hit in hits
    ]
