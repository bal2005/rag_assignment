"""
routes.py – FastAPI API routes for the Contract Manager and Audit Checking Bot.
"""

from __future__ import annotations

import logging
import traceback

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

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
    logger.info("✅ /health check called")
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
async def query_endpoint(request: Request, body: QueryRequest) -> QueryResponse:
    logger.info("=" * 50)
    logger.info("📥 /query called | query=%r", body.query[:100])
    logger.info("   Content-Type : %s", request.headers.get("content-type"))
    logger.info("   Origin       : %s", request.headers.get("origin", "none"))

    # ── Step 1: Run pipeline in threadpool (non-blocking) ─────────────────────
    logger.info("🔄 STEP: Starting RAG pipeline …")
    try:
        result = await run_in_threadpool(run_rag_pipeline, body.query)
        logger.info("✅ STEP: Pipeline completed successfully")
    except HTTPException:
        raise   # re-raise FastAPI exceptions as-is
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("❌ STEP: Pipeline FAILED with %s: %s\n%s", type(exc).__name__, exc, tb)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline error [{type(exc).__name__}]: {str(exc)}",
        ) from exc

    # ── Step 2: Validate result structure ─────────────────────────────────────
    logger.info("🔄 STEP: Validating pipeline result …")
    if not result:
        logger.error("❌ STEP: Pipeline returned None or empty dict")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG pipeline returned an empty result.",
        )

    for key in ("answer", "retrieved_chunks", "structured_records"):
        if key not in result:
            logger.error("❌ STEP: Missing key in pipeline result: %r", key)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Pipeline output missing required key: '{key}'",
            )

    logger.info(
        "✅ STEP: Validation passed | answer_len=%d | chunks=%d | records=%d",
        len(result.get("answer", "")),
        len(result.get("retrieved_chunks", [])),
        len(result.get("structured_records", [])),
    )

    # ── Step 3: Build and return response ────────────────────────────────────
    logger.info("🔄 STEP: Building QueryResponse …")
    try:
        response_obj = QueryResponse(**result)
        logger.info("✅ STEP: QueryResponse built successfully")
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("❌ STEP: QueryResponse validation FAILED: %s\n%s", exc, tb)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Response schema validation error [{type(exc).__name__}]: {str(exc)}",
        ) from exc

    logger.info("📤 Sending response")
    logger.info("=" * 50)
    return response_obj
