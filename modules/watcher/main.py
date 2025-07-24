"""
Watcher Service for IM2 Audio Processing Pipeline

This service:
1. Monitors the input directory for new files
2. Detects when files are fully written and stable
3. Submits jobs to the queue service
4. Provides health and metrics endpoints
"""

import os
import sys
import time
import json
import logging
import asyncio
import hashlib
from typing import Dict, Any, List, Set
from datetime import datetime
from pathlib import Path

import aiohttp
import watchdog.events
import watchdog.observers
from fastapi import FastAPI, HTTPException, APIRouter, Depends, Request, Response
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
logger = logging.getLogger("watcher")

class FileEvent(BaseModel):
    """File event model."""
    path: str = Field(..., description="File path")
    event_type: str = Field(..., description="Event type (created, modified, etc.)")
    timestamp: str = Field(..., description="Event timestamp")

class FileState(BaseModel):
    """File state tracking model."""
    path: str = Field(..., description="File path")
    size: int = Field(..., description="File size")
    hash: str = Field(..., description="File hash")
    mtime: float = Field(..., description="Last modification time")
    last_checked: float = Field(..., description="Last check time")
    is_stable: bool = Field(False, description="Whether the file is stable")
    stability_count: int = Field(0, description="Number of stable checks")

class WatcherService(BaseService):
    """Watcher service for detecting new files and submitting jobs."""
    
    def __init__(self):
        """Initialize the watcher service."""
        super().__init__(
            name="watcher",
            version="0.1.0",
            description="File system watcher for IM2 Audio Processing Pipeline",
            dependencies=["queue"]
        )
        
        # Configure file paths
        self.input_path = os.getenv("INPUT_PATH", "/pipeline-data/input")
        self.stability_checks = int(os.getenv("STABILITY_CHECKS", "3"))
        self.stability_interval = int(os.getenv("STABILITY_INTERVAL", "5"))
        self.queue_service_url = os.getenv("QUEUE_SERVICE_URL", "http://queue:8003")
        
        # Initialize state
        self.files_being_watched: Dict[str, FileState] = {}
        self.processed_files: Set[str] = set()
        
        # Create router
        router = APIRouter()
        
        # Additional routes
        router.get("/files/watching", response_model=List[FileState])(self.get_watched_files)
        router.get("/files/processed", response_model=List[str])(self.get_processed_files)
        router.post("/files/reset")(self.reset_watched_files)
        
        # Include router
        self.app.include_router(router, prefix="/api")
        
        # Initialize watchdog observer
        self.event_handler = FileSystemEventHandler(self)
        self.observer = watchdog.observers.Observer()
    
    async def get_watched_files(self) -> List[FileState]:
        """Get list of files being watched."""
        return list(self.files_being_watched.values())
    
    async def get_processed_files(self) -> List[str]:
        """Get list of processed files."""
        return list(self.processed_files)
    
    async def reset_watched_files(self) -> Dict[str, Any]:
        """Reset the watched files state."""
        self.files_being_watched.clear()
        self.processed_files.clear()
        return {"status": "reset", "timestamp": datetime.now().isoformat()}
    
    async def check_file_stability(self, path: str) -> bool:
        """Check if a file is stable (not being written to)."""
        try:
            file_path = Path(path)
            if not file_path.exists():
                return False
            
            # Get current stats
            stat = file_path.stat()
            current_size = stat.st_size
            current_mtime = stat.st_mtime
            
            # Calculate hash of first and last blocks to detect changes
            # This is more efficient than hashing the entire file
            block_size = 8192  # 8KB blocks
            current_hash = ""
            
            if current_size > 0:
                with open(path, 'rb') as f:
                    # Read first block
                    first_block = f.read(block_size)
                    
                    # Read last block if file is larger than block size
                    last_block = b""
                    if current_size > block_size:
                        f.seek(max(0, current_size - block_size))
                        last_block = f.read(block_size)
                    
                    # Calculate hash
                    hasher = hashlib.md5()
                    hasher.update(first_block)
                    hasher.update(last_block)
                    current_hash = hasher.hexdigest()
            
            # Check if file is in watched files
            if path in self.files_being_watched:
                file_state = self.files_being_watched[path]
                
                # Update last checked time
                file_state.last_checked = time.time()
                
                # Check if file has changed
                if (
                    file_state.size == current_size and
                    file_state.mtime == current_mtime and
                    file_state.hash == current_hash
                ):
                    # File hasn't changed, increment stability count
                    file_state.stability_count += 1
                    if file_state.stability_count >= self.stability_checks:
                        file_state.is_stable = True
                        return True
                else:
                    # File has changed, reset stability count
                    file_state.size = current_size
                    file_state.mtime = current_mtime
                    file_state.hash = current_hash
                    file_state.stability_count = 0
                    file_state.is_stable = False
            else:
                # New file, add to watched files
                self.files_being_watched[path] = FileState(
                    path=path,
                    size=current_size,
                    hash=current_hash,
                    mtime=current_mtime,
                    last_checked=time.time(),
                    is_stable=False,
                    stability_count=0
                )
            
            return False
        except Exception as e:
            logger.error(f"Error checking file stability: {str(e)}")
            return False
    
    async def submit_file_to_queue(self, path: str) -> bool:
        """Submit a file to the queue service."""
        try:
            # Extract user_id and job_uuid from path
            # Expected format: input/{user_id}/{job_uuid}/filename.ext
            parts = Path(path).parts
            if len(parts) < 4:
                logger.error(f"Invalid path format: {path}")
                return False
            
            user_id = parts[-3]
            job_uuid = parts[-2]
            filename = parts[-1]
            
            # Submit to queue
            async with aiohttp.ClientSession() as session:
                payload = {
                    "file_path": path,
                    "user_id": user_id,
                    "job_uuid": job_uuid,
                    "filename": filename,
                    "timestamp": datetime.now().isoformat()
                }
                
                async with session.post(
                    f"{self.queue_service_url}/api/jobs",
                    json=payload
                ) as response:
                    if response.status == 200:
                        logger.info(f"File submitted to queue: {path}")
                        self.processed_files.add(path)
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to submit file to queue: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error submitting file to queue: {str(e)}")
            return False
    
    async def process_stable_files(self):
        """Process files that are stable and ready for submission."""
        for path, state in list(self.files_being_watched.items()):
            if state.is_stable and path not in self.processed_files:
                logger.info(f"Processing stable file: {path}")
                success = await self.submit_file_to_queue(path)
                if success:
                    logger.info(f"File processed successfully: {path}")
                    # Remove from watched files
                    self.files_being_watched.pop(path, None)
    
    async def scan_input_directory(self):
        """Scan input directory for files not being watched."""
        for root, _, files in os.walk(self.input_path):
            for file in files:
                path = os.path.join(root, file)
                if path not in self.files_being_watched and path not in self.processed_files:
                    logger.info(f"Found new file: {path}")
                    await self.check_file_stability(path)
    
    async def watch_loop(self):
        """Main watch loop."""
        while True:
            try:
                # Scan for new files
                await self.scan_input_directory()
                
                # Check stability of watched files
                for path in list(self.files_being_watched.keys()):
                    await self.check_file_stability(path)
                
                # Process stable files
                await self.process_stable_files()
                
                # Sleep before next iteration
                await asyncio.sleep(self.stability_interval)
            except Exception as e:
                logger.error(f"Error in watch loop: {str(e)}")
                await asyncio.sleep(self.stability_interval)
    
    def start_watching(self):
        """Start watching the input directory."""
        # Start watchdog observer
        self.observer.schedule(self.event_handler, self.input_path, recursive=True)
        self.observer.start()
        logger.info(f"Started watching directory: {self.input_path}")
        
        # Start async watch loop
        asyncio.create_task(self.watch_loop())
    
    def stop_watching(self):
        """Stop watching the input directory."""
        self.observer.stop()
        self.observer.join()
        logger.info("Stopped watching directory")
    
    async def startup_event(self):
        """FastAPI startup event."""
        self.start_watching()
    
    async def shutdown_event(self):
        """FastAPI shutdown event."""
        self.stop_watching()
    
    def run(self, host: str = "0.0.0.0", port: int = 8001):
        """Run the watcher service."""
        # Add startup and shutdown events
        self.app.add_event_handler("startup", self.startup_event)
        self.app.add_event_handler("shutdown", self.shutdown_event)
        
        # Run the service
        super().run(host=host, port=port)


class FileSystemEventHandler(watchdog.events.FileSystemEventHandler):
    """Watchdog event handler for file system events."""
    
    def __init__(self, service: WatcherService):
        """Initialize the event handler."""
        self.service = service
        super().__init__()
    
    def on_created(self, event):
        """Handle file created event."""
        if not event.is_directory:
            logger.info(f"File created: {event.src_path}")
            asyncio.create_task(self.service.check_file_stability(event.src_path))
    
    def on_modified(self, event):
        """Handle file modified event."""
        if not event.is_directory:
            logger.info(f"File modified: {event.src_path}")
            asyncio.create_task(self.service.check_file_stability(event.src_path))
    
    def on_moved(self, event):
        """Handle file moved event."""
        if not event.is_directory:
            logger.info(f"File moved: {event.src_path} -> {event.dest_path}")
            # Remove old path if it was being watched
            self.service.files_being_watched.pop(event.src_path, None)
            # Add new path to watched files
            asyncio.create_task(self.service.check_file_stability(event.dest_path))


if __name__ == "__main__":
    # Get service port from environment
    port = int(os.getenv("WATCHER_PORT", "8001"))
    
    # Create and run service
    service = WatcherService()
    service.run(port=port)
