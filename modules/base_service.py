"""
Base service module providing common functionality for all IM2 microservices.

This module implements:
- Health and metrics endpoints
- Structured logging
- Configuration management
- Base API structure
"""

import os
import sys
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="Current timestamp")
    uptime: float = Field(..., description="Service uptime in seconds")
    dependencies: Dict[str, str] = Field(..., description="Status of dependencies")

class MetricsResponse(BaseModel):
    """Metrics response model."""
    metrics: Dict[str, Any] = Field(..., description="Service metrics")

class BaseService:
    """Base class for all IM2 microservices."""
    
    def __init__(
        self, 
        name: str, 
        version: str = "0.1.0",
        description: str = "",
        dependencies: List[str] = None
    ):
        """Initialize the service."""
        self.name = name
        self.version = version
        self.description = description or f"{name} microservice for IM2 Audio Processing Pipeline"
        self.dependencies = dependencies or []
        self.start_time = time.time()
        
        # Initialize FastAPI
        self.app = FastAPI(
            title=f"IM2 {name}",
            description=self.description,
            version=self.version
        )
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add middleware for request ID tracing
        self.app.middleware("http")(self.add_trace_id_middleware)
        
        # Configure routes
        self.app.get("/health", response_model=HealthResponse)(self.health_check)
        self.app.get("/metrics")(self.metrics)
        
        # Initialize metrics
        self.request_counter = Counter(
            f"{self.name}_requests_total", 
            f"Total number of requests to the {self.name} service",
            ["method", "endpoint", "status"]
        )
        self.request_latency = Histogram(
            f"{self.name}_request_latency_seconds", 
            f"Request latency in seconds for {self.name} service",
            ["method", "endpoint"]
        )
        
        # Configure logger
        self.logger = logging.getLogger(self.name)

    async def add_trace_id_middleware(self, request: Request, call_next):
        """Add trace ID to request and response."""
        # Get or generate trace ID
        trace_id = request.headers.get("X-Trace-ID", f"{int(time.time() * 1000)}-{self.name}")
        request.state.trace_id = trace_id
        
        # Measure request duration
        start_time = time.time()
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            self.logger.error(f"Request failed: {str(e)}", extra={"trace_id": trace_id})
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            
            # Record metrics
            self.request_counter.labels(
                method=request.method,
                endpoint=request.url.path,
                status=status_code
            ).inc()
            
            self.request_latency.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
        
        # Add trace ID to response
        response.headers["X-Trace-ID"] = trace_id
        return response

    async def health_check(self) -> HealthResponse:
        """Health check endpoint."""
        # Check dependencies
        dependency_status = {}
        for dep in self.dependencies:
            # This would actually check dependency health in a real implementation
            dependency_status[dep] = "healthy"
        
        return HealthResponse(
            status="healthy",
            version=self.version,
            timestamp=datetime.now().isoformat(),
            uptime=time.time() - self.start_time,
            dependencies=dependency_status
        )

    async def metrics(self) -> Response:
        """Metrics endpoint."""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the service."""
        self.logger.info(f"Starting {self.name} service on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)
