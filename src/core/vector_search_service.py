"""
Vector Search Service for GraphRAG
Provides semantic search capabilities using pgvector embeddings
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import structlog

from .config import GraphRAGSettings
from ..clients.supabase_client import SupabaseClient

logger = structlog.get_logger(__name__)


class SearchType(Enum):
    """Search type enumeration."""
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    LOCAL = "local"
    GLOBAL = "global"


class SearchScope(Enum):
    """Search scope enumeration."""
    NODES = "nodes"
    CHUNKS = "chunks"
    COMMUNITIES = "communities"
    ALL = "all"


@dataclass
class SearchQuery:
    """Vector search query parameters."""
    query_text: str
    client_id: str
    search_type: SearchType = SearchType.SEMANTIC
    search_scope: SearchScope = SearchScope.CHUNKS
    limit: int = 10
    similarity_threshold: float = 0.7
    include_metadata: bool = True
    filters: Optional[Dict[str, Any]] = None
    rerank: bool = True
    alpha: float = 0.5  # For hybrid search (0.5 = equal weight)


@dataclass
class SearchResult:
    """Search result container."""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    search_type: SearchType
    matched_fields: List[str]
    created_at: datetime


@dataclass
class GraphRAGSearchResult:
    """GraphRAG search result with context."""
    query: str
    results: List[SearchResult]
    total_results: int
    search_metadata: Dict[str, Any]
    communities_involved: List[str]
    entity_matches: List[Dict[str, Any]]
    reasoning_chain: Optional[List[str]] = None
    quality_score: float = 0.0
    search_time_ms: float = 0.0


class VectorSearchService:
    """
    Vector Search Service for GraphRAG.
    
    Provides semantic search capabilities over knowledge graphs using:
    - pgvector for high-dimensional similarity search
    - Hybrid search combining semantic and keyword matching
    - Local search within specific communities
    - Global search across the entire knowledge graph
    - Multi-tenant filtering with client_id isolation
    """

    def __init__(self, settings: GraphRAGSettings):
        self.settings = settings
        self.supabase_client: Optional[SupabaseClient] = None
        self.is_initialized = False
        
        # Performance tracking
        self.total_searches = 0
        self.avg_search_time = 0.0
        self.cache_hit_rate = 0.0
        
        # Search caches
        self._query_cache: Dict[str, GraphRAGSearchResult] = {}
        self._embedding_cache: Dict[str, List[float]] = {}
        
        logger.info("VectorSearchService initialized",
                   similarity_threshold=settings.entity_similarity_threshold)

    async def initialize(self, supabase_client: SupabaseClient) -> None:
        """Initialize the Vector Search Service."""
        try:
            logger.info("🔍 Initializing Vector Search Service")
            
            self.supabase_client = supabase_client
            
            # Verify vector search functions are available
            await self._verify_vector_functions()
            
            # Warm up search indices
            if self.settings.enable_cache:
                await self._warm_search_indices()
            
            self.is_initialized = True
            logger.info("✅ Vector Search Service initialized successfully")
            
        except Exception as e:
            logger.error("❌ Vector Search Service initialization failed", error=str(e))
            raise

    async def search(self, query: SearchQuery) -> GraphRAGSearchResult:
        """
        Perform vector search based on query type.
        
        Args:
            query: Search query parameters
            
        Returns:
            GraphRAGSearchResult with semantic matches and context
        """
        start_time = time.time()
        
        try:
            logger.info("🔍 Executing vector search",
                       query_text=query.query_text[:100],
                       client_id=query.client_id,
                       search_type=query.search_type.value,
                       search_scope=query.search_scope.value)
            
            # Check cache first
            cache_key = self._build_cache_key(query)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                self._update_metrics(start_time, cache_hit=True)
                return cached_result
            
            # Route to appropriate search method
            if query.search_type == SearchType.SEMANTIC:
                results = await self._semantic_search(query)
            elif query.search_type == SearchType.HYBRID:
                results = await self._hybrid_search(query)
            elif query.search_type == SearchType.LOCAL:
                results = await self._local_search(query)
            elif query.search_type == SearchType.GLOBAL:
                results = await self._global_search(query)
            else:
                raise ValueError(f"Unsupported search type: {query.search_type}")
            
            # Get involved communities
            communities_involved = await self._get_involved_communities(results, query.client_id)
            
            # Extract entity matches
            entity_matches = await self._extract_entity_matches(results, query.client_id)
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(results, query)
            
            # Build final result
            search_result = GraphRAGSearchResult(
                query=query.query_text,
                results=results,
                total_results=len(results),
                search_metadata={
                    "search_type": query.search_type.value,
                    "search_scope": query.search_scope.value,
                    "similarity_threshold": query.similarity_threshold,
                    "filters": query.filters or {},
                    "client_id": query.client_id
                },
                communities_involved=communities_involved,
                entity_matches=entity_matches,
                quality_score=quality_score,
                search_time_ms=(time.time() - start_time) * 1000
            )
            
            # Cache the result
            if self.settings.enable_cache:
                self._add_to_cache(cache_key, search_result)
            
            self._update_metrics(start_time, cache_hit=False)
            self.total_searches += 1
            
            logger.info("✅ Vector search completed",
                       results_count=len(results),
                       quality_score=quality_score,
                       search_time_ms=search_result.search_time_ms,
                       communities_count=len(communities_involved))
            
            return search_result
            
        except Exception as e:
            logger.error("❌ Vector search failed",
                        query_text=query.query_text[:100],
                        client_id=query.client_id,
                        error=str(e))
            raise

    async def semantic_search_chunks(
        self,
        client_id: str,
        query_text: str,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[SearchResult]:
        """
        Perform semantic search on document chunks.
        
        Args:
            client_id: Client identifier for multi-tenancy
            query_text: Query text to search for
            limit: Maximum number of results
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            List of matching chunks with similarity scores
        """
        try:
            logger.info("🔍 Semantic chunk search",
                       client_id=client_id,
                       query=query_text[:50],
                       limit=limit,
                       threshold=similarity_threshold)
            
            # Get query embedding (placeholder - would integrate with embedding service)
            query_embedding = await self._get_query_embedding(query_text)
            
            # Execute semantic search function
            search_params = {
                "query_embedding": query_embedding,
                "filter_client_id": client_id,
                "match_threshold": similarity_threshold,
                "match_count": limit
            }
            
            results = await self.supabase_client.execute_function(
                "search_similar_chunks",
                search_params
            )
            
            # Convert to SearchResult objects
            search_results = []
            for row in results:
                search_results.append(SearchResult(
                    id=row["id"],
                    content=row["content"],
                    score=float(row["similarity"]),
                    metadata={
                        "document_id": row["document_id"],
                        "chunk_index": row["chunk_index"],
                        "embedding_model": row.get("embedding_model", "unknown"),
                        "created_at": row["created_at"]
                    },
                    search_type=SearchType.SEMANTIC,
                    matched_fields=["content"],
                    created_at=datetime.fromisoformat(row["created_at"])
                ))
            
            logger.info("✅ Semantic chunk search completed",
                       client_id=client_id,
                       results_count=len(search_results))
            
            return search_results
            
        except Exception as e:
            logger.error("❌ Semantic chunk search failed",
                        client_id=client_id,
                        query=query_text[:50],
                        error=str(e))
            raise

    async def hybrid_search_with_ranking(
        self,
        client_id: str,
        query_text: str,
        limit: int = 10,
        alpha: float = 0.5
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining semantic and keyword search.
        
        Args:
            client_id: Client identifier
            query_text: Query text
            limit: Maximum results
            alpha: Weight between semantic (1.0) and keyword (0.0) search
            
        Returns:
            List of results ranked using Reciprocal Rank Fusion
        """
        try:
            logger.info("🔍 Hybrid search with RRF",
                       client_id=client_id,
                       query=query_text[:50],
                       alpha=alpha)
            
            # Get query embedding
            query_embedding = await self._get_query_embedding(query_text)
            
            # Execute hybrid search function
            search_params = {
                "query_text": query_text,
                "query_embedding": query_embedding,
                "client_id": client_id,
                "keyword_weight": 1.0 - alpha,  # Convert alpha to keyword weight
                "semantic_weight": alpha,  # Semantic weight
                "match_count": limit
            }
            
            results = await self.supabase_client.execute_function(
                "hybrid_search",
                search_params
            )
            
            # Convert to SearchResult objects
            search_results = []
            for row in results:
                search_results.append(SearchResult(
                    id=row["id"],
                    content=row["content"],
                    score=float(row["combined_score"]),
                    metadata={
                        "document_id": row["document_id"],
                        "semantic_score": row["semantic_score"],
                        "keyword_score": row["keyword_score"],
                        "rrf_score": row["rrf_score"],
                        "alpha": alpha
                    },
                    search_type=SearchType.HYBRID,
                    matched_fields=["content"],
                    created_at=datetime.fromisoformat(row["created_at"])
                ))
            
            logger.info("✅ Hybrid search completed",
                       client_id=client_id,
                       results_count=len(search_results))
            
            return search_results
            
        except Exception as e:
            logger.error("❌ Hybrid search failed",
                        client_id=client_id,
                        error=str(e))
            raise

    async def local_community_search(
        self,
        client_id: str,
        query_text: str,
        community_id: Optional[str] = None,
        limit: int = 10
    ) -> List[SearchResult]:
        """
        Perform local search within specific communities.
        
        Args:
            client_id: Client identifier
            query_text: Query text
            community_id: Specific community to search (if None, searches all)
            limit: Maximum results
            
        Returns:
            List of community-scoped search results
        """
        try:
            logger.info("🔍 Local community search",
                       client_id=client_id,
                       community_id=community_id,
                       query=query_text[:50])
            
            # Get query embedding
            query_embedding = await self._get_query_embedding(query_text)
            
            # Execute local search function
            search_params = {
                "query_embedding": query_embedding,
                "client_id": client_id,
                "document_id": None,  # No document filter
                "entity_id": community_id,  # Using entity_id for community filtering
                "match_count": limit
            }
            
            results = await self.supabase_client.execute_function(
                "local_search",
                search_params
            )
            
            # Convert to SearchResult objects
            search_results = []
            for row in results:
                search_results.append(SearchResult(
                    id=row["id"],
                    content=row["content"],
                    score=float(row["similarity"]),
                    metadata={
                        "community_id": row["community_id"],
                        "entity_type": row.get("entity_type"),
                        "relationship_count": row.get("relationship_count", 0)
                    },
                    search_type=SearchType.LOCAL,
                    matched_fields=["content"],
                    created_at=datetime.fromisoformat(row.get("created_at", datetime.utcnow().isoformat()))
                ))
            
            logger.info("✅ Local community search completed",
                       client_id=client_id,
                       community_id=community_id,
                       results_count=len(search_results))
            
            return search_results
            
        except Exception as e:
            logger.error("❌ Local community search failed",
                        client_id=client_id,
                        community_id=community_id,
                        error=str(e))
            raise

    async def global_knowledge_search(
        self,
        client_id: str,
        query_text: str,
        limit: int = 10,
        include_reasoning: bool = True
    ) -> GraphRAGSearchResult:
        """
        Perform global search across the entire knowledge graph.
        
        Args:
            client_id: Client identifier
            query_text: Query text
            limit: Maximum results
            include_reasoning: Whether to include reasoning chain
            
        Returns:
            Comprehensive GraphRAG search result with global context
        """
        try:
            logger.info("🔍 Global knowledge search",
                       client_id=client_id,
                       query=query_text[:50],
                       include_reasoning=include_reasoning)
            
            start_time = time.time()
            
            # Get query embedding
            query_embedding = await self._get_query_embedding(query_text)
            
            # Execute global search function
            search_params = {
                "query_embedding": query_embedding,
                "client_id": client_id,
                "max_results": limit
            }
            
            results = await self.supabase_client.execute_function(
                "global_search",
                search_params
            )
            
            # Process results
            search_results = []
            communities_involved = set()
            entity_matches = []
            
            for row in results:
                # Add to search results
                search_results.append(SearchResult(
                    id=row["id"],
                    content=row["content"],
                    score=float(row["relevance_score"]),
                    metadata={
                        "source_type": row["source_type"],
                        "entity_count": row.get("entity_count", 0),
                        "relationship_count": row.get("relationship_count", 0),
                        "community_relevance": row.get("community_relevance", 0.0)
                    },
                    search_type=SearchType.GLOBAL,
                    matched_fields=row.get("matched_fields", ["content"]),
                    created_at=datetime.fromisoformat(row.get("created_at", datetime.utcnow().isoformat()))
                ))
                
                # Collect communities
                if row.get("community_id"):
                    communities_involved.add(row["community_id"])
                
                # Collect entity matches
                if row.get("entities"):
                    for entity in row["entities"]:
                        entity_matches.append({
                            "entity_id": entity["id"],
                            "entity_name": entity["name"],
                            "entity_type": entity["type"],
                            "relevance_score": entity.get("relevance", 0.0)
                        })
            
            # Generate reasoning chain if requested
            reasoning_chain = None
            if include_reasoning and search_results:
                reasoning_chain = await self._generate_reasoning_chain(
                    query_text, search_results[:5], client_id
                )
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(search_results, SearchQuery(
                query_text=query_text,
                client_id=client_id,
                search_type=SearchType.GLOBAL,
                limit=limit
            ))
            
            result = GraphRAGSearchResult(
                query=query_text,
                results=search_results,
                total_results=len(search_results),
                search_metadata={
                    "search_type": "global",
                    "client_id": client_id,
                    "include_reasoning": include_reasoning,
                    "embedding_dimensions": 2048  # Jina v4 embeddings
                },
                communities_involved=list(communities_involved),
                entity_matches=entity_matches,
                reasoning_chain=reasoning_chain,
                quality_score=quality_score,
                search_time_ms=(time.time() - start_time) * 1000
            )
            
            logger.info("✅ Global knowledge search completed",
                       client_id=client_id,
                       results_count=len(search_results),
                       communities_count=len(communities_involved),
                       entities_count=len(entity_matches),
                       quality_score=quality_score)
            
            return result
            
        except Exception as e:
            logger.error("❌ Global knowledge search failed",
                        client_id=client_id,
                        error=str(e))
            raise

    # Private helper methods
    
    async def _semantic_search(self, query: SearchQuery) -> List[SearchResult]:
        """Execute semantic search."""
        if query.search_scope == SearchScope.CHUNKS:
            return await self.semantic_search_chunks(
                query.client_id,
                query.query_text,
                query.limit,
                query.similarity_threshold
            )
        else:
            # Implement other scopes as needed
            return await self.semantic_search_chunks(
                query.client_id,
                query.query_text,
                query.limit,
                query.similarity_threshold
            )
    
    async def _hybrid_search(self, query: SearchQuery) -> List[SearchResult]:
        """Execute hybrid search."""
        return await self.hybrid_search_with_ranking(
            query.client_id,
            query.query_text,
            query.limit,
            query.alpha
        )
    
    async def _local_search(self, query: SearchQuery) -> List[SearchResult]:
        """Execute local community search."""
        community_id = query.filters.get("community_id") if query.filters else None
        return await self.local_community_search(
            query.client_id,
            query.query_text,
            community_id,
            query.limit
        )
    
    async def _global_search(self, query: SearchQuery) -> List[SearchResult]:
        """Execute global search."""
        result = await self.global_knowledge_search(
            query.client_id,
            query.query_text,
            query.limit,
            include_reasoning=False
        )
        return result.results
    
    async def _get_query_embedding(self, query_text: str) -> List[float]:
        """Get embedding for query text (placeholder for embeddings service integration)."""
        # Cache check
        if query_text in self._embedding_cache:
            return self._embedding_cache[query_text]
        
        # This would integrate with the embeddings service (port 8081)
        # For now, return a placeholder embedding vector
        embedding = [0.0] * 1536  # Changed to 1536 dimensions for Supabase compatibility
        
        # Cache the result
        self._embedding_cache[query_text] = embedding
        
        return embedding
    
    async def _verify_vector_functions(self) -> None:
        """Verify that required vector search functions exist."""
        functions_to_check = [
            "search_similar_chunks",
            "hybrid_search", 
            "local_search",
            "global_search"
        ]
        
        for func_name in functions_to_check:
            try:
                # Test function existence by calling with minimal parameters
                await self.supabase_client.execute_function(func_name, {})
            except Exception as e:
                if "function" in str(e).lower() and "does not exist" in str(e).lower():
                    logger.warning(f"Vector function {func_name} not available: {str(e)}")
                # Other errors are fine - function exists but parameters were invalid
    
    async def _warm_search_indices(self) -> None:
        """Warm up search indices for better performance."""
        try:
            # Warm up vector index
            logger.info("🔥 Warming up vector search indices")
            
            # Execute a sample query to warm caches
            sample_embedding = [0.1] * 1536  # Changed to 1536 dimensions for Supabase
            await self.supabase_client.execute_function(
                "search_similar_chunks",
                {
                    "query_embedding": sample_embedding,
                    "filter_client_id": "warmup",
                    "match_threshold": 0.9,
                    "match_count": 1
                }
            )
            
            logger.info("✅ Vector search indices warmed")
            
        except Exception as e:
            logger.warning("⚠️ Index warming failed", error=str(e))
    
    async def _get_involved_communities(self, results: List[SearchResult], client_id: str) -> List[str]:
        """Get communities involved in search results."""
        communities = set()
        
        for result in results:
            if result.metadata.get("community_id"):
                communities.add(result.metadata["community_id"])
        
        return list(communities)
    
    async def _extract_entity_matches(self, results: List[SearchResult], client_id: str) -> List[Dict[str, Any]]:
        """Extract entity matches from search results."""
        entities = []
        
        for result in results:
            if result.metadata.get("entity_type"):
                entities.append({
                    "entity_id": result.id,
                    "entity_type": result.metadata["entity_type"],
                    "relevance_score": result.score
                })
        
        return entities
    
    async def _generate_reasoning_chain(
        self,
        query: str,
        results: List[SearchResult],
        client_id: str
    ) -> List[str]:
        """Generate reasoning chain for global search results."""
        reasoning = [
            f"Analyzed query: '{query}'",
            f"Found {len(results)} relevant results across knowledge graph",
            f"Results span multiple communities and entity types",
            f"Ranking based on semantic similarity and graph connectivity"
        ]
        
        if results:
            top_score = results[0].score
            reasoning.append(f"Top result has {top_score:.3f} relevance score")
        
        return reasoning
    
    def _calculate_quality_score(self, results: List[SearchResult], query: SearchQuery) -> float:
        """Calculate search quality score."""
        if not results:
            return 0.0
        
        # Base score from result scores
        avg_score = sum(r.score for r in results) / len(results)
        
        # Adjust based on number of results vs requested limit
        completeness = min(len(results) / query.limit, 1.0)
        
        # Adjust based on score distribution (diversity penalty)
        score_variance = 0.0
        if len(results) > 1:
            scores = [r.score for r in results]
            mean_score = sum(scores) / len(scores)
            score_variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
            diversity_factor = min(score_variance * 2, 0.2)  # Cap diversity bonus
        else:
            diversity_factor = 0.0
        
        quality_score = (avg_score * 0.7) + (completeness * 0.2) + diversity_factor
        
        return min(quality_score, 1.0)
    
    def _build_cache_key(self, query: SearchQuery) -> str:
        """Build cache key for search query."""
        filters_str = str(sorted(query.filters.items())) if query.filters else "none"
        return f"search:{query.client_id}:{query.search_type.value}:{query.query_text[:50]}:{filters_str}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[GraphRAGSearchResult]:
        """Get result from cache."""
        if not self.settings.enable_cache:
            return None
        
        return self._query_cache.get(cache_key)
    
    def _add_to_cache(self, cache_key: str, result: GraphRAGSearchResult) -> None:
        """Add result to cache."""
        if self.settings.enable_cache:
            self._query_cache[cache_key] = result
            
            # Simple cache size management
            if len(self._query_cache) > 1000:
                # Remove oldest entries
                keys_to_remove = list(self._query_cache.keys())[:100]
                for key in keys_to_remove:
                    del self._query_cache[key]
    
    def _update_metrics(self, start_time: float, cache_hit: bool) -> None:
        """Update performance metrics."""
        search_time = time.time() - start_time
        
        # Update rolling averages
        if cache_hit:
            self.cache_hit_rate = (self.cache_hit_rate * 0.9) + (1.0 * 0.1)
        else:
            self.cache_hit_rate = (self.cache_hit_rate * 0.9) + (0.0 * 0.1)
        
        self.avg_search_time = (self.avg_search_time * 0.9) + (search_time * 1000 * 0.1)

    @property
    def performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            "total_searches": self.total_searches,
            "avg_search_time_ms": self.avg_search_time,
            "cache_hit_rate": self.cache_hit_rate,
            "cache_size": len(self._query_cache),
            "embedding_cache_size": len(self._embedding_cache),
            "is_initialized": self.is_initialized
        }