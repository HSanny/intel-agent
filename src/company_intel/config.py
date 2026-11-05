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

    # Milestone 2 placeholders (Decision D3).
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
