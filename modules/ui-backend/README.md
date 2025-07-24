# UI Backend Service

This service provides the API backend for the UI frontend and system management. It acts as a gateway to interact with all other services in the IM2 pipeline.

## Features

- JWT Authentication and user management
- Job management (create, read, update, delete)
- File operations (upload, status tracking, browsing)
- System control (start, stop, reset services)
- Queue management (view, modify queue)
- Statistics and metrics collection

## Endpoints

### Authentication
- `POST /auth/token` - Get JWT token
- `POST /auth/register` - Register new user (admin only)
- `GET /auth/me` - Get current user info

### Jobs
- `GET /jobs` - List all jobs
- `GET /jobs/{job_id}` - Get job details
- `POST /jobs` - Create new job
- `DELETE /jobs/{job_id}` - Cancel job
- `PATCH /jobs/{job_id}` - Update job

### Files
- `GET /files` - Browse files by directory
- `GET /files/{file_id}` - Get file details
- `POST /files/upload` - Upload file
- `GET /files/download/{file_id}` - Download file

### System
- `GET /system/status` - Get system status
- `POST /system/services/{service_name}/restart` - Restart service
- `GET /system/services` - List all services

### Queue
- `GET /queue/status` - Get queue status
- `POST /queue/clear` - Clear queue (admin only)
- `POST /queue/pause` - Pause queue (admin only)
- `POST /queue/resume` - Resume queue (admin only)

### Admin
- `GET /admin/users` - List all users (admin only)
- `PATCH /admin/users/{user_id}` - Update user (admin only)
- `DELETE /admin/users/{user_id}` - Delete user (admin only)

## Configuration

Configuration is done through environment variables:

- `SECRET_KEY` - Secret key for JWT encoding
- `JWT_EXPIRY_MINUTES` - JWT token expiry in minutes
- `ADMIN_USERNAME` - Initial admin username
- `ADMIN_PASSWORD` - Initial admin password
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

## Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run service:
   ```
   python main.py
   ```

3. Access documentation:
   ```
   http://localhost:8000/docs
   ```
