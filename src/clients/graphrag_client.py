"""
GraphRAG Client for Service Integration

This client orchestrates interactions between the GraphRAG service and other services
in the document processing pipeline, including Entity Extraction, Chunking, and
Supabase services.
"""

import logging
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import httpx
from pydantic import BaseModel, Field

from .entity_client import EntityClient

logger = logging.getLogger(__name__)


class DocumentChunk(BaseModel):
    """Represents a document chunk with contextual layers."""
    chunk_id: str
    document_id: str
    chunk_index: int
    original_content: str
    contextual_content: Optional[str] = None
    bm25_content: Optional[str] = None
    cleaned_content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractedEntity(BaseModel):
    """Represents an extracted entity from the Entity Extraction Service."""
    entity_id: str
    entity_type: str
    text: str
    confidence: float
    start_position: int
    end_position: int
    chunk_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphNode(BaseModel):
    """Represents a node in the knowledge graph."""
    node_id: str
    entity_id: str
    entity_type: str
    entity_text: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    embeddings: Optional[List[float]] = None


class GraphEdge(BaseModel):
    """Represents an edge in the knowledge graph."""
    edge_id: str
    source_id: str
    target_id: str
    relationship_type: str
    confidence: float
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphRAGClient:
    """
    Main client for orchestrating GraphRAG operations across services.
    
    This client coordinates:
    - Document chunking with Anthropic contextualization
    - Entity extraction from chunks
    - Knowledge graph construction
    - Community detection and hierarchy
    - Graph persistence to Supabase
    """
    
    def __init__(
        self,
        graphrag_url: str = "http://localhost:8010",
        entity_service_url: str = "http://localhost:8007",
        chunking_service_url: str = "http://localhost:8009",
        supabase_service_url: str = "http://localhost:8002",
        timeout: float = 60.0
    ):
        """
        Initialize the GraphRAG client with service endpoints.
        
        Args:
            graphrag_url: URL of the GraphRAG service
            entity_service_url: URL of the Entity Extraction service
            chunking_service_url: URL of the Chunking service
            supabase_service_url: URL of the Supabase service
            timeout: Request timeout in seconds
        """
        self.graphrag_url = graphrag_url.rstrip("/")
        self.entity_service_url = entity_service_url.rstrip("/")
        self.chunking_service_url = chunking_service_url.rstrip("/")
        self.supabase_service_url = supabase_service_url.rstrip("/")
        self.timeout = timeout
        
        # Initialize service clients
        self.entity_client = EntityClient(base_url=entity_service_url)
        
        # HTTP client for direct API calls
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={"Content-Type": "application/json"}
        )
        
        logger.info("GraphRAG Client initialized with service endpoints")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close all client connections."""
        await self.entity_client.close()
        await self.client.aclose()
    
    async def process_document(
        self,
        document_id: str,
        content: str,
        document_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a document through the full GraphRAG pipeline.
        
        This orchestrates:
        1. Document chunking with Anthropic contextualization
        2. Entity extraction from chunks
        3. Knowledge graph construction
        4. Community detection
        5. Graph persistence
        
        Args:
            document_id: Unique document identifier
            content: Document content
            document_type: Type of document (e.g., "contract", "opinion")
            metadata: Additional document metadata
            
        Returns:
            Dict containing processing results and graph statistics
        """
        request_id = str(uuid.uuid4())
        logger.info(f"Processing document {document_id} with request {request_id}")
        
        try:
            # Step 1: Chunk document with Anthropic contextualization
            chunks = await self._chunk_document(
                document_id=document_id,
                content=content,
                document_type=document_type
            )
            logger.info(f"Created {len(chunks)} contextual chunks for document {document_id}")
            
            # Step 2: Extract entities from chunks
            entities = await self._extract_entities_from_chunks(
                chunks=chunks,
                document_id=document_id
            )
            logger.info(f"Extracted {len(entities)} entities from document {document_id}")
            
            # Step 3: Build knowledge graph
            graph_data = await self._build_knowledge_graph(
                document_id=document_id,
                chunks=chunks,
                entities=entities,
                metadata=metadata
            )
            logger.info(
                f"Built graph with {graph_data['node_count']} nodes and "
                f"{graph_data['edge_count']} edges for document {document_id}"
            )
            
            # Step 4: Detect communities
            communities = await self._detect_communities(
                document_id=document_id,
                graph_data=graph_data
            )
            logger.info(f"Detected {len(communities)} communities in document {document_id}")
            
            # Step 5: Persist to database
            await self._persist_graph(
                document_id=document_id,
                graph_data=graph_data,
                communities=communities
            )
            logger.info(f"Persisted graph for document {document_id} to database")
            
            return {
                "document_id": document_id,
                "request_id": request_id,
                "chunk_count": len(chunks),
                "entity_count": len(entities),
                "node_count": graph_data["node_count"],
                "edge_count": graph_data["edge_count"],
                "community_count": len(communities),
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}")
            raise
    
    async def _chunk_document(
        self,
        document_id: str,
        content: str,
        document_type: Optional[str] = None
    ) -> List[DocumentChunk]:
        """
        Chunk document using the Chunking Service with Anthropic contextualization.
        
        Args:
            document_id: Document identifier
            content: Document content
            document_type: Type of document
            
        Returns:
            List of document chunks with contextual layers
        """
        try:
            response = await self.client.post(
                f"{self.chunking_service_url}/api/v1/chunk",
                json={
                    "document_id": document_id,
                    "content": content,
                    "chunking_strategy": "anthropic_contextual",
                    "chunk_size": 8000,  # Large chunks for entity extraction
                    "chunk_overlap": 2000,  # Significant overlap
                    "enable_contextual_enhancement": True,
                    "document_type": document_type,
                    "metadata": {
                        "purpose": "entity_extraction",
                        "contextual_layers": ["original", "contextual", "bm25", "cleaned"]
                    }
                }
            )
            response.raise_for_status()
            
            chunks_data = response.json()
            chunks = []
            
            for chunk_data in chunks_data.get("chunks", []):
                chunk = DocumentChunk(
                    chunk_id=chunk_data["chunk_id"],
                    document_id=document_id,
                    chunk_index=chunk_data["chunk_index"],
                    original_content=chunk_data.get("original_content", chunk_data.get("content", "")),
                    contextual_content=chunk_data.get("contextual_content"),
                    bm25_content=chunk_data.get("bm25_content"),
                    cleaned_content=chunk_data.get("cleaned_content"),
                    metadata=chunk_data.get("metadata", {})
                )
                chunks.append(chunk)
            
            return chunks
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to chunk document: {e}")
            raise
    
    async def _extract_entities_from_chunks(
        self,
        chunks: List[DocumentChunk],
        document_id: str
    ) -> List[ExtractedEntity]:
        """
        Extract entities from document chunks using Entity Extraction Service.
        
        Args:
            chunks: List of document chunks
            document_id: Document identifier
            
        Returns:
            List of extracted entities
        """
        all_entities = []
        
        # Process chunks in parallel with concurrency limit
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent extractions
        
        async def extract_from_chunk(chunk: DocumentChunk):
            async with semaphore:
                try:
                    # Use contextual content for better extraction
                    content = chunk.contextual_content or chunk.original_content
                    
                    response = await self.client.post(
                        f"{self.entity_service_url}/api/v1/extract",
                        json={
                            "document_id": document_id,
                            "content": content,
                            "extraction_mode": "hybrid",
                            "context_window": 500,
                            "metadata": {
                                "chunk_id": chunk.chunk_id,
                                "chunk_index": chunk.chunk_index
                            }
                        }
                    )
                    response.raise_for_status()
                    
                    extraction_data = response.json()
                    entities = []
                    
                    for entity_data in extraction_data.get("entities", []):
                        entity = ExtractedEntity(
                            entity_id=str(uuid.uuid4()),
                            entity_type=entity_data["entity_type"],
                            text=entity_data["text"],
                            confidence=entity_data["confidence"],
                            start_position=entity_data["start_position"],
                            end_position=entity_data["end_position"],
                            chunk_id=chunk.chunk_id,
                            metadata=entity_data.get("metadata", {})
                        )
                        entities.append(entity)
                    
                    return entities
                    
                except Exception as e:
                    logger.error(f"Failed to extract entities from chunk {chunk.chunk_id}: {e}")
                    return []
        
        # Extract entities from all chunks in parallel
        tasks = [extract_from_chunk(chunk) for chunk in chunks]
        chunk_entities = await asyncio.gather(*tasks)
        
        # Flatten results
        for entities in chunk_entities:
            all_entities.extend(entities)
        
        # Deduplicate entities based on text and type
        seen = set()
        unique_entities = []
        for entity in all_entities:
            key = (entity.entity_type, entity.text.lower())
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        return unique_entities
    
    async def _build_knowledge_graph(
        self,
        document_id: str,
        chunks: List[DocumentChunk],
        entities: List[ExtractedEntity],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build knowledge graph from extracted entities.
        
        Args:
            document_id: Document identifier
            chunks: Document chunks
            entities: Extracted entities
            metadata: Document metadata
            
        Returns:
            Graph data with nodes and edges
        """
        try:
            response = await self.client.post(
                f"{self.graphrag_url}/api/v1/graph/build",
                json={
                    "document_id": document_id,
                    "chunks": [chunk.dict() for chunk in chunks],
                    "entities": [entity.dict() for entity in entities],
                    "metadata": metadata or {},
                    "config": {
                        "enable_embeddings": True,
                        "enable_relationship_extraction": True,
                        "min_confidence": 0.7,
                        "max_edges_per_node": 50
                    }
                }
            )
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to build knowledge graph: {e}")
            raise
    
    async def _detect_communities(
        self,
        document_id: str,
        graph_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Detect communities in the knowledge graph.
        
        Args:
            document_id: Document identifier
            graph_data: Graph data with nodes and edges
            
        Returns:
            List of detected communities
        """
        try:
            response = await self.client.post(
                f"{self.graphrag_url}/api/v1/graph/communities",
                json={
                    "document_id": document_id,
                    "graph_data": graph_data,
                    "config": {
                        "algorithm": "leiden",
                        "resolution": 1.0,
                        "min_community_size": 3,
                        "enable_hierarchy": True
                    }
                }
            )
            response.raise_for_status()
            
            return response.json().get("communities", [])
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to detect communities: {e}")
            raise
    
    async def _persist_graph(
        self,
        document_id: str,
        graph_data: Dict[str, Any],
        communities: List[Dict[str, Any]]
    ):
        """
        Persist graph data to database via Supabase service.
        
        Args:
            document_id: Document identifier
            graph_data: Graph data with nodes and edges
            communities: Detected communities
        """
        try:
            response = await self.client.post(
                f"{self.supabase_service_url}/api/v1/graph/persist",
                json={
                    "document_id": document_id,
                    "graph_data": graph_data,
                    "communities": communities,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            response.raise_for_status()
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to persist graph: {e}")
            raise
    
    async def query_graph(
        self,
        query: str,
        document_ids: Optional[List[str]] = None,
        entity_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Query the knowledge graph.
        
        Args:
            query: Search query
            document_ids: Filter by document IDs
            entity_types: Filter by entity types
            limit: Maximum results
            
        Returns:
            Query results with relevant nodes and relationships
        """
        try:
            # Validate entity types if provided
            if entity_types:
                validation = await self.entity_client.validate_entity_types(entity_types)
                invalid_types = [t for t, valid in validation.items() if not valid]
                if invalid_types:
                    logger.warning(f"Invalid entity types: {invalid_types}")
                    entity_types = [t for t, valid in validation.items() if valid]
            
            response = await self.client.post(
                f"{self.graphrag_url}/api/v1/graph/query",
                json={
                    "query": query,
                    "filters": {
                        "document_ids": document_ids,
                        "entity_types": entity_types
                    },
                    "limit": limit,
                    "include_communities": True,
                    "include_embeddings": False
                }
            )
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to query graph: {e}")
            raise
    
    async def get_graph_statistics(
        self,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about the knowledge graph.
        
        Args:
            document_id: Optional document ID to filter statistics
            
        Returns:
            Graph statistics
        """
        try:
            params = {}
            if document_id:
                params["document_id"] = document_id
            
            response = await self.client.get(
                f"{self.graphrag_url}/api/v1/graph/statistics",
                params=params
            )
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get graph statistics: {e}")
            raise
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all dependent services.
        
        Returns:
            Dict mapping service names to health status
        """
        health_status = {}
        
        # Check GraphRAG service
        try:
            response = await self.client.get(f"{self.graphrag_url}/api/v1/health")
            health_status["graphrag"] = response.status_code == 200
        except:
            health_status["graphrag"] = False
        
        # Check Entity Extraction service
        health_status["entity_extraction"] = await self.entity_client.health_check()
        
        # Check Chunking service
        try:
            response = await self.client.get(f"{self.chunking_service_url}/api/v1/health")
            health_status["chunking"] = response.status_code == 200
        except:
            health_status["chunking"] = False
        
        # Check Supabase service
        try:
            response = await self.client.get(f"{self.supabase_service_url}/api/v1/health")
            health_status["supabase"] = response.status_code == 200
        except:
            health_status["supabase"] = False
        
        return health_status


# Example usage
async def test_graphrag_client():
    """Test the GraphRAG client functionality."""
    async with GraphRAGClient() as client:
        # Check service health
        health = await client.health_check()
        print("Service Health Status:")
        for service, status in health.items():
            print(f"  {service}: {'✓' if status else '✗'}")
        
        # Process a sample document
        if all(health.values()):
            result = await client.process_document(
                document_id="test-doc-001",
                content="This is a test legal document...",
                document_type="contract",
                metadata={"source": "test"}
            )
            print(f"\nDocument processing result:")
            print(f"  Chunks: {result['chunk_count']}")
            print(f"  Entities: {result['entity_count']}")
            print(f"  Graph nodes: {result['node_count']}")
            print(f"  Graph edges: {result['edge_count']}")
            print(f"  Communities: {result['community_count']}")


if __name__ == "__main__":
    asyncio.run(test_graphrag_client())