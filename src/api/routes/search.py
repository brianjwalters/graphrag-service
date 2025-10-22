"""
GraphRAG API Routes - Vector Search and RAG
Provides endpoints for semantic search and retrieval-augmented generation
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse
import structlog

from ...core.vector_search_service import (
    VectorSearchService, SearchQuery, SearchType, SearchScope, 
    SearchResult, GraphRAGSearchResult
)
from ...core.rag_orchestrator import (
    RAGOrchestrator, RAGQuery, RAGMode, RAGResult, QueryIntent
)

logger = structlog.get_logger(__name__)
router = APIRouter()


# Request/Response Models

class VectorSearchRequest(BaseModel):
    """Vector search request model."""
    query_text: str = Field(..., description="Text to search for")
    client_id: str = Field(..., description="Client identifier for multi-tenancy")
    search_type: str = Field(default="semantic", description="Type of search to perform")
    search_scope: str = Field(default="chunks", description="Scope of search")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")
    include_metadata: bool = Field(default=True, description="Include result metadata")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional search filters")
    rerank: bool = Field(default=True, description="Apply reranking to results")
    alpha: float = Field(default=0.5, ge=0.0, le=1.0, description="Hybrid search weight (semantic vs keyword)")

    @validator("search_type")
    def validate_search_type(cls, v):
        valid_types = ["semantic", "hybrid", "local", "global"]
        if v not in valid_types:
            raise ValueError(f"Invalid search type. Must be one of: {valid_types}")
        return v

    @validator("search_scope")
    def validate_search_scope(cls, v):
        valid_scopes = ["nodes", "chunks", "communities", "all"]
        if v not in valid_scopes:
            raise ValueError(f"Invalid search scope. Must be one of: {valid_scopes}")
        return v


class RAGQueryRequest(BaseModel):
    """RAG query request model."""
    query_text: str = Field(..., description="Query text for RAG processing")
    client_id: str = Field(..., description="Client identifier")
    case_id: Optional[str] = Field(None, description="Specific case context")
    mode: str = Field(default="adaptive", description="RAG execution mode")
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum results to retrieve")
    include_context: bool = Field(default=True, description="Include context from Context Engine")
    include_reasoning: bool = Field(default=True, description="Include reasoning chain")
    quality_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Quality threshold")
    context_depth: int = Field(default=3, ge=1, le=10, description="Context traversal depth")
    search_types: Optional[List[str]] = Field(None, description="Preferred search types")

    @validator("mode")
    def validate_mode(cls, v):
        valid_modes = ["context_first", "retrieve_first", "parallel", "adaptive"]
        if v not in valid_modes:
            raise ValueError(f"Invalid mode. Must be one of: {valid_modes}")
        return v

    @validator("search_types")
    def validate_search_types(cls, v):
        if v is not None:
            valid_types = ["semantic", "hybrid", "local", "global"]
            for search_type in v:
                if search_type not in valid_types:
                    raise ValueError(f"Invalid search type '{search_type}'. Must be one of: {valid_types}")
        return v


class SearchResultResponse(BaseModel):
    """Search result response model."""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    search_type: str
    matched_fields: List[str]
    created_at: datetime


class GraphRAGSearchResponse(BaseModel):
    """GraphRAG search response model."""
    query: str
    results: List[SearchResultResponse]
    total_results: int
    search_metadata: Dict[str, Any]
    communities_involved: List[str]
    entity_matches: List[Dict[str, Any]]
    reasoning_chain: Optional[List[str]] = None
    quality_score: float
    search_time_ms: float


class RAGResponse(BaseModel):
    """RAG response model."""
    query: str
    intent: str
    mode_used: str
    context_data: Optional[Dict[str, Any]] = None
    context_quality: float
    retrieval_results: Optional[GraphRAGSearchResponse] = None
    retrieval_quality: float
    synthesized_response: Optional[str] = None
    evidence_chain: List[Dict[str, Any]]
    confidence_score: float
    total_time_ms: float
    context_time_ms: float
    retrieval_time_ms: float
    synthesis_time_ms: float
    metadata: Dict[str, Any]
    created_at: datetime


# Vector Search Endpoints

@router.post("/vector/search")
async def vector_search(request: Request, search_request: VectorSearchRequest):
    """
    Perform vector search on the knowledge graph.
    
    Provides semantic search capabilities using pgvector embeddings
    with support for multiple search types and scopes.
    """
    try:
        vector_search_service: VectorSearchService = request.app.state.vector_search_service
        
        logger.info("Vector search requested",
                   query=search_request.query_text[:100],
                   client_id=search_request.client_id,
                   search_type=search_request.search_type,
                   search_scope=search_request.search_scope)
        
        # Convert request to internal query format
        search_query = SearchQuery(
            query_text=search_request.query_text,
            client_id=search_request.client_id,
            search_type=SearchType(search_request.search_type),
            search_scope=SearchScope(search_request.search_scope),
            limit=search_request.limit,
            similarity_threshold=search_request.similarity_threshold,
            include_metadata=search_request.include_metadata,
            filters=search_request.filters,
            rerank=search_request.rerank,
            alpha=search_request.alpha
        )
        
        # Execute search
        result = await vector_search_service.search(search_query)
        
        # Convert results to response format
        response_results = [
            SearchResultResponse(
                id=r.id,
                content=r.content,
                score=r.score,
                metadata=r.metadata,
                search_type=r.search_type.value,
                matched_fields=r.matched_fields,
                created_at=r.created_at
            )
            for r in result.results
        ]
        
        return GraphRAGSearchResponse(
            query=result.query,
            results=response_results,
            total_results=result.total_results,
            search_metadata=result.search_metadata,
            communities_involved=result.communities_involved,
            entity_matches=result.entity_matches,
            reasoning_chain=result.reasoning_chain,
            quality_score=result.quality_score,
            search_time_ms=result.search_time_ms
        )
        
    except ValueError as e:
        logger.error("Vector search validation failed",
                    client_id=search_request.client_id,
                    error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Vector search failed",
                    client_id=search_request.client_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Vector search failed: {str(e)}")


@router.get("/vector/semantic")
async def semantic_search(
    request: Request,
    client_id: str = Query(..., description="Client identifier"),
    query: str = Query(..., description="Search query"),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum results"),
    threshold: float = Query(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")
):
    """
    Perform semantic search on document chunks.
    
    Uses vector embeddings to find semantically similar content
    across the client's document collection.
    """
    try:
        vector_search_service: VectorSearchService = request.app.state.vector_search_service
        
        logger.info("Semantic search requested",
                   client_id=client_id,
                   query=query[:50],
                   limit=limit,
                   threshold=threshold)
        
        # Execute semantic search
        results = await vector_search_service.semantic_search_chunks(
            client_id=client_id,
            query_text=query,
            limit=limit,
            similarity_threshold=threshold
        )
        
        # Convert to response format
        response_results = [
            {
                "id": r.id,
                "content": r.content,
                "similarity_score": r.score,
                "metadata": r.metadata,
                "matched_at": r.created_at
            }
            for r in results
        ]
        
        return {
            "query": query,
            "client_id": client_id,
            "search_type": "semantic",
            "results": response_results,
            "total_results": len(results),
            "parameters": {
                "limit": limit,
                "similarity_threshold": threshold
            },
            "retrieved_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error("Semantic search failed",
                    client_id=client_id,
                    query=query[:50],
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")


@router.get("/vector/hybrid")
async def hybrid_search(
    request: Request,
    client_id: str = Query(..., description="Client identifier"),
    query: str = Query(..., description="Search query"),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum results"),
    alpha: float = Query(default=0.5, ge=0.0, le=1.0, description="Semantic vs keyword weight")
):
    """
    Perform hybrid search combining semantic and keyword matching.
    
    Uses Reciprocal Rank Fusion to combine semantic similarity
    with keyword-based search for comprehensive results.
    """
    try:
        vector_search_service: VectorSearchService = request.app.state.vector_search_service
        
        logger.info("Hybrid search requested",
                   client_id=client_id,
                   query=query[:50],
                   limit=limit,
                   alpha=alpha)
        
        # Execute hybrid search
        results = await vector_search_service.hybrid_search_with_ranking(
            client_id=client_id,
            query_text=query,
            limit=limit,
            alpha=alpha
        )
        
        # Convert to response format
        response_results = [
            {
                "id": r.id,
                "content": r.content,
                "combined_score": r.score,
                "metadata": r.metadata,
                "search_components": {
                    "semantic_score": r.metadata.get("semantic_score", 0.0),
                    "keyword_score": r.metadata.get("keyword_score", 0.0),
                    "rrf_score": r.metadata.get("rrf_score", 0.0)
                },
                "matched_at": r.created_at
            }
            for r in results
        ]
        
        return {
            "query": query,
            "client_id": client_id,
            "search_type": "hybrid",
            "results": response_results,
            "total_results": len(results),
            "parameters": {
                "limit": limit,
                "alpha": alpha,
                "description": f"Alpha {alpha} (1.0=pure semantic, 0.0=pure keyword)"
            },
            "retrieved_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error("Hybrid search failed",
                    client_id=client_id,
                    query=query[:50],
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Hybrid search failed: {str(e)}")


@router.get("/vector/global")
async def global_search(
    request: Request,
    client_id: str = Query(..., description="Client identifier"),
    query: str = Query(..., description="Search query"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum results"),
    include_reasoning: bool = Query(default=True, description="Include reasoning chain")
):
    """
    Perform global search across the entire knowledge graph.
    
    Searches across all communities, entities, and relationships
    to provide comprehensive results with full context.
    """
    try:
        vector_search_service: VectorSearchService = request.app.state.vector_search_service
        
        logger.info("Global search requested",
                   client_id=client_id,
                   query=query[:50],
                   limit=limit,
                   include_reasoning=include_reasoning)
        
        # Execute global search
        result = await vector_search_service.global_knowledge_search(
            client_id=client_id,
            query_text=query,
            limit=limit,
            include_reasoning=include_reasoning
        )
        
        # Convert to response format
        response_results = [
            {
                "id": r.id,
                "content": r.content,
                "relevance_score": r.score,
                "metadata": r.metadata,
                "matched_fields": r.matched_fields,
                "matched_at": r.created_at
            }
            for r in result.results
        ]
        
        return {
            "query": result.query,
            "client_id": client_id,
            "search_type": "global",
            "results": response_results,
            "total_results": result.total_results,
            "communities_involved": result.communities_involved,
            "entity_matches": result.entity_matches,
            "reasoning_chain": result.reasoning_chain,
            "quality_score": result.quality_score,
            "search_time_ms": result.search_time_ms,
            "metadata": result.search_metadata,
            "retrieved_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error("Global search failed",
                    client_id=client_id,
                    query=query[:50],
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Global search failed: {str(e)}")


# RAG Endpoints

@router.post("/rag/query")
async def rag_query(request: Request, rag_request: RAGQueryRequest):
    """
    Process a comprehensive RAG query.
    
    Combines Context Engine (situational awareness) with GraphRAG (knowledge retrieval)
    to provide comprehensive legal document analysis and question answering.
    """
    try:
        rag_orchestrator: RAGOrchestrator = request.app.state.rag_orchestrator
        
        logger.info("RAG query requested",
                   query=rag_request.query_text[:100],
                   client_id=rag_request.client_id,
                   case_id=rag_request.case_id,
                   mode=rag_request.mode)
        
        # Convert request to internal query format
        search_types = None
        if rag_request.search_types:
            search_types = [SearchType(t) for t in rag_request.search_types]
        
        rag_query_obj = RAGQuery(
            query_text=rag_request.query_text,
            client_id=rag_request.client_id,
            case_id=rag_request.case_id,
            mode=RAGMode(rag_request.mode),
            max_results=rag_request.max_results,
            include_context=rag_request.include_context,
            include_reasoning=rag_request.include_reasoning,
            quality_threshold=rag_request.quality_threshold,
            context_depth=rag_request.context_depth,
            search_types=search_types
        )
        
        # Execute RAG query
        result = await rag_orchestrator.process_query(rag_query_obj)
        
        # Convert retrieval results to response format
        retrieval_response = None
        if result.retrieval_results:
            retrieval_response = GraphRAGSearchResponse(
                query=result.retrieval_results.query,
                results=[
                    SearchResultResponse(
                        id=r.id,
                        content=r.content,
                        score=r.score,
                        metadata=r.metadata,
                        search_type=r.search_type.value,
                        matched_fields=r.matched_fields,
                        created_at=r.created_at
                    )
                    for r in result.retrieval_results.results
                ],
                total_results=result.retrieval_results.total_results,
                search_metadata=result.retrieval_results.search_metadata,
                communities_involved=result.retrieval_results.communities_involved,
                entity_matches=result.retrieval_results.entity_matches,
                reasoning_chain=result.retrieval_results.reasoning_chain,
                quality_score=result.retrieval_results.quality_score,
                search_time_ms=result.retrieval_results.search_time_ms
            )
        
        return RAGResponse(
            query=result.query,
            intent=result.intent.value,
            mode_used=result.mode_used.value,
            context_data=result.context_data,
            context_quality=result.context_quality,
            retrieval_results=retrieval_response,
            retrieval_quality=result.retrieval_quality,
            synthesized_response=result.synthesized_response,
            evidence_chain=result.evidence_chain,
            confidence_score=result.confidence_score,
            total_time_ms=result.total_time_ms,
            context_time_ms=result.context_time_ms,
            retrieval_time_ms=result.retrieval_time_ms,
            synthesis_time_ms=result.synthesis_time_ms,
            metadata=result.metadata,
            created_at=result.created_at
        )
        
    except ValueError as e:
        logger.error("RAG query validation failed",
                    client_id=rag_request.client_id,
                    error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("RAG query failed",
                    client_id=rag_request.client_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")


@router.get("/rag/contextual")
async def contextual_retrieval(
    request: Request,
    client_id: str = Query(..., description="Client identifier"),
    query: str = Query(..., description="Query text"),
    case_id: Optional[str] = Query(None, description="Case context"),
    max_results: int = Query(default=10, ge=1, le=50, description="Maximum results")
):
    """
    Perform contextual retrieval with situational awareness.
    
    Gets context from Context Engine first, then performs
    enhanced retrieval based on the contextual information.
    """
    try:
        rag_orchestrator: RAGOrchestrator = request.app.state.rag_orchestrator
        
        logger.info("Contextual retrieval requested",
                   client_id=client_id,
                   query=query[:50],
                   case_id=case_id)
        
        # Execute contextual retrieval
        result = await rag_orchestrator.get_contextual_retrieval(
            client_id=client_id,
            query_text=query,
            case_id=case_id,
            max_results=max_results
        )
        
        return {
            "query": result.query,
            "client_id": client_id,
            "case_id": case_id,
            "intent": result.intent.value,
            "mode_used": result.mode_used.value,
            "context_summary": result.context_data,
            "context_quality": result.context_quality,
            "retrieval_results": {
                "results": [
                    {
                        "id": r.id,
                        "content": r.content,
                        "score": r.score,
                        "metadata": r.metadata
                    }
                    for r in result.retrieval_results.results
                ] if result.retrieval_results else [],
                "quality_score": result.retrieval_quality
            },
            "synthesized_response": result.synthesized_response,
            "confidence_score": result.confidence_score,
            "performance": {
                "total_time_ms": result.total_time_ms,
                "context_time_ms": result.context_time_ms,
                "retrieval_time_ms": result.retrieval_time_ms
            },
            "retrieved_at": result.created_at
        }
        
    except Exception as e:
        logger.error("Contextual retrieval failed",
                    client_id=client_id,
                    query=query[:50],
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Contextual retrieval failed: {str(e)}")


@router.get("/rag/precedent")
async def precedent_analysis(
    request: Request,
    client_id: str = Query(..., description="Client identifier"),
    query: str = Query(..., description="Legal query"),
    jurisdiction: Optional[str] = Query(None, description="Jurisdiction filter"),
    case_type: Optional[str] = Query(None, description="Case type filter")
):
    """
    Get precedent analysis with legal context.
    
    Specializes in finding relevant case law and precedents
    with proper legal context and analysis.
    """
    try:
        rag_orchestrator: RAGOrchestrator = request.app.state.rag_orchestrator
        
        logger.info("Precedent analysis requested",
                   client_id=client_id,
                   query=query[:50],
                   jurisdiction=jurisdiction,
                   case_type=case_type)
        
        # Execute precedent analysis
        result = await rag_orchestrator.get_precedent_analysis(
            client_id=client_id,
            query_text=query,
            jurisdiction=jurisdiction,
            case_type=case_type
        )
        
        return {
            "query": result.query,
            "client_id": client_id,
            "analysis_type": "precedent",
            "filters": {
                "jurisdiction": jurisdiction,
                "case_type": case_type
            },
            "intent": result.intent.value,
            "precedent_results": {
                "results": [
                    {
                        "id": r.id,
                        "content": r.content,
                        "relevance_score": r.score,
                        "metadata": r.metadata,
                        "legal_citation": r.metadata.get("citation", "Unknown"),
                        "court": r.metadata.get("court", "Unknown"),
                        "year": r.metadata.get("year", "Unknown")
                    }
                    for r in result.retrieval_results.results
                ] if result.retrieval_results else [],
                "communities_involved": result.retrieval_results.communities_involved if result.retrieval_results else [],
                "entity_matches": result.retrieval_results.entity_matches if result.retrieval_results else []
            },
            "legal_context": result.context_data,
            "synthesized_analysis": result.synthesized_response,
            "confidence_score": result.confidence_score,
            "quality_metrics": {
                "context_quality": result.context_quality,
                "retrieval_quality": result.retrieval_quality,
                "overall_confidence": result.confidence_score
            },
            "performance": {
                "total_time_ms": result.total_time_ms,
                "search_time_ms": result.retrieval_time_ms
            },
            "analyzed_at": result.created_at
        }
        
    except Exception as e:
        logger.error("Precedent analysis failed",
                    client_id=client_id,
                    query=query[:50],
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Precedent analysis failed: {str(e)}")


# Utility Endpoints

@router.get("/search/types")
async def get_search_types():
    """Get available search types and their descriptions."""
    return {
        "search_types": {
            "semantic": {
                "description": "Pure vector similarity search using embeddings",
                "best_for": "Finding conceptually similar content",
                "parameters": ["similarity_threshold", "limit"]
            },
            "hybrid": {
                "description": "Combines semantic and keyword search with RRF ranking", 
                "best_for": "Balanced relevance and precision",
                "parameters": ["alpha", "limit"]
            },
            "local": {
                "description": "Community-scoped search within specific graph regions",
                "best_for": "Focused search within related entities",
                "parameters": ["community_id", "limit"]
            },
            "global": {
                "description": "Full knowledge graph traversal with reasoning",
                "best_for": "Comprehensive analysis across all data",
                "parameters": ["include_reasoning", "limit"]
            }
        },
        "search_scopes": {
            "chunks": "Document chunks and content pieces",
            "nodes": "Graph nodes (entities)",
            "communities": "Entity communities",
            "all": "All searchable content types"
        }
    }


@router.get("/rag/modes")
async def get_rag_modes():
    """Get available RAG execution modes."""
    return {
        "rag_modes": {
            "context_first": {
                "description": "Get context first, then enhance retrieval",
                "best_for": "Case-specific queries needing situational awareness",
                "flow": "Context → Enhanced Retrieval → Synthesis"
            },
            "retrieve_first": {
                "description": "Retrieve first, then contextualize results",
                "best_for": "General legal knowledge and precedent queries",
                "flow": "Retrieval → Context → Synthesis"
            },
            "parallel": {
                "description": "Run context and retrieval in parallel",
                "best_for": "Balanced performance and comprehensive results",
                "flow": "Context ∥ Retrieval → Synthesis"
            },
            "adaptive": {
                "description": "Automatically choose best mode based on query",
                "best_for": "General use when optimal strategy is unclear",
                "flow": "Query Analysis → Optimal Mode Selection"
            }
        },
        "query_intents": [
            "case_specific",
            "general_legal", 
            "procedural",
            "precedent",
            "contextual"
        ]
    }


@router.get("/performance/metrics")
async def get_performance_metrics(request: Request):
    """Get search and RAG performance metrics."""
    try:
        vector_search_service: VectorSearchService = request.app.state.vector_search_service
        rag_orchestrator: RAGOrchestrator = request.app.state.rag_orchestrator
        
        return {
            "vector_search_metrics": vector_search_service.performance_metrics,
            "rag_orchestrator_metrics": rag_orchestrator.performance_metrics,
            "service_status": {
                "vector_search_initialized": vector_search_service.is_initialized,
                "rag_orchestrator_initialized": rag_orchestrator.is_initialized
            },
            "retrieved_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error("Performance metrics retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Metrics retrieval failed: {str(e)}")