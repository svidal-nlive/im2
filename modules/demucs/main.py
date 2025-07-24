"""
Demucs Service for IM2 Audio Processing Pipeline

This service:
1. Separates audio files into stems using Demucs
2. Supports different separation models (htdemucs, htdemucs_6s, htdemucs_ft)
3. Processes jobs from the queue
4. Provides health and metrics endpoints
"""

import os
import sys
import json
import logging
import asyncio
import time
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
logger = logging.getLogger("demucs")

class DemucsModel(str, Enum):
    """Supported Demucs separation models."""
    HTDEMUCS = "htdemucs"           # Standard model (4 stems)
    HTDEMUCS_6S = "htdemucs_6s"     # 6-stem model (vocals, drums, bass, guitar, piano, other)
    HTDEMUCS_FT = "htdemucs_ft"     # Fine-tuned model (4 stems)

class SeparationRequest(BaseModel):
    """Separation request model."""
    job_uuid: str = Field(..., description="Job UUID")
    input_file: str = Field(..., description="Input file path")
    output_dir: Optional[str] = Field(None, description="Output directory")
    model: DemucsModel = Field(default=DemucsModel.HTDEMUCS, description="Separation model")
    mp3: bool = Field(default=False, description="Use MP3 for output")
    mp3_bitrate: int = Field(default=320, description="MP3 bitrate")
    overlap: float = Field(default=0.25, description="Overlap ratio")
    shifts: int = Field(default=2, description="Number of shifts")

class SeparationResult(BaseModel):
    """Separation result model."""
    job_uuid: str = Field(..., description="Job UUID")
    input_file: str = Field(..., description="Input file path")
    output_dir: str = Field(..., description="Output directory")
    model: DemucsModel = Field(..., description="Separation model")
    stems: Dict[str, str] = Field(..., description="Stem file paths")
    duration: float = Field(..., description="Processing duration in seconds")
    timestamp: str = Field(..., description="Completion timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")

