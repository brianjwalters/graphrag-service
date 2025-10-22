"""
Health Check Routes for GraphRAG Service

Standardized health monitoring endpoints following common patterns.
Includes graph processing metrics and dependency checks.
"""

from fastapi import APIRouter, Request
from typing import Dict, Any, Optional
from datetime import datetime
import psutil
import traceback
from pydantic import Field

# Import common health models from src
from ...common_health_models import (
    HealthResponse,
    PingResponse,
    ReadinessResponse,
    DetailedHealthResponse as BaseDetailedHealthResponse,
    calculate_health_status
)

router = APIRouter()

# Track service start time
SERVICE_START_TIME = datetime.utcnow()


# Extended health response for GraphRAG-specific data
class DetailedHealthResponse(BaseDetailedHealthResponse):
    """Extended detailed health response with graph-specific stats."""
    graph_stats: Optional[Dict[str, Any]] = Field(default=None, description="Graph processing statistics")


@router.get("/", response_model=HealthResponse)
@router.get("", response_model=HealthResponse)
async def health_check(req: Request) -> HealthResponse:
    """
    Basic health check endpoint.
    
    Returns service status and basic information.
    """
    uptime = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()
    
    return HealthResponse(
        status="healthy",
        service_name="graphrag-service",
        service_version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=uptime
    )


@router.get("/ping", response_model=PingResponse)
async def ping() -> PingResponse:
    """
    Simple ping endpoint for load balancers.
    
    Returns a simple pong response with timestamp.
    """
    return PingResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(req: Request) -> ReadinessResponse:
    """
    Readiness check endpoint with dependency verification.
    
    Checks if the service and its dependencies are ready to handle requests.
    """
    uptime = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()
    
    # Check dependencies
    dependencies = await check_dependencies(req)
    
    # Determine if service is ready
    critical_deps = ["supabase"]
    ready = all(
        dependencies.get(dep) == "healthy" 
        for dep in critical_deps 
        if dep in dependencies
    )
    
    # Calculate overall status
    if not ready:
        status = "unhealthy"
    elif any(v not in ["healthy", "not_configured"] for v in dependencies.values()):
        status = "degraded"
    else:
        status = "healthy"
    
    return ReadinessResponse(
        status=status,
        service_name="graphrag-service",
        service_version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=uptime,
        ready=ready,
        dependencies=dependencies
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health(req: Request) -> DetailedHealthResponse:
    """
    Detailed health check endpoint with comprehensive information.
    
    Returns detailed health status including all checks, dependencies, and metrics.
    """
    uptime = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()
    
    # Check dependencies
    dependencies = await check_dependencies(req)
    
    # Check components
    checks = await check_components(req)
    
    # Collect metrics
    metrics = await collect_metrics(req)
    
    # Get graph statistics
    graph_stats = await get_graph_stats(req)
    
    # Calculate overall status
    status = calculate_overall_status(checks, dependencies)
    
    return DetailedHealthResponse(
        status=status,
        service_name="graphrag-service",
        service_version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=uptime,
        checks=checks,
        dependencies=dependencies,
        metrics=metrics,
        graph_stats=graph_stats
    )


@router.get("/metrics")
async def get_metrics_endpoint(req: Request) -> Dict[str, Any]:
    """
    Get detailed service metrics.
    
    Returns resource usage, graph processing statistics, and performance metrics.
    """
    metrics = await collect_metrics(req)
    graph_stats = await get_graph_stats(req)
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics,
        "graph_stats": graph_stats,
        "status": "healthy"
    }


# Helper functions
async def check_dependencies(req: Request) -> Dict[str, str]:
    """Check status of external dependencies."""
    dependencies = {}
    
    # Check Supabase connection
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        if supabase_client:
            # Try a simple query
            await supabase_client.get("graph.nodes", limit=1)
            dependencies["supabase"] = "healthy"
        else:
            dependencies["supabase"] = "not_initialized"
    except Exception as e:
        dependencies["supabase"] = "unhealthy"
    
    # Check Prompt Service (if configured)
    if req.app.state.settings.prompt_service_url:
        try:
            http_client = req.app.state.graph_constructor.http_client
            if http_client:
                response = await http_client.get(
                    f"{req.app.state.settings.prompt_service_url}/api/v1/health/ping",
                    timeout=2.0
                )
                if response.status_code == 200:
                    dependencies["prompt_service"] = "healthy"
                else:
                    dependencies["prompt_service"] = "unhealthy"
            else:
                dependencies["prompt_service"] = "not_initialized"
        except Exception:
            dependencies["prompt_service"] = "unhealthy"
    else:
        dependencies["prompt_service"] = "not_configured"
    
    # Check Entity Extraction Service (if configured)
    if hasattr(req.app.state.settings, "entity_extraction_url"):
        try:
            http_client = req.app.state.graph_constructor.http_client
            if http_client:
                response = await http_client.get(
                    f"{req.app.state.settings.entity_extraction_url}/api/v1/health/ping",
                    timeout=2.0
                )
                if response.status_code == 200:
                    dependencies["entity_extraction"] = "healthy"
                else:
                    dependencies["entity_extraction"] = "unhealthy"
            else:
                dependencies["entity_extraction"] = "not_initialized"
        except Exception:
            dependencies["entity_extraction"] = "unhealthy"
    else:
        dependencies["entity_extraction"] = "not_configured"
    
    return dependencies


