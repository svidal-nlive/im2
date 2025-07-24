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
RUN mkdir -p /pipeline-data/spleeter-input /pipeline-data/spleeter-output

# Download pre-trained models
RUN mkdir -p /pretrained_models && \
    python -c "from spleeter.separator import Separator; Separator('2stems'); Separator('4stems'); Separator('5stems')"

# Expose port
EXPOSE 8006

# Run service
CMD ["python", "main.py"]
