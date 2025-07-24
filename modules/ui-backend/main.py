"""
UI Backend Service for IM2 Audio Processing Pipeline

This service:
1. Provides a REST API for the frontend UI
2. Manages user authentication and authorization
3. Acts as a gateway to other microservices
4. Provides job monitoring and control
5. Serves documentation and metrics endpoints
"""

import os
import sys
import json
import logging
import asyncio
import time
import uuid
import secrets
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

import aiohttp
import aiofiles
from fastapi import FastAPI, HTTPException, APIRouter, Depends, Request, Response, BackgroundTasks, Header, Cookie, status, File, UploadFile, Form, Query, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, EmailStr, validator
import jwt
from passlib.context import CryptContext

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
logger = logging.getLogger("ui-backend")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Models for authentication
class User(BaseModel):
    """User model."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None
    disabled: Optional[bool] = False
    role: str = "user"  # "user", "admin", etc.

class UserInDB(User):
    """User model with hashed password."""
    hashed_password: str

class UserCreate(User):
    """User creation model."""
    password: str = Field(..., min_length=8)

class Token(BaseModel):
    """Token model."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Token data model."""
    username: Optional[str] = None
    role: Optional[str] = None

# Models for jobs
class JobStatus(str, Enum):
    """Job status enum."""
    NEW = "new"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobType(str, Enum):
    """Job type enum."""
    SEPARATION = "separation"
    RECOMBINATION = "recombination"
    ORGANIZATION = "organization"
    CUSTOM = "custom"

