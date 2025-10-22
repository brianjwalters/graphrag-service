"""
GraphRAG Service Response Models
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class GraphSummary(BaseModel):
    """Summary statistics for the constructed graph."""
    nodes_created: int = Field(description="Number of nodes created")
    edges_created: int = Field(description="Number of edges created")
    communities_detected: int = Field(description="Number of communities detected")
    deduplication_rate: float = Field(description="Entity deduplication rate (0-1)")
    graph_density: float = Field(description="Graph density metric")
    processing_time_seconds: float = Field(description="Total processing time")


class QualityMetrics(BaseModel):
    """Quality metrics for the constructed graph."""
    graph_completeness: float = Field(description="Graph completeness score (0-1)")
    community_coherence: float = Field(description="Average community coherence")
    entity_confidence_avg: float = Field(description="Average entity confidence")
    relationship_confidence_avg: float = Field(description="Average relationship confidence")
    coverage_score: float = Field(description="Entity coverage score")
    
    warnings: List[str] = Field(default=[], description="Quality warnings")
    suggestions: List[str] = Field(default=[], description="Improvement suggestions")


class CommunityInfo(BaseModel):
    """Information about a detected community."""
    community_id: str = Field(description="Unique community identifier")
    description: str = Field(description="Community description")
    entity_count: int = Field(description="Number of entities in community")
    coherence_score: float = Field(description="Community coherence score (0-1)")
    
    entity_ids: List[str] = Field(description="Entity IDs in this community")
    central_entities: List[str] = Field(default=[], description="Most central entities")
    community_type: Optional[str] = Field(default=None, description="Type of community (legal, contract, etc.)")
    
    ai_summary: Optional[str] = Field(default=None, description="AI-generated community summary")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional community metadata")


class GraphAnalytics(BaseModel):
    """Advanced graph analytics results."""
    top_entities: List[Dict[str, Any]] = Field(description="Top entities by centrality")
    relationship_types: Dict[str, int] = Field(description="Relationship type distribution")
    cross_document_connections: int = Field(description="Number of cross-document connections")
    
    entity_type_distribution: Dict[str, int] = Field(default={}, description="Entity type counts")
    average_degree: float = Field(default=0.0, description="Average node degree")
    clustering_coefficient: float = Field(default=0.0, description="Graph clustering coefficient")
    
    legal_metrics: Optional[Dict[str, Any]] = Field(default=None, description="Legal-specific metrics")
    temporal_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Temporal relationship analysis")


class DeduplicationResult(BaseModel):
    """Result of entity deduplication."""
    original_count: int = Field(description="Original entity count")
    deduplicated_count: int = Field(description="Count after deduplication")
    merge_operations: int = Field(description="Number of merge operations")
    
    merged_entities: List[Dict[str, Any]] = Field(default=[], description="Merged entity details")
    canonical_mappings: Dict[str, str] = Field(default={}, description="Entity ID mappings")


class CreateGraphResponse(BaseModel):
    """Response from graph creation."""
    success: bool = Field(description="Operation success status")
    graph_id: str = Field(description="Unique graph identifier")
    document_id: str = Field(description="Processed document ID")
    
    graph_summary: GraphSummary = Field(description="Graph construction summary")
    quality_metrics: QualityMetrics = Field(description="Quality assessment metrics")
    communities: List[CommunityInfo] = Field(default=[], description="Detected communities")
    analytics: Optional[GraphAnalytics] = Field(default=None, description="Graph analytics")
    
    deduplication: Optional[DeduplicationResult] = Field(default=None, description="Deduplication results")
    
    storage_info: Dict[str, Any] = Field(default={}, description="Database storage information")
    processing_metadata: Dict[str, Any] = Field(default={}, description="Processing metadata")
    
    errors: List[str] = Field(default=[], description="Non-fatal errors encountered")
    warnings: List[str] = Field(default=[], description="Processing warnings")


class UpdateGraphResponse(BaseModel):
    """Response from graph update."""
    success: bool = Field(description="Operation success status")
    graph_id: str = Field(description="Updated graph identifier")
    
    nodes_added: int = Field(description="New nodes added")
    edges_added: int = Field(description="New edges added")
    communities_updated: int = Field(description="Communities updated")
    
    quality_metrics: QualityMetrics = Field(description="Updated quality metrics")
    deduplication: Optional[DeduplicationResult] = Field(default=None, description="Deduplication results")
    
    processing_time_seconds: float = Field(description="Update processing time")


class QueryGraphResponse(BaseModel):
    """Response from graph query."""
    query_type: str = Field(description="Type of query executed")
    result_count: int = Field(description="Number of results returned")
    
    entities: Optional[List[Dict[str, Any]]] = Field(default=None, description="Entity results")
    relationships: Optional[List[Dict[str, Any]]] = Field(default=None, description="Relationship results")
    communities: Optional[List[CommunityInfo]] = Field(default=None, description="Community results")
    analytics: Optional[GraphAnalytics] = Field(default=None, description="Analytics results")
    
    graph_context: Optional[Dict[str, Any]] = Field(default=None, description="Graph context information")
    query_metadata: Dict[str, Any] = Field(default={}, description="Query execution metadata")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(description="Service health status")
    service: str = Field(default="graphrag-service", description="Service name")
    version: str = Field(default="1.0.0", description="Service version")
    
    dependencies: Dict[str, str] = Field(description="Dependency health status")
    metrics: Optional[Dict[str, Any]] = Field(default=None, description="Service metrics")
    
    graph_stats: Optional[Dict[str, Any]] = Field(default=None, description="Graph database statistics")