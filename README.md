# Audio Processing Pipeline

This project implements a modular audio processing system for separating and processing audio tracks.

## Services

- **Demucs**: Separates audio tracks into stems using the Demucs neural network
- **Spleeter**: Alternative audio separation using Spleeter
- **Audio-Recon**: Recombines processed audio tracks
- **Categorizer**: Analyzes and categorizes audio files
- **Metadata Service**: Manages metadata for audio files
- **Watcher**: Monitors input directories for new files
- **Queue**: Manages processing jobs
- **UI Backend**: FastAPI-based backend for the UI
- **UI Frontend**: Next.js-based frontend

## Directory Structure

- `/modules`: Contains individual service implementations
- `/pipeline-data`: Working directory for the pipeline data (excluded from git)
  - `/models`: Pre-trained models (excluded from git)
  - `/input`: Input files for processing
  - `/output`: Processed output files
  - `/logs`: Service logs
  - And other working directories

## Setup and Usage

1. Make sure Docker and Docker Compose are installed
2. Copy `.env.example` to `.env` and configure as needed
3. Run `docker-compose up` to start the services

## Non-Root User Configuration

All services run as non-root users for security. The user and group IDs can be configured using the `APP_USER_ID` and `APP_GROUP_ID` environment variables in the `.env` file.

To reset permissions on the pipeline data directory:

```bash
make reset-permissions
```

## Documentation

See the `Services PRD` directory for detailed service documentation.
