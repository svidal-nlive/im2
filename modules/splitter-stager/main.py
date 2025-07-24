"""
Splitter-Stager Service for IM2 Audio Processing Pipeline

This service:
1. Prepares audio files for stem separation
2. Manages staging for different separation engines
3. Handles plugin interfaces for custom engines
4. Provides health and metrics endpoints
"""

import os
import sys
import json
import logging
import asyncio
import time
import shutil
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path
from enum import Enum

import aiohttp
import aiofiles
from fastapi import FastAPI, HTTPException, APIRouter, Depends, Request, Response, BackgroundTasks
from pydantic import BaseModel, Field

# Add parent directory to path for importing base_service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_service import BaseService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("splitter-stager")

class SeparationEngine(str, Enum):
    """Supported separation engines."""
    SPLEETER = "spleeter"
    DEMUCS = "demucs"
    AUTO = "auto"  # Automatically select engine based on file characteristics

class StagingResult(BaseModel):
    """Staging result model."""
    job_uuid: str = Field(..., description="Job UUID")
    user_id: str = Field(..., description="User ID")
    original_file_path: str = Field(..., description="Original file path")
    staged_file_path: str = Field(..., description="Staged file path")
    engine: SeparationEngine = Field(..., description="Selected separation engine")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="File metadata")
    timestamp: str = Field(..., description="Staging timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")

class EnginePlugin(BaseModel):
    """Engine plugin model."""
    name: str = Field(..., description="Plugin name")
    version: str = Field(..., description="Plugin version")
    input_path: str = Field(..., description="Input directory for plugin")
    supported_formats: List[str] = Field(..., description="Supported audio formats")

