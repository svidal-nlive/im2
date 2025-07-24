FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY main.py .

# Create directories
RUN mkdir -p /pipeline-data/input /pipeline-data/output /pipeline-data/logs

# Expose port
EXPOSE 8000

# Run service
CMD ["python", "main.py"]
