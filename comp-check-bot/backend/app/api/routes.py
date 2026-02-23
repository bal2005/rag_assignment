"""
routes.py – FastAPI API routes for the Contract Manager and Audit Checking Bot.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.schemas.request import QueryRequest
from app.schemas.response import HealthResponse, QueryResponse
from app.services.rag_pipeline import run_rag_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["utility"],
)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        message="Contract Manager and Audit Checking Bot is running",
    )


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Run RAG pipeline",
    tags=["rag"],
)
async def query_endpoint(body: QueryRequest) -> QueryResponse:
    logger.info("📥 Received /query request: %s …", body.query[:80])

    # ── Run synchronous pipeline in a thread so the event loop isn't blocked ──
    try:
        result = await run_in_threadpool(run_rag_pipeline, body.query)
    except HTTPException:
        # Re-raise FastAPI exceptions as-is (don't wrap them again)
        raise
    except Exception as exc:
        logger.exception("❌ Pipeline error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    # ── Validate pipeline output ───────────────────────────────────────────────
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG pipeline returned an empty result.",
        )
    if "retrieved_chunks" not in result or "answer" not in result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid pipeline output format.",
        )

    logger.info(
        "📤 Sending response with %d chunks, %d records",
        len(result.get("retrieved_chunks", [])),
        len(result.get("structured_records", [])),
    )
    return QueryResponse(**result)
