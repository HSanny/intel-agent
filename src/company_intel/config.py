"""Application settings, loaded from the environment / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Field names map to upper-case environment variables (case-insensitive),
    so ``sec_user_agent`` reads ``SEC_USER_AGENT``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required by SEC: a descriptive User-Agent with name + email.
    sec_user_agent: str

    # Read-write DB connection used by ingest.
    database_url: str = "postgresql://intel:intel@localhost:5432/intel"

    # Local cache for SEC responses.
    sec_cache_dir: Path = Path("data/sec_cache")

    # Requests per second to SEC (kept under the 10 req/s limit).
    sec_rate_limit: float = 8.0

    # Embeddings (Decision D3: local bge-small-en-v1.5, 384-dim, swappable).
    embedding_provider: str = "local_bge"  # "local_bge" | "openai"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    embed_batch_size: int = 32

    # Chunking (word-based sliding window).
    chunk_target_words: int = 400
    chunk_overlap_words: int = 60

    # Reranking (local cross-encoder).
    rerank_enabled: bool = True
    rerank_model: str = "BAAI/bge-reranker-base"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
