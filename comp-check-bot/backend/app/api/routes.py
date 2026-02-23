"""
routes.py – FastAPI API routes for the Comp-Check Bot.
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
    return HealthResponse(status="ok", message="Comp-Check Bot is running")


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Run RAG pipeline",
    tags=["rag"],
)
async def query_endpoint(body: QueryRequest) -> QueryResponse:
    """
    Accepts a natural-language compliance query and returns:
    - `answer`            – Grounded LLM response
    - `retrieved_chunks`  – Top-k Milvus chunks with similarity scores
    - `structured_records`– Matching Postgres contract rows
    """
    logger.info("📥 Received /query request: %s …", body.query[:80])

    try:
        result = run_rag_pipeline(body.query)
    except Exception as exc:
        logger.exception("❌ Pipeline error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    logger.info("📤 Sending response with %d chunks", len(result["retrieved_chunks"]))
    return QueryResponse(**result)
