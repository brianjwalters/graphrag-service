"""
GraphRAG Service Configuration
Port 8010 - Knowledge Graph Construction Service
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class GraphRAGSettings(BaseSettings):
    """GraphRAG Service configuration with Microsoft GraphRAG methodology parameters."""
    
    # Service configuration
    service_name: str = "graphrag-service"
    service_port: int = 8010
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # API configuration
    api_prefix: str = "/api/v1"
    cors_origins: list = ["*"]
    
    # GraphRAG algorithm parameters (Microsoft GraphRAG paper)
    entity_similarity_threshold: float = 0.85  # Threshold for entity deduplication
    min_community_size: int = 3  # Minimum entities for a valid community
    max_community_size: int = 50  # Maximum entities per community
    leiden_resolution: float = 1.0  # Leiden algorithm resolution parameter
    community_coherence_threshold: float = 0.7  # Minimum coherence for community
    
    # Legal specialization parameters
    legal_entity_boost: float = 1.2  # Boost for legal entity matching
    citation_relationship_weight: float = 2.0  # Weight for citation relationships
    court_hierarchy_weight: float = 1.5  # Weight for court hierarchy relationships
    
    # Performance parameters
    batch_size: int = 100  # Batch size for bulk operations
    max_graph_nodes: int = 10000  # Maximum nodes in a single graph
    max_graph_edges: int = 50000  # Maximum edges in a single graph
    processing_timeout: int = 120  # Timeout in seconds for graph processing
    
    # Quality metrics thresholds
    min_graph_completeness: float = 0.5  # Minimum acceptable completeness
    min_entity_confidence: float = 0.6  # Minimum confidence for entity inclusion
    min_relationship_confidence: float = 0.5  # Minimum confidence for relationship
    
    # Service dependencies
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_API_KEY", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    max_connections: int = int(os.getenv("SUPABASE_MAX_CONNECTIONS", "30"))
    
    prompt_service_url: str = os.getenv("PROMPT_SERVICE_URL", "http://localhost:8003")
    log_service_url: str = os.getenv("LOG_SERVICE_URL", "http://localhost:8001")
    
    # Caching configuration
    enable_cache: bool = True
    cache_ttl: int = 3600  # Cache TTL in seconds
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9010
    
    model_config = {
        "case_sensitive": False,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


def get_settings() -> GraphRAGSettings:
    """Get GraphRAG service settings."""
    return GraphRAGSettings()