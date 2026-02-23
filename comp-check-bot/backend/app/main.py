"""
main.py – FastAPI application entry point.
"""

from __future__ import annotations

import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Comp-Check Bot API",
    description=(
        "Production-ready RAG API for legal contract compliance queries. "
        "Powered by Neon Postgres + Milvus + BGE-M3 + Groq."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
origins = settings.origins
logger.info("🌐 CORS allowed origins: %s", origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("🚀 Comp-Check Bot starting up …")
    logger.info("   DB host    : %s", settings.DB_NEON_HOST)
    logger.info("   Milvus URI : %s", settings.MILVUS_URI.strip())
    logger.info("   Model      : %s", settings.EMBEDDING_MODEL)
    logger.info("   LLM        : %s", settings.GROQ_MODEL)
    logger.info("   Top-K      : %d", settings.TOP_K)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("👋 Comp-Check Bot shutting down …")


# ── Dev entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.PORT))
    logger.info("▶  Starting server on port %d", port)
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
