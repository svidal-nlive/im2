"""
Metadata Service for IM2 Audio Processing Pipeline

This service:
1. Extracts metadata and artwork from audio files
2. Looks up additional metadata from external sources (MusicBrainz)
3. Caches artwork and metadata for future use
4. Updates job status in the queue
"""

import os
import sys
import json
import logging
import asyncio
import time
import hashlib
import base64
from io import BytesIO
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from enum import Enum

import aiohttp
import aiofiles
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, APIRouter, Depends, Request, Response, BackgroundTasks
from pydantic import BaseModel, Field
from mutagen import File as MutagenFile
from mutagen.id3 import ID3, APIC
from PIL import Image

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
logger = logging.getLogger("metadata-service")

class MetadataSource(str, Enum):
    """Metadata source enum."""
    FILE = "file"
    MUSICBRAINZ = "musicbrainz"
    CACHE = "cache"
    FALLBACK = "fallback"

class ArtworkSource(str, Enum):
    """Artwork source enum."""
    FILE = "file"
    MUSICBRAINZ = "musicbrainz"
    CACHE = "cache"
    NONE = "none"

class AudioMetadata(BaseModel):
    """Audio metadata model."""
    title: Optional[str] = Field(None, description="Track title")
    artist: Optional[str] = Field(None, description="Artist name")
    album: Optional[str] = Field(None, description="Album name")
    album_artist: Optional[str] = Field(None, description="Album artist name")
    genre: Optional[str] = Field(None, description="Genre")
    year: Optional[int] = Field(None, description="Release year")
    track_number: Optional[int] = Field(None, description="Track number")
    total_tracks: Optional[int] = Field(None, description="Total tracks in album")
    disc_number: Optional[int] = Field(None, description="Disc number")
    total_discs: Optional[int] = Field(None, description="Total discs in album")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    source: MetadataSource = Field(MetadataSource.FILE, description="Metadata source")
    has_artwork: bool = Field(False, description="Whether artwork is available")
    artwork_source: ArtworkSource = Field(ArtworkSource.NONE, description="Artwork source")
    additional_tags: Dict[str, Any] = Field(default_factory=dict, description="Additional tags")

class MetadataResult(BaseModel):
    """Metadata extraction result model."""
    job_uuid: str = Field(..., description="Job UUID")
    user_id: str = Field(..., description="User ID")
    file_path: str = Field(..., description="File path")
    filename: str = Field(..., description="Filename")
    metadata: AudioMetadata = Field(..., description="Extracted metadata")
    artwork_path: Optional[str] = Field(None, description="Path to extracted artwork")
    timestamp: str = Field(..., description="Extraction timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")

class MusicBrainzResult(BaseModel):
    """MusicBrainz lookup result model."""
    recording_id: Optional[str] = Field(None, description="MusicBrainz recording ID")
    release_id: Optional[str] = Field(None, description="MusicBrainz release ID")
    artist_id: Optional[str] = Field(None, description="MusicBrainz artist ID")
    title: Optional[str] = Field(None, description="Track title")
    artist: Optional[str] = Field(None, description="Artist name")
    album: Optional[str] = Field(None, description="Album name")
    album_artist: Optional[str] = Field(None, description="Album artist name")
    genre: Optional[str] = Field(None, description="Genre")
    year: Optional[int] = Field(None, description="Release year")
    track_number: Optional[int] = Field(None, description="Track number")
    total_tracks: Optional[int] = Field(None, description="Total tracks in album")
    disc_number: Optional[int] = Field(None, description="Disc number")
    total_discs: Optional[int] = Field(None, description="Total discs in album")
    artwork_url: Optional[str] = Field(None, description="URL to artwork")

