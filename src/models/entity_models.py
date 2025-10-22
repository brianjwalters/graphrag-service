"""
Entity Upsert Models for GraphRAG Service
Pydantic models for entity deduplication and upsert operations
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class EntityUpsertRequest(BaseModel):
    """
    Request model for entity upsert operation with intelligent deduplication.

    This model supports entity creation, update, or merging based on:
    1. Exact match by entity_id (MD5 hash of text + type)
    2. Semantic similarity using vector embeddings (threshold: 0.85)
    """
    entity_text: str = Field(description="Entity text (e.g., 'Supreme Court', 'John Doe')")
    entity_type: str = Field(description="Entity type (e.g., 'COURT', 'PERSON', 'CASE_CITATION')")

    # Optional fields for enhanced processing
    confidence: Optional[float] = Field(default=0.95, description="Entity extraction confidence (0-1)")
    embedding: Optional[List[float]] = Field(default=None, description="2048-dimensional Jina Embeddings v4 vector for semantic matching")
    attributes: Optional[Dict[str, Any]] = Field(default=None, description="Additional entity attributes")

    # Document tracking
    document_ids: Optional[List[str]] = Field(default=None, description="Document IDs where this entity appears")
    source_chunk_id: Optional[str] = Field(default=None, description="Source chunk identifier")

    # Tenant context
    client_id: Optional[str] = Field(default=None, description="Client identifier for multi-tenant isolation")
    case_id: Optional[str] = Field(default=None, description="Case identifier for case-specific data")

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "entity_text": "Supreme Court of the United States",
                "entity_type": "COURT",
                "confidence": 0.98,
                "embedding": [0.1, 0.2, 0.3],  # Truncated for example
                "attributes": {
                    "jurisdiction": "federal",
                    "court_level": "supreme"
                },
                "document_ids": ["doc_001"],
                "client_id": None,  # None for public entities
                "metadata": {
                    "extraction_method": "ai_enhanced",
                    "extraction_date": "2025-10-10"
                }
            }
        }


class EntityUpsertResponse(BaseModel):
    """
    Response model for entity upsert operation.

    Includes action taken (created, updated, merged) and complete entity information.
    """
    success: bool = Field(description="Operation success status")
    action: str = Field(description="Action taken: 'created', 'updated', or 'merged'")

    # Entity information
    node_id: str = Field(description="Unique node identifier (entity_id)")
    entity_text: str = Field(description="Entity text")
    entity_type: str = Field(description="Entity type")

    # Operation details
    merged_with: Optional[str] = Field(default=None, description="Node ID of canonical entity if merged")
    similarity_score: Optional[float] = Field(default=None, description="Semantic similarity score if merged (0-1)")

    # Document tracking
    document_ids: List[str] = Field(default=[], description="All document IDs where entity appears")
    document_count: int = Field(default=0, description="Number of documents referencing entity")

    # Complete node data
    node_data: Optional[Dict[str, Any]] = Field(default=None, description="Complete node record from database")

    # Performance metrics
    processing_time_ms: Optional[float] = Field(default=None, description="Processing time in milliseconds")

    # Warnings/info
    warnings: List[str] = Field(default=[], description="Any warnings encountered")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "action": "merged",
                "node_id": "entity_a1b2c3d4e5f6",
                "entity_text": "Supreme Court",
                "entity_type": "COURT",
                "merged_with": "entity_f6e5d4c3b2a1",
                "similarity_score": 0.92,
                "document_ids": ["doc_001", "doc_002"],
                "document_count": 2,
                "processing_time_ms": 45.2,
                "warnings": []
            }
        }


class BatchEntityUpsertRequest(BaseModel):
    """
    Request model for batch entity upsert operations.

    Allows upserting multiple entities in a single operation with
    deduplication across the batch.
    """
    entities: List[EntityUpsertRequest] = Field(description="List of entities to upsert")

    # Batch options
    deduplicate_within_batch: bool = Field(default=True, description="Deduplicate entities within this batch")
    max_concurrent: int = Field(default=10, description="Maximum concurrent upsert operations")

    class Config:
        json_schema_extra = {
            "example": {
                "entities": [
                    {
                        "entity_text": "Supreme Court",
                        "entity_type": "COURT",
                        "confidence": 0.98
                    },
                    {
                        "entity_text": "Judge Roberts",
                        "entity_type": "JUDGE",
                        "confidence": 0.95
                    }
                ],
                "deduplicate_within_batch": True,
                "max_concurrent": 10
            }
        }


class BatchEntityUpsertResponse(BaseModel):
    """Response model for batch entity upsert operations."""
    success: bool = Field(description="Overall batch operation success")
    total_entities: int = Field(description="Total entities in batch")

    # Operation counts
    created_count: int = Field(default=0, description="Number of entities created")
    updated_count: int = Field(default=0, description="Number of entities updated")
    merged_count: int = Field(default=0, description="Number of entities merged")
    failed_count: int = Field(default=0, description="Number of entities that failed")

    # Detailed results
    results: List[EntityUpsertResponse] = Field(default=[], description="Individual entity upsert results")
    errors: List[Dict[str, Any]] = Field(default=[], description="Errors for failed entities")

    # Performance
    total_processing_time_ms: float = Field(description="Total batch processing time")

    # Deduplication stats
    within_batch_duplicates: int = Field(default=0, description="Duplicates found within batch")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total_entities": 10,
                "created_count": 7,
                "updated_count": 2,
                "merged_count": 1,
                "failed_count": 0,
                "total_processing_time_ms": 234.5,
                "within_batch_duplicates": 2
            }
        }


class EntitySearchRequest(BaseModel):
    """
    Request model for entity search operations.

    Supports text search, type filtering, and tenant isolation.
    """
    query: str = Field(description="Search query text")

    # Filters
    entity_types: Optional[List[str]] = Field(default=None, description="Filter by entity types")
    client_id: Optional[str] = Field(default=None, description="Filter by client ID")
    case_id: Optional[str] = Field(default=None, description="Filter by case ID")

    # Pagination
    limit: int = Field(default=50, ge=1, le=500, description="Maximum results to return")
    offset: int = Field(default=0, ge=0, description="Results offset for pagination")

    # Search options
    exact_match: bool = Field(default=False, description="Require exact text match")
    include_public: bool = Field(default=True, description="Include public entities (client_id is NULL)")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Supreme Court",
                "entity_types": ["COURT"],
                "client_id": None,
                "limit": 50,
                "exact_match": False,
                "include_public": True
            }
        }


class EntitySearchResponse(BaseModel):
    """Response model for entity search operations."""
    success: bool = Field(description="Operation success status")
    query: str = Field(description="Original search query")

    # Results
    results: List[Dict[str, Any]] = Field(description="Search results (node records)")
    count: int = Field(description="Number of results returned")
    total_count: Optional[int] = Field(default=None, description="Total matching entities (if available)")

    # Pagination
    has_more: bool = Field(default=False, description="More results available")
    offset: int = Field(description="Current offset")
    limit: int = Field(description="Current limit")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "query": "Supreme Court",
                "results": [
                    {
                        "node_id": "entity_a1b2c3d4e5f6",
                        "title": "Supreme Court of the United States",
                        "node_type": "entity",
                        "description": "Judicial body"
                    }
                ],
                "count": 1,
                "has_more": False
            }
        }


class EntityCheckRequest(BaseModel):
    """
    Request model for batch entity existence checking.

    Efficiently check if multiple entities already exist in the database.
    """
    entities: List[Dict[str, str]] = Field(
        description="List of entities with 'entity_text' and 'entity_type' fields"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "entities": [
                    {"entity_text": "Supreme Court", "entity_type": "COURT"},
                    {"entity_text": "Judge Roberts", "entity_type": "JUDGE"}
                ]
            }
        }


class EntityCheckResponse(BaseModel):
    """Response model for batch entity existence checking."""
    success: bool = Field(description="Operation success status")
    total_checked: int = Field(description="Total entities checked")

    # Results
    exists: List[Dict[str, Any]] = Field(
        default=[],
        description="Entities that exist (with node_id and details)"
    )
    missing: List[Dict[str, Any]] = Field(
        default=[],
        description="Entities that don't exist (with computed entity_id)"
    )

    # Summary
    exists_count: int = Field(description="Number of existing entities")
    missing_count: int = Field(description="Number of missing entities")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total_checked": 2,
                "exists": [
                    {
                        "entity_text": "Supreme Court",
                        "entity_type": "COURT",
                        "node_id": "entity_a1b2c3d4e5f6",
                        "exists": True
                    }
                ],
                "missing": [
                    {
                        "entity_text": "Judge Roberts",
                        "entity_type": "JUDGE",
                        "entity_id": "entity_b2c3d4e5f6a1",
                        "exists": False
                    }
                ],
                "exists_count": 1,
                "missing_count": 1
            }
        }
