"""
Queue Service for IM2 Audio Processing Pipeline

This service:
1. Manages job queue and state transitions
2. Provides atomic operations with advisory locks
3. Tracks job history and enables retry/replay
4. Offers health and metrics endpoints
"""

import os
import sys
import time
import json
import logging
import asyncio
import uuid
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

import asyncpg
import redis.asyncio as redis
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
logger = logging.getLogger("queue")

class JobStatus(str, Enum):
    """Job status enum."""
    SUBMITTED = "submitted"
    CATEGORIZING = "categorizing"
    CATEGORIZED = "categorized"
    METADATA_EXTRACTING = "metadata_extracting"
    METADATA_EXTRACTED = "metadata_extracted"
    STAGING = "staging"
    STAGED = "staged"
    SPLITTING = "splitting"
    SPLIT = "split"
    RECOMBINING = "recombining"
    RECOMBINED = "recombined"
    ORGANIZING = "organizing"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELED = "canceled"

class JobModel(BaseModel):
    """Job model."""
    job_uuid: str = Field(..., description="Job UUID")
    user_id: str = Field(..., description="User ID")
    file_path: str = Field(..., description="File path")
    filename: str = Field(..., description="Filename")
    status: JobStatus = Field(..., description="Job status")
    engine: Optional[str] = Field(None, description="Separation engine (spleeter, demucs)")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")
    trace_id: Optional[str] = Field(None, description="Trace ID for job")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Job metadata")

class JobSubmission(BaseModel):
    """Job submission model."""
    file_path: str = Field(..., description="File path")
    user_id: str = Field(..., description="User ID")
    job_uuid: Optional[str] = Field(None, description="Job UUID (optional, generated if not provided)")
    filename: str = Field(..., description="Filename")
    engine: Optional[str] = Field(None, description="Separation engine (spleeter, demucs)")
    timestamp: Optional[str] = Field(None, description="Submission timestamp")
    trace_id: Optional[str] = Field(None, description="Trace ID for job")

class JobUpdate(BaseModel):
    """Job update model."""
    status: JobStatus = Field(..., description="New job status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")
    error: Optional[str] = Field(None, description="Error message if failed")

class QueueStats(BaseModel):
    """Queue statistics model."""
    total_jobs: int = Field(..., description="Total number of jobs")
    active_jobs: int = Field(..., description="Number of active jobs")
    completed_jobs: int = Field(..., description="Number of completed jobs")
    failed_jobs: int = Field(..., description="Number of failed jobs")
    jobs_by_status: Dict[str, int] = Field(..., description="Jobs grouped by status")

