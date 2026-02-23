"""Request schemas for the RAG API."""

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        examples=["Show summary about contract with TransContinental Corp"],
    )
