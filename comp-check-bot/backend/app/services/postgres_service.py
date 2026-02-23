"""
postgres_service.py
Neon Postgres integration with connection pooling, retry logic, and
dynamic filter-based contract querying.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ── Engine (singleton) ────────────────────────────────────────────────────────
def _build_engine():
    logger.info("🔌 Building Neon Postgres engine …")
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,       # keeps connections alive across sleeps
        pool_recycle=300,
        connect_args={"connect_timeout": 10},
    )
    logger.info("✅ Postgres engine ready")
    return engine


engine = _build_engine()


# ── Retry helper ─────────────────────────────────────────────────────────────
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def _execute(query_str: str, params: dict) -> list:
    with engine.connect() as conn:
        result = conn.execute(text(query_str), params)
        return result.fetchall()


# ── Filter extraction → SQL ───────────────────────────────────────────────────
def get_contract_ids_by_filters(filters: dict) -> list[int]:
    """
    Translate LLM-extracted filter dict into a SQL WHERE clause and return
    matching contract IDs.
    """
    base_query = "SELECT contract_id FROM contracts WHERE 1=1"
    params: dict[str, Any] = {}

    # Text filters ─────────────────────────────────────────────────────────
    if filters.get("vendor_name"):
        base_query += " AND vendor_name ILIKE :vendor_name"
        params["vendor_name"] = f"%{filters['vendor_name']}%"

    if filters.get("contract_type"):
        base_query += " AND contract_type ILIKE :contract_type"
        params["contract_type"] = f"%{filters['contract_type']}%"

    if filters.get("audit_status"):
        base_query += " AND audit_status ILIKE :audit_status"
        params["audit_status"] = f"%{filters['audit_status']}%"

    if filters.get("region"):
        base_query += " AND region ILIKE :region"
        params["region"] = f"%{filters['region']}%"

    if filters.get("jurisdiction"):
        base_query += " AND jurisdiction ILIKE :jurisdiction"
        params["jurisdiction"] = f"%{filters['jurisdiction']}%"

    if filters.get("policy_name"):
        base_query += " AND policy_name ILIKE :policy_name"
        params["policy_name"] = f"%{filters['policy_name']}%"

    # Compliance score ─────────────────────────────────────────────────────
    if filters.get("compliance_score_min") is not None:
        base_query += " AND compliance_score >= :compliance_score_min"
        params["compliance_score_min"] = filters["compliance_score_min"]

    if filters.get("compliance_score_max") is not None:
        base_query += " AND compliance_score <= :compliance_score_max"
        params["compliance_score_max"] = filters["compliance_score_max"]

    if filters.get("compliance_score_between"):
        base_query += " AND compliance_score BETWEEN :score_min AND :score_max"
        params["score_min"] = filters["compliance_score_between"][0]
        params["score_max"] = filters["compliance_score_between"][1]

    # Duration ─────────────────────────────────────────────────────────────
    if filters.get("duration_min") is not None:
        base_query += " AND duration_months >= :duration_min"
        params["duration_min"] = filters["duration_min"]

    if filters.get("duration_max") is not None:
        base_query += " AND duration_months <= :duration_max"
        params["duration_max"] = filters["duration_max"]

    # Relative date ────────────────────────────────────────────────────────
    if filters.get("last_n_months") is not None:
        months = filters["last_n_months"]
        cutoff = datetime.today() - timedelta(days=30 * months)
        base_query += " AND contract_date >= :date_threshold"
        params["date_threshold"] = cutoff

    logger.info("📋 SQL Filter query: %s | params: %s", base_query, params)

    try:
        rows = _execute(base_query, params)
    except OperationalError as exc:
        logger.error("❌ Postgres query failed: %s", exc)
        raise

    contract_ids = [row[0] for row in rows]
    logger.info("📄 Matching contract IDs: %s", contract_ids)
    return contract_ids


def get_contracts_by_ids(contract_ids: list[int]) -> list[dict]:
    """Fetch full contract rows for a list of IDs."""
    if not contract_ids:
        return []

    query_str = """
        SELECT contract_id, vendor_name, contract_type, duration_months,
               compliance_score, audit_status, contract_date,
               jurisdiction, policy_name, region
        FROM contracts
        WHERE contract_id = ANY(:ids)
        ORDER BY contract_id
    """
    try:
        rows = _execute(query_str, {"ids": contract_ids})
    except OperationalError as exc:
        logger.error("❌ Postgres row fetch failed: %s", exc)
        raise

    result = []
    for row in rows:
        result.append(
            {
                "contract_id": row[0],
                "vendor_name": row[1],
                "contract_type": row[2],
                "duration_months": row[3],
                "compliance_score": row[4],
                "audit_status": row[5],
                "contract_date": str(row[6]),
                "jurisdiction": row[7],
                "policy_name": row[8],
                "region": row[9],
            }
        )
    logger.info("🗃  Fetched %d contract rows", len(result))
    return result
