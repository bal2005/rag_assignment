"""
embedding_service.py
HuggingFace InferenceClient wrapper for BGE-M3 embeddings.
"""

from __future__ import annotations

import logging

import numpy as np
from huggingface_hub import InferenceClient

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Singleton client ──────────────────────────────────────────────────────────
_client: InferenceClient | None = None


def _get_client() -> InferenceClient:
    global _client
    if _client is None:
        logger.info("🤗 Initialising HuggingFace InferenceClient …")
        _client = InferenceClient(api_key=settings.HF_TOKEN)
        logger.info("✅ HuggingFace client ready (model=%s)", settings.EMBEDDING_MODEL)
    return _client


def get_embedding(text: str) -> list[float]:
    """
    Generate a normalised BGE-M3 embedding for `text`.
    Returns a flat list of floats for direct use in Milvus.
    """
    logger.info("🔢 Generating embedding for query (len=%d chars)", len(text))
    client = _get_client()

    raw = client.feature_extraction(text, model=settings.EMBEDDING_MODEL)
    vec = np.array(raw, dtype=np.float32)

    # Handle 2-D output (batch of 1) from some API versions
    if vec.ndim == 2:
        vec = vec[0]

    norm = np.linalg.norm(vec)
    if norm == 0:
        raise ValueError("Embedding returned a zero vector – cannot normalise")

    normalised = (vec / norm).tolist()
    logger.info("✅ Embedding generated (dim=%d)", len(normalised))
    return normalised