class QueueService(BaseService):
    """Queue service for managing job queue and state transitions."""
    
    def __init__(self):
        """Initialize the queue service."""
        super().__init__(
            name="queue",
            version="0.1.0",
            description="Job queue management for IM2 Audio Processing Pipeline",
            dependencies=["postgres", "redis"]
        )
        
        # Configure database connection
        self.db_host = os.getenv("POSTGRES_HOST", "postgres")
        self.db_port = os.getenv("POSTGRES_PORT", "5432")
        self.db_name = os.getenv("POSTGRES_DB", "im2_queue")
        self.db_user = os.getenv("POSTGRES_USER", "postgres")
        self.db_password = os.getenv("POSTGRES_PASSWORD", "postgres")
        self.db_pool = None
        
        # Configure Redis connection
        self.redis_host = os.getenv("REDIS_HOST", "redis")
        self.redis_port = os.getenv("REDIS_PORT", "6379")
        self.redis_client = None
        
        # Create router
        router = APIRouter()
        
        # Job routes
        router.post("/jobs", response_model=JobModel)(self.create_job)
        router.get("/jobs", response_model=List[JobModel])(self.list_jobs)
        router.get("/jobs/{job_uuid}", response_model=JobModel)(self.get_job)
        router.put("/jobs/{job_uuid}", response_model=JobModel)(self.update_job)
        router.post("/jobs/{job_uuid}/retry", response_model=JobModel)(self.retry_job)
        router.post("/jobs/{job_uuid}/cancel", response_model=JobModel)(self.cancel_job)
        
        # Queue management routes
        router.get("/stats", response_model=QueueStats)(self.get_queue_stats)
        router.post("/pause")(self.pause_queue)
        router.post("/resume")(self.resume_queue)
        
        # Include router
        self.app.include_router(router, prefix="/api")
        
        # Pipeline paused flag
        self.pipeline_paused = False
    
    async def startup_event(self):
        """FastAPI startup event."""
        # Initialize database connection pool
        self.db_pool = await asyncpg.create_pool(
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            user=self.db_user,
            password=self.db_password
        )
        
        # Initialize Redis connection
        self.redis_client = redis.Redis(
            host=self.redis_host,
            port=int(self.redis_port),
            decode_responses=True
        )
        
        # Initialize database schema
        await self.init_db()
        
        logger.info("Queue service started")
    
    async def shutdown_event(self):
        """FastAPI shutdown event."""
        # Close database connection pool
        if self.db_pool:
            await self.db_pool.close()
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Queue service stopped")
    
    async def init_db(self):
        """Initialize database schema."""
        async with self.db_pool.acquire() as conn:
            # Create jobs table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    job_uuid TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    status TEXT NOT NULL,
                    engine TEXT,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    error TEXT,
                    trace_id TEXT,
                    metadata JSONB
                )
            ''')
            
            # Create job history table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS job_history (
                    id SERIAL PRIMARY KEY,
                    job_uuid TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    metadata JSONB,
                    error TEXT,
                    FOREIGN KEY (job_uuid) REFERENCES jobs (job_uuid)
                )
            ''')
            
            # Create indexes
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON jobs (user_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_job_history_job_uuid ON job_history (job_uuid)')
    
    async def create_job(self, job: JobSubmission, request: Request) -> JobModel:
        """Create a new job."""
        # Check if pipeline is paused
        if self.pipeline_paused:
            raise HTTPException(status_code=503, detail="Pipeline is paused")
        
        # Generate job UUID if not provided
        job_uuid = job.job_uuid or str(uuid.uuid4())
        
        # Get trace ID from request or generate one
        trace_id = request.headers.get("X-Trace-ID") or job.trace_id or f"{int(time.time() * 1000)}-{job_uuid}"
        
        # Get current timestamp
        timestamp = job.timestamp or datetime.now().isoformat()
        
        async with self.db_pool.acquire() as conn:
            # Acquire advisory lock
            lock_key = int(hashlib.md5(job_uuid.encode()).hexdigest()[:8], 16)
            async with conn.transaction():
                # Check if job already exists
                existing_job = await conn.fetchrow(
                    'SELECT * FROM jobs WHERE job_uuid = $1',
                    job_uuid
                )
                
                if existing_job:
                    raise HTTPException(status_code=409, detail=f"Job with UUID {job_uuid} already exists")
                
                # Insert job
                job_record = await conn.fetchrow('''
                    INSERT INTO jobs (
                        job_uuid, user_id, file_path, filename, status,
                        engine, created_at, updated_at, trace_id, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    RETURNING *
                ''', 
                    job_uuid, job.user_id, job.file_path, job.filename,
                    JobStatus.SUBMITTED, job.engine, timestamp, timestamp,
                    trace_id, json.dumps({})
                )
                
                # Insert job history
                await conn.execute('''
                    INSERT INTO job_history (
                        job_uuid, status, timestamp, metadata
                    ) VALUES ($1, $2, $3, $4)
                ''',
                    job_uuid, JobStatus.SUBMITTED, timestamp, json.dumps({})
                )
                
                # Publish job creation event
                await self.redis_client.publish(
                    "job_events",
                    json.dumps({
                        "event": "job_created",
                        "job_uuid": job_uuid,
                        "user_id": job.user_id,
                        "status": JobStatus.SUBMITTED,
                        "timestamp": timestamp,
                        "trace_id": trace_id
                    })
                )
        
        # Return job model
        return JobModel(
            job_uuid=job_record["job_uuid"],
            user_id=job_record["user_id"],
            file_path=job_record["file_path"],
            filename=job_record["filename"],
            status=job_record["status"],
            engine=job_record["engine"],
            created_at=job_record["created_at"].isoformat(),
            updated_at=job_record["updated_at"].isoformat(),
            trace_id=job_record["trace_id"],
            metadata=json.loads(job_record["metadata"]) if job_record["metadata"] else {},
            error=job_record["error"]
        )
    
    async def list_jobs(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[JobModel]:
        """List jobs with optional filtering."""
        query = 'SELECT * FROM jobs'
        params = []
        
        # Add filters
        filters = []
        if user_id:
            filters.append(f'user_id = ${len(params) + 1}')
            params.append(user_id)
        
        if status:
            filters.append(f'status = ${len(params) + 1}')
            params.append(status)
        
        if filters:
            query += ' WHERE ' + ' AND '.join(filters)
        
        # Add pagination
        query += f' ORDER BY created_at DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}'
        params.extend([limit, offset])
        
        # Execute query
        async with self.db_pool.acquire() as conn:
            job_records = await conn.fetch(query, *params)
        
        # Convert to models
        return [
            JobModel(
                job_uuid=record["job_uuid"],
                user_id=record["user_id"],
                file_path=record["file_path"],
                filename=record["filename"],
                status=record["status"],
                engine=record["engine"],
                created_at=record["created_at"].isoformat(),
                updated_at=record["updated_at"].isoformat(),
                trace_id=record["trace_id"],
                metadata=json.loads(record["metadata"]) if record["metadata"] else {},
                error=record["error"]
            )
            for record in job_records
        ]
    
    async def get_job(self, job_uuid: str) -> JobModel:
        """Get a job by UUID."""
        async with self.db_pool.acquire() as conn:
            job_record = await conn.fetchrow(
                'SELECT * FROM jobs WHERE job_uuid = $1',
                job_uuid
            )
        
        if not job_record:
            raise HTTPException(status_code=404, detail=f"Job with UUID {job_uuid} not found")
        
        return JobModel(
            job_uuid=job_record["job_uuid"],
            user_id=job_record["user_id"],
            file_path=job_record["file_path"],
            filename=job_record["filename"],
            status=job_record["status"],
            engine=job_record["engine"],
            created_at=job_record["created_at"].isoformat(),
            updated_at=job_record["updated_at"].isoformat(),
            trace_id=job_record["trace_id"],
            metadata=json.loads(job_record["metadata"]) if job_record["metadata"] else {},
            error=job_record["error"]
        )
    
    async def update_job(
        self,
        job_uuid: str,
        job_update: JobUpdate,
        request: Request,
        background_tasks: BackgroundTasks
    ) -> JobModel:
        """Update a job status and metadata."""
        # Check if pipeline is paused (but allow updates to failed or canceled status)
        if self.pipeline_paused and job_update.status not in [JobStatus.FAILED, JobStatus.CANCELED]:
            raise HTTPException(status_code=503, detail="Pipeline is paused")
        
        # Get trace ID from request
        trace_id = request.headers.get("X-Trace-ID")
        
        async with self.db_pool.acquire() as conn:
            # Acquire advisory lock
            lock_key = int(hashlib.md5(job_uuid.encode()).hexdigest()[:8], 16)
            await conn.execute('SELECT pg_advisory_xact_lock($1)', lock_key)
            
            async with conn.transaction():
                # Get current job
                current_job = await conn.fetchrow(
                    'SELECT * FROM jobs WHERE job_uuid = $1',
                    job_uuid
                )
                
                if not current_job:
                    raise HTTPException(status_code=404, detail=f"Job with UUID {job_uuid} not found")
                
                # Get current timestamp
                timestamp = datetime.now()
                
                # Update metadata if provided
                metadata = json.loads(current_job["metadata"]) if current_job["metadata"] else {}
                if job_update.metadata:
                    metadata.update(job_update.metadata)
                
                # Update job
                updated_job = await conn.fetchrow('''
                    UPDATE jobs
                    SET status = $1, updated_at = $2, metadata = $3, error = $4
                    WHERE job_uuid = $5
                    RETURNING *
                ''',
                    job_update.status, timestamp, json.dumps(metadata),
                    job_update.error, job_uuid
                )
                
                # Insert job history
                await conn.execute('''
                    INSERT INTO job_history (
                        job_uuid, status, timestamp, metadata, error
                    ) VALUES ($1, $2, $3, $4, $5)
                ''',
                    job_uuid, job_update.status, timestamp,
                    json.dumps(metadata), job_update.error
                )
                
                # Add background task to publish event
                background_tasks.add_task(
                    self.publish_job_event,
                    "job_updated",
                    job_uuid,
                    current_job["user_id"],
                    job_update.status,
                    timestamp.isoformat(),
                    trace_id or current_job["trace_id"]
                )
        
        # Return updated job
        return JobModel(
            job_uuid=updated_job["job_uuid"],
            user_id=updated_job["user_id"],
            file_path=updated_job["file_path"],
            filename=updated_job["filename"],
            status=updated_job["status"],
            engine=updated_job["engine"],
            created_at=updated_job["created_at"].isoformat(),
            updated_at=updated_job["updated_at"].isoformat(),
            trace_id=updated_job["trace_id"],
            metadata=json.loads(updated_job["metadata"]) if updated_job["metadata"] else {},
            error=updated_job["error"]
        )
    
    async def retry_job(self, job_uuid: str, request: Request) -> JobModel:
        """Retry a failed job."""
        # Check if pipeline is paused
        if self.pipeline_paused:
            raise HTTPException(status_code=503, detail="Pipeline is paused")
        
        # Get trace ID from request
        trace_id = request.headers.get("X-Trace-ID")
        
        async with self.db_pool.acquire() as conn:
            # Acquire advisory lock
            lock_key = int(hashlib.md5(job_uuid.encode()).hexdigest()[:8], 16)
            await conn.execute('SELECT pg_advisory_xact_lock($1)', lock_key)
            
            async with conn.transaction():
                # Get current job
                current_job = await conn.fetchrow(
                    'SELECT * FROM jobs WHERE job_uuid = $1',
                    job_uuid
                )
                
                if not current_job:
                    raise HTTPException(status_code=404, detail=f"Job with UUID {job_uuid} not found")
                
                # Check if job is failed
                if current_job["status"] != JobStatus.FAILED:
                    raise HTTPException(status_code=400, detail="Only failed jobs can be retried")
                
                # Get last successful status from history
                last_success = await conn.fetchrow('''
                    SELECT status FROM job_history
                    WHERE job_uuid = $1 AND status != $2
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''',
                    job_uuid, JobStatus.FAILED
                )
                
                # Default to submitted if no successful status
                retry_status = last_success["status"] if last_success else JobStatus.SUBMITTED
                
                # Get current timestamp
                timestamp = datetime.now()
                
                # Update job
                updated_job = await conn.fetchrow('''
                    UPDATE jobs
                    SET status = $1, updated_at = $2, error = NULL
                    WHERE job_uuid = $3
                    RETURNING *
                ''',
                    retry_status, timestamp, job_uuid
                )
                
                # Insert job history
                await conn.execute('''
                    INSERT INTO job_history (
                        job_uuid, status, timestamp, metadata
                    ) VALUES ($1, $2, $3, $4)
                ''',
                    job_uuid, retry_status, timestamp,
                    updated_job["metadata"]
                )
                
                # Publish job retry event
                await self.redis_client.publish(
                    "job_events",
                    json.dumps({
                        "event": "job_retried",
                        "job_uuid": job_uuid,
                        "user_id": current_job["user_id"],
                        "status": retry_status,
                        "timestamp": timestamp.isoformat(),
                        "trace_id": trace_id or current_job["trace_id"]
                    })
                )
        
        # Return updated job
        return JobModel(
            job_uuid=updated_job["job_uuid"],
            user_id=updated_job["user_id"],
            file_path=updated_job["file_path"],
            filename=updated_job["filename"],
            status=updated_job["status"],
            engine=updated_job["engine"],
            created_at=updated_job["created_at"].isoformat(),
            updated_at=updated_job["updated_at"].isoformat(),
            trace_id=updated_job["trace_id"],
            metadata=json.loads(updated_job["metadata"]) if updated_job["metadata"] else {},
            error=updated_job["error"]
        )
    
    async def cancel_job(self, job_uuid: str, request: Request) -> JobModel:
        """Cancel a job."""
        # Get trace ID from request
        trace_id = request.headers.get("X-Trace-ID")
        
        async with self.db_pool.acquire() as conn:
            # Acquire advisory lock
            lock_key = int(hashlib.md5(job_uuid.encode()).hexdigest()[:8], 16)
            await conn.execute('SELECT pg_advisory_xact_lock($1)', lock_key)
            
            async with conn.transaction():
                # Get current job
                current_job = await conn.fetchrow(
                    'SELECT * FROM jobs WHERE job_uuid = $1',
                    job_uuid
                )
                
                if not current_job:
                    raise HTTPException(status_code=404, detail=f"Job with UUID {job_uuid} not found")
                
                # Check if job is already completed or canceled
                if current_job["status"] in [JobStatus.COMPLETE, JobStatus.CANCELED]:
                    raise HTTPException(status_code=400, detail="Job is already completed or canceled")
                
                # Get current timestamp
                timestamp = datetime.now()
                
                # Update job
                updated_job = await conn.fetchrow('''
                    UPDATE jobs
                    SET status = $1, updated_at = $2
                    WHERE job_uuid = $3
                    RETURNING *
                ''',
                    JobStatus.CANCELED, timestamp, job_uuid
                )
                
                # Insert job history
                await conn.execute('''
                    INSERT INTO job_history (
                        job_uuid, status, timestamp, metadata
                    ) VALUES ($1, $2, $3, $4)
                ''',
                    job_uuid, JobStatus.CANCELED, timestamp,
                    updated_job["metadata"]
                )
                
                # Publish job cancel event
                await self.redis_client.publish(
                    "job_events",
                    json.dumps({
                        "event": "job_canceled",
                        "job_uuid": job_uuid,
                        "user_id": current_job["user_id"],
                        "status": JobStatus.CANCELED,
                        "timestamp": timestamp.isoformat(),
                        "trace_id": trace_id or current_job["trace_id"]
                    })
                )
        
        # Return updated job
        return JobModel(
            job_uuid=updated_job["job_uuid"],
            user_id=updated_job["user_id"],
            file_path=updated_job["file_path"],
            filename=updated_job["filename"],
            status=updated_job["status"],
            engine=updated_job["engine"],
            created_at=updated_job["created_at"].isoformat(),
            updated_at=updated_job["updated_at"].isoformat(),
            trace_id=updated_job["trace_id"],
            metadata=json.loads(updated_job["metadata"]) if updated_job["metadata"] else {},
            error=updated_job["error"]
        )
    
    async def get_queue_stats(self) -> QueueStats:
        """Get queue statistics."""
        async with self.db_pool.acquire() as conn:
            # Get total jobs
            total_jobs = await conn.fetchval('SELECT COUNT(*) FROM jobs')
            
            # Get jobs by status
            jobs_by_status = {}
            for status in JobStatus:
                count = await conn.fetchval(
                    'SELECT COUNT(*) FROM jobs WHERE status = $1',
                    status
                )
                jobs_by_status[status] = count
            
            # Calculate aggregates
            active_jobs = sum(count for status, count in jobs_by_status.items() 
                          if status not in [JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.CANCELED])
            completed_jobs = jobs_by_status.get(JobStatus.COMPLETE, 0)
            failed_jobs = jobs_by_status.get(JobStatus.FAILED, 0)
        
        return QueueStats(
            total_jobs=total_jobs,
            active_jobs=active_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            jobs_by_status=jobs_by_status
        )
    
    async def pause_queue(self):
        """Pause the pipeline."""
        self.pipeline_paused = True
        
        # Publish pause event
        await self.redis_client.publish(
            "system_events",
            json.dumps({
                "event": "pipeline_paused",
                "timestamp": datetime.now().isoformat()
            })
        )
        
        return {"status": "paused", "timestamp": datetime.now().isoformat()}
    
    async def resume_queue(self):
        """Resume the pipeline."""
        self.pipeline_paused = False
        
        # Publish resume event
        await self.redis_client.publish(
            "system_events",
            json.dumps({
                "event": "pipeline_resumed",
                "timestamp": datetime.now().isoformat()
            })
        )
        
        return {"status": "resumed", "timestamp": datetime.now().isoformat()}
    
    async def publish_job_event(
        self,
        event_type: str,
        job_uuid: str,
        user_id: str,
        status: str,
        timestamp: str,
        trace_id: Optional[str] = None
    ):
        """Publish a job event to Redis."""
        await self.redis_client.publish(
            "job_events",
            json.dumps({
                "event": event_type,
                "job_uuid": job_uuid,
                "user_id": user_id,
                "status": status,
                "timestamp": timestamp,
                "trace_id": trace_id
            })
        )
    
    def run(self, host: str = "0.0.0.0", port: int = 8003):
        """Run the queue service."""
        # Add startup and shutdown events
        self.app.add_event_handler("startup", self.startup_event)
        self.app.add_event_handler("shutdown", self.shutdown_event)
        
        # Run the service
        super().run(host=host, port=port)


if __name__ == "__main__":
    # Get service port from environment
    port = int(os.getenv("QUEUE_PORT", "8003"))
    
    # Create and run service
    service = QueueService()
    service.run(port=port)
