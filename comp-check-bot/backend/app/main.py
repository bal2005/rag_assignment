"""
main.py – FastAPI application entry point.

Includes:
  - Global exception handler (ensures JSON is ALWAYS returned, never empty body)
  - Request/response logging middleware
  - CORS middleware
"""

from __future__ import annotations

import logging
import os
import time
import traceback

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,          # DEBUG so every step is visible on Render
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Contract Manager and Audit Checking Bot API",
    description=(
        "RAG API for legal contract compliance queries and audit checking. "
        "Powered by Neon Postgres + Milvus + BGE-M3 + Groq."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
origins = settings.origins
logger.info("🌐 CORS allowed origins: %s", origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global catch-all exception handler ────────────────────────────────────────
# This GUARANTEES a valid JSON body is always returned, even for
# completely unhandled exceptions (import errors, etc.)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    tb = traceback.format_exc()
    logger.critical(
        "💥 UNHANDLED EXCEPTION on %s %s\n%s",
        request.method,
        request.url.path,
        tb,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {type(exc).__name__}: {str(exc)}",
            "path": str(request.url.path),
        },
    )


# ── Request / Response logging middleware ─────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    logger.info(
        "➡️  REQUEST  %s %s | client=%s",
        request.method,
        request.url,
        request.client.host if request.client else "unknown",
    )

    try:
        response = await call_next(request)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        logger.critical(
            "💥 MIDDLEWARE caught exception after %.1fms: %s",
            elapsed,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": f"Unexpected error: {type(exc).__name__}: {str(exc)}"},
        )

    elapsed = (time.perf_counter() - start) * 1000
    logger.info(
        "⬅️  RESPONSE %s %s | status=%d | %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api/v1")


# ── Startup / shutdown events ─────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    logger.info("=" * 60)
    logger.info("🚀 Contract Manager and Audit Checking Bot STARTUP")
    logger.info("   DB host      : %s", settings.DB_NEON_HOST)
    logger.info("   DB name      : %s", settings.DB_NEON_NAME)
    logger.info("   DB user      : %s", settings.DB_USER_NEON)
    logger.info("   Milvus URI   : %s", settings.MILVUS_URI.strip())
    logger.info("   Collection   : %s", settings.MILVUS_COLLECTION)
    logger.info("   Embed model  : %s", settings.EMBEDDING_MODEL)
    logger.info("   LLM model    : %s", settings.GROQ_MODEL)
    logger.info("   Top-K        : %d", settings.TOP_K)
    logger.info("   CORS origins : %s", settings.origins)
    logger.info("   PORT         : %s", os.environ.get("PORT", settings.PORT))
    logger.info("=" * 60)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("👋 Contract Manager and Audit Checking Bot shutting down …")


# ── Dev entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.PORT))
    logger.info("▶  Starting server on port %d", port)
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
