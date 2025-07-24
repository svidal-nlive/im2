"""
Output Organizer Service for IM2 Audio Processing Pipeline

This service:
1. Organizes processed audio files into appropriate directory structures
2. Handles archiving original files
3. Applies naming conventions and metadata-based organization
4. Cleans up temporary files
5. Provides health and metrics endpoints
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
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC

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
logger = logging.getLogger("output-organizer")

class OrganizationType(str, Enum):
    """Types of organization structures."""
    ARTIST_ALBUM = "artist_album"         # Artist/Album/Tracks
    GENRE_ARTIST = "genre_artist"         # Genre/Artist/Album/Tracks
    YEAR_ALBUM = "year_album"             # Year/Album/Tracks
    TYPE_ARTIST = "type_artist"           # Type/Artist/Album/Tracks (Type = instrumental, vocal, etc.)
    FLAT = "flat"                         # All in a single directory with prefixes

class OrganizationRequest(BaseModel):
    """Organization request model."""
    job_uuid: str = Field(..., description="Job UUID")
    input_files: Dict[str, str] = Field(..., description="Input files by type")
    original_file: Optional[str] = Field(None, description="Original file path")
    output_dir: Optional[str] = Field(None, description="Base output directory")
    organization_type: OrganizationType = Field(default=OrganizationType.ARTIST_ALBUM, description="Organization structure type")
    archive_original: bool = Field(default=True, description="Archive original file")
    generate_playlists: bool = Field(default=False, description="Generate M3U playlists")
    clean_temp_files: bool = Field(default=True, description="Clean temporary files")

class OrganizationResult(BaseModel):
    """Organization result model."""
    job_uuid: str = Field(..., description="Job UUID")
    organized_files: Dict[str, str] = Field(..., description="Organized file paths by type")
    archived_original: Optional[str] = Field(None, description="Archived original path")
    playlists: Dict[str, str] = Field(default_factory=dict, description="Generated playlist paths")
    duration: float = Field(..., description="Processing duration in seconds")
    timestamp: str = Field(..., description="Completion timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")

class OutputOrganizerService(BaseService):
    """Output Organizer service for final file organization and cleanup."""
    
    def __init__(self):
        """Initialize the output organizer service."""
        super().__init__(
            name="output-organizer",
            version="0.1.0",
            description="Output organization service for IM2 Audio Processing Pipeline",
            dependencies=["queue", "audio-recon"]
        )
        
        # Configure settings
        self.recon_input_path = os.getenv("RECON_OUTPUT_PATH", "/pipeline-data/recon-output")
        self.output_path = os.getenv("OUTPUT_PATH", "/pipeline-data/output")
        self.archive_path = os.getenv("ARCHIVE_PATH", "/pipeline-data/archive")
        self.queue_service_url = os.getenv("QUEUE_SERVICE_URL", "http://queue:8003")
        self.polling_interval = int(os.getenv("POLLING_INTERVAL", "5"))
        self.default_organization = OrganizationType(os.getenv("DEFAULT_ORGANIZATION", OrganizationType.ARTIST_ALBUM))
        
        # Job processing
        self.processing = False
        self.current_jobs = {}
        self.queue_polling_task = None
        
        # Create router
        router = APIRouter()
        
        # Additional routes
        router.post("/organize", response_model=OrganizationResult)(self.organize_files)
        router.get("/organization-types", response_model=List[str])(self.get_organization_types)
        router.post("/process-job/{job_uuid}", response_model=Dict[str, Any])(self.process_job)
        
        # Include router
        self.app.include_router(router, prefix="/api")
    
    async def startup_event(self):
        """FastAPI startup event."""
        # Create output directories if they don't exist
        os.makedirs(self.output_path, exist_ok=True)
        os.makedirs(self.archive_path, exist_ok=True)
        
        # Start job polling
        self.processing = True
        self.queue_polling_task = asyncio.create_task(self.poll_queue())
        
        logger.info("Output Organizer service started")
    
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
        
        logger.info("Output Organizer service stopped")
    
    async def get_organization_types(self) -> List[str]:
        """Get list of supported organization types."""
        return [org.value for org in OrganizationType]
    
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
                            "status": "recon-completed",
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
                                logger.info(f"Found job {job_uuid}, starting organization")
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
            await self.update_job_status(job_uuid, "organizing")
            
            # Get input files from metadata
            input_files = {}
            recon_metadata = metadata.get("output_files", {})
            for key, path in recon_metadata.items():
                input_files[key] = path
            
            if not input_files:
                raise ValueError("No input files found in metadata")
            
            # Get original file path
            job_history = job.get("history", [])
            original_file = None
            for step in job_history:
                if step.get("status") == "new":
                    original_metadata = step.get("metadata", {})
                    original_file = original_metadata.get("file_path")
                    break
            
            # Process the job
            result = await self.organize_output_files(
                job_uuid=job_uuid,
                input_files=input_files,
                original_file=original_file,
                organization_type=self.default_organization,
                user_id=job.get("user_id", "unknown")
            )
            
            # Update job with result
            await self.update_job_status(
                job_uuid=job_uuid,
                status="completed",
                metadata={
                    "organized_files": result.organized_files,
                    "archived_original": result.archived_original,
                    "playlists": result.playlists
                }
            )
            
            logger.info(f"Job {job_uuid} organization completed successfully")
        
        except Exception as e:
            logger.error(f"Error processing job {job_uuid}: {str(e)}")
            
            # Update job status to failed
            await self.update_job_status(
                job_uuid=job_uuid,
                status="organizing-failed",
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
    
    async def organize_files(self, request: Request) -> OrganizationResult:
        """Organize files on demand."""
        try:
            # Get request body
            body = await request.json()
            
            # Create organization request
            organization_request = OrganizationRequest(**body)
            
            # Process the request
            return await self.organize_output_files(
                job_uuid=organization_request.job_uuid,
                input_files=organization_request.input_files,
                original_file=organization_request.original_file,
                output_dir=organization_request.output_dir,
                organization_type=organization_request.organization_type,
                archive_original=organization_request.archive_original,
                generate_playlists=organization_request.generate_playlists,
                clean_temp_files=organization_request.clean_temp_files
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error organizing files: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error organizing files: {str(e)}"
            )
    
    async def organize_output_files(
        self,
        job_uuid: str,
        input_files: Dict[str, str],
        original_file: Optional[str] = None,
        output_dir: Optional[str] = None,
        organization_type: Union[OrganizationType, str] = OrganizationType.ARTIST_ALBUM,
        user_id: str = "unknown",
        archive_original: bool = True,
        generate_playlists: bool = False,
        clean_temp_files: bool = True
    ) -> OrganizationResult:
        """Organize output files according to specified structure."""
        try:
            # Record start time
            start_time = time.time()
            
            # Ensure organization_type is enum
            if isinstance(organization_type, str):
                organization_type = OrganizationType(organization_type)
            
            # Set output directory if not provided
            if not output_dir:
                output_dir = os.path.join(self.output_path, user_id)
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Extract metadata from first input file for organization
            metadata = await self.extract_metadata(next(iter(input_files.values())))
            
            # Determine directory structure based on organization type
            org_path = await self.build_organization_path(
                metadata=metadata,
                organization_type=organization_type,
                base_dir=output_dir
            )
            
            # Ensure organization path exists
            os.makedirs(org_path, exist_ok=True)
            
            # Move and rename output files
            organized_files = {}
            for file_type, file_path in input_files.items():
                if not os.path.exists(file_path):
                    logger.warning(f"Input file not found: {file_path}")
                    continue
                
                # Get file extension
                _, ext = os.path.splitext(file_path)
                
                # Create organized filename
                filename = await self.build_filename(metadata, file_type, ext)
                
                # Create destination path
                dest_path = os.path.join(org_path, filename)
                
                # Copy file to destination
                await self.safe_copy_file(file_path, dest_path)
                
                # Add to organized files
                organized_files[file_type] = dest_path
            
            # Archive original file if requested
            archived_original = None
            if archive_original and original_file and os.path.exists(original_file):
                archived_original = await self.archive_original_file(
                    original_file=original_file,
                    metadata=metadata,
                    user_id=user_id
                )
            
            # Generate playlists if requested
            playlists = {}
            if generate_playlists and organized_files:
                playlists = await self.generate_playlists(
                    organized_files=organized_files,
                    org_path=org_path,
                    metadata=metadata
                )
            
            # Clean temporary files if requested
            if clean_temp_files:
                await self.clean_temporary_files(
                    job_uuid=job_uuid,
                    input_files=input_files
                )
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Create result
            result = OrganizationResult(
                job_uuid=job_uuid,
                organized_files=organized_files,
                archived_original=archived_original,
                playlists=playlists,
                duration=duration,
                timestamp=datetime.now().isoformat()
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error organizing output files: {str(e)}")
            
            # Create error result
            return OrganizationResult(
                job_uuid=job_uuid,
                organized_files={},
                duration=0.0,
                timestamp=datetime.now().isoformat(),
                error=str(e)
            )
    
    async def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from an audio file."""
        metadata = {
            "artist": "Unknown Artist",
            "album": "Unknown Album",
            "title": "Unknown Title",
            "genre": "Unknown",
            "year": "Unknown",
            "track": "00"
        }
        
        try:
            # Get file extension
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            if ext == ".mp3":
                audio = MP3(file_path)
                
                if audio.tags:
                    # Extract ID3 tags
                    tags = audio.tags
                    if "TPE1" in tags:  # Artist
                        metadata["artist"] = str(tags["TPE1"])
                    if "TALB" in tags:  # Album
                        metadata["album"] = str(tags["TALB"])
                    if "TIT2" in tags:  # Title
                        metadata["title"] = str(tags["TIT2"])
                    if "TCON" in tags:  # Genre
                        metadata["genre"] = str(tags["TCON"])
                    if "TDRC" in tags:  # Year
                        metadata["year"] = str(tags["TDRC"])
                    if "TRCK" in tags:  # Track
                        metadata["track"] = str(tags["TRCK"])
            
            elif ext == ".flac":
                audio = FLAC(file_path)
                
                # Extract FLAC tags
                if "artist" in audio:
                    metadata["artist"] = audio["artist"][0]
                if "album" in audio:
                    metadata["album"] = audio["album"][0]
                if "title" in audio:
                    metadata["title"] = audio["title"][0]
                if "genre" in audio:
                    metadata["genre"] = audio["genre"][0]
                if "date" in audio:
                    metadata["year"] = audio["date"][0]
                if "tracknumber" in audio:
                    metadata["track"] = audio["tracknumber"][0]
            
            # If we couldn't extract a title, use the filename
            if metadata["title"] == "Unknown Title":
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                metadata["title"] = base_name
        
        except Exception as e:
            logger.warning(f"Error extracting metadata from {file_path}: {str(e)}")
            
            # If we can't extract metadata, use the filename for title
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            metadata["title"] = base_name
        
        return metadata
    
    async def build_organization_path(
        self,
        metadata: Dict[str, Any],
        organization_type: OrganizationType,
        base_dir: str
    ) -> str:
        """Build the organization path based on metadata and organization type."""
        if organization_type == OrganizationType.ARTIST_ALBUM:
            # Artist/Album
            artist_dir = await self.sanitize_path(metadata.get("artist", "Unknown Artist"))
            album_dir = await self.sanitize_path(metadata.get("album", "Unknown Album"))
            return os.path.join(base_dir, artist_dir, album_dir)
        
        elif organization_type == OrganizationType.GENRE_ARTIST:
            # Genre/Artist/Album
            genre_dir = await self.sanitize_path(metadata.get("genre", "Unknown Genre"))
            artist_dir = await self.sanitize_path(metadata.get("artist", "Unknown Artist"))
            album_dir = await self.sanitize_path(metadata.get("album", "Unknown Album"))
            return os.path.join(base_dir, genre_dir, artist_dir, album_dir)
        
        elif organization_type == OrganizationType.YEAR_ALBUM:
            # Year/Album
            year_dir = await self.sanitize_path(metadata.get("year", "Unknown Year"))
            album_dir = await self.sanitize_path(metadata.get("album", "Unknown Album"))
            return os.path.join(base_dir, year_dir, album_dir)
        
        elif organization_type == OrganizationType.TYPE_ARTIST:
            # Type/Artist/Album
            file_type = "Instrumental"  # Default to instrumental
            artist_dir = await self.sanitize_path(metadata.get("artist", "Unknown Artist"))
            album_dir = await self.sanitize_path(metadata.get("album", "Unknown Album"))
            return os.path.join(base_dir, file_type, artist_dir, album_dir)
        
        elif organization_type == OrganizationType.FLAT:
            # Flat structure (just the base directory)
            return base_dir
        
        else:
            # Default to Artist/Album
            artist_dir = await self.sanitize_path(metadata.get("artist", "Unknown Artist"))
            album_dir = await self.sanitize_path(metadata.get("album", "Unknown Album"))
            return os.path.join(base_dir, artist_dir, album_dir)
    
    async def build_filename(
        self,
        metadata: Dict[str, Any],
        file_type: str,
        extension: str
    ) -> str:
        """Build a filename based on metadata and file type."""
        # Get track number and pad with zeros
        track = metadata.get("track", "00")
        if isinstance(track, str) and "/" in track:
            # Handle "01/12" format
            track = track.split("/")[0]
        
        try:
            track_num = int(track)
            track_str = f"{track_num:02d}"
        except (ValueError, TypeError):
            track_str = "00"
        
        # Get title
        title = metadata.get("title", "Unknown Title")
        
        # Sanitize title
        title = await self.sanitize_filename(title)
        
        # Determine suffix based on file type
        suffix = ""
        if file_type == "karaoke":
            suffix = " (Instrumental)"
        elif file_type == "vocals_only":
            suffix = " (Vocals Only)"
        elif file_type == "drums_bass":
            suffix = " (Drums & Bass)"
        elif file_type == "custom":
            suffix = " (Custom Mix)"
        
        # Build filename
        filename = f"{track_str} - {title}{suffix}{extension}"
        
        return filename
    
    async def safe_copy_file(self, source_path: str, dest_path: str) -> bool:
        """Safely copy a file with error handling."""
        try:
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Check if destination file already exists
            if os.path.exists(dest_path):
                # Add a timestamp to make it unique
                base, ext = os.path.splitext(dest_path)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                dest_path = f"{base}_{timestamp}{ext}"
            
            # Copy the file
            shutil.copy2(source_path, dest_path)
            
            logger.info(f"Copied {source_path} to {dest_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error copying file from {source_path} to {dest_path}: {str(e)}")
            return False
    
    async def archive_original_file(
        self,
        original_file: str,
        metadata: Dict[str, Any],
        user_id: str
    ) -> Optional[str]:
        """Archive the original file."""
        try:
            # Create archive path
            archive_base = os.path.join(self.archive_path, user_id)
            
            # Build archive path based on artist/album
            artist_dir = await self.sanitize_path(metadata.get("artist", "Unknown Artist"))
            album_dir = await self.sanitize_path(metadata.get("album", "Unknown Album"))
            archive_dir = os.path.join(archive_base, artist_dir, album_dir)
            
            # Ensure archive directory exists
            os.makedirs(archive_dir, exist_ok=True)
            
            # Get original filename
            original_filename = os.path.basename(original_file)
            
            # Create archive file path
            archive_path = os.path.join(archive_dir, original_filename)
            
            # Check if file already exists in archive
            if os.path.exists(archive_path):
                # Add a timestamp to make it unique
                base, ext = os.path.splitext(archive_path)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                archive_path = f"{base}_{timestamp}{ext}"
            
            # Copy file to archive
            shutil.copy2(original_file, archive_path)
            
            logger.info(f"Archived original file {original_file} to {archive_path}")
            
            return archive_path
        
        except Exception as e:
            logger.error(f"Error archiving original file {original_file}: {str(e)}")
            return None
    
    async def generate_playlists(
        self,
        organized_files: Dict[str, str],
        org_path: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate M3U playlists for organized files."""
        playlists = {}
        
        try:
            # Get album and artist info
            artist = metadata.get("artist", "Unknown Artist")
            album = metadata.get("album", "Unknown Album")
            
            # Create playlist name
            playlist_name = f"{artist} - {album}"
            playlist_name = await self.sanitize_filename(playlist_name)
            
            # Create different playlists for different types
            for file_type, file_path in organized_files.items():
                # Skip if file doesn't exist
                if not os.path.exists(file_path):
                    continue
                
                # Create playlist filename
                playlist_filename = f"{playlist_name} - {file_type}.m3u"
                playlist_path = os.path.join(org_path, playlist_filename)
                
                # Create playlist content
                content = "#EXTM3U\n"
                
                # Add file to playlist (using relative path)
                rel_path = os.path.basename(file_path)
                content += f"{rel_path}\n"
                
                # Write playlist file
                async with aiofiles.open(playlist_path, "w") as f:
                    await f.write(content)
                
                # Add to playlists
                playlists[file_type] = playlist_path
            
            # Also create a combined playlist with all files
            if len(organized_files) > 1:
                combined_playlist = f"{playlist_name} - All Files.m3u"
                combined_path = os.path.join(org_path, combined_playlist)
                
                # Create combined playlist content
                content = "#EXTM3U\n"
                
                # Add all files to playlist
                for file_path in organized_files.values():
                    # Skip if file doesn't exist
                    if not os.path.exists(file_path):
                        continue
                    
                    # Add file to playlist (using relative path)
                    rel_path = os.path.basename(file_path)
                    content += f"{rel_path}\n"
                
                # Write combined playlist file
                async with aiofiles.open(combined_path, "w") as f:
                    await f.write(content)
                
                # Add to playlists
                playlists["combined"] = combined_path
        
        except Exception as e:
            logger.error(f"Error generating playlists: {str(e)}")
        
        return playlists
    
    async def clean_temporary_files(
        self,
        job_uuid: str,
        input_files: Dict[str, str]
    ):
        """Clean up temporary files after organization."""
        try:
            # Collect directories to check for cleanup
            directories = set()
            
            # Add input file directories
            for file_path in input_files.values():
                if os.path.exists(file_path):
                    directories.add(os.path.dirname(file_path))
            
            # Check each directory
            for directory in directories:
                # Only clean directories containing the job UUID
                if job_uuid in directory:
                    # Check if directory is empty after removing input files
                    remaining_files = [
                        f for f in os.listdir(directory) 
                        if os.path.isfile(os.path.join(directory, f)) and 
                        os.path.join(directory, f) not in input_files.values()
                    ]
                    
                    # If no other files, remove the directory
                    if not remaining_files:
                        try:
                            shutil.rmtree(directory)
                            logger.info(f"Cleaned up temporary directory: {directory}")
                        except Exception as e:
                            logger.warning(f"Failed to remove directory {directory}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error cleaning temporary files: {str(e)}")
    
    async def sanitize_path(self, path: str) -> str:
        """Sanitize a path segment."""
        if not path:
            return "Unknown"
        
        # Replace invalid characters
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            path = path.replace(char, '_')
        
        # Remove leading/trailing whitespace and periods
        path = path.strip().strip('.')
        
        # Replace empty result with "Unknown"
        if not path:
            path = "Unknown"
        
        return path
    
    async def sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename."""
        if not filename:
            return "Unknown"
        
        # Replace invalid characters
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove leading/trailing whitespace and periods
        filename = filename.strip().strip('.')
        
        # Replace empty result with "Unknown"
        if not filename:
            filename = "Unknown"
        
        return filename
    
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
    
    def run(self, host: str = "0.0.0.0", port: int = 8009):
        """Run the output organizer service."""
        # Add startup and shutdown events
        self.app.add_event_handler("startup", self.startup_event)
        self.app.add_event_handler("shutdown", self.shutdown_event)
        
        # Run the service
        super().run(host=host, port=port)


if __name__ == "__main__":
    # Get service port from environment
    port = int(os.getenv("OUTPUT_ORGANIZER_PORT", "8009"))
    
    # Create and run service
    service = OutputOrganizerService()
    service.run(port=port)
