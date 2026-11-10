"""Shared retrieval types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class Hit:
    """One retrieved chunk, carrying the metadata needed to cite it."""

    chunk_id: int
    accession_no: str
    item: str
    chunk_idx: int
    text: str
    score: float
    ticker: str
    form: str
    filed_date: date | None


def hit_from_row(row: dict, score: float) -> Hit:
    """Build a Hit from a DB row dict."""
    return Hit(
        chunk_id=row["id"],
        accession_no=row["accession_no"],
        item=row["item"],
        chunk_idx=row["chunk_idx"],
        text=row["text"],
        score=score,
        ticker=row["ticker"],
        form=row["form"],
        filed_date=row["filed_date"],
    )
