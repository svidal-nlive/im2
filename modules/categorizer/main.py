"""
Categorizer Service for IM2 Audio Processing Pipeline

This service:
1. Receives new files from the watcher service
2. Classifies and validates audio files
3. Updates job status in the queue
4. Provides health and metrics endpoints
"""

import os
import sys
import json
import logging
import asyncio
import time
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from enum import Enum
import mimetypes

import aiohttp
import aiofiles
from fastapi import FastAPI, HTTPException, APIRouter, Depends, Request, Response, BackgroundTasks, File, UploadFile
from pydantic import BaseModel, Field
from mutagen import File as MutagenFile

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
logger = logging.getLogger("categorizer")

class AudioFormat(str, Enum):
    """Supported audio formats."""
    MP3 = "mp3"
    FLAC = "flac"
    WAV = "wav"
    AAC = "aac"
    OGG = "ogg"
    UNKNOWN = "unknown"

class ValidationResult(BaseModel):
    """File validation result model."""
    is_valid: bool = Field(..., description="Whether the file is valid")
    format: AudioFormat = Field(..., description="Audio format")
    error: Optional[str] = Field(None, description="Error message if invalid")
    file_info: Dict[str, Any] = Field(default_factory=dict, description="File metadata")

class FileCategory(BaseModel):
    """File categorization result model."""
    job_uuid: str = Field(..., description="Job UUID")
    user_id: str = Field(..., description="User ID")
    file_path: str = Field(..., description="File path")
    filename: str = Field(..., description="Filename")
    format: AudioFormat = Field(..., description="Audio format")
    is_valid: bool = Field(..., description="Whether the file is valid")
    error: Optional[str] = Field(None, description="Error message if invalid")
    file_info: Dict[str, Any] = Field(default_factory=dict, description="File metadata")
    timestamp: str = Field(..., description="Categorization timestamp")

