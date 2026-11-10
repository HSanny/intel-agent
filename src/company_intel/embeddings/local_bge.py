"""Local embedding provider using sentence-transformers (bge-small-en-v1.5).

The model is loaded lazily so importing this module (and running the test suite)
does not require torch to be installed.
"""

from __future__ import annotations

from collections.abc import Sequence


class LocalBGEProvider:
    """bge-small-en-v1.5: 384-dim, normalized embeddings, CPU-friendly."""

    # bge retrieval recommends prefixing the *query* with this instruction.
    QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

    def __init__(
        self, model_name: str = "BAAI/bge-small-en-v1.5", device: str = "cpu"
    ) -> None:
        self.name = model_name.split("/")[-1]
        self.model_name = model_name
        self.device = device
        self.dim = 384
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._load()
        vectors = model.encode(
            list(texts), normalize_embeddings=True, batch_size=32
        )
        return [v.tolist() for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([self.QUERY_INSTRUCTION + text])[0]
