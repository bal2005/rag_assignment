"""
rag_pipeline.py
Orchestrates the full RAG flow:
  1. Extract structured filters from the query (via Groq / LLM)
  2. Query Neon Postgres for matching contract IDs
  3. Embed the query with BGE-M3
  4. Vector search Milvus with contract_id filter
  5. Fetch full contract rows from Postgres
  6. Build context and generate a grounded answer with Groq
"""

from __future__ import annotations

import json
import logging
import traceback

from groq import Groq

from app.config import get_settings
from app.services.embedding_service import get_embedding
from app.services.milvus_service import vector_search
from app.services.postgres_service import (
    get_contract_ids_by_filters,
    get_contracts_by_ids,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Groq client (singleton) ───────────────────────────────────────────────────
_groq: Groq | None = None


def _get_groq() -> Groq:
    global _groq
    if _groq is None:
        logger.info("🔑 Initialising Groq client (model=%s) …", settings.GROQ_MODEL)
        _groq = Groq(api_key=settings.GROQ_API_KEY)
        logger.info("✅ Groq client ready")
    return _groq


# ── System prompts ────────────────────────────────────────────────────────────
SYSTEM_PROMPT_EXTRACT = """
You are a legal data extraction assistant.

Your task is to extract structured filters from a user query
and return ONLY valid JSON.

Available database columns:
- vendor_name (string)
- contract_type (must be one of: NDA, Service Agreement, Vendor Agreement, Partnership, General)
- compliance_score (integer)
- audit_status (Passed, Failed, Pending)
- jurisdiction (string)
- region (string)
- duration_months (integer)
- contract_date (date)

Rules:
1. Ignore capitalization differences.
2. Only return JSON.
3. Include only fields explicitly mentioned in the query.
4. Do NOT add extra fields.
5. If nothing relevant is found, return {}.
6. Always strictly use the column names provided above.

Numeric Filtering Rules:
• If query says:
  - "above X", "greater than X", "more than X"
    → use: "compliance_score_min": X
  - "below X", "less than X"
    → use: "compliance_score_max": X
  - "between X and Y"
    → use: "compliance_score_between": [X, Y]
• For duration:
  - "longer than X months"
    → use: "duration_min": X
  - "shorter than X months"
    → use: "duration_max": X
• For relative dates:
  - "last X months"
    → use: "last_n_months": X

• Never output natural language.
• Never explain anything.
• Output must be valid JSON only.

Examples:
Query: Show failed vendor agreements in APAC with compliance score above 70
Output:
{
  "contract_type": "Vendor Agreement",
  "audit_status": "Failed",
  "region": "APAC",
  "compliance_score_min": 70
}

Query: Contracts between 60 and 80 score from last 3 months
Output:
{
  "compliance_score_between": [60, 80],
  "last_n_months": 3
}
"""

SYSTEM_PROMPT_ANSWER = """
You are Contract Manager and Audit Checking Bot, a professional legal compliance assistant.

IMPORTANT RULES:
- Answer strictly based on the provided contract data and clauses.
- Do NOT hallucinate.
- If information is missing, clearly state: "Not found in the available contract records."
- Provide structured legal-style response.

Structure your answer as:
1. Executive Summary
2. Relevant Clauses
3. Risk Assessment
4. Missing Information (if any)
5. Final Compliance Status
"""


# ── Step 1: Filter extraction ─────────────────────────────────────────────────
def extract_filters(user_query: str) -> dict:
    logger.info("🧠 [Step 1] Extracting filters from query …")
    groq = _get_groq()

    try:
        completion = groq.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_EXTRACT},
                {"role": "user", "content": user_query},
            ],
            temperature=0,
            max_completion_tokens=300,
            top_p=1,
            stream=False,
        )
    except Exception as exc:
        logger.error("❌ [Step 1] Groq filter extraction FAILED: %s\n%s", exc, traceback.format_exc())
        raise

    content = completion.choices[0].message.content.strip()
    logger.debug("   Raw Groq filter output: %r", content)

    # Strip markdown code fences if present
    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()

    try:
        filters = json.loads(content)
        logger.info("✅ [Step 1] Extracted filters: %s", filters)
        return filters
    except json.JSONDecodeError as exc:
        logger.warning("⚠️  [Step 1] LLM returned invalid JSON; using empty filters. Raw: %r | Error: %s", content, exc)
        return {}


