"""
milvus_service.py
Milvus Cloud (Zilliz) vector search with contract_id pre-filtering.
"""

from __future__ import annotations

import logging

from pymilvus import Collection, connections, utility

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Connection ────────────────────────────────────────────────────────────────
_connected = False
_collection: Collection | None = None


def _ensure_connected() -> None:
    global _connected, _collection

    if not _connected:
        logger.info("🔗 Connecting to Milvus Cloud at %s …", settings.MILVUS_URI)
        connections.connect(
            alias="default",
            uri=settings.MILVUS_URI.strip(),
            token=settings.MILVUS_API_KEY,
        )
        _connected = True
        logger.info("✅ Milvus connected")

    if _collection is None:
        if not utility.has_collection(settings.MILVUS_COLLECTION):
            raise RuntimeError(
                f"Milvus collection '{settings.MILVUS_COLLECTION}' does not exist. "
                "Please run the ingestion notebook first."
            )
        _collection = Collection(settings.MILVUS_COLLECTION)
        _collection.load()
        logger.info("📦 Collection '%s' loaded", settings.MILVUS_COLLECTION)


def vector_search(
    query_embedding: list[float],
    contract_ids: list[int],
    top_k: int = 5,
) -> list[dict]:
    """
    Search Milvus for the top-k most similar chunks.

    Args:
        query_embedding:  Normalised query vector (dim=1024).
        contract_ids:     Postgres-filtered IDs to constrain the search.
        top_k:            Number of results to return.

    Returns:
        List of dicts with keys: contract_id, contract_type, chunk_text, score.
    """
    _ensure_connected()
    assert _collection is not None

    if not contract_ids:
        logger.warning("⚠️  No contract IDs – skipping vector search")
        return []

    # Build filter expression
    filter_expr = f"contract_id in {contract_ids}"
    logger.info(
        "🔍 Milvus search | filter=%s | top_k=%d", filter_expr, top_k
    )

    search_params = {
        "metric_type": "COSINE",
        "params": {"nprobe": 10},
    }

    results = _collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        expr=filter_expr,
        output_fields=["contract_id", "contract_type", "text_chunk"],
    )

    chunks = []
    for hits in results:
        for hit in hits:
            chunks.append(
                {
                    "contract_id": hit.entity.get("contract_id"),
                    "contract_type": hit.entity.get("contract_type"),
                    "chunk_text": hit.entity.get("text_chunk"),
                    "similarity_score": round(float(hit.score), 6),
                }
            )

    logger.info("✅ Milvus returned %d chunks", len(chunks))
    return chunks
