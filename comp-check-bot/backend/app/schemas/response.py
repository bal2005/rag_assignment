"""Response schemas for the RAG API."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    chunk_text: str
    similarity_score: float
    contract_id: int
    contract_type: str


class StructuredRecord(BaseModel):
    contract_id: int
    vendor_name: str
    contract_type: str
    duration_months: int
    compliance_score: int
    audit_status: str
    contract_date: str          # ISO date string
    jurisdiction: str
    policy_name: str
    region: str


class QueryResponse(BaseModel):
    answer: str
    retrieved_chunks: list[RetrievedChunk]
    structured_records: list[StructuredRecord]


class HealthResponse(BaseModel):
    status: str
    message: str
