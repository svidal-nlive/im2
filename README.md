# Ironclad Modular Audio Processing Stack (IM2)

A robust, microservices-based audio processing pipeline for audio stem separation and organization.

## Project Overview

IM2 is a resilient, observable, and secure audio processing system designed to:
- Separate audio stems using multiple engines (Spleeter, Demucs)
- Preserve metadata and artwork
- Organize outputs for media servers (Plex/Jellyfin)
- Provide comprehensive observability and monitoring
- Ensure high reliability and safety for all operations

## Architecture

The system is built as a series of microservices, each handling a specific step in the audio processing pipeline:

1. **Watcher**: File system monitoring for new uploads
2. **Categorizer**: Classification and filtering of audio files
3. **Queue**: Job management with PostgreSQL
4. **Metadata Service**: Tag and artwork extraction
5. **Splitter-Stager**: Prepares files for splitting
6. **Spleeter/Demucs**: Stem separation engines
7. **Audio-Recon**: Recombination and tag application
8. **Output Organizer**: Final organization and cleanup
9. **UI Backend/Frontend**: User interface and API
10. **Notifications**: Error and event notification
11. **PipelineCtl**: CLI tool for pipeline management

## Key Features

- **Resilience**: Atomic operations, crash recovery, markers for all stages
- **Observability**: Health/metrics endpoints, structured logging, Grafana dashboards
- **Security**: RBAC, API tokens, file validation, secrets management
- **Efficiency**: Parallelism, resource limits, cleanup automation
- **Developer Experience**: One-command setup, comprehensive testing

## Directory Structure

```
im2/
├── docs/                   # Documentation
├── modules/                # Microservice modules
│   ├── watcher/            # File system watcher service
│   ├── categorizer/        # File classification service
│   ├── queue/              # Job management service
│   ├── metadata-service/   # Metadata extraction service
│   ├── splitter-stager/    # Audio file preparation service
│   ├── spleeter/           # Spleeter stem separation service
│   ├── demucs/             # Demucs stem separation service
│   ├── audio-recon/        # Audio recombination service
│   ├── output-organizer/   # Output organization service
│   ├── ui-backend/         # API backend service
│   ├── ui-frontend/        # User interface service
│   ├── notifications/      # Notification service
│   └── pipelinectl/        # CLI control tool
├── config/                 # Configuration files
└── pipeline-data/          # Data directories
    ├── input/              # Raw uploads
    ├── output/             # Organized instrumentals
    ├── archive/            # Originals (backup)
    ├── error/              # Failed jobs
    ├── logs/               # Structured logs
    ├── cover-art-cache/    # Album art cache
    ├── spleeter-input/     # Staged files for Spleeter
    ├── demucs-input/       # Staged files for Demucs
    └── orphaned/           # Partial/corrupt cleanup targets
```

## Implementation Progress

### Implemented Services

The following services have been implemented with their core functionality:

1. **Watcher**: File system monitoring with stability detection and job queuing
2. **Categorizer**: Audio file validation and format classification
3. **Queue**: PostgreSQL-backed job queue with advisory locking
4. **Metadata Service**: Audio tag extraction and MusicBrainz enrichment
5. **Splitter-Stager**: Input preparation and engine selection for separation
6. **Spleeter**: Stem separation with 2/4/5 stem models
7. **Demucs**: High-quality stem separation with multiple models
8. **Audio-Recon**: Recombination with metadata/artwork preservation
9. **Output Organizer**: Smart organization with archiving and playlist generation
10. **UI Backend**: FastAPI-based backend service with JWT authentication, job management endpoints, and system control functions
11. **UI Frontend**: Next.js 14 web interface with real-time job monitoring, file upload, and system management
12. **Notifications**: Multi-channel notification service with email, UI, webhook, PagerDuty and Slack support
13. **PipelineCtl**: Command-line tool for pipeline management (see details below)

## Pipeline Control Tool (pipelinectl)

The `pipelinectl` CLI tool provides a comprehensive interface for managing the IM2 pipeline:

### Key Features

- **Job Management**: Submit, list, retry, and cancel jobs
- **Pipeline Control**: Start, stop, pause, resume services
- **System Administration**: Health checks, pruning, backup/restore
- **Diagnostics**: Create diagnostic bundles, search logs
- **Developer Tools**: One-command setup, shell completion

### Usage Examples

```bash
# Start the pipeline
pipelinectl pipeline up

# Submit a job
pipelinectl job submit --file /path/to/audio.mp3

# Check system health
pipelinectl system health

# Create diagnostic bundle
pipelinectl diag bundle job_123456
```

For detailed usage, see the [pipelinectl README](modules/pipelinectl/README.md).

## Getting Started

### Prerequisites

- Docker Engine 23.0.0 or newer (with Docker Compose V2 plugin)
- Git
- Make (optional, for convenience commands)

### Setting Up Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/im2.git
   cd im2
   ```

2. Create a local .env file:
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

3. Start the services:
   ```bash
   # Using Docker Compose V2 (plugin)
   docker compose up -d
   
   # Or using Make (which also uses Docker Compose V2)
   make up
   ```

4. Access the services:
   - UI Frontend: http://localhost:3000
   - API Backend: http://localhost:8000/docs
   - Other services have health endpoints: http://localhost:{PORT}/health

### Docker Compose V2

This project uses Docker Compose V2 (the plugin version), which is invoked with `docker compose` (no hyphen) rather than the older `docker-compose`. The compose file format is compatible with both versions, but some features and behaviors might differ.

Key differences when using Docker Compose V2:
- Command syntax: `docker compose` vs. `docker-compose`
- Improved performance and resource usage
- Better integration with Docker CLI
- Parallel execution of commands

For more information, see the [Docker Compose V2 documentation](https://docs.docker.com/compose/).

## License

TBD
