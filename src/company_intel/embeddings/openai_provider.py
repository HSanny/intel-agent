"""Optional OpenAI embedding provider (alternate to the local bge default).

Not a default dependency: ``openai`` is imported lazily and a clear error is
raised if it is missing. Kept so we can A/B the local model against an API later.
"""

from __future__ import annotations

from collections.abc import Sequence

_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}


class OpenAIProvider:
    def __init__(self, model_name: str = "text-embedding-3-small") -> None:
        # Guard against being constructed with a bge model name from shared config.
        if model_name not in _DIMS:
            model_name = "text-embedding-3-small"
        self.name = model_name
        self.model_name = model_name
        self.dim = _DIMS[model_name]
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover
                raise ImportError(
                    "the openai package is required for the openai embedding "
                    "provider: pip install openai"
                ) from exc
            self._client = OpenAI()
        return self._client

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        client = self._get_client()
        resp = client.embeddings.create(model=self.model_name, input=list(texts))
        return [item.embedding for item in resp.data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]
