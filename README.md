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

## Getting Started

Instructions for local development setup coming soon.

## License

TBD
