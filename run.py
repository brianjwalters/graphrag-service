#!/usr/bin/env python3
"""
GraphRAG Service Launcher
Port 8010 - Knowledge Graph Construction Service
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import uvicorn
from src.api.main import app
from src.core.config import get_settings

def main():
    """Run the GraphRAG service."""
    settings = get_settings()
    
    print(f"🚀 Starting GraphRAG Service")
    print(f"   Port: {settings.service_port}")
    print(f"   Environment: {settings.environment}")
    print(f"   API Docs: http://localhost:{settings.service_port}/docs")
    print(f"   Health Check: http://localhost:{settings.service_port}/api/v1/health/ping")
    
    # Run the service
    if settings.environment == "development":
        # Use import string for reload functionality
        uvicorn.run(
            "src.api.main:app",
            host="0.0.0.0",
            port=settings.service_port,
            reload=True,
            log_level="info",
            access_log=True,
            timeout_keep_alive=2700,  # 45 minutes for long graph processing
            timeout_graceful_shutdown=30,  # 30 seconds for graceful shutdown
            limit_concurrency=100,
            limit_max_requests=1000  # Restart worker after 1000 requests
        )
    else:
        # Use app object for production
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=settings.service_port,
            log_level="info",
            access_log=True,
            timeout_keep_alive=2700,  # 45 minutes for long graph processing
            timeout_graceful_shutdown=30,  # 30 seconds for graceful shutdown
            limit_concurrency=100,
            limit_max_requests=1000  # Restart worker after 1000 requests
        )

if __name__ == "__main__":
    main()