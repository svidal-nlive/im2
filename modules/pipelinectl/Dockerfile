FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Make script executable
RUN chmod +x pipelinectl.py

# Create symlink to make the command available as 'pipelinectl'
RUN ln -s /app/pipelinectl.py /usr/local/bin/pipelinectl

# Set entrypoint
ENTRYPOINT ["pipelinectl"]

# Default command (will show help)
CMD ["--help"]
