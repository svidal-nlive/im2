FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ffmpeg \
    libsndfile1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with dynamic UID/GID
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} demucs && \
    useradd -m -u ${USER_ID} -g demucs demucs

# Create cache directory structure with proper permissions
RUN mkdir -p /home/demucs/.cache/torch/hub/checkpoints && \
    chown -R demucs:demucs /home/demucs/.cache

# Copy requirements file
COPY demucs/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY demucs/main.py .
COPY base_service.py .

# Create volumes directory structure
RUN mkdir -p /pipeline-data/demucs-input /pipeline-data/demucs-output && \
    chown -R demucs:demucs /pipeline-data

# Expose port
EXPOSE 8007

# Switch to non-root user
USER demucs

# Make demucs use the right cache directory
ENV TORCH_HOME=/home/demucs/.cache/torch

# Run service
CMD ["python", "main.py"]
