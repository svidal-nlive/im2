#!/bin/bash

# This script updates all service Dockerfiles to use the standard non-root user template

# Get a list of all service directories
SERVICE_DIRS=$(find modules -maxdepth 1 -mindepth 1 -type d -not -path "modules/tests" -not -path "modules/__pycache__")

# Template Dockerfile content
TEMPLATE=$(cat modules/Dockerfile.template)

# Process each service directory
for SERVICE_DIR in $SERVICE_DIRS; do
    SERVICE_NAME=$(basename $SERVICE_DIR)
    DOCKERFILE_PATH="$SERVICE_DIR/Dockerfile"
    
    echo "Updating Dockerfile for $SERVICE_NAME..."
    
    # Create a backup of the existing Dockerfile if it exists
    if [ -f "$DOCKERFILE_PATH" ] && [ -s "$DOCKERFILE_PATH" ]; then
        cp "$DOCKERFILE_PATH" "${DOCKERFILE_PATH}.bak"
        echo "  Created backup at ${DOCKERFILE_PATH}.bak"
    fi
    
    # Start with the template
    DOCKERFILE_CONTENT="FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PIP_NO_CACHE_DIR=off \\
    PIP_DISABLE_PIP_VERSION_CHECK=on \\
    SERVICE_PORT=8000

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    # Add any additional dependencies here \\
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with dynamic UID/GID
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g \${GROUP_ID} ${SERVICE_NAME} && \\
    useradd -m -u \${USER_ID} -g ${SERVICE_NAME} ${SERVICE_NAME}

# Copy requirements file
COPY ${SERVICE_NAME}/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY ${SERVICE_NAME}/main.py .
COPY base_service.py .

# Create necessary directories with proper permissions
RUN mkdir -p /pipeline-data && chown -R ${SERVICE_NAME}:${SERVICE_NAME} /pipeline-data

# Switch to non-root user
USER ${SERVICE_NAME}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:\${SERVICE_PORT}/health || exit 1

# Command to run the service
CMD [\"python\", \"main.py\"]
"
    
    # Write the new Dockerfile
    echo "$DOCKERFILE_CONTENT" > "$DOCKERFILE_PATH"
    echo "  Updated $DOCKERFILE_PATH"
done

echo "All Dockerfiles have been updated with non-root user configuration."
echo "Review the changes and rebuild your services with: docker compose build"
echo "Then reset permissions with: make reset-permissions"