class SplitterStagerService(BaseService):
    """Splitter-stager service for preparing audio files for stem separation."""
    
    def __init__(self):
        """Initialize the splitter-stager service."""
        super().__init__(
            name="splitter-stager",
            version="0.1.0",
            description="File preparation service for IM2 Audio Processing Pipeline",
            dependencies=["queue", "metadata-service"]
        )
        
        # Configure settings
        self.spleeter_input_path = os.getenv("SPLEETER_INPUT_PATH", "/pipeline-data/spleeter-input")
        self.demucs_input_path = os.getenv("DEMUCS_INPUT_PATH", "/pipeline-data/demucs-input")
        self.queue_service_url = os.getenv("QUEUE_SERVICE_URL", "http://queue:8003")
        
        # Initialize plugins (empty for now)
        self.plugins: Dict[str, EnginePlugin] = {}
        
        # Create router
        router = APIRouter()
        
        # Additional routes
        router.post("/stage", response_model=StagingResult)(self.stage_file)
        router.get("/engines", response_model=List[str])(self.get_supported_engines)
        router.post("/plugins", response_model=Dict[str, Any])(self.register_plugin)
        router.get("/plugins", response_model=List[EnginePlugin])(self.get_plugins)
        
        # Include router
        self.app.include_router(router, prefix="/api")
    
    async def startup_event(self):
        """FastAPI startup event."""
        # Create input directories if they don't exist
        os.makedirs(self.spleeter_input_path, exist_ok=True)
        os.makedirs(self.demucs_input_path, exist_ok=True)
        
        # Initialize plugins
        await self.init_plugins()
        
        logger.info("Splitter-stager service started")
    
    async def shutdown_event(self):
        """FastAPI shutdown event."""
        logger.info("Splitter-stager service stopped")
    
    async def init_plugins(self):
        """Initialize engine plugins."""
        # Register built-in engines as plugins
        self.plugins["spleeter"] = EnginePlugin(
            name="spleeter",
            version="2.4.0",
            input_path=self.spleeter_input_path,
            supported_formats=["mp3", "wav", "flac", "ogg"]
        )
        
        self.plugins["demucs"] = EnginePlugin(
            name="demucs",
            version="4.0.0",
            input_path=self.demucs_input_path,
            supported_formats=["mp3", "wav", "flac", "ogg"]
        )
    
    def select_engine(self, metadata: Dict[str, Any], requested_engine: str = None) -> SeparationEngine:
        """Select the best separation engine based on file characteristics."""
        # If engine is explicitly requested and supported
        if requested_engine and requested_engine != SeparationEngine.AUTO:
            if requested_engine in self.plugins:
                return SeparationEngine(requested_engine)
        
        # Get audio format from metadata
        audio_format = metadata.get("format", "unknown")
        
        # Get file info from metadata
        file_info = metadata.get("file_info", {})
        duration = file_info.get("duration", 0)
        
        # Simple auto-selection logic
        if duration and duration > 600:  # Longer than 10 minutes
            # Use Spleeter for very long tracks as it's faster
            return SeparationEngine.SPLEETER
        
        # For high-quality audio formats, prefer Demucs
        if audio_format in ["flac", "wav"] and "bitrate" in file_info and file_info["bitrate"] > 320000:
            return SeparationEngine.DEMUCS
        
        # Default to Spleeter for everything else (it's generally faster)
        return SeparationEngine.SPLEETER
    
    async def stage_file(self, request: Request, background_tasks: BackgroundTasks) -> StagingResult:
        """Stage a file for stem separation."""
        try:
            # Get request body
            body = await request.json()
            
            # Get required fields
            job_uuid = body.get("job_uuid")
            user_id = body.get("user_id")
            file_path = body.get("file_path")
            
            # Get optional fields
            requested_engine = body.get("engine", SeparationEngine.AUTO)
            metadata = body.get("metadata", {})
            
            if not all([job_uuid, user_id, file_path]):
                raise HTTPException(status_code=400, detail="Missing required fields")
            
            # Check if file exists
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
            
            # Get trace ID from request
            trace_id = request.headers.get("X-Trace-ID")
            
            # Select engine
            engine = self.select_engine(metadata, requested_engine)
            
            # Get target directory for selected engine
            if engine == SeparationEngine.SPLEETER:
                target_dir = Path(self.spleeter_input_path) / user_id / job_uuid
            elif engine == SeparationEngine.DEMUCS:
                target_dir = Path(self.demucs_input_path) / user_id / job_uuid
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported engine: {engine}")
            
            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Get filename from original path
            filename = os.path.basename(file_path)
            target_path = target_dir / filename
            
            # Copy file to target directory
            try:
                # Use shutil.copy2 to preserve metadata
                shutil.copy2(file_path, target_path)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error copying file: {str(e)}")
            
            # Create result
            result = StagingResult(
                job_uuid=job_uuid,
                user_id=user_id,
                original_file_path=file_path,
                staged_file_path=str(target_path),
                engine=engine,
                metadata=metadata,
                timestamp=datetime.now().isoformat()
            )
            
            # Update job status in queue
            background_tasks.add_task(
                self.update_job_status,
                job_uuid,
                str(target_path),
                engine,
                metadata,
                trace_id
            )
            
            return result
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error staging file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error staging file: {str(e)}")
    
    async def get_supported_engines(self) -> List[str]:
        """Get list of supported separation engines."""
        return list(self.plugins.keys()) + ["auto"]
    
    async def register_plugin(self, plugin: EnginePlugin) -> Dict[str, Any]:
        """Register a new engine plugin."""
        try:
            # Validate plugin
            if not os.path.exists(plugin.input_path):
                # Create plugin input directory if it doesn't exist
                os.makedirs(plugin.input_path, exist_ok=True)
            
            # Register plugin
            self.plugins[plugin.name] = plugin
            
            return {"status": "success", "message": f"Plugin {plugin.name} registered successfully"}
        
        except Exception as e:
            logger.error(f"Error registering plugin: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error registering plugin: {str(e)}")
    
    async def get_plugins(self) -> List[EnginePlugin]:
        """Get list of registered plugins."""
        return list(self.plugins.values())
    
    async def update_job_status(
        self,
        job_uuid: str,
        staged_file_path: str,
        engine: SeparationEngine,
        metadata: Dict[str, Any],
        trace_id: Optional[str] = None
    ):
        """Update job status in queue."""
        try:
            # Prepare metadata
            job_metadata = {
                "staged_file_path": staged_file_path,
                "engine": engine,
                "original_metadata": metadata
            }
            
            # Update job in queue
            async with aiohttp.ClientSession() as session:
                headers = {}
                if trace_id:
                    headers["X-Trace-ID"] = trace_id
                
                async with session.put(
                    f"{self.queue_service_url}/api/jobs/{job_uuid}",
                    json={
                        "status": "staged",
                        "metadata": job_metadata
                    },
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to update job status: {error_text}")
                    else:
                        logger.info(f"Updated job {job_uuid} status to staged")
        except Exception as e:
            logger.error(f"Error updating job status: {str(e)}")
    
    def run(self, host: str = "0.0.0.0", port: int = 8005):
        """Run the splitter-stager service."""
        # Add startup and shutdown events
        self.app.add_event_handler("startup", self.startup_event)
        self.app.add_event_handler("shutdown", self.shutdown_event)
        
        # Run the service
        super().run(host=host, port=port)


if __name__ == "__main__":
    # Get service port from environment
    port = int(os.getenv("SPLITTER_STAGER_PORT", "8005"))
    
    # Create and run service
    service = SplitterStagerService()
    service.run(port=port)
