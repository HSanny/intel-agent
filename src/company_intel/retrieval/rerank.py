"""Reranking: a second, more accurate pass over the fused candidates.

Retrieval uses a *bi-encoder* (query and passage embedded separately, compared
by cosine) — fast, but it never sees the two together. A *cross-encoder* reads
the (query, passage) pair jointly and scores relevance directly. It is too slow
to run over the whole corpus, so we use it only to reorder the top fused hits.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Protocol

from .types import Hit

if TYPE_CHECKING:
    from ..config import Settings


class Reranker(Protocol):
    def rerank(self, query: str, hits: list[Hit], top_k: int = 5) -> list[Hit]: ...


class NoopReranker:
    """Passthrough: keep fused order, just truncate. Used in tests / when disabled."""

    def rerank(self, query: str, hits: list[Hit], top_k: int = 5) -> list[Hit]:
        return hits[:top_k]


class CrossEncoderReranker:
    """Local cross-encoder (e.g. bge-reranker-base), lazy-loaded."""

    def __init__(
        self, model_name: str = "BAAI/bge-reranker-base", device: str = "cpu"
    ) -> None:
        self.model_name = model_name
        self.device = device
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name, device=self.device)
        return self._model

    def rerank(self, query: str, hits: list[Hit], top_k: int = 5) -> list[Hit]:
        if not hits:
            return []
        model = self._load()
        scores = model.predict([(query, hit.text) for hit in hits])
        ranked = sorted(
            zip(hits, scores, strict=True), key=lambda pair: pair[1], reverse=True
        )
        return [replace(hit, score=float(score)) for hit, score in ranked[:top_k]]


def get_reranker(settings: Settings) -> Reranker:
    """Return the configured reranker."""
    if settings.rerank_enabled:
        return CrossEncoderReranker(settings.rerank_model)
    return NoopReranker()