async def check_components(req: Request) -> Dict[str, Any]:
    """Check status of internal components."""
    checks = {}
    
    # Check graph constructor
    try:
        graph_constructor = req.app.state.graph_constructor
        if graph_constructor:
            checks["graph_constructor"] = {
                "status": "healthy",
                "message": "Graph constructor operational"
            }
        else:
            checks["graph_constructor"] = {
                "status": "unhealthy",
                "message": "Graph constructor not initialized"
            }
    except Exception as e:
        checks["graph_constructor"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check HTTP client
    try:
        http_client = getattr(req.app.state.graph_constructor, "http_client", None)
        if http_client:
            checks["http_client"] = {
                "status": "healthy",
                "message": "HTTP client operational"
            }
        else:
            checks["http_client"] = {
                "status": "unavailable",
                "message": "HTTP client not initialized"
            }
    except Exception as e:
        checks["http_client"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    return checks


async def collect_metrics(req: Request) -> Dict[str, Any]:
    """Collect performance and resource metrics."""
    metrics = {}
    
    # System metrics
    try:
        process = psutil.Process()
        metrics["cpu_percent"] = process.cpu_percent()
        metrics["memory_mb"] = process.memory_info().rss / 1024 / 1024
        metrics["threads"] = process.num_threads()
    except:
        pass
    
    # Service metrics
    metrics["uptime_seconds"] = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()
    metrics["environment"] = req.app.state.settings.environment
    
    # Request metrics (if tracked)
    try:
        if hasattr(req.app.state, "request_count"):
            metrics["total_requests"] = req.app.state.request_count
        if hasattr(req.app.state, "error_count"):
            metrics["total_errors"] = req.app.state.error_count
    except:
        pass
    
    return metrics


async def get_graph_stats(req: Request) -> Optional[Dict[str, Any]]:
    """Get graph processing statistics."""
    try:
        supabase_client = req.app.state.graph_constructor.supabase_client
        if not supabase_client:
            return None
        
        stats = {}
        
        # Get node count
        try:
            nodes_result = await supabase_client.get("graph.nodes", count="exact")
            stats["total_nodes"] = nodes_result.get("count", 0)
        except:
            stats["total_nodes"] = 0
        
        # Get edge count
        try:
            edges_result = await supabase_client.get("graph.edges", count="exact")
            stats["total_edges"] = edges_result.get("count", 0)
        except:
            stats["total_edges"] = 0

        # Get community count
        try:
            communities_result = await supabase_client.get("graph.communities", count="exact")
            stats["total_communities"] = communities_result.get("count", 0)
        except:
            stats["total_communities"] = 0
        
        # Processing stats
        if hasattr(req.app.state, "graphs_created"):
            stats["graphs_created"] = req.app.state.graphs_created
        if hasattr(req.app.state, "last_processing_time_ms"):
            stats["last_processing_time_ms"] = req.app.state.last_processing_time_ms
        
        return stats
        
    except Exception:
        return None


def calculate_overall_status(checks: Dict[str, Any], dependencies: Dict[str, str]) -> str:
    """Calculate overall health status based on checks and dependencies."""
    
    # Check for any unhealthy components
    for check in checks.values():
        if isinstance(check, dict) and check.get("status") == "unhealthy":
            return "unhealthy"
    
    for dep, status in dependencies.items():
        # Ignore not_configured dependencies
        if status == "unhealthy" and dep in ["supabase"]:  # Critical dependencies
            return "unhealthy"
    
    # Check for degraded components
    for check in checks.values():
        if isinstance(check, dict) and check.get("status") in ["degraded", "unavailable"]:
            return "degraded"
    
    for dep, status in dependencies.items():
        if status in ["degraded", "unavailable", "unhealthy"] and status != "not_configured":
            return "degraded"
    
    return "healthy"