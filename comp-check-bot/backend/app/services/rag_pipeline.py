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
        _groq = Groq(api_key=settings.GROQ_API_KEY)
        logger.info("✅ Groq client ready (model=%s)", settings.GROQ_MODEL)
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
    logger.info("🧠 Extracting filters from query …")
    groq = _get_groq()

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

    content = completion.choices[0].message.content.strip()

    # Strip markdown code fences if present
    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()

    try:
        filters = json.loads(content)
        logger.info("🔎 Extracted filters: %s", filters)
        return filters
    except json.JSONDecodeError:
        logger.warning("⚠️  LLM returned invalid JSON; using empty filters. Raw: %s", content)
        return {}


# ── Step 6: Answer generation ─────────────────────────────────────────────────
def _build_context(contract_rows: list[dict], chunks: list[dict]) -> str:
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

    return ctx


def generate_answer(user_query: str, context: str) -> str:
    logger.info("💡 Generating answer with Groq …")
    groq = _get_groq()

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

    answer = completion.choices[0].message.content
    logger.info("✅ Answer generated (%d chars)", len(answer))
    return answer


# ── Full pipeline ─────────────────────────────────────────────────────────────
def run_rag_pipeline(user_query: str) -> dict:
    """
    Execute the complete RAG pipeline for a user query.

    Returns dict matching the QueryResponse schema.
    """
    logger.info("🚀 RAG pipeline started for query: %s", user_query[:80])

    # 1️⃣  Extract structured filters
    filters = extract_filters(user_query)

    # 2️⃣  Query Postgres
    contract_ids = get_contract_ids_by_filters(filters)

    # 3️⃣  Handle no-match: fall back to all contracts (broad search)
    if not contract_ids:
        logger.warning("⚠️  No Postgres matches; falling back to broad vector search")

    # 4️⃣  Embed query
    query_embedding = get_embedding(user_query)

    # 5️⃣  Vector search (only if we have IDs)
    chunks: list[dict] = []
    if contract_ids:
        chunks = vector_search(query_embedding, contract_ids, top_k=settings.TOP_K)

    # 6️⃣  Fetch full contract rows
    contract_rows = get_contracts_by_ids(contract_ids)

    # 7️⃣  Build context & generate answer
    context = _build_context(contract_rows, chunks)
    answer = generate_answer(user_query, context)

    return {
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
