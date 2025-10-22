"""
GraphRAG Service API
Port 8010 - Knowledge Graph Construction Service
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import traceback
from datetime import datetime

from ..core.config import get_settings
from ..core.graph_constructor import GraphConstructor
from ..core.vector_search_service import VectorSearchService
from ..core.rag_orchestrator import RAGOrchestrator
from ..clients.supabase_client import SupabaseClient
from .routes import graph, health, nodes, edges, communities, search, entity


# Service configuration
settings = get_settings()

# Global service instances
graph_constructor = None
vector_search_service = None
rag_orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage service lifecycle - startup and shutdown.
    """
    global graph_constructor, vector_search_service, rag_orchestrator
    
    # Startup
    print(f"🚀 Starting GraphRAG Service on port {settings.service_port}")
    print(f"   Environment: {settings.environment}")
    print(f"   API Prefix: {settings.api_prefix}")
    print(f"   Features: Graph Construction + Vector Search + RAG")
    
    try:
        # Initialize Supabase client
        supabase_client = SupabaseClient()
        print("✅ Supabase client initialized")
        
        # Initialize graph constructor
        graph_constructor = GraphConstructor(settings)
        await graph_constructor.initialize_clients()
        print("✅ Graph constructor initialized")
        
        # Initialize vector search service
        vector_search_service = VectorSearchService(settings)
        await vector_search_service.initialize(supabase_client)
        print("✅ Vector search service initialized")
        
        # Initialize RAG orchestrator
        rag_orchestrator = RAGOrchestrator(settings)
        await rag_orchestrator.initialize(supabase_client, vector_search_service)
        print("✅ RAG orchestrator initialized")
        
        # Store in app state for access in routes
        app.state.graph_constructor = graph_constructor
        app.state.vector_search_service = vector_search_service
        app.state.rag_orchestrator = rag_orchestrator
        app.state.supabase_client = supabase_client
        app.state.settings = settings
        
        print("✅ GraphRAG Service (with Vector Search & RAG) started successfully")
        
    except Exception as e:
        print(f"❌ GraphRAG Service startup failed: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    print("🛑 Shutting down GraphRAG Service...")
    
    try:
        if rag_orchestrator:
            # RAG orchestrator doesn't need explicit cleanup currently
            pass
        
        if vector_search_service:
            # Vector search service doesn't need explicit cleanup currently
            pass
        
        if graph_constructor:
            await graph_constructor.close()
        
        if supabase_client:
            await supabase_client.close()
        
        print("✅ GraphRAG Service shutdown complete")
    except Exception as e:
        print(f"⚠️ Shutdown error: {str(e)}")


# Create FastAPI app
app = FastAPI(
    title="GraphRAG Service",
    description="Knowledge Graph Construction & Vector Search Service with RAG capabilities",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.
    """
    error_id = f"error_{int(datetime.utcnow().timestamp())}"
    
    # Log the error
    print(f"❌ Unhandled error {error_id}: {str(exc)}")
    print(f"   Traceback: {traceback.format_exc()}")
    
    # Return structured error response
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_id": error_id,
            "message": str(exc) if settings.environment == "development" else "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Include routers
app.include_router(
    graph.router,
    prefix=f"{settings.api_prefix}/graph",
    tags=["graph"]
)

app.include_router(
    nodes.router,
    prefix=f"{settings.api_prefix}/nodes",
    tags=["nodes"]
)

app.include_router(
    edges.router,
    prefix=f"{settings.api_prefix}/edges",
    tags=["edges"]
)

app.include_router(
    communities.router,
    prefix=f"{settings.api_prefix}/communities",
    tags=["communities"]
)

app.include_router(
    health.router,
    prefix=f"{settings.api_prefix}/health",
    tags=["health"]
)

app.include_router(
    search.router,
    prefix=f"{settings.api_prefix}/search",
    tags=["search", "vector_search", "rag"]
)

app.include_router(
    entity.router,
    prefix=f"{settings.api_prefix}/entity",
    tags=["entity", "upsert", "deduplication"]
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "GraphRAG Service",
        "version": "1.0.0",
        "status": "operational",
        "port": settings.service_port,
        "environment": settings.environment,
        "description": "Knowledge Graph Construction using Microsoft GraphRAG",
        "endpoints": {
            "create_graph": f"{settings.api_prefix}/graph/create",
            "update_graph": f"{settings.api_prefix}/graph/update",
            "query_graph": f"{settings.api_prefix}/graph/query",
            "vector_search": f"{settings.api_prefix}/search/vector/search",
            "semantic_search": f"{settings.api_prefix}/search/vector/semantic",
            "hybrid_search": f"{settings.api_prefix}/search/vector/hybrid",
            "global_search": f"{settings.api_prefix}/search/vector/global",
            "rag_query": f"{settings.api_prefix}/search/rag/query",
            "contextual_retrieval": f"{settings.api_prefix}/search/rag/contextual",
            "precedent_analysis": f"{settings.api_prefix}/search/rag/precedent",
            "health": f"{settings.api_prefix}/health/ping",
            "metrics": f"{settings.api_prefix}/health/metrics"
        },
        "features": [
            "Knowledge Graph Construction with Microsoft GraphRAG",
            "Entity deduplication with 0.85 threshold",
            "Leiden algorithm community detection",
            "Cross-document relationship discovery",
            "Legal entity specialization",
            "Graph analytics and quality scoring",
            "Vector Search with 2048D Jina embeddings",
            "Semantic, Hybrid, Local & Global search modes",
            "RAG orchestration with Context Engine integration",
            "Legal precedent analysis and contextual retrieval",
            "Multi-tenant search with client isolation",
            "AI-powered community summaries"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.environment == "development",
        log_level="info"
    )