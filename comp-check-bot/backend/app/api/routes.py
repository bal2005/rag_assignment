"""
routes.py – FastAPI API routes for the Contract Manager and Audit Checking Bot.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

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
    return HealthResponse(status="ok", message="Contract Manager and Audit Checking Bot is running")


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Run RAG pipeline",
    tags=["rag"],
)
async def query_endpoint(body: QueryRequest) -> QueryResponse:

    logger.info("📥 Received /query request: %s …", body.query[:80])

    try:
        result = run_rag_pipeline(body.query)

        if not result:
            raise HTTPException(
                status_code=500,
                detail="RAG pipeline returned empty result"
            )

        if "retrieved_chunks" not in result:
            raise HTTPException(
                status_code=500,
                detail="Invalid pipeline output format"
            )

    except Exception as exc:
        logger.exception("❌ Pipeline error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    logger.info(
        "📤 Sending response with %d chunks",
        len(result.get("retrieved_chunks", []))
    )

    return QueryResponse(**result)
