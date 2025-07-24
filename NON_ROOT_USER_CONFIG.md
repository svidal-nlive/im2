# Non-Root User Configuration for IM2 Services

This document describes how the IM2 services are configured to run with non-root users, enhancing security and providing consistent permission management across the system.

## Overview

All services that interact with the `/pipeline-data/` directory are configured to:
1. Run as a non-root user with customizable UID/GID
2. Use consistent permissions for file access
3. Support permission resets via the Makefile

## Configuration

### Environment Variables

The `.env` file contains the following variables for controlling user and group IDs:

```
APP_USER_ID=1000    # Default UID for service containers
APP_GROUP_ID=1000   # Default GID for service containers
```

You can modify these values to match your host system's user/group IDs if needed.

### Docker Compose Configuration

The `docker-compose.yml` file passes these variables to each service:

```yaml
build:
  context: ./modules/service-name
  dockerfile: Dockerfile
  args:
    - USER_ID=${APP_USER_ID:-1000}
    - GROUP_ID=${APP_GROUP_ID:-1000}
```

### Dockerfile Configuration

Each service's Dockerfile creates a non-root user with the specified UID/GID:

```dockerfile
# Create non-root user with dynamic UID/GID
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} appgroup && \
    useradd -m -u ${USER_ID} -g appgroup appuser

# Later in the Dockerfile
USER appuser
```

## Managing Permissions

### Reset Permissions

To reset permissions for the `/pipeline-data/` directory:

```bash
make reset-permissions
```

This command:
1. Ensures the pipeline-data directory exists
2. Sets ownership based on APP_USER_ID and APP_GROUP_ID
3. Sets proper permissions for directories (755) and files (644)

## Updating Service Dockerfiles

When creating new services or updating existing ones, follow these guidelines:

1. Use the template in `modules/Dockerfile.template` as a reference
2. Accept USER_ID and GROUP_ID as build arguments
3. Create a non-root user with those IDs
4. Set appropriate permissions for service-specific directories
5. Run the service as the non-root user

## Special Considerations

### Demucs Service

The Demucs service has specific requirements for caching models, so it uses a dedicated user named "demucs" with the correct UID/GID, and has a volume mapping for persistent model caching:

```yaml
volumes:
  - ./pipeline-data:/pipeline-data
  - ./pipeline-data/models/demucs:/home/demucs/.cache/torch
```
