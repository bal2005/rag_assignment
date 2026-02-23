"""
milvus_service.py
Milvus Cloud (Zilliz) vector search with contract_id pre-filtering.
"""

from __future__ import annotations

import logging
import traceback

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
        milvus_uri = settings.MILVUS_URI.strip()
        logger.info("🔗 Connecting to Milvus Cloud …")
        logger.info("   URI        : %s", milvus_uri)
        logger.info("   Collection : %s", settings.MILVUS_COLLECTION)
        try:
            connections.connect(
                alias="default",
                uri=milvus_uri,
                token=settings.MILVUS_API_KEY,
            )
            _connected = True
            logger.info("✅ Milvus connected successfully")
        except Exception as exc:
            logger.critical("💥 Milvus CONNECTION FAILED: %s\n%s", exc, traceback.format_exc())
            raise

    if _collection is None:
        logger.info("📦 Loading Milvus collection '%s' …", settings.MILVUS_COLLECTION)
        try:
            if not utility.has_collection(settings.MILVUS_COLLECTION):
                raise RuntimeError(
                    f"Milvus collection '{settings.MILVUS_COLLECTION}' does not exist. "
                    "Please run the ingestion notebook first."
                )
            _collection = Collection(settings.MILVUS_COLLECTION)
            _collection.load()
            logger.info("✅ Collection '%s' loaded", settings.MILVUS_COLLECTION)
        except Exception as exc:
            logger.critical("💥 Milvus collection load FAILED: %s\n%s", exc, traceback.format_exc())
            raise


def vector_search(
    query_embedding: list[float],
    contract_ids: list[int],
    top_k: int = 5,
) -> list[dict]:
    """
    Search Milvus for the top-k most similar chunks.
    """
    logger.info("🔗 Ensuring Milvus connection …")
    _ensure_connected()
    assert _collection is not None

    if not contract_ids:
        logger.warning("⚠️  vector_search called with no contract_ids → returning []")
        return []

    filter_expr = f"contract_id in {contract_ids}"
    logger.info("🔍 Milvus search params | filter=%s | top_k=%d | embedding_dim=%d",
                filter_expr, top_k, len(query_embedding))

    search_params = {
        "metric_type": "COSINE",
        "params": {"nprobe": 10},
    }

    try:
        results = _collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=["contract_id", "contract_type", "text_chunk"],
        )
        logger.info("✅ Milvus search completed")
    except Exception as exc:
        logger.error("❌ Milvus search FAILED: %s\n%s", exc, traceback.format_exc())
        raise

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

    logger.info("✅ Milvus returned %d chunk(s)", len(chunks))
    for i, c in enumerate(chunks):
        logger.debug("   chunk[%d]: contract_id=%s score=%.4f text_len=%d",
                     i, c["contract_id"], c["similarity_score"],
                     len(c["chunk_text"] or ""))
    return chunks
