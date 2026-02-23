"""
embedding_service.py
HuggingFace InferenceClient wrapper for BGE-M3 embeddings.
"""

from __future__ import annotations

import logging
import traceback

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
        logger.info("   Model: %s", settings.EMBEDDING_MODEL)
        logger.info("   HF_TOKEN set: %s", bool(settings.HF_TOKEN))
        try:
            _client = InferenceClient(api_key=settings.HF_TOKEN)
            logger.info("✅ HuggingFace InferenceClient ready")
        except Exception as exc:
            logger.critical("💥 HuggingFace client init FAILED: %s\n%s", exc, traceback.format_exc())
            raise
    return _client


def get_embedding(text: str) -> list[float]:
    """
    Generate a normalised BGE-M3 embedding for `text`.
    Returns a flat list of floats for direct use in Milvus.
    """
    logger.info("🔢 Generating embedding | text_len=%d chars | model=%s", len(text), settings.EMBEDDING_MODEL)
    client = _get_client()

    try:
        raw = client.feature_extraction(text, model=settings.EMBEDDING_MODEL)
        logger.debug("   Raw embedding type=%s shape-hint=%s", type(raw).__name__,
                     getattr(raw, "shape", "N/A"))
    except Exception as exc:
        logger.error("❌ HuggingFace feature_extraction FAILED: %s\n%s", exc, traceback.format_exc())
        raise

    try:
        vec = np.array(raw, dtype=np.float32)

        # Handle 2-D output (batch of 1) from some API versions
        if vec.ndim == 2:
            logger.debug("   Embedding was 2D (shape=%s), taking first row", vec.shape)
            vec = vec[0]

        norm = np.linalg.norm(vec)
        logger.debug("   Embedding dim=%d | norm=%.6f", len(vec), norm)

        if norm == 0:
            raise ValueError("Embedding returned a zero vector – cannot normalise")

        normalised = (vec / norm).tolist()
        logger.info("✅ Embedding ready (dim=%d)", len(normalised))
        return normalised
    except Exception as exc:
        logger.error("❌ Embedding normalisation FAILED: %s\n%s", exc, traceback.format_exc())
        raise