class MetadataService(BaseService):
    """Metadata service for extracting metadata and artwork from audio files."""
    
    def __init__(self):
        """Initialize the metadata service."""
        super().__init__(
            name="metadata-service",
            version="0.1.0",
            description="Metadata extraction service for IM2 Audio Processing Pipeline",
            dependencies=["queue", "redis"]
        )
        
        # Configure settings
        self.cover_art_cache_path = os.getenv("COVER_ART_CACHE_PATH", "/pipeline-data/cover-art-cache")
        self.queue_service_url = os.getenv("QUEUE_SERVICE_URL", "http://queue:8003")
        self.redis_host = os.getenv("REDIS_HOST", "redis")
        self.redis_port = os.getenv("REDIS_PORT", "6379")
        self.musicbrainz_app_name = os.getenv("MUSICBRAINZ_APP_NAME", "IM2")
        self.musicbrainz_app_version = os.getenv("MUSICBRAINZ_APP_VERSION", "1.0.0")
        self.musicbrainz_contact = os.getenv("MUSICBRAINZ_CONTACT", "admin@example.com")
        
        # Initialize Redis client
        self.redis_client = None
        
        # Create router
        router = APIRouter()
        
        # Additional routes
        router.post("/extract", response_model=MetadataResult)(self.extract_metadata)
        router.get("/artwork/{job_uuid}", response_model=str)(self.get_artwork)
        router.get("/musicbrainz/lookup", response_model=MusicBrainzResult)(self.lookup_musicbrainz)
        router.get("/cache/status", response_model=Dict[str, Any])(self.get_cache_status)
        
        # Include router
        self.app.include_router(router, prefix="/api")
    
    async def startup_event(self):
        """FastAPI startup event."""
        # Initialize Redis connection
        self.redis_client = redis.Redis(
            host=self.redis_host,
            port=int(self.redis_port),
            decode_responses=True
        )
        
        # Create cover art cache directory if it doesn't exist
        os.makedirs(self.cover_art_cache_path, exist_ok=True)
        
        logger.info("Metadata service started")
    
    async def shutdown_event(self):
        """FastAPI shutdown event."""
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Metadata service stopped")
    
    async def extract_metadata_from_file(self, file_path: str) -> Tuple[AudioMetadata, Optional[bytes]]:
        """Extract metadata and artwork from an audio file."""
        try:
            # Check if file exists
            path = Path(file_path)
            if not path.exists():
                raise Exception("File not found")
            
            # Extract metadata using mutagen
            audio_file = MutagenFile(file_path)
            if audio_file is None:
                raise Exception("Unsupported audio format")
            
            # Initialize metadata
            metadata = AudioMetadata(
                source=MetadataSource.FILE,
                artwork_source=ArtworkSource.NONE
            )
            artwork = None
            
            # Extract duration
            if hasattr(audio_file, 'info') and hasattr(audio_file.info, 'length'):
                metadata.duration = audio_file.info.length
            
            # Extract tags based on file format
            if audio_file.__class__.__name__ == "MP3":
                # Extract MP3 tags
                if audio_file.tags:
                    for tag in audio_file.tags:
                        if tag.startswith("TIT2"):  # Title
                            metadata.title = str(audio_file.tags[tag])
                        elif tag.startswith("TPE1"):  # Artist
                            metadata.artist = str(audio_file.tags[tag])
                        elif tag.startswith("TALB"):  # Album
                            metadata.album = str(audio_file.tags[tag])
                        elif tag.startswith("TPE2"):  # Album Artist
                            metadata.album_artist = str(audio_file.tags[tag])
                        elif tag.startswith("TCON"):  # Genre
                            metadata.genre = str(audio_file.tags[tag])
                        elif tag.startswith("TDRC"):  # Year
                            try:
                                metadata.year = int(str(audio_file.tags[tag]))
                            except:
                                pass
                        elif tag.startswith("TRCK"):  # Track number
                            try:
                                track_info = str(audio_file.tags[tag]).split('/')
                                metadata.track_number = int(track_info[0])
                                if len(track_info) > 1:
                                    metadata.total_tracks = int(track_info[1])
                            except:
                                pass
                        elif tag.startswith("TPOS"):  # Disc number
                            try:
                                disc_info = str(audio_file.tags[tag]).split('/')
                                metadata.disc_number = int(disc_info[0])
                                if len(disc_info) > 1:
                                    metadata.total_discs = int(disc_info[1])
                            except:
                                pass
                
                # Extract artwork
                try:
                    id3 = ID3(file_path)
                    for tag in id3:
                        if tag.startswith("APIC"):
                            apic = id3[tag]
                            artwork = apic.data
                            metadata.has_artwork = True
                            metadata.artwork_source = ArtworkSource.FILE
                            break
                except:
                    pass
            
            elif audio_file.__class__.__name__ in ["FLAC", "OggVorbis", "OggOpus", "WavPack"]:
                # Extract FLAC/Ogg tags
                if hasattr(audio_file, 'tags') and audio_file.tags:
                    if "title" in audio_file:
                        metadata.title = str(audio_file["title"][0])
                    if "artist" in audio_file:
                        metadata.artist = str(audio_file["artist"][0])
                    if "album" in audio_file:
                        metadata.album = str(audio_file["album"][0])
                    if "albumartist" in audio_file:
                        metadata.album_artist = str(audio_file["albumartist"][0])
                    if "genre" in audio_file:
                        metadata.genre = str(audio_file["genre"][0])
                    if "date" in audio_file:
                        try:
                            metadata.year = int(str(audio_file["date"][0]))
                        except:
                            pass
                    if "tracknumber" in audio_file:
                        try:
                            track_info = str(audio_file["tracknumber"][0]).split('/')
                            metadata.track_number = int(track_info[0])
                            if len(track_info) > 1:
                                metadata.total_tracks = int(track_info[1])
                        except:
                            pass
                    if "discnumber" in audio_file:
                        try:
                            disc_info = str(audio_file["discnumber"][0]).split('/')
                            metadata.disc_number = int(disc_info[0])
                            if len(disc_info) > 1:
                                metadata.total_discs = int(disc_info[1])
                        except:
                            pass
                
                # Extract artwork for FLAC
                if audio_file.__class__.__name__ == "FLAC" and audio_file.pictures:
                    artwork = audio_file.pictures[0].data
                    metadata.has_artwork = True
                    metadata.artwork_source = ArtworkSource.FILE
            
            elif audio_file.__class__.__name__ in ["MP4"]:
                # Extract MP4 tags
                if hasattr(audio_file, 'tags') and audio_file.tags:
                    if "©nam" in audio_file:
                        metadata.title = str(audio_file["©nam"][0])
                    if "©ART" in audio_file:
                        metadata.artist = str(audio_file["©ART"][0])
                    if "©alb" in audio_file:
                        metadata.album = str(audio_file["©alb"][0])
                    if "aART" in audio_file:
                        metadata.album_artist = str(audio_file["aART"][0])
                    if "©gen" in audio_file:
                        metadata.genre = str(audio_file["©gen"][0])
                    if "©day" in audio_file:
                        try:
                            metadata.year = int(str(audio_file["©day"][0]))
                        except:
                            pass
                    if "trkn" in audio_file:
                        try:
                            track_info = audio_file["trkn"][0]
                            metadata.track_number = track_info[0]
                            metadata.total_tracks = track_info[1]
                        except:
                            pass
                    if "disk" in audio_file:
                        try:
                            disc_info = audio_file["disk"][0]
                            metadata.disc_number = disc_info[0]
                            metadata.total_discs = disc_info[1]
                        except:
                            pass
                
                # Extract artwork
                if "covr" in audio_file:
                    artwork = audio_file["covr"][0]
                    metadata.has_artwork = True
                    metadata.artwork_source = ArtworkSource.FILE
            
            # Store additional tags
            if hasattr(audio_file, 'tags') and audio_file.tags:
                for key, value in audio_file.items():
                    if key not in ["title", "artist", "album", "albumartist", "genre", "date", "tracknumber", "discnumber"]:
                        try:
                            metadata.additional_tags[key] = str(value)
                        except:
                            pass
            
            return metadata, artwork
        
        except Exception as e:
            logger.error(f"Error extracting metadata from file: {str(e)}")
            return AudioMetadata(
                source=MetadataSource.FILE,
                artwork_source=ArtworkSource.NONE
            ), None
    
    async def lookup_musicbrainz_metadata(
        self,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        duration: Optional[float] = None
    ) -> MusicBrainzResult:
        """Look up metadata from MusicBrainz."""
        try:
            # Skip lookup if not enough information
            if not (title and artist) and not (album and artist):
                return MusicBrainzResult()
            
            # Try to find in cache first
            cache_key = f"mb:{artist}:{title}:{album}"
            cached_result = await self.redis_client.get(cache_key)
            if cached_result:
                return MusicBrainzResult(**json.loads(cached_result))
            
            # Build query
            query = []
            if title:
                query.append(f"recording:\"{title}\"")
            if artist:
                query.append(f"artist:\"{artist}\"")
            if album:
                query.append(f"release:\"{album}\"")
            
            query_string = " AND ".join(query)
            
            # Set up headers
            headers = {
                "User-Agent": f"{self.musicbrainz_app_name}/{self.musicbrainz_app_version} ( {self.musicbrainz_contact} )"
            }
            
            # Make request to MusicBrainz API
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://musicbrainz.org/ws/2/recording",
                    params={
                        "query": query_string,
                        "fmt": "json",
                        "limit": 1
                    },
                    headers=headers
                ) as response:
                    if response.status != 200:
                        return MusicBrainzResult()
                    
                    data = await response.json()
                    
                    if "recordings" not in data or len(data["recordings"]) == 0:
                        return MusicBrainzResult()
                    
                    recording = data["recordings"][0]
                    
                    # Extract metadata
                    result = MusicBrainzResult(
                        recording_id=recording.get("id"),
                        title=recording.get("title")
                    )
                    
                    # Extract artist
                    if "artist-credit" in recording and len(recording["artist-credit"]) > 0:
                        artist_credit = recording["artist-credit"][0]
                        result.artist = artist_credit.get("name")
                        if "artist" in artist_credit:
                            result.artist_id = artist_credit["artist"].get("id")
                    
                    # Extract release
                    if "releases" in recording and len(recording["releases"]) > 0:
                        release = recording["releases"][0]
                        result.release_id = release.get("id")
                        result.album = release.get("title")
                        
                        # Extract release group info
                        if "release-group" in release:
                            if "primary-type" in release["release-group"]:
                                result.additional_tags = {"primary-type": release["release-group"]["primary-type"]}
                        
                        # Extract date
                        if "date" in release:
                            try:
                                result.year = int(release["date"].split("-")[0])
                            except:
                                pass
                        
                        # Extract media info
                        if "media" in release and len(release["media"]) > 0:
                            media = release["media"][0]
                            if "position" in media:
                                result.disc_number = int(media["position"])
                            if "track-count" in media:
                                result.total_tracks = int(media["track-count"])
                            if "track-offset" in media and "position" in recording:
                                result.track_number = int(recording["position"]) + int(media["track-offset"])
                    
                    # Get cover art URL
                    if result.release_id:
                        result.artwork_url = f"https://coverartarchive.org/release/{result.release_id}/front"
                    
                    # Cache result
                    await self.redis_client.set(
                        cache_key,
                        json.dumps(result.dict()),
                        ex=86400 * 7  # Cache for 7 days
                    )
                    
                    return result
        
        except Exception as e:
            logger.error(f"Error looking up MusicBrainz metadata: {str(e)}")
            return MusicBrainzResult()
    
    async def fetch_artwork(self, url: str) -> Optional[bytes]:
        """Fetch artwork from a URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    
                    return await response.read()
        except Exception as e:
            logger.error(f"Error fetching artwork: {str(e)}")
            return None
    
    async def save_artwork(self, artwork: bytes, job_uuid: str, filename: str) -> Optional[str]:
        """Save artwork to cache."""
        try:
            # Create hash of artwork data
            artwork_hash = hashlib.md5(artwork).hexdigest()
            
            # Create artwork path
            artwork_dir = Path(self.cover_art_cache_path)
            artwork_dir.mkdir(parents=True, exist_ok=True)
            
            # Check format and convert if needed
            try:
                img = Image.open(BytesIO(artwork))
                format_name = img.format.lower() if img.format else "jpeg"
                
                # Save artwork
                artwork_path = artwork_dir / f"{job_uuid}_{artwork_hash}.{format_name}"
                with open(artwork_path, "wb") as f:
                    f.write(artwork)
                
                return str(artwork_path)
            except Exception as e:
                logger.error(f"Error processing artwork: {str(e)}")
                
                # Save raw artwork as fallback
                artwork_path = artwork_dir / f"{job_uuid}_{artwork_hash}.bin"
                with open(artwork_path, "wb") as f:
                    f.write(artwork)
                
                return str(artwork_path)
        
        except Exception as e:
            logger.error(f"Error saving artwork: {str(e)}")
            return None
    
    async def extract_metadata(self, request: Request, background_tasks: BackgroundTasks) -> MetadataResult:
        """Extract metadata from a file and update job status."""
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
            
            # Extract metadata from file
            file_metadata, file_artwork = await self.extract_metadata_from_file(file_path)
            
            # Lookup metadata from MusicBrainz if possible
            mb_metadata = None
            if file_metadata.title and file_metadata.artist:
                mb_metadata = await self.lookup_musicbrainz_metadata(
                    title=file_metadata.title,
                    artist=file_metadata.artist,
                    album=file_metadata.album,
                    duration=file_metadata.duration
                )
            
            # Merge metadata (prefer file metadata for basic tags)
            metadata = AudioMetadata(
                title=file_metadata.title or mb_metadata.title if mb_metadata else None,
                artist=file_metadata.artist or mb_metadata.artist if mb_metadata else None,
                album=file_metadata.album or mb_metadata.album if mb_metadata else None,
                album_artist=file_metadata.album_artist or mb_metadata.album_artist if mb_metadata else None,
                genre=file_metadata.genre,
                year=file_metadata.year or mb_metadata.year if mb_metadata else None,
                track_number=file_metadata.track_number or mb_metadata.track_number if mb_metadata else None,
                total_tracks=file_metadata.total_tracks or mb_metadata.total_tracks if mb_metadata else None,
                disc_number=file_metadata.disc_number or mb_metadata.disc_number if mb_metadata else None,
                total_discs=file_metadata.total_discs or mb_metadata.total_discs if mb_metadata else None,
                duration=file_metadata.duration,
                source=MetadataSource.FILE if file_metadata.title else (
                    MetadataSource.MUSICBRAINZ if mb_metadata and mb_metadata.title else MetadataSource.FALLBACK
                ),
                has_artwork=file_metadata.has_artwork,
                artwork_source=file_metadata.artwork_source,
                additional_tags=file_metadata.additional_tags
            )
            
            # Add MusicBrainz IDs to additional tags if available
            if mb_metadata:
                if mb_metadata.recording_id:
                    metadata.additional_tags["musicbrainz_recording_id"] = mb_metadata.recording_id
                if mb_metadata.release_id:
                    metadata.additional_tags["musicbrainz_release_id"] = mb_metadata.release_id
                if mb_metadata.artist_id:
                    metadata.additional_tags["musicbrainz_artist_id"] = mb_metadata.artist_id
            
            # Process artwork
            artwork_path = None
            if file_artwork:
                # Save file artwork
                artwork_path = await self.save_artwork(file_artwork, job_uuid, filename)
            elif mb_metadata and mb_metadata.artwork_url:
                # Try to fetch artwork from MusicBrainz
                mb_artwork = await self.fetch_artwork(mb_metadata.artwork_url)
                if mb_artwork:
                    artwork_path = await self.save_artwork(mb_artwork, job_uuid, filename)
                    metadata.has_artwork = True
                    metadata.artwork_source = ArtworkSource.MUSICBRAINZ
            
            # Create result
            result = MetadataResult(
                job_uuid=job_uuid,
                user_id=user_id,
                file_path=file_path,
                filename=filename,
                metadata=metadata,
                artwork_path=artwork_path,
                timestamp=datetime.now().isoformat()
            )
            
            # Update job status in queue
            background_tasks.add_task(
                self.update_job_status,
                job_uuid,
                metadata,
                artwork_path,
                trace_id
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error extracting metadata: {str(e)}")
    
    async def get_artwork(self, job_uuid: str) -> str:
        """Get artwork for a job."""
        try:
            # Look up artwork in cache directory
            artwork_dir = Path(self.cover_art_cache_path)
            artwork_files = list(artwork_dir.glob(f"{job_uuid}_*"))
            
            if not artwork_files:
                raise HTTPException(status_code=404, detail="Artwork not found")
            
            # Return the first matching artwork
            with open(artwork_files[0], "rb") as f:
                artwork_data = f.read()
            
            # Encode as base64
            return f"data:image/jpeg;base64,{base64.b64encode(artwork_data).decode('utf-8')}"
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting artwork: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error getting artwork: {str(e)}")
    
    async def lookup_musicbrainz(
        self,
        title: Optional[str] = None,
        artist: Optional[str] = None,
        album: Optional[str] = None
    ) -> MusicBrainzResult:
        """Look up metadata from MusicBrainz."""
        return await self.lookup_musicbrainz_metadata(title, artist, album)
    
    async def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status."""
        try:
            # Count artwork files
            artwork_dir = Path(self.cover_art_cache_path)
            artwork_count = len(list(artwork_dir.glob("*")))
            
            # Get cache size
            cache_size = sum(f.stat().st_size for f in artwork_dir.glob("*") if f.is_file())
            
            # Get Redis cache info
            redis_info = await self.redis_client.info()
            
            return {
                "artwork_count": artwork_count,
                "artwork_cache_size_bytes": cache_size,
                "redis_used_memory": redis_info.get("used_memory_human", "N/A"),
                "redis_keys": redis_info.get("keyspace_hits", 0) + redis_info.get("keyspace_misses", 0)
            }
        
        except Exception as e:
            logger.error(f"Error getting cache status: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error getting cache status: {str(e)}")
    
    async def update_job_status(
        self,
        job_uuid: str,
        metadata: AudioMetadata,
        artwork_path: Optional[str],
        trace_id: Optional[str] = None
    ):
        """Update job status in queue."""
        try:
            # Prepare metadata
            job_metadata = {
                "metadata": metadata.dict(),
                "artwork_path": artwork_path
            }
            
            # Update job in queue
            async with aiohttp.ClientSession() as session:
                headers = {}
                if trace_id:
                    headers["X-Trace-ID"] = trace_id
                
                async with session.put(
                    f"{self.queue_service_url}/api/jobs/{job_uuid}",
                    json={
                        "status": "metadata_extracted",
                        "metadata": job_metadata
                    },
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to update job status: {error_text}")
                    else:
                        logger.info(f"Updated job {job_uuid} status to metadata_extracted")
        except Exception as e:
            logger.error(f"Error updating job status: {str(e)}")
    
    def run(self, host: str = "0.0.0.0", port: int = 8004):
        """Run the metadata service."""
        # Add startup and shutdown events
        self.app.add_event_handler("startup", self.startup_event)
        self.app.add_event_handler("shutdown", self.shutdown_event)
        
        # Run the service
        super().run(host=host, port=port)


if __name__ == "__main__":
    # Get service port from environment
    port = int(os.getenv("METADATA_SERVICE_PORT", "8004"))
    
    # Create and run service
    service = MetadataService()
    service.run(port=port)