class DemucsService(BaseService):
    """Demucs service for audio stem separation."""
    
    def __init__(self):
        """Initialize the demucs service."""
        super().__init__(
            name="demucs",
            version="0.1.0",
            description="Audio separation service using Demucs",
            dependencies=["queue", "splitter-stager"]
        )
        
        # Configure settings
        self.input_path = os.getenv("DEMUCS_INPUT_PATH", "/pipeline-data/demucs-input")
        self.output_path = os.getenv("DEMUCS_OUTPUT_PATH", "/pipeline-data/demucs-output")
        self.queue_service_url = os.getenv("QUEUE_SERVICE_URL", "http://queue:8003")
        self.polling_interval = int(os.getenv("POLLING_INTERVAL", "5"))
        self.default_model = DemucsModel(os.getenv("DEFAULT_MODEL", DemucsModel.HTDEMUCS))
        
        # Job processing
        self.processing = False
        self.current_jobs = {}
        self.queue_polling_task = None
        
        # Create router
        router = APIRouter()
        
        # Additional routes
        router.post("/separate", response_model=SeparationResult)(self.separate_file)
        router.get("/models", response_model=List[str])(self.get_supported_models)
        router.post("/process-job/{job_uuid}", response_model=Dict[str, Any])(self.process_job)
        
        # Include router
        self.app.include_router(router, prefix="/api")
    
    async def startup_event(self):
        """FastAPI startup event."""
        # Create output directory if it doesn't exist
        os.makedirs(self.output_path, exist_ok=True)
        
        # Start job polling
        self.processing = True
        self.queue_polling_task = asyncio.create_task(self.poll_queue())
        
        logger.info("Demucs service started")
    
    async def shutdown_event(self):
        """FastAPI shutdown event."""
        # Stop job polling
        self.processing = False
        if self.queue_polling_task:
            self.queue_polling_task.cancel()
            try:
                await self.queue_polling_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Demucs service stopped")
    
    async def get_supported_models(self) -> List[str]:
        """Get list of supported separation models."""
        return [model.value for model in DemucsModel]
    
    async def poll_queue(self):
        """Poll queue for jobs to process."""
        logger.info("Starting job polling")
        
        while self.processing:
            try:
                # Check for available jobs in queue
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.queue_service_url}/api/jobs",
                        params={
                            "status": "staged",
                            "engine": "demucs",
                            "limit": 5
                        }
                    ) as response:
                        if response.status != 200:
                            logger.error(f"Failed to fetch jobs: {await response.text()}")
                        else:
                            data = await response.json()
                            jobs = data.get("jobs", [])
                            
                            # Process available jobs
                            for job in jobs:
                                job_uuid = job.get("uuid")
                                
                                # Skip jobs that are already being processed
                                if job_uuid in self.current_jobs:
                                    continue
                                
                                # Start processing job
                                logger.info(f"Found job {job_uuid}, starting processing")
                                asyncio.create_task(self.process_queued_job(job))
            
            except Exception as e:
                logger.error(f"Error polling queue: {str(e)}")
            
            # Sleep before polling again
            await asyncio.sleep(self.polling_interval)
    
    async def process_queued_job(self, job: Dict[str, Any]):
        """Process a job from the queue."""
        job_uuid = job.get("uuid")
        metadata = job.get("metadata", {})
        
        try:
            # Mark job as processing
            self.current_jobs[job_uuid] = "processing"
            
            # Update job status in queue
            await self.update_job_status(job_uuid, "processing")
            
            # Get file path from metadata
            file_path = metadata.get("staged_file_path")
            if not file_path:
                raise ValueError("No staged file path in metadata")
            
            # Create output directory
            user_id = job.get("user_id", "unknown")
            output_dir = os.path.join(self.output_path, user_id, job_uuid)
            os.makedirs(output_dir, exist_ok=True)
            
            # Determine model from metadata or use default
            model = metadata.get("model", self.default_model)
            
            # Process the file
            result = await self.separate_audio(
                job_uuid=job_uuid,
                input_file=file_path,
                output_dir=output_dir,
                model=model
            )
            
            # Update job with result
            await self.update_job_status(
                job_uuid=job_uuid,
                status="completed",
                metadata={
                    "output_dir": output_dir,
                    "stems": result.stems,
                    "processing_time": result.duration
                }
            )
            
            logger.info(f"Job {job_uuid} completed successfully")
        
        except Exception as e:
            logger.error(f"Error processing job {job_uuid}: {str(e)}")
            
            # Update job status to failed
            await self.update_job_status(
                job_uuid=job_uuid,
                status="failed",
                metadata={"error": str(e)}
            )
        
        finally:
            # Remove job from current jobs
            if job_uuid in self.current_jobs:
                del self.current_jobs[job_uuid]
    
    async def process_job(self, job_uuid: str) -> Dict[str, Any]:
        """Process a specific job."""
        try:
            # Get job details from queue
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.queue_service_url}/api/jobs/{job_uuid}"
                ) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Job {job_uuid} not found"
                        )
                    
                    job = await response.json()
            
            # Check if job is already being processed
            if job_uuid in self.current_jobs:
                return {"status": "already_processing", "job_uuid": job_uuid}
            
            # Start processing job
            asyncio.create_task(self.process_queued_job(job))
            
            return {"status": "processing_started", "job_uuid": job_uuid}
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error starting job {job_uuid}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error starting job: {str(e)}"
            )
    
    async def separate_file(self, request: Request) -> SeparationResult:
        """Separate a single file on demand."""
        try:
            # Get request body
            body = await request.json()
            
            # Create separation request
            separation_request = SeparationRequest(**body)
            
            # Check if input file exists
            if not os.path.exists(separation_request.input_file):
                raise HTTPException(
                    status_code=404,
                    detail=f"Input file not found: {separation_request.input_file}"
                )
            
            # Create output directory if not provided
            if not separation_request.output_dir:
                separation_request.output_dir = os.path.join(
                    self.output_path,
                    "direct",
                    separation_request.job_uuid
                )
            
            # Ensure output directory exists
            os.makedirs(separation_request.output_dir, exist_ok=True)
            
            # Separate audio
            return await self.separate_audio(
                job_uuid=separation_request.job_uuid,
                input_file=separation_request.input_file,
                output_dir=separation_request.output_dir,
                model=separation_request.model,
                mp3=separation_request.mp3,
                mp3_bitrate=separation_request.mp3_bitrate,
                overlap=separation_request.overlap,
                shifts=separation_request.shifts
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error separating file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error separating file: {str(e)}"
            )
    
    async def separate_audio(
        self,
        job_uuid: str,
        input_file: str,
        output_dir: str,
        model: str = DemucsModel.HTDEMUCS,
        mp3: bool = False,
        mp3_bitrate: int = 320,
        overlap: float = 0.25,
        shifts: int = 2
    ) -> SeparationResult:
        """Separate audio using Demucs."""
        try:
            # Record start time
            start_time = time.time()
            
            # Ensure model is valid
            if isinstance(model, str):
                model = DemucsModel(model)
            
            # Prepare stem names based on model
            if model == DemucsModel.HTDEMUCS_6S:
                stem_names = ["vocals", "drums", "bass", "guitar", "piano", "other"]
            else:
                stem_names = ["vocals", "drums", "bass", "other"]
            
            # Define command
            command = [
                "demucs",
                "--out", output_dir,
                "--model", model,
                "--overlap", str(overlap),
                "--shifts", str(shifts),
                "--jobs", "4"  # Number of parallel jobs
            ]
            
            # Add MP3 output if requested
            if mp3:
                command.extend(["--mp3", "--mp3-bitrate", str(mp3_bitrate)])
            
            # Add input file
            command.append(input_file)
            
            # Execute command using asyncio.subprocess
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for process to complete
            stdout, stderr = await proc.communicate()
            
            # Check for errors
            if proc.returncode != 0:
                logger.error(f"Demucs command failed: {stderr.decode()}")
                raise RuntimeError(f"Demucs command failed: {stderr.decode()}")
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Get output file paths
            stems = {}
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            extension = "mp3" if mp3 else "wav"
            
            # Demucs outputs to a folder named after the model
            output_subdir = os.path.join(output_dir, model, base_name)
            
            for stem in stem_names:
                stem_file = os.path.join(output_subdir, f"{stem}.{extension}")
                if os.path.exists(stem_file):
                    stems[stem] = stem_file
            
            # Create result
            result = SeparationResult(
                job_uuid=job_uuid,
                input_file=input_file,
                output_dir=output_dir,
                model=model,
                stems=stems,
                duration=duration,
                timestamp=datetime.now().isoformat()
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error separating audio: {str(e)}")
            
            # Create error result
            return SeparationResult(
                job_uuid=job_uuid,
                input_file=input_file,
                output_dir=output_dir,
                model=model,
                stems={},
                duration=0.0,
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    async def update_job_status(
        self,
        job_uuid: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update job status in queue."""
        try:
            update_data = {"status": status}
            if metadata:
                update_data["metadata"] = metadata
            
            # Update job in queue
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{self.queue_service_url}/api/jobs/{job_uuid}",
                    json=update_data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to update job status: {error_text}")
                    else:
                        logger.info(f"Updated job {job_uuid} status to {status}")
        except Exception as e:
            logger.error(f"Error updating job status: {str(e)}")
    
    def run(self, host: str = "0.0.0.0", port: int = 8007):
        """Run the demucs service."""
        # Add startup and shutdown events
        self.app.add_event_handler("startup", self.startup_event)
        self.app.add_event_handler("shutdown", self.shutdown_event)
        
        # Run the service
        super().run(host=host, port=port)


if __name__ == "__main__":
    # Get service port from environment
    port = int(os.getenv("DEMUCS_PORT", "8007"))
    
    # Create and run service
    service = DemucsService()
    service.run(port=port)
