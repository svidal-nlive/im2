#!/bin/bash

# This script updates all service Dockerfiles to use dynamic UID/GID

# Base template for service Dockerfiles
cat > dockerfile_template.txt << 'EOL'
FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    SERVICE_PORT=8000

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    # Additional dependencies can be added here \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with dynamic UID/GID
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} appgroup && \
    useradd -m -u ${USER_ID} -g appgroup appuser

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /pipeline-data && chown -R appuser:appgroup /pipeline-data

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${SERVICE_PORT}/health || exit 1

# Command to run the service
CMD ["python", "main.py"]
EOL

echo "Template created. Use this as a reference when updating your Dockerfiles."
echo "Make sure to adapt it to each service's specific requirements."
echo ""
echo "Example usage:"
echo "1. For services with specific requirements (like demucs), update the Dockerfile directly."
echo "2. For standard services, use this template as a base, adjusting service-specific details."
echo ""
echo "After updating all Dockerfiles, rebuild your services with:"
echo "  docker compose build"
echo ""
echo "Then reset permissions with:"
echo "  make reset-permissions"
