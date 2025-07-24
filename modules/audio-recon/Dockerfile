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
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with dynamic UID/GID
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} audio-recon && \
    useradd -m -u ${USER_ID} -g audio-recon audio-recon

# Copy requirements file
COPY audio-recon/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY audio-recon/main.py .
COPY base_service.py .

# Create necessary directories with proper permissions
RUN mkdir -p /pipeline-data/recon-output && chown -R audio-recon:audio-recon /pipeline-data

# Switch to non-root user
USER audio-recon

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${SERVICE_PORT}/health || exit 1

# Command to run the service
CMD ["python", "main.py"]
