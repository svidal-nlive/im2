FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ffmpeg \
    libsndfile1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY main.py .

# Create volumes directory structure
RUN mkdir -p /pipeline-data/demucs-input /pipeline-data/demucs-output

# Expose port
EXPOSE 8007

# Run service
CMD ["python", "main.py"]
