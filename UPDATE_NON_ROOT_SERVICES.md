# Updating Non-Root User Configuration

This document explains how to update all service Dockerfiles to use the non-root user configuration.

## Overview

For security reasons, all services in the IM2 pipeline should run as non-root users with configurable user IDs. This is important for:

1. Security: Limiting container privileges to reduce attack surface
2. File permissions: Ensuring consistent access to shared files
3. Host integration: Matching container user IDs to host system users

## Using the Update Script

We've provided a script that will update all service Dockerfiles to use the standard non-root user template:

```bash
./update_non_root_dockerfiles.sh
```

This script:
1. Takes a template Dockerfile configuration
2. Creates a backup of existing Dockerfiles
3. Updates each service's Dockerfile to include proper non-root user configuration
4. Uses the service's name for the user/group

## After Running the Script

After updating the Dockerfiles:

1. Review the changes made to each Dockerfile
2. Make any service-specific adjustments as needed
3. Rebuild all services:
   ```bash
   docker compose build
   ```
4. Reset permissions for the pipeline-data directory:
   ```bash
   make reset-permissions
   ```

## Manual Adjustments

Some services might need special configuration:

- **Demucs**: Requires specific cache directories for model storage
- **UI Frontend**: Might have different build and runtime requirements
- **Services with special dependencies**: May need additional apt packages

Review each Dockerfile after the update and make any necessary adjustments while preserving the non-root user configuration.

## Testing

After updating and rebuilding:

1. Start the services: `docker compose up -d`
2. Verify they start correctly: `docker compose ps`
3. Check that file permissions work properly by running a test job
4. Confirm that all services can access the files they need in the pipeline-data directory
