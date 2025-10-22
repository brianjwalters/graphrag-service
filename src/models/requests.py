"""
GraphRAG Service Request Models
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class GraphOptions(BaseModel):
    """Options for graph construction."""
    enable_deduplication: bool = Field(default=True, description="Enable entity deduplication")
    enable_community_detection: bool = Field(default=True, description="Enable community detection")
    enable_cross_document_linking: bool = Field(default=True, description="Enable cross-document relationship discovery")
    enable_analytics: bool = Field(default=True, description="Enable graph analytics computation")
    
    similarity_threshold: Optional[float] = Field(default=None, description="Override default similarity threshold")
    leiden_resolution: Optional[float] = Field(default=None, description="Override Leiden algorithm resolution")
    min_community_size: Optional[int] = Field(default=None, description="Override minimum community size")
    
    focus_entity_types: Optional[List[str]] = Field(default=None, description="Focus on specific entity types")
    exclude_entity_types: Optional[List[str]] = Field(default=None, description="Exclude specific entity types")
    
    use_ai_summaries: bool = Field(default=True, description="Generate AI summaries for communities")
    batch_mode: bool = Field(default=False, description="Process in batch mode for large datasets")


class EntityData(BaseModel):
    """Entity data from entity extraction."""
    entity_id: str = Field(description="Unique entity identifier")
    entity_text: str = Field(description="Entity text")
    entity_type: str = Field(description="Entity type (PARTY, COURT, etc.)")
    confidence: float = Field(default=0.95, description="Extraction confidence")
    attributes: Optional[Dict[str, Any]] = Field(default=None, description="Additional entity attributes")
    source_chunk_id: Optional[str] = Field(default=None, description="Source chunk identifier")


class CitationData(BaseModel):
    """Citation data from citation extraction."""
    citation_id: str = Field(description="Unique citation identifier")
    citation_text: str = Field(description="Citation text")
    citation_type: str = Field(description="Citation type (case, statute, etc.)")
    is_valid: bool = Field(default=True, description="Citation validity")
    bluebook_format: Optional[str] = Field(default=None, description="Bluebook formatted citation")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Citation metadata")


class RelationshipData(BaseModel):
    """Relationship data from entity extraction."""
    relationship_id: str = Field(description="Unique relationship identifier")
    source_entity: str = Field(description="Source entity ID")
    target_entity: str = Field(description="Target entity ID")
    relationship_type: str = Field(description="Relationship type")
    confidence: float = Field(default=0.8, description="Relationship confidence")
    attributes: Optional[Dict[str, Any]] = Field(default=None, description="Relationship attributes")


class EnhancedChunkData(BaseModel):
    """Enhanced chunk data with context."""
    chunk_id: str = Field(description="Unique chunk identifier")
    content: str = Field(description="Chunk content")
    contextualized_content: Optional[str] = Field(default=None, description="Content with added context")
    chunk_index: int = Field(description="Chunk position in document")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Chunk metadata")


class CreateGraphRequest(BaseModel):
    """Request to create a knowledge graph for a document."""
    document_id: str = Field(description="Document identifier")
    client_id: Optional[str] = Field(default=None, description="Client identifier")
    case_id: Optional[str] = Field(default=None, description="Case identifier")
    
    markdown_content: str = Field(description="Document content in markdown")
    entities: List[EntityData] = Field(description="Extracted entities")
    citations: List[CitationData] = Field(default=[], description="Extracted citations")
    relationships: List[RelationshipData] = Field(default=[], description="Extracted relationships")
    enhanced_chunks: List[EnhancedChunkData] = Field(default=[], description="Enhanced document chunks")
    
    graph_options: GraphOptions = Field(default_factory=GraphOptions, description="Graph construction options")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional document metadata")


class UpdateGraphRequest(BaseModel):
    """Request to update an existing graph with new data."""
    graph_id: str = Field(description="Existing graph identifier")
    document_id: str = Field(description="New document to add")
    
    entities: List[EntityData] = Field(description="New entities to add")
    relationships: List[RelationshipData] = Field(default=[], description="New relationships")
    
    merge_strategy: str = Field(default="smart", description="Merge strategy: smart, replace, append")
    graph_options: GraphOptions = Field(default_factory=GraphOptions, description="Update options")


class QueryGraphRequest(BaseModel):
    """Request to query the knowledge graph with tenant filtering."""
    query_type: str = Field(description="Query type: entities, relationships, communities, analytics")
    
    client_id: Optional[str] = Field(default=None, description="Client identifier for tenant filtering")
    case_id: Optional[str] = Field(default=None, description="Case identifier for case-specific filtering")
    
    entity_ids: Optional[List[str]] = Field(default=None, description="Specific entity IDs to query")
    document_ids: Optional[List[str]] = Field(default=None, description="Filter by document IDs")
    entity_types: Optional[List[str]] = Field(default=None, description="Filter by entity types")
    
    max_hops: int = Field(default=2, description="Maximum hops for graph traversal")
    limit: int = Field(default=100, description="Maximum results to return")
    
    include_analytics: bool = Field(default=False, description="Include graph analytics")
    include_communities: bool = Field(default=False, description="Include community information")
    include_public: bool = Field(default=False, description="Include public entities in results")