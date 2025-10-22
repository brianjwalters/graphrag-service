"""Common health models for services."""

from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime


class HealthResponse(BaseModel):
    """Standard health response model."""
    status: str = "healthy"
    service: str = "graphrag-service"
    version: str = "1.0.0"
    timestamp: datetime = None
    dependencies: Dict[str, Any] = {}
    
    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.now()
        super().__init__(**data)


class PingResponse(BaseModel):
    """Simple ping response."""
    status: str = "pong"
    timestamp: datetime = None
    
    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.now()
        super().__init__(**data)


class ReadinessResponse(BaseModel):
    """Readiness check response."""
    ready: bool = True
    service: str = "graphrag-service"
    timestamp: datetime = None
    checks: Dict[str, bool] = {}
    
    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.now()
        super().__init__(**data)


class DetailedHealthResponse(BaseModel):
    """Detailed health response with metrics."""
    status: str = "healthy"
    service: str = "graphrag-service"
    version: str = "1.0.0"
    timestamp: datetime = None
    uptime_seconds: float = 0
    request_count: int = 0
    error_count: int = 0
    dependencies: Dict[str, Any] = {}
    metrics: Dict[str, Any] = {}
    
    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.now()
        super().__init__(**data)


class RouteInfo(BaseModel):
    """Information about an API route."""
    path: str
    methods: List[str]
    description: Optional[str] = None
    parameters: Optional[List[str]] = None


def calculate_health_status(dependencies: Dict[str, Any]) -> str:
    """Calculate overall health status based on dependencies."""
    if not dependencies:
        return "healthy"
    
    unhealthy_deps = [k for k, v in dependencies.items() 
                      if isinstance(v, dict) and v.get("status") == "unhealthy"]
    
    if unhealthy_deps:
        return "degraded" if len(unhealthy_deps) < len(dependencies) else "unhealthy"
    
    return "healthy"