# ── Step 6: Answer generation ─────────────────────────────────────────────────
def _build_context(contract_rows: list[dict], chunks: list[dict]) -> str:
    logger.info("🔨 [Step 6a] Building context | rows=%d chunks=%d", len(contract_rows), len(chunks))
    ctx = "STRUCTURED CONTRACT DATA:\n"
    for row in contract_rows:
        ctx += f"""
Contract ID    : {row['contract_id']}
Vendor         : {row['vendor_name']}
Contract Type  : {row['contract_type']}
Duration       : {row['duration_months']} months
Compliance     : {row['compliance_score']}
Audit Status   : {row['audit_status']}
Date           : {row['contract_date']}
Jurisdiction   : {row['jurisdiction']}
Policy         : {row['policy_name']}
Region         : {row['region']}
-------------------------------------
"""

    ctx += "\nRELEVANT CONTRACT CLAUSES:\n"
    for c in chunks:
        ctx += f"\n[Contract ID: {c['contract_id']} | Score: {round(c['similarity_score'], 3)}]\n"
        ctx += c["chunk_text"] + "\n-------------------------------------\n"

    logger.info("✅ [Step 6a] Context built (%d chars)", len(ctx))
    return ctx


def generate_answer(user_query: str, context: str) -> str:
    logger.info("💡 [Step 6b] Calling Groq for final answer (context_len=%d chars) …", len(context))
    groq = _get_groq()

    try:
        completion = groq.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_ANSWER},
                {
                    "role": "user",
                    "content": f"User Query:\n{user_query}\n\nContext:\n{context}",
                },
            ],
            temperature=0.2,
            max_completion_tokens=2048,
            top_p=1,
            stream=False,
        )
    except Exception as exc:
        logger.error("❌ [Step 6b] Groq answer generation FAILED: %s\n%s", exc, traceback.format_exc())
        raise

    answer = completion.choices[0].message.content
    logger.info("✅ [Step 6b] Answer generated (%d chars)", len(answer))
    return answer


# ── Full pipeline ─────────────────────────────────────────────────────────────
def run_rag_pipeline(user_query: str) -> dict:
    """
    Execute the complete RAG pipeline for a user query.
    Returns dict matching the QueryResponse schema.
    """
    logger.info("🚀 ===== RAG PIPELINE START =====")
    logger.info("   Query: %r", user_query[:120])

    # 1️⃣  Extract structured filters
    filters = extract_filters(user_query)

    # 2️⃣  Query Postgres
    logger.info("🐘 [Step 2] Querying Postgres for contract IDs …")
    try:
        contract_ids = get_contract_ids_by_filters(filters)
        logger.info("✅ [Step 2] Postgres returned %d contract_id(s): %s", len(contract_ids), contract_ids)
    except Exception as exc:
        logger.error("❌ [Step 2] Postgres query FAILED: %s\n%s", exc, traceback.format_exc())
        raise

    # 3️⃣  Fallback warning if no IDs
    if not contract_ids:
        logger.warning("⚠️  [Step 3] No Postgres matches → vector search will be SKIPPED")

    # 4️⃣  Embed query
    logger.info("🔢 [Step 4] Generating query embedding …")
    try:
        query_embedding = get_embedding(user_query)
        logger.info("✅ [Step 4] Embedding generated (dim=%d)", len(query_embedding))
    except Exception as exc:
        logger.error("❌ [Step 4] Embedding FAILED: %s\n%s", exc, traceback.format_exc())
        raise

    # 5️⃣  Vector search
    chunks: list[dict] = []
    if contract_ids:
        logger.info("🔍 [Step 5] Running Milvus vector search (top_k=%d) …", settings.TOP_K)
        try:
            chunks = vector_search(query_embedding, contract_ids, top_k=settings.TOP_K)
            logger.info("✅ [Step 5] Milvus returned %d chunk(s)", len(chunks))
        except Exception as exc:
            logger.error("❌ [Step 5] Milvus vector search FAILED: %s\n%s", exc, traceback.format_exc())
            raise
    else:
        logger.warning("⚠️  [Step 5] Skipping vector search (no contract IDs)")

    # 6️⃣  Fetch full contract rows
    logger.info("🗃  [Step 6] Fetching full contract rows from Postgres …")
    try:
        contract_rows = get_contracts_by_ids(contract_ids)
        logger.info("✅ [Step 6] Fetched %d row(s)", len(contract_rows))
    except Exception as exc:
        logger.error("❌ [Step 6] Postgres row fetch FAILED: %s\n%s", exc, traceback.format_exc())
        raise

    # 7️⃣  Build context & generate answer
    context = _build_context(contract_rows, chunks)
    answer = generate_answer(user_query, context)

    result = {
        "answer": answer,
        "retrieved_chunks": [
            {
                "chunk_text": c["chunk_text"],
                "similarity_score": c["similarity_score"],
                "contract_id": c["contract_id"],
                "contract_type": c["contract_type"],
            }
            for c in chunks
        ],
        "structured_records": contract_rows,
    }

    logger.info(
        "🏁 ===== RAG PIPELINE DONE | answer=%d chars | chunks=%d | records=%d =====",
        len(answer),
        len(result["retrieved_chunks"]),
        len(result["structured_records"]),
    )
    return result
