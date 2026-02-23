"""
config.py – Application settings loaded from environment variables.
All secrets come from the environment; no hardcoded values.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Neon / Postgres ──────────────────────────────────────────────────────
    DB_USER_NEON: str
    DB_PW_NEON: str
    DB_NEON_HOST: str
    DB_NEON_NAME: str

    # ── Milvus / Zilliz Cloud ────────────────────────────────────────────────
    MILVUS_URI: str
    MILVUS_API_KEY: str
    MILVUS_COLLECTION: str = "legal_policy_vectors"

    # ── HuggingFace ──────────────────────────────────────────────────────────
    HF_TOKEN: str
    EMBEDDING_MODEL: str = "BAAI/bge-m3"

    # ── Groq LLM ─────────────────────────────────────────────────────────────
    GROQ_API_KEY: str
    GROQ_MODEL: str = "openai/gpt-oss-20b"

    # ── Application ──────────────────────────────────────────────────────────
    PORT: int = 8000
    ALLOWED_ORIGINS: str = "*"          # comma-separated list or "*"
    TOP_K: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )

    @property
    def DATABASE_URL(self) -> str:
        # Note: channel_binding=require is NOT supported by psycopg2 – use sslmode only
        return (
            f"postgresql://{self.DB_USER_NEON}:{self.DB_PW_NEON}"
            f"@{self.DB_NEON_HOST}/{self.DB_NEON_NAME}"
            f"?sslmode=require"
        )

    @property
    def origins(self) -> list[str]:
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
