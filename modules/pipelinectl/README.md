# IM2 Pipeline Control Tool (pipelinectl)

A command-line interface for managing the IM2 Audio Processing Pipeline.

## Features

- **Pipeline Control**: Start, stop, pause, resume, and check status of services
- **Job Management**: Submit, list, check status, retry, and cancel jobs
- **System Administration**: Health checks, data pruning, backup and restore
- **Diagnostics**: Generate diagnostic bundles, search logs
- **Developer Tools**: One-command development environment setup

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/im2.git
cd im2/modules/pipelinectl

# Install dependencies
pip install -r requirements.txt

# Make the CLI executable
chmod +x pipelinectl.py

# Optional: Create a symlink for easier access
ln -s $(pwd)/pipelinectl.py /usr/local/bin/pipelinectl
```

### Using Docker

```bash
# Build the Docker image
docker build -t im2/pipelinectl .

# Run the CLI using Docker
docker run -it --rm im2/pipelinectl
```

## Configuration

The CLI looks for configuration in `~/.im2/config.yaml`. You can set the following environment variables:

- `IM2_API_URL`: URL of the IM2 API (default: http://localhost:8000)
- `IM2_API_TOKEN`: Authentication token for the API

## Shell Completion

To enable shell completion for Bash:

```bash
source /path/to/pipelinectl_completion.sh
```

Add this line to your `~/.bashrc` to enable completion permanently.

## Usage

### Pipeline Control

```bash
# Start the pipeline
pipelinectl pipeline up

# Start with automatic rebuilding
pipelinectl pipeline up --build

# Start in detached mode
pipelinectl pipeline up --detach

# Check pipeline status
pipelinectl pipeline status

# View logs
pipelinectl pipeline logs
pipelinectl pipeline logs --follow
pipelinectl pipeline logs queue  # View logs for specific service

# Stop the pipeline
pipelinectl pipeline down

# Pause job processing (services remain running)
pipelinectl pipeline pause

# Resume job processing
pipelinectl pipeline resume
```

### Job Management

```bash
# Submit a new job
pipelinectl job submit --file /path/to/audio.mp3 --engine auto

# List jobs
pipelinectl job list
pipelinectl job list --status failed --user john

# Check job status
pipelinectl job status job_123456

# Retry a failed job
pipelinectl job retry job_123456

# Cancel a job
pipelinectl job cancel job_123456
```

### System Management

```bash
# Check system health
pipelinectl system health

# Check specific service health
pipelinectl system health --service queue

# Prune old data (dry run)
pipelinectl system prune --dry-run

# Prune old data (actual)
pipelinectl system prune --older-than 30 --type jobs

# Backup system data
pipelinectl system backup --output /path/to/backups

# Restore from backup
pipelinectl system restore --input /path/to/backup
```

### Diagnostics

```bash
# Create diagnostic bundle for a job
pipelinectl diag bundle job_123456

# Search logs
pipelinectl diag logs --job-id job_123456 --service splitter
```

### Developer Tools

```bash
# Start development environment
pipelinectl dev up

# View API documentation
pipelinectl dev docs
```

## Output Formats

Most commands support JSON output for scripting:

```bash
pipelinectl job list --json
pipelinectl system health --json
```

## License

MIT
