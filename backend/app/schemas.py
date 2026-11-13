from typing import Any, Optional

from pydantic import BaseModel, Field


class ChunkOut(BaseModel):
    index: int
    text: str
    chunk_id: str


class MetadataOut(BaseModel):
    source_name: str
    filename: str
    size: int
    chunk_count: int
    created_at: str
    doc_type: str = "markdown"
    extras: dict[str, Any] = Field(default_factory=dict)


class DocumentDetail(BaseModel):
    document_id: str
    metadata: MetadataOut
    chunks: list[ChunkOut]


class MetaUpdate(BaseModel):
    metadata: dict[str, Any]


class ChatRequest(BaseModel):
    query: str
    top_k: int = 4
    threshold: float = 0.3


class ChatToken(BaseModel):
    token: str


class HealthOut(BaseModel):
    status: str
    model: str
    embedding: str
    embedding_dim: int
    collection_count: int = 0