class JobFilter(BaseModel):
    """Job filter model."""
    status: Optional[List[JobStatus]] = None
    user_id: Optional[str] = None
    job_type: Optional[JobType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 10
    offset: int = 0

class JobCreateRequest(BaseModel):
    """Job creation request model."""
    job_type: JobType
    file_path: Optional[str] = None
    engine: Optional[str] = None
    options: Optional[Dict[str, Any]] = None

class JobDetail(BaseModel):
    """Job detail model."""
    uuid: str
    user_id: str
    status: JobStatus
    job_type: JobType
    created_at: datetime
    updated_at: datetime
    file_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    progress: Optional[float] = None
    error: Optional[str] = None
    outputs: Optional[Dict[str, str]] = None

class SystemStats(BaseModel):
    """System statistics model."""
    active_jobs: int
    completed_jobs: int
    failed_jobs: int
    queue_size: int
    disk_usage: Dict[str, Any]
    service_status: Dict[str, bool]
    version: str

class ServiceInfo(BaseModel):
    """Service information model."""
    name: str
    status: bool
    version: Optional[str] = None
    url: Optional[str] = None

class UIBackendService(BaseService):
    """UI Backend service for IM2 Audio Processing Pipeline."""
    
    def __init__(self):
        """Initialize the UI Backend service."""
        super().__init__(
            name="ui-backend",
            version="0.1.0",
            description="API Backend service for IM2 Audio Processing Pipeline",
            dependencies=["queue"]
        )
        
        # Configure settings
        self.queue_service_url = os.getenv("QUEUE_SERVICE_URL", "http://queue:8003")
        self.watcher_service_url = os.getenv("WATCHER_SERVICE_URL", "http://watcher:8001")
        self.categorizer_service_url = os.getenv("CATEGORIZER_SERVICE_URL", "http://categorizer:8002")
        self.metadata_service_url = os.getenv("METADATA_SERVICE_URL", "http://metadata-service:8004")
        self.splitter_stager_service_url = os.getenv("SPLITTER_STAGER_SERVICE_URL", "http://splitter-stager:8005")
        self.spleeter_service_url = os.getenv("SPLEETER_SERVICE_URL", "http://spleeter:8006")
        self.demucs_service_url = os.getenv("DEMUCS_SERVICE_URL", "http://demucs:8007")
        self.audio_recon_service_url = os.getenv("AUDIO_RECON_SERVICE_URL", "http://audio-recon:8008")
        self.output_organizer_service_url = os.getenv("OUTPUT_ORGANIZER_SERVICE_URL", "http://output-organizer:8009")
        
        # Data directories
        self.input_path = os.getenv("INPUT_PATH", "/pipeline-data/input")
        self.output_path = os.getenv("OUTPUT_PATH", "/pipeline-data/output")
        self.logs_path = os.getenv("LOGS_PATH", "/pipeline-data/logs")
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # For development, replace with specific origins in production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup routes
        self.setup_routes()
        
        # Mock user database (replace with real DB in production)
        self.users_db = {
            "admin": {
                "username": "admin",
                "email": "admin@example.com",
                "full_name": "Admin User",
                "disabled": False,
                "role": "admin",
                "hashed_password": pwd_context.hash("adminpassword")
            },
            "user": {
                "username": "user",
                "email": "user@example.com",
                "full_name": "Regular User",
                "disabled": False,
                "role": "user",
                "hashed_password": pwd_context.hash("userpassword")
            }
        }
    
    def setup_routes(self):
        """Setup API routes."""
        # Auth router
        auth_router = APIRouter(tags=["authentication"])
        auth_router.post("/token", response_model=Token)(self.login_for_access_token)
        auth_router.post("/register", response_model=User)(self.register_user)
        auth_router.get("/users/me", response_model=User)(self.get_current_user_endpoint)
        
        # Jobs router
        jobs_router = APIRouter(tags=["jobs"])
        jobs_router.get("/jobs", response_model=Dict[str, Any])(self.get_jobs)
        jobs_router.post("/jobs", response_model=JobDetail)(self.create_job)
        jobs_router.get("/jobs/{job_uuid}", response_model=JobDetail)(self.get_job)
        jobs_router.put("/jobs/{job_uuid}", response_model=JobDetail)(self.update_job)
        jobs_router.delete("/jobs/{job_uuid}", response_model=Dict[str, Any])(self.delete_job)
        jobs_router.post("/jobs/{job_uuid}/cancel", response_model=Dict[str, Any])(self.cancel_job)
        jobs_router.post("/jobs/{job_uuid}/retry", response_model=Dict[str, Any])(self.retry_job)
        
        # Files router
        files_router = APIRouter(tags=["files"])
        files_router.post("/upload", response_model=Dict[str, Any])(self.upload_file)
        files_router.get("/files", response_model=List[Dict[str, Any]])(self.list_files)
        files_router.get("/files/{path:path}", response_class=FileResponse)(self.get_file)
        files_router.delete("/files/{path:path}", response_model=Dict[str, Any])(self.delete_file)
        
        # System router
        system_router = APIRouter(tags=["system"])
        system_router.get("/stats", response_model=SystemStats)(self.get_system_stats)
        system_router.get("/services", response_model=List[ServiceInfo])(self.get_services_status)
        system_router.get("/logs", response_model=Dict[str, Any])(self.get_logs)
        system_router.post("/restart/{service_name}", response_model=Dict[str, Any])(self.restart_service)
        
        # Include routers with prefix and dependencies
        self.app.include_router(
            auth_router,
            prefix="/api",
        )
        
        self.app.include_router(
            jobs_router,
            prefix="/api",
            dependencies=[Depends(self.get_current_user)]
        )
        
        self.app.include_router(
            files_router,
            prefix="/api",
            dependencies=[Depends(self.get_current_user)]
        )
        
        self.app.include_router(
            system_router,
            prefix="/api",
            dependencies=[Depends(self.get_current_admin)]
        )
    
    # Authentication functions
    def verify_password(self, plain_password, hashed_password):
        """Verify password against hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password):
        """Get password hash."""
        return pwd_context.hash(password)
    
    async def get_user(self, username: str) -> Optional[UserInDB]:
        """Get user from database."""
        if username in self.users_db:
            user_dict = self.users_db[username]
            return UserInDB(**user_dict)
        return None
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user."""
        user = await self.get_user(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    
    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> User:
        """Get current user from token."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = TokenData(username=username, role=payload.get("role"))
        except jwt.PyJWTError:
            raise credentials_exception
        user = await self.get_user(username=token_data.username)
        if user is None:
            raise credentials_exception
        return user
    
    async def get_current_active_user(self, current_user: User = Depends(get_current_user)) -> User:
        """Get current active user."""
        if current_user.disabled:
            raise HTTPException(status_code=400, detail="Inactive user")
        return current_user
    
    async def get_current_admin(self, current_user: User = Depends(get_current_user)) -> User:
        """Get current admin user."""
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return current_user
    
    # Auth endpoints
    async def login_for_access_token(self, form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
        """Login endpoint to get access token."""
        user = await self.authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": user.username, "role": user.role},
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    
    async def register_user(self, user_data: UserCreate) -> User:
        """Register a new user."""
        # Check if username already exists
        if user_data.username in self.users_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Create new user (in a real app, you'd save to a database)
        hashed_password = self.get_password_hash(user_data.password)
        self.users_db[user_data.username] = {
            "username": user_data.username,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "disabled": False,
            "role": "user",  # Default role
            "hashed_password": hashed_password
        }
        
        # Return user info (without password)
        return User(**self.users_db[user_data.username])
    
    async def get_current_user_endpoint(self, current_user: User = Depends(get_current_active_user)) -> User:
        """Get current user information endpoint."""
        return current_user
    
    # Job management endpoints
    async def get_jobs(self, filter_params: JobFilter = Depends()) -> Dict[str, Any]:
        """Get jobs with filtering."""
        try:
            # Convert filters to query parameters
            params = {}
            if filter_params.status:
                params["status"] = ",".join(filter_params.status)
            if filter_params.user_id:
                params["user_id"] = filter_params.user_id
            if filter_params.job_type:
                params["job_type"] = filter_params.job_type
            if filter_params.start_date:
                params["start_date"] = filter_params.start_date.isoformat()
            if filter_params.end_date:
                params["end_date"] = filter_params.end_date.isoformat()
            
            params["limit"] = filter_params.limit
            params["offset"] = filter_params.offset
            
            # Call queue service
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.queue_service_url}/api/jobs",
                    params=params
                ) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Error fetching jobs: {await response.text()}"
                        )
                    
                    data = await response.json()
                    return data
        
        except Exception as e:
            logger.error(f"Error getting jobs: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting jobs: {str(e)}"
            )
    
    async def create_job(
        self,
        job_request: JobCreateRequest,
        current_user: User = Depends(get_current_active_user)
    ) -> JobDetail:
        """Create a new job."""
        try:
            # Prepare job data
            job_data = {
                "job_type": job_request.job_type,
                "user_id": current_user.username,
                "file_path": job_request.file_path,
                "metadata": {
                    "engine": job_request.engine,
                    "options": job_request.options
                }
            }
            
            # Call queue service
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.queue_service_url}/api/jobs",
                    json=job_data
                ) as response:
                    if response.status != 200 and response.status != 201:
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Error creating job: {await response.text()}"
                        )
                    
                    data = await response.json()
                    return JobDetail(**data)
        
        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error creating job: {str(e)}"
            )
    
    async def get_job(
        self,
        job_uuid: str,
        current_user: User = Depends(get_current_active_user)
    ) -> JobDetail:
        """Get job details."""
        try:
            # Call queue service
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.queue_service_url}/api/jobs/{job_uuid}"
                ) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Error fetching job: {await response.text()}"
                        )
                    
                    data = await response.json()
                    
                    # Check if user has access to this job
                    if current_user.role != "admin" and data.get("user_id") != current_user.username:
                        raise HTTPException(
                            status_code=403,
                            detail="Not authorized to access this job"
                        )
                    
                    return JobDetail(**data)
        
        except Exception as e:
            logger.error(f"Error getting job {job_uuid}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting job: {str(e)}"
            )
    
    async def update_job(
        self,
        job_uuid: str,
        job_data: Dict[str, Any],
        current_user: User = Depends(get_current_active_user)
    ) -> JobDetail:
        """Update job details."""
        try:
            # First, get current job to check permissions
            current_job = await self.get_job(job_uuid, current_user)
            
            # Check if user has permission to update this job
            if current_user.role != "admin" and current_job.user_id != current_user.username:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to update this job"
                )
            
            # Call queue service
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{self.queue_service_url}/api/jobs/{job_uuid}",
                    json=job_data
                ) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Error updating job: {await response.text()}"
                        )
                    
                    data = await response.json()
                    return JobDetail(**data)
        
        except Exception as e:
            logger.error(f"Error updating job {job_uuid}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error updating job: {str(e)}"
            )
    
    async def delete_job(
        self,
        job_uuid: str,
        current_user: User = Depends(get_current_active_user)
    ) -> Dict[str, Any]:
        """Delete a job."""
        try:
            # First, get current job to check permissions
            current_job = await self.get_job(job_uuid, current_user)
            
            # Check if user has permission to delete this job
            if current_user.role != "admin" and current_job.user_id != current_user.username:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to delete this job"
                )
            
            # Call queue service
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.queue_service_url}/api/jobs/{job_uuid}"
                ) as response:
                    if response.status != 200 and response.status != 204:
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Error deleting job: {await response.text()}"
                        )
                    
                    return {"status": "success", "message": f"Job {job_uuid} deleted successfully"}
        
        except Exception as e:
            logger.error(f"Error deleting job {job_uuid}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting job: {str(e)}"
            )
    
    async def cancel_job(
        self,
        job_uuid: str,
        current_user: User = Depends(get_current_active_user)
    ) -> Dict[str, Any]:
        """Cancel a running job."""
        try:
            # First, get current job to check permissions
            current_job = await self.get_job(job_uuid, current_user)
            
            # Check if user has permission to cancel this job
            if current_user.role != "admin" and current_job.user_id != current_user.username:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to cancel this job"
                )
            
            # Check if job can be cancelled (status check)
            if current_job.status not in [JobStatus.NEW, JobStatus.PROCESSING]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Job cannot be cancelled in status: {current_job.status}"
                )
            
            # Call queue service
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.queue_service_url}/api/jobs/{job_uuid}/cancel"
                ) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Error cancelling job: {await response.text()}"
                        )
                    
                    data = await response.json()
                    return data
        
        except Exception as e:
            logger.error(f"Error cancelling job {job_uuid}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error cancelling job: {str(e)}"
            )
    
    async def retry_job(
        self,
        job_uuid: str,
        current_user: User = Depends(get_current_active_user)
    ) -> Dict[str, Any]:
        """Retry a failed job."""
        try:
            # First, get current job to check permissions
            current_job = await self.get_job(job_uuid, current_user)
            
            # Check if user has permission to retry this job
            if current_user.role != "admin" and current_job.user_id != current_user.username:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to retry this job"
                )
            
            # Check if job can be retried (status check)
            if current_job.status not in [JobStatus.FAILED, JobStatus.CANCELLED]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Job cannot be retried in status: {current_job.status}"
                )
            
            # Call queue service
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.queue_service_url}/api/jobs/{job_uuid}/retry"
                ) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Error retrying job: {await response.text()}"
                        )
                    
                    data = await response.json()
                    return data
        
        except Exception as e:
            logger.error(f"Error retrying job {job_uuid}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error retrying job: {str(e)}"
            )
    
    # File management endpoints
    async def upload_file(
        self,
        file: UploadFile = File(...),
        user_id: str = Form(...),
        destination: Optional[str] = Form(None),
        current_user: User = Depends(get_current_active_user)
    ) -> Dict[str, Any]:
        """Upload a file."""
        try:
            # Verify user has permission to upload for this user_id
            if current_user.role != "admin" and user_id != current_user.username:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to upload for this user"
                )
            
            # Determine destination path
            if not destination:
                destination = "uploads"
            
            # Create user-specific input directory
            user_input_dir = os.path.join(self.input_path, user_id, destination)
            os.makedirs(user_input_dir, exist_ok=True)
            
            # Generate unique filename if needed
            filename = file.filename
            file_path = os.path.join(user_input_dir, filename)
            
            # Check if file already exists
            if os.path.exists(file_path):
                # Add timestamp to make unique
                base_name, extension = os.path.splitext(filename)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"{base_name}_{timestamp}{extension}"
                file_path = os.path.join(user_input_dir, filename)
            
            # Save the file
            async with aiofiles.open(file_path, "wb") as f:
                # Read and write in chunks to handle large files
                CHUNK_SIZE = 1024 * 1024  # 1MB chunks
                while chunk := await file.read(CHUNK_SIZE):
                    await f.write(chunk)
            
            # Return file info
            return {
                "filename": filename,
                "path": file_path,
                "size": os.path.getsize(file_path),
                "status": "success",
                "message": "File uploaded successfully"
            }
        
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error uploading file: {str(e)}"
            )
    
    async def list_files(
        self,
        directory: Optional[str] = Query(None),
        user_id: Optional[str] = Query(None),
        recursive: bool = Query(False),
        current_user: User = Depends(get_current_active_user)
    ) -> List[Dict[str, Any]]:
        """List files in a directory."""
        try:
            # Determine user_id and verify permissions
            if not user_id:
                user_id = current_user.username
            elif current_user.role != "admin" and user_id != current_user.username:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to list files for this user"
                )
            
            # Determine base directory
            base_dir = os.path.join(self.input_path, user_id)
            if directory:
                base_dir = os.path.join(base_dir, directory)
            
            # Check if directory exists
            if not os.path.exists(base_dir) or not os.path.isdir(base_dir):
                return []
            
            # Get file list
            file_list = []
            
            if recursive:
                # Recursive walk
                for root, dirs, files in os.walk(base_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, base_dir)
                        
                        file_list.append({
                            "name": file,
                            "path": rel_path,
                            "full_path": file_path,
                            "size": os.path.getsize(file_path),
                            "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                            "type": "file"
                        })
            else:
                # Non-recursive list
                items = os.listdir(base_dir)
                for item in items:
                    item_path = os.path.join(base_dir, item)
                    
                    if os.path.isfile(item_path):
                        file_list.append({
                            "name": item,
                            "path": item,
                            "full_path": item_path,
                            "size": os.path.getsize(item_path),
                            "modified": datetime.fromtimestamp(os.path.getmtime(item_path)).isoformat(),
                            "type": "file"
                        })
                    elif os.path.isdir(item_path):
                        file_list.append({
                            "name": item,
                            "path": item,
                            "full_path": item_path,
                            "modified": datetime.fromtimestamp(os.path.getmtime(item_path)).isoformat(),
                            "type": "directory"
                        })
            
            return file_list
        
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error listing files: {str(e)}"
            )
    
    async def get_file(
        self,
        path: str,
        user_id: Optional[str] = Query(None),
        current_user: User = Depends(get_current_active_user)
    ) -> FileResponse:
        """Get/download a file."""
        try:
            # Determine user_id and verify permissions
            if not user_id:
                user_id = current_user.username
            elif current_user.role != "admin" and user_id != current_user.username:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to access files for this user"
                )
            
            # Determine file path
            file_path = os.path.join(self.input_path, user_id, path)
            
            # Check if file exists
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                raise HTTPException(
                    status_code=404,
                    detail=f"File not found: {path}"
                )
            
            # Return file
            return FileResponse(
                path=file_path,
                filename=os.path.basename(file_path),
                media_type="application/octet-stream"
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting file {path}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting file: {str(e)}"
            )
    
    async def delete_file(
        self,
        path: str,
        user_id: Optional[str] = Query(None),
        current_user: User = Depends(get_current_active_user)
    ) -> Dict[str, Any]:
        """Delete a file."""
        try:
            # Determine user_id and verify permissions
            if not user_id:
                user_id = current_user.username
            elif current_user.role != "admin" and user_id != current_user.username:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to delete files for this user"
                )
            
            # Determine file path
            file_path = os.path.join(self.input_path, user_id, path)
            
            # Check if file exists
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                raise HTTPException(
                    status_code=404,
                    detail=f"File not found: {path}"
                )
            
            # Delete file
            os.remove(file_path)
            
            return {
                "status": "success",
                "message": f"File {path} deleted successfully"
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting file {path}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting file: {str(e)}"
            )
    
    # System management endpoints
    async def get_system_stats(self, current_user: User = Depends(get_current_admin)) -> SystemStats:
        """Get system statistics."""
        try:
            # Get job stats from queue service
            job_stats = await self.get_job_stats()
            
            # Get disk usage stats
            disk_usage = await self.get_disk_usage()
            
            # Get service status
            service_status = await self.get_service_status()
            
            # Create system stats
            stats = SystemStats(
                active_jobs=job_stats.get("active_jobs", 0),
                completed_jobs=job_stats.get("completed_jobs", 0),
                failed_jobs=job_stats.get("failed_jobs", 0),
                queue_size=job_stats.get("queue_size", 0),
                disk_usage=disk_usage,
                service_status=service_status,
                version="0.1.0"
            )
            
            return stats
        
        except Exception as e:
            logger.error(f"Error getting system stats: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting system stats: {str(e)}"
            )
    
    async def get_job_stats(self) -> Dict[str, Any]:
        """Get job statistics from queue service."""
        try:
            # Call queue service
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.queue_service_url}/api/stats"
                ) as response:
                    if response.status != 200:
                        logger.error(f"Error fetching job stats: {await response.text()}")
                        return {
                            "active_jobs": 0,
                            "completed_jobs": 0,
                            "failed_jobs": 0,
                            "queue_size": 0
                        }
                    
                    data = await response.json()
                    return data
        
        except Exception as e:
            logger.error(f"Error getting job stats: {str(e)}")
            return {
                "active_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "queue_size": 0
            }
    
    async def get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage statistics."""
        try:
            # Get usage for different directories
            input_usage = self.get_directory_size(self.input_path)
            output_usage = self.get_directory_size(self.output_path)
            logs_usage = self.get_directory_size(self.logs_path)
            
            # Get total disk space
            total, used, free = shutil.disk_usage("/")
            
            return {
                "input": input_usage,
                "output": output_usage,
                "logs": logs_usage,
                "total": total,
                "used": used,
                "free": free,
                "used_percent": (used / total) * 100
            }
        
        except Exception as e:
            logger.error(f"Error getting disk usage: {str(e)}")
            return {
                "input": 0,
                "output": 0,
                "logs": 0,
                "total": 0,
                "used": 0,
                "free": 0,
                "used_percent": 0
            }
    
    def get_directory_size(self, path: str) -> int:
        """Get directory size in bytes."""
        try:
            if not os.path.exists(path):
                return 0
            
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
            
            return total_size
        
        except Exception as e:
            logger.error(f"Error getting directory size for {path}: {str(e)}")
            return 0
    
    async def get_service_status(self) -> Dict[str, bool]:
        """Get status of all services."""
        services = {
            "queue": False,
            "watcher": False,
            "categorizer": False,
            "metadata-service": False,
            "splitter-stager": False,
            "spleeter": False,
            "demucs": False,
            "audio-recon": False,
            "output-organizer": False,
            "ui-backend": True  # This service is running if we're here
        }
        
        # Dictionary of service URLs
        service_urls = {
            "queue": self.queue_service_url,
            "watcher": self.watcher_service_url,
            "categorizer": self.categorizer_service_url,
            "metadata-service": self.metadata_service_url,
            "splitter-stager": self.splitter_stager_service_url,
            "spleeter": self.spleeter_service_url,
            "demucs": self.demucs_service_url,
            "audio-recon": self.audio_recon_service_url,
            "output-organizer": self.output_organizer_service_url
        }
        
        # Check each service
        async with aiohttp.ClientSession() as session:
            for service_name, service_url in service_urls.items():
                try:
                    async with session.get(
                        f"{service_url}/health",
                        timeout=2  # Short timeout
                    ) as response:
                        if response.status == 200:
                            services[service_name] = True
                except Exception:
                    # Service is down or unreachable
                    pass
        
        return services
    
    async def get_services_status(self, current_user: User = Depends(get_current_admin)) -> List[ServiceInfo]:
        """Get detailed status of all services."""
        services = [
            {"name": "queue", "url": self.queue_service_url},
            {"name": "watcher", "url": self.watcher_service_url},
            {"name": "categorizer", "url": self.categorizer_service_url},
            {"name": "metadata-service", "url": self.metadata_service_url},
            {"name": "splitter-stager", "url": self.splitter_stager_service_url},
            {"name": "spleeter", "url": self.spleeter_service_url},
            {"name": "demucs", "url": self.demucs_service_url},
            {"name": "audio-recon", "url": self.audio_recon_service_url},
            {"name": "output-organizer", "url": self.output_organizer_service_url},
            {"name": "ui-backend", "url": "http://localhost:8000", "status": True, "version": "0.1.0"}
        ]
        
        # Check each service
        result = []
        async with aiohttp.ClientSession() as session:
            for service in services:
                if service["name"] == "ui-backend":
                    # This service is already marked as running
                    result.append(ServiceInfo(**service))
                    continue
                
                try:
                    async with session.get(
                        f"{service['url']}/health",
                        timeout=2  # Short timeout
                    ) as response:
                        if response.status == 200:
                            # Get service info from response
                            data = await response.json()
                            result.append(ServiceInfo(
                                name=service["name"],
                                status=True,
                                version=data.get("version"),
                                url=service["url"]
                            ))
                        else:
                            result.append(ServiceInfo(
                                name=service["name"],
                                status=False,
                                url=service["url"]
                            ))
                except Exception:
                    # Service is down or unreachable
                    result.append(ServiceInfo(
                        name=service["name"],
                        status=False,
                        url=service["url"]
                    ))
        
        return result
    
    async def get_logs(
        self,
        service: Optional[str] = Query(None),
        lines: int = Query(100),
        current_user: User = Depends(get_current_admin)
    ) -> Dict[str, Any]:
        """Get logs for a service."""
        try:
            # Validate lines parameter
            if lines < 1:
                lines = 100
            elif lines > 1000:
                lines = 1000
            
            log_data = {}
            
            if service:
                # Get logs for specific service
                log_file = os.path.join(self.logs_path, f"{service}.log")
                if os.path.exists(log_file):
                    log_data[service] = await self.read_log_file(log_file, lines)
                else:
                    log_data[service] = []
            else:
                # Get logs for all services
                services = [
                    "queue", "watcher", "categorizer", "metadata-service",
                    "splitter-stager", "spleeter", "demucs", "audio-recon",
                    "output-organizer", "ui-backend"
                ]
                
                for svc in services:
                    log_file = os.path.join(self.logs_path, f"{svc}.log")
                    if os.path.exists(log_file):
                        log_data[svc] = await self.read_log_file(log_file, lines)
                    else:
                        log_data[svc] = []
            
            return {
                "logs": log_data
            }
        
        except Exception as e:
            logger.error(f"Error getting logs: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting logs: {str(e)}"
            )
    
    async def read_log_file(self, file_path: str, lines: int) -> List[str]:
        """Read the last N lines from a log file."""
        try:
            # This is a simple implementation; for large files, a more efficient
            # approach would be to read from the end of the file
            async with aiofiles.open(file_path, "r") as f:
                all_lines = await f.readlines()
                return all_lines[-lines:]
        
        except Exception as e:
            logger.error(f"Error reading log file {file_path}: {str(e)}")
            return []
    
    async def restart_service(
        self,
        service_name: str,
        current_user: User = Depends(get_current_admin)
    ) -> Dict[str, Any]:
        """Restart a service."""
        # This would typically call Docker or Kubernetes API to restart the service
        # For now, we'll just return a mock response
        return {
            "status": "success",
            "message": f"Service {service_name} restart initiated",
            "note": "This is a mock implementation. In production, this would restart the actual service."
        }
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the UI Backend service."""
        # Run the service
        super().run(host=host, port=port)


if __name__ == "__main__":
    # Get service port from environment
    port = int(os.getenv("UI_BACKEND_PORT", "8000"))
    
    # Create and run service
    service = UIBackendService()
    service.run(port=port)
