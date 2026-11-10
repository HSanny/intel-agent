"""Lexical (keyword) retrieval using BM25 (Decision D6: rank_bm25).

BM25 scores a document by how often the query's terms appear in it, weighted
down for terms that are common across the whole corpus (IDF). It catches exact
words — tickers, defined terms, numbers — that a dense model may smooth over.

For this project's small corpus we build the index per query over the candidate
rows. At larger scale this would move to a persistent index or Postgres FTS.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rank_bm25 import BM25Okapi

from .types import Hit, hit_from_row

if TYPE_CHECKING:
    from ..store.db import DB

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase word/number tokens."""
    return _TOKEN.findall(text.lower())


def bm25_search(
    db: DB, query: str, k: int = 20, ticker: str | None = None
) -> list[Hit]:
    """Return the top-k chunks for a query by BM25 score."""
    rows = db.fetch_chunks(ticker=ticker)
    if not rows:
        return []

    corpus = [tokenize(row["text"]) for row in rows]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(tokenize(query))

    ranked = sorted(
        zip(rows, scores, strict=True), key=lambda pair: pair[1], reverse=True
    )
    return [hit_from_row(row, float(score)) for row, score in ranked[:k]]
