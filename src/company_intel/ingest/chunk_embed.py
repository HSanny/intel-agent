"""Chunk filing sections and embed them into the ``chunks`` table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .filings import Section

if TYPE_CHECKING:  # avoid runtime import cycles
    from ..embeddings.base import EmbeddingProvider
    from ..store.db import DB


@dataclass
class Chunk:
    """A slice of one filing section, ready to embed."""

    accession_no: str
    item: str
    chunk_idx: int
    text: str


def chunk_text(text: str, target_words: int = 400, overlap: int = 60) -> list[str]:
    """Split text into overlapping word windows.

    A sliding window keeps a little context shared between neighbours so a fact
    that straddles a boundary is not lost. ``overlap`` words are repeated at the
    start of each next window.
    """
    words = text.split()
    if not words:
        return []
    step = max(1, target_words - overlap)
    chunks: list[str] = []
    start = 0
    n = len(words)
    while start < n:
        window = words[start : start + target_words]
        chunks.append(" ".join(window))
        if start + target_words >= n:
            break
        start += step
    return chunks


def chunk_sections(
    sections: list[Section], target_words: int = 400, overlap: int = 60
) -> list[Chunk]:
    """Chunk each section; ``chunk_idx`` restarts per item (unique with item)."""
    chunks: list[Chunk] = []
    for section in sections:
        for idx, piece in enumerate(
            chunk_text(section.text, target_words, overlap)
        ):
            chunks.append(
                Chunk(
                    accession_no=section.accession_no,
                    item=section.item,
                    chunk_idx=idx,
                    text=piece,
                )
            )
    return chunks


def embed_and_store(
    db: DB,
    provider: EmbeddingProvider,
    accession_no: str,
    *,
    target_words: int = 400,
    overlap: int = 60,
    batch_size: int = 32,
) -> int:
    """Chunk a filing's sections, embed in batches, and store. Returns #chunks."""
    sections = db.get_sections(accession_no)
    chunks = chunk_sections(sections, target_words, overlap)
    if not chunks:
        return 0

    texts = [c.text for c in chunks]
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        embeddings.extend(provider.embed(texts[i : i + batch_size]))

    db.insert_chunks(chunks, embeddings)
    return len(chunks)