class CategorizerService(BaseService):
    """Categorizer service for classifying and validating audio files."""
    
    def __init__(self):
        """Initialize the categorizer service."""
        super().__init__(
            name="categorizer",
            version="0.1.0",
            description="File categorization service for IM2 Audio Processing Pipeline",
            dependencies=["queue"]
        )
        
        # Configure settings
        self.input_path = os.getenv("INPUT_PATH", "/pipeline-data/input")
        self.error_path = os.getenv("ERROR_PATH", "/pipeline-data/error")
        self.queue_service_url = os.getenv("QUEUE_SERVICE_URL", "http://queue:8003")
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE_MB", "500")) * 1024 * 1024  # Convert MB to bytes
        
        # Create router
        router = APIRouter()
        
        # Additional routes
        router.post("/categorize", response_model=FileCategory)(self.categorize_file)
        router.post("/upload", response_model=FileCategory)(self.upload_file)
        router.get("/formats", response_model=List[str])(self.get_supported_formats)
        
        # Include router
        self.app.include_router(router, prefix="/api")
    
    async def validate_audio_file(self, file_path: str) -> ValidationResult:
        """Validate an audio file and determine its format."""
        try:
            # Check if file exists
            path = Path(file_path)
            if not path.exists():
                return ValidationResult(
                    is_valid=False,
                    format=AudioFormat.UNKNOWN,
                    error="File not found"
                )
            
            # Check file size
            file_size = path.stat().st_size
            if file_size > self.max_file_size:
                return ValidationResult(
                    is_valid=False,
                    format=AudioFormat.UNKNOWN,
                    error=f"File exceeds maximum size of {self.max_file_size // (1024*1024)} MB"
                )
            
            # Check file format using mutagen
            try:
                audio_file = MutagenFile(file_path)
                if audio_file is None:
                    return ValidationResult(
                        is_valid=False,
                        format=AudioFormat.UNKNOWN,
                        error="Unsupported audio format"
                    )
                
                # Determine format
                format_type = AudioFormat.UNKNOWN
                file_info = {}
                
                # Get file extension
                file_ext = path.suffix.lower().lstrip('.')
                
                if file_ext in ['mp3'] or (hasattr(audio_file, 'mime') and 'audio/mpeg' in audio_file.mime):
                    format_type = AudioFormat.MP3
                elif file_ext in ['flac'] or (hasattr(audio_file, 'mime') and 'audio/flac' in audio_file.mime):
                    format_type = AudioFormat.FLAC
                elif file_ext in ['wav'] or (hasattr(audio_file, 'mime') and 'audio/wav' in audio_file.mime):
                    format_type = AudioFormat.WAV
                elif file_ext in ['aac', 'm4a'] or (hasattr(audio_file, 'mime') and 'audio/aac' in audio_file.mime):
                    format_type = AudioFormat.AAC
                elif file_ext in ['ogg'] or (hasattr(audio_file, 'mime') and 'audio/ogg' in audio_file.mime):
                    format_type = AudioFormat.OGG
                
                # Extract basic metadata
                if hasattr(audio_file, 'info'):
                    if hasattr(audio_file.info, 'length'):
                        file_info['duration'] = audio_file.info.length
                    if hasattr(audio_file.info, 'bitrate'):
                        file_info['bitrate'] = audio_file.info.bitrate
                    if hasattr(audio_file.info, 'sample_rate'):
                        file_info['sample_rate'] = audio_file.info.sample_rate
                    if hasattr(audio_file.info, 'channels'):
                        file_info['channels'] = audio_file.info.channels
                
                file_info['size'] = file_size
                
                return ValidationResult(
                    is_valid=True,
                    format=format_type,
                    file_info=file_info
                )
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    format=AudioFormat.UNKNOWN,
                    error=f"Error analyzing audio file: {str(e)}"
                )
                
        except Exception as e:
            logger.error(f"Error validating audio file: {str(e)}")
            return ValidationResult(
                is_valid=False,
                format=AudioFormat.UNKNOWN,
                error=f"Error validating file: {str(e)}"
            )
    
    async def categorize_file(self, request: Request, background_tasks: BackgroundTasks) -> FileCategory:
        """Categorize a file and update its status in the queue."""
        try:
            # Get request body
            body = await request.json()
            
            # Get required fields
            job_uuid = body.get("job_uuid")
            user_id = body.get("user_id")
            file_path = body.get("file_path")
            filename = body.get("filename")
            
            if not all([job_uuid, user_id, file_path, filename]):
                raise HTTPException(status_code=400, detail="Missing required fields")
            
            # Get trace ID from request
            trace_id = request.headers.get("X-Trace-ID")
            
            # Validate the file
            validation_result = await self.validate_audio_file(file_path)
            
            # Create categorization result
            category = FileCategory(
                job_uuid=job_uuid,
                user_id=user_id,
                file_path=file_path,
                filename=filename,
                format=validation_result.format,
                is_valid=validation_result.is_valid,
                error=validation_result.error,
                file_info=validation_result.file_info,
                timestamp=datetime.now().isoformat()
            )
            
            # Update job status in queue
            background_tasks.add_task(
                self.update_job_status,
                job_uuid,
                validation_result.is_valid,
                validation_result.format,
                validation_result.error,
                validation_result.file_info,
                trace_id
            )
            
            return category
        except Exception as e:
            logger.error(f"Error categorizing file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error categorizing file: {str(e)}")
    
    async def upload_file(self, background_tasks: BackgroundTasks, file: UploadFile = File(...), user_id: str = None) -> FileCategory:
        """Upload and categorize a file."""
        try:
            if not user_id:
                user_id = "default"
            
            # Generate job UUID
            job_uuid = f"{int(time.time() * 1000)}_{hashlib.md5(file.filename.encode()).hexdigest()[:8]}"
            
            # Create user directory if it doesn't exist
            user_dir = Path(self.input_path) / user_id / job_uuid
            user_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the file
            file_path = user_dir / file.filename
            
            async with aiofiles.open(file_path, 'wb') as out_file:
                # Read file in chunks to avoid memory issues
                while chunk := await file.read(1024 * 1024):  # 1MB chunks
                    await out_file.write(chunk)
            
            # Validate the file
            validation_result = await self.validate_audio_file(str(file_path))
            
            # If invalid, move to error directory
            if not validation_result.is_valid:
                error_dir = Path(self.error_path) / user_id / job_uuid
                error_dir.mkdir(parents=True, exist_ok=True)
                error_file_path = error_dir / file.filename
                
                # Move file to error directory
                file_path.rename(error_file_path)
                file_path = error_file_path
            
            # Create job in queue
            background_tasks.add_task(
                self.create_job,
                str(file_path),
                user_id,
                job_uuid,
                file.filename,
                validation_result.is_valid,
                validation_result.format,
                validation_result.error,
                validation_result.file_info
            )
            
            # Create categorization result
            category = FileCategory(
                job_uuid=job_uuid,
                user_id=user_id,
                file_path=str(file_path),
                filename=file.filename,
                format=validation_result.format,
                is_valid=validation_result.is_valid,
                error=validation_result.error,
                file_info=validation_result.file_info,
                timestamp=datetime.now().isoformat()
            )
            
            return category
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")
    
    async def get_supported_formats(self) -> List[str]:
        """Get list of supported audio formats."""
        return [format.value for format in AudioFormat if format != AudioFormat.UNKNOWN]
    
    async def update_job_status(
        self,
        job_uuid: str,
        is_valid: bool,
        format: AudioFormat,
        error: Optional[str],
        file_info: Dict[str, Any],
        trace_id: Optional[str] = None
    ):
        """Update job status in queue."""
        try:
            # Prepare metadata
            metadata = {
                "format": format,
                "file_info": file_info
            }
            
            # Prepare status update
            if is_valid:
                status = "categorized"
            else:
                status = "failed"
            
            # Update job in queue
            async with aiohttp.ClientSession() as session:
                headers = {}
                if trace_id:
                    headers["X-Trace-ID"] = trace_id
                
                async with session.put(
                    f"{self.queue_service_url}/api/jobs/{job_uuid}",
                    json={
                        "status": status,
                        "metadata": metadata,
                        "error": error
                    },
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to update job status: {error_text}")
                    else:
                        logger.info(f"Updated job {job_uuid} status to {status}")
        except Exception as e:
            logger.error(f"Error updating job status: {str(e)}")
    
    async def create_job(
        self,
        file_path: str,
        user_id: str,
        job_uuid: str,
        filename: str,
        is_valid: bool,
        format: AudioFormat,
        error: Optional[str],
        file_info: Dict[str, Any]
    ):
        """Create a new job in queue."""
        try:
            # Generate trace ID
            trace_id = f"{int(time.time() * 1000)}-{job_uuid}"
            
            # Create job in queue
            async with aiohttp.ClientSession() as session:
                headers = {"X-Trace-ID": trace_id}
                
                # Submit job
                async with session.post(
                    f"{self.queue_service_url}/api/jobs",
                    json={
                        "file_path": file_path,
                        "user_id": user_id,
                        "job_uuid": job_uuid,
                        "filename": filename,
                        "trace_id": trace_id
                    },
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to create job: {error_text}")
                        return
                    
                    logger.info(f"Created job {job_uuid}")
                
                # If job created successfully, update its status
                if is_valid:
                    # Prepare metadata
                    metadata = {
                        "format": format,
                        "file_info": file_info
                    }
                    
                    # Update status
                    async with session.put(
                        f"{self.queue_service_url}/api/jobs/{job_uuid}",
                        json={
                            "status": "categorized",
                            "metadata": metadata
                        },
                        headers=headers
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Failed to update job status: {error_text}")
                        else:
                            logger.info(f"Updated job {job_uuid} status to categorized")
                else:
                    # Update status to failed
                    async with session.put(
                        f"{self.queue_service_url}/api/jobs/{job_uuid}",
                        json={
                            "status": "failed",
                            "metadata": {"format": format},
                            "error": error
                        },
                        headers=headers
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Failed to update job status: {error_text}")
                        else:
                            logger.info(f"Updated job {job_uuid} status to failed")
        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
    
    def run(self, host: str = "0.0.0.0", port: int = 8002):
        """Run the categorizer service."""
        # Run the service
        super().run(host=host, port=port)


if __name__ == "__main__":
    # Get service port from environment
    port = int(os.getenv("CATEGORIZER_PORT", "8002"))
    
    # Create and run service
    service = CategorizerService()
    service.run(port=port)
