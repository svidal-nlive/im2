"""
Audio-Recon Service for IM2 Audio Processing Pipeline

This service:
1. Recombines stems as needed for various outputs
2. Applies original metadata and artwork to new files
3. Processes completed separation jobs from the queue
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
import mutagen
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3
from mutagen.flac import FLAC, Picture
from PIL import Image
from io import BytesIO

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
logger = logging.getLogger("audio-recon")

class ReconType(str, Enum):
    """Types of recombination operations."""
    KARAOKE = "karaoke"               # Instrumental (no vocals)
    VOCALS_ONLY = "vocals_only"       # Vocals only
    DRUMS_BASS = "drums_bass"         # Drums and bass only
    CUSTOM = "custom"                 # Custom stem combination

class RecombinationRequest(BaseModel):
    """Recombination request model."""
    job_uuid: str = Field(..., description="Job UUID")
    engine: str = Field(..., description="Source engine (spleeter/demucs)")
    stems_dir: str = Field(..., description="Directory containing stems")
    output_dir: Optional[str] = Field(None, description="Output directory")
    recon_types: List[ReconType] = Field(default=[ReconType.KARAOKE], description="Types of recombinations to perform")
    custom_stems: Optional[Dict[str, List[str]]] = Field(None, description="Custom stem combinations")
    apply_metadata: bool = Field(default=True, description="Apply original metadata to outputs")
    apply_artwork: bool = Field(default=True, description="Apply original artwork to outputs")
    output_format: str = Field(default="mp3", description="Output format")
    bitrate: str = Field(default="320k", description="Output bitrate for lossy formats")

class RecombinationResult(BaseModel):
    """Recombination result model."""
    job_uuid: str = Field(..., description="Job UUID")
    engine: str = Field(..., description="Source engine")
    output_files: Dict[str, str] = Field(..., description="Output file paths by type")
    duration: float = Field(..., description="Processing duration in seconds")
    timestamp: str = Field(..., description="Completion timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")

class AudioReconService(BaseService):
    """Audio-Recon service for stem recombination and metadata application."""
    
    def __init__(self):
        """Initialize the audio-recon service."""
        super().__init__(
            name="audio-recon",
            version="0.1.0",
            description="Audio recombination service for IM2 Audio Processing Pipeline",
            dependencies=["queue", "spleeter", "demucs"]
        )
        
        # Configure settings
        self.spleeter_input_path = os.getenv("SPLEETER_OUTPUT_PATH", "/pipeline-data/spleeter-output")
        self.demucs_input_path = os.getenv("DEMUCS_OUTPUT_PATH", "/pipeline-data/demucs-output")
        self.output_path = os.getenv("RECON_OUTPUT_PATH", "/pipeline-data/recon-output")
        self.queue_service_url = os.getenv("QUEUE_SERVICE_URL", "http://queue:8003")
        self.polling_interval = int(os.getenv("POLLING_INTERVAL", "5"))
        
        # Job processing
        self.processing = False
        self.current_jobs = {}
        self.queue_polling_task = None
        
        # Create router
        router = APIRouter()
        
        # Additional routes
        router.post("/recombine", response_model=RecombinationResult)(self.recombine_stems)
        router.get("/recon-types", response_model=List[str])(self.get_recon_types)
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
        
        logger.info("Audio-Recon service started")
    
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
        
        logger.info("Audio-Recon service stopped")
    
    async def get_recon_types(self) -> List[str]:
        """Get list of supported recombination types."""
        return [rt.value for rt in ReconType]
    
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
                            "status": "completed",
                            "service": ["spleeter", "demucs"],
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
            await self.update_job_status(job_uuid, "recon-processing")
            
            # Get engine info from metadata
            engine = metadata.get("engine", "spleeter")
            
            # Get stems directory from metadata
            stems_dir = metadata.get("output_dir")
            if not stems_dir:
                raise ValueError("No stems directory in metadata")
            
            # Get original metadata
            original_metadata = metadata.get("original_metadata", {})
            
            # Create output directory
            user_id = job.get("user_id", "unknown")
            output_dir = os.path.join(self.output_path, user_id, job_uuid)
            os.makedirs(output_dir, exist_ok=True)
            
            # Default to karaoke if no preference is specified
            recon_types = [ReconType.KARAOKE]
            
            # Process the file
            result = await self.recombine_audio(
                job_uuid=job_uuid,
                engine=engine,
                stems_dir=stems_dir,
                output_dir=output_dir,
                recon_types=recon_types,
                apply_metadata=True,
                apply_artwork=True,
                original_metadata=original_metadata
            )
            
            # Update job with result
            await self.update_job_status(
                job_uuid=job_uuid,
                status="recon-completed",
                metadata={
                    "output_dir": output_dir,
                    "output_files": result.output_files,
                    "processing_time": result.duration
                }
            )
            
            logger.info(f"Job {job_uuid} recombination completed successfully")
        
        except Exception as e:
            logger.error(f"Error processing job {job_uuid}: {str(e)}")
            
            # Update job status to failed
            await self.update_job_status(
                job_uuid=job_uuid,
                status="recon-failed",
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
    
    async def recombine_stems(self, request: Request) -> RecombinationResult:
        """Recombine stems on demand."""
        try:
            # Get request body
            body = await request.json()
            
            # Create recombination request
            recombination_request = RecombinationRequest(**body)
            
            # Check if stems directory exists
            if not os.path.exists(recombination_request.stems_dir):
                raise HTTPException(
                    status_code=404,
                    detail=f"Stems directory not found: {recombination_request.stems_dir}"
                )
            
            # Create output directory if not provided
            if not recombination_request.output_dir:
                recombination_request.output_dir = os.path.join(
                    self.output_path,
                    "direct",
                    recombination_request.job_uuid
                )
            
            # Ensure output directory exists
            os.makedirs(recombination_request.output_dir, exist_ok=True)
            
            # Recombine stems
            return await self.recombine_audio(
                job_uuid=recombination_request.job_uuid,
                engine=recombination_request.engine,
                stems_dir=recombination_request.stems_dir,
                output_dir=recombination_request.output_dir,
                recon_types=recombination_request.recon_types,
                custom_stems=recombination_request.custom_stems,
                apply_metadata=recombination_request.apply_metadata,
                apply_artwork=recombination_request.apply_artwork,
                output_format=recombination_request.output_format,
                bitrate=recombination_request.bitrate
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error recombining stems: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error recombining stems: {str(e)}"
            )
    
    async def recombine_audio(
        self,
        job_uuid: str,
        engine: str,
        stems_dir: str,
        output_dir: str,
        recon_types: List[Union[ReconType, str]] = [ReconType.KARAOKE],
        custom_stems: Optional[Dict[str, List[str]]] = None,
        apply_metadata: bool = True,
        apply_artwork: bool = True,
        original_metadata: Optional[Dict[str, Any]] = None,
        output_format: str = "mp3",
        bitrate: str = "320k"
    ) -> RecombinationResult:
        """Recombine audio stems."""
        try:
            # Record start time
            start_time = time.time()
            
            # Convert recon_types to enum if provided as strings
            recon_types = [
                rt if isinstance(rt, ReconType) else ReconType(rt)
                for rt in recon_types
            ]
            
            # Discover stems
            stems = await self.discover_stems(stems_dir, engine)
            if not stems:
                raise ValueError(f"No stems found in directory: {stems_dir}")
            
            # Determine source audio format
            first_stem = next(iter(stems.values()))
            source_format = os.path.splitext(first_stem)[1].lstrip('.')
            
            # Determine output format
            if output_format not in ["mp3", "wav", "flac"]:
                logger.warning(f"Unsupported output format: {output_format}, using mp3")
                output_format = "mp3"
            
            # Get file base name
            base_name = os.path.basename(stems_dir)
            if not base_name:
                base_name = f"recon_{job_uuid}"
            
            # Prepare output files
            output_files = {}
            
            # Process each recombination type
            for recon_type in recon_types:
                stems_to_combine = []
                output_name = ""
                
                if recon_type == ReconType.KARAOKE:
                    # All stems except vocals
                    stems_to_combine = [s for name, s in stems.items() if name != "vocals"]
                    output_name = f"{base_name}_instrumental"
                
                elif recon_type == ReconType.VOCALS_ONLY:
                    # Only vocals
                    if "vocals" in stems:
                        stems_to_combine = [stems["vocals"]]
                        output_name = f"{base_name}_vocals_only"
                    else:
                        logger.warning("No vocals stem found, skipping vocals-only recombination")
                        continue
                
                elif recon_type == ReconType.DRUMS_BASS:
                    # Only drums and bass
                    drum_bass_stems = []
                    if "drums" in stems:
                        drum_bass_stems.append(stems["drums"])
                    if "bass" in stems:
                        drum_bass_stems.append(stems["bass"])
                    
                    if drum_bass_stems:
                        stems_to_combine = drum_bass_stems
                        output_name = f"{base_name}_drums_bass"
                    else:
                        logger.warning("No drums or bass stems found, skipping drums-bass recombination")
                        continue
                
                elif recon_type == ReconType.CUSTOM:
                    # Custom stem combination
                    if not custom_stems or not custom_stems.get(recon_type):
                        logger.warning("No custom stems specified, skipping custom recombination")
                        continue
                    
                    # Get custom stem names for this type
                    custom_stem_names = custom_stems.get(recon_type, [])
                    custom_stem_files = [
                        stems[name] for name in custom_stem_names
                        if name in stems
                    ]
                    
                    if custom_stem_files:
                        stems_to_combine = custom_stem_files
                        stem_desc = "_".join(custom_stem_names)
                        output_name = f"{base_name}_{stem_desc}"
                    else:
                        logger.warning("No matching stems found for custom recombination")
                        continue
                
                # Skip if no stems to combine
                if not stems_to_combine:
                    logger.warning(f"No stems to combine for {recon_type}")
                    continue
                
                # Generate output file path
                output_file = os.path.join(output_dir, f"{output_name}.{output_format}")
                
                # Combine stems
                await self.combine_stems(
                    stems_to_combine,
                    output_file,
                    output_format,
                    bitrate
                )
                
                # Apply metadata and artwork if requested
                if apply_metadata or apply_artwork:
                    await self.apply_metadata_and_artwork(
                        output_file,
                        original_metadata,
                        apply_metadata,
                        apply_artwork,
                        recon_type
                    )
                
                # Add to output files
                output_files[recon_type] = output_file
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Create result
            result = RecombinationResult(
                job_uuid=job_uuid,
                engine=engine,
                output_files=output_files,
                duration=duration,
                timestamp=datetime.now().isoformat()
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error recombining audio: {str(e)}")
            
            # Create error result
            return RecombinationResult(
                job_uuid=job_uuid,
                engine=engine,
                output_files={},
                duration=0.0,
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    async def discover_stems(self, stems_dir: str, engine: str) -> Dict[str, str]:
        """Discover stems in the stems directory."""
        stems = {}
        
        try:
            # Different engines have different directory structures
            if engine == "spleeter":
                # Spleeter puts stems directly in the output directory
                for item in os.listdir(stems_dir):
                    item_path = os.path.join(stems_dir, item)
                    if os.path.isfile(item_path) and item_path.endswith((".wav", ".mp3")):
                        # Extract stem name from filename (vocals.wav, drums.wav, etc.)
                        stem_name = os.path.splitext(item)[0]
                        stems[stem_name] = item_path
            
            elif engine == "demucs":
                # Demucs organizes by model name and then filename
                # Find the model subdirectory
                model_dirs = [d for d in os.listdir(stems_dir) 
                             if os.path.isdir(os.path.join(stems_dir, d))]
                
                if not model_dirs:
                    raise ValueError(f"No model directories found in {stems_dir}")
                
                # Use the first model directory found
                model_dir = os.path.join(stems_dir, model_dirs[0])
                
                # Find the audio subdirectory (usually named after the original file)
                audio_dirs = [d for d in os.listdir(model_dir) 
                             if os.path.isdir(os.path.join(model_dir, d))]
                
                if not audio_dirs:
                    raise ValueError(f"No audio directories found in {model_dir}")
                
                # Use the first audio directory found
                audio_dir = os.path.join(model_dir, audio_dirs[0])
                
                # Get stems from audio directory
                for item in os.listdir(audio_dir):
                    item_path = os.path.join(audio_dir, item)
                    if os.path.isfile(item_path) and item_path.endswith((".wav", ".mp3")):
                        # Extract stem name from filename
                        stem_name = os.path.splitext(item)[0]
                        stems[stem_name] = item_path
            
            else:
                # For unknown engines, try to find any audio files
                for root, _, files in os.walk(stems_dir):
                    for file in files:
                        if file.endswith((".wav", ".mp3")):
                            # Try to extract stem name from filename
                            stem_name = os.path.splitext(file)[0]
                            stems[stem_name] = os.path.join(root, file)
        
        except Exception as e:
            logger.error(f"Error discovering stems: {str(e)}")
        
        return stems
    
    async def combine_stems(
        self,
        stem_files: List[str],
        output_file: str,
        output_format: str = "mp3",
        bitrate: str = "320k"
    ):
        """Combine stems into a single audio file using FFmpeg."""
        try:
            # Prepare FFmpeg command
            # Use filter_complex to mix multiple audio inputs
            filter_complex = f"amix=inputs={len(stem_files)}:duration=longest:dropout_transition=0"
            
            command = ["ffmpeg", "-y"]
            
            # Add input files
            for stem_file in stem_files:
                command.extend(["-i", stem_file])
            
            # Add filter complex
            command.extend(["-filter_complex", filter_complex])
            
            # Set output format parameters
            if output_format == "mp3":
                command.extend(["-b:a", bitrate])
            elif output_format == "flac":
                command.extend(["-sample_fmt", "s16", "-compression_level", "8"])
            
            # Add output file
            command.append(output_file)
            
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
                logger.error(f"FFmpeg command failed: {stderr.decode()}")
                raise RuntimeError(f"FFmpeg command failed: {stderr.decode()}")
            
            logger.info(f"Successfully combined {len(stem_files)} stems into {output_file}")
        
        except Exception as e:
            logger.error(f"Error combining stems: {str(e)}")
            raise
    
    async def apply_metadata_and_artwork(
        self,
        output_file: str,
        original_metadata: Optional[Dict[str, Any]] = None,
        apply_metadata: bool = True,
        apply_artwork: bool = True,
        recon_type: Optional[Union[ReconType, str]] = None
    ):
        """Apply metadata and artwork to output file."""
        try:
            # Skip if no original metadata
            if not original_metadata:
                logger.warning("No original metadata available, skipping metadata/artwork application")
                return
            
            # Get file extension
            ext = os.path.splitext(output_file)[1].lower()
            
            # Determine file type
            if ext == ".mp3":
                # MP3 file with ID3 tags
                audio = MP3(output_file)
                
                # Create ID3 if it doesn't exist
                if audio.tags is None:
                    audio.add_tags()
                
                # Apply metadata
                if apply_metadata:
                    # Copy common metadata fields
                    metadata = original_metadata.get("tags", {})
                    
                    for key, value in metadata.items():
                        if key in ["title", "artist", "album", "date", "genre"]:
                            # Modify title for different recombination types
                            if key == "title" and recon_type:
                                if isinstance(recon_type, str):
                                    recon_type = ReconType(recon_type)
                                
                                if recon_type == ReconType.KARAOKE:
                                    value = f"{value} (Instrumental)"
                                elif recon_type == ReconType.VOCALS_ONLY:
                                    value = f"{value} (Vocals Only)"
                                elif recon_type == ReconType.DRUMS_BASS:
                                    value = f"{value} (Drums & Bass)"
                                elif recon_type == ReconType.CUSTOM:
                                    value = f"{value} (Custom Mix)"
                            
                            # Set ID3 tag
                            tag_name = f"TPE1" if key == "artist" else f"TIT2" if key == "title" else f"TALB" if key == "album" else f"TDRC" if key == "date" else f"TCON"
                            audio.tags.add(getattr(mutagen.id3, tag_name)(encoding=3, text=value))
                
                # Apply artwork
                if apply_artwork and "artwork" in original_metadata:
                    artwork_path = original_metadata.get("artwork")
                    if artwork_path and os.path.exists(artwork_path):
                        with open(artwork_path, "rb") as f:
                            artwork_data = f.read()
                        
                        # Add artwork to ID3
                        audio.tags.add(
                            APIC(
                                encoding=3,  # UTF-8
                                mime="image/jpeg" if artwork_path.endswith(".jpg") else "image/png",
                                type=3,  # Cover (front)
                                desc="Cover",
                                data=artwork_data
                            )
                        )
                
                # Save changes
                audio.save()
            
            elif ext == ".flac":
                # FLAC file
                audio = FLAC(output_file)
                
                # Apply metadata
                if apply_metadata:
                    # Copy common metadata fields
                    metadata = original_metadata.get("tags", {})
                    
                    for key, value in metadata.items():
                        if key in ["title", "artist", "album", "date", "genre"]:
                            # Modify title for different recombination types
                            if key == "title" and recon_type:
                                if isinstance(recon_type, str):
                                    recon_type = ReconType(recon_type)
                                
                                if recon_type == ReconType.KARAOKE:
                                    value = f"{value} (Instrumental)"
                                elif recon_type == ReconType.VOCALS_ONLY:
                                    value = f"{value} (Vocals Only)"
                                elif recon_type == ReconType.DRUMS_BASS:
                                    value = f"{value} (Drums & Bass)"
                                elif recon_type == ReconType.CUSTOM:
                                    value = f"{value} (Custom Mix)"
                            
                            # Set FLAC tag
                            audio[key] = value
                
                # Apply artwork
                if apply_artwork and "artwork" in original_metadata:
                    artwork_path = original_metadata.get("artwork")
                    if artwork_path and os.path.exists(artwork_path):
                        with open(artwork_path, "rb") as f:
                            artwork_data = f.read()
                        
                        # Create Picture object
                        picture = Picture()
                        picture.data = artwork_data
                        picture.type = 3  # Cover (front)
                        picture.mime = "image/jpeg" if artwork_path.endswith(".jpg") else "image/png"
                        picture.desc = "Cover"
                        
                        # Add artwork to FLAC
                        audio.add_picture(picture)
                
                # Save changes
                audio.save()
            
            # WAV doesn't support embedded metadata
            
            logger.info(f"Applied metadata to {output_file}")
        
        except Exception as e:
            logger.warning(f"Error applying metadata: {str(e)}")
    
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
    
    def run(self, host: str = "0.0.0.0", port: int = 8008):
        """Run the audio-recon service."""
        # Add startup and shutdown events
        self.app.add_event_handler("startup", self.startup_event)
        self.app.add_event_handler("shutdown", self.shutdown_event)
        
        # Run the service
        super().run(host=host, port=port)


if __name__ == "__main__":
    # Get service port from environment
    port = int(os.getenv("AUDIO_RECON_PORT", "8008"))
    
    # Create and run service
    service = AudioReconService()
    service.run(port=port)
