.PHONY: help build up down logs ps reset-permissions

# Default target
help:
	@echo "Available commands:"
	@echo "  make build             - Build all containers"
	@echo "  make up                - Start all containers"
	@echo "  make down              - Stop all containers"
	@echo "  make logs              - View logs from all containers"
	@echo "  make ps                - List running containers"
	@echo "  make reset-permissions - Reset permissions for pipeline-data directory"

# Build containers
build:
	docker compose build

# Start containers
up:
	docker compose up -d

# Stop containers
down:
	docker compose down

# View logs
logs:
	docker compose logs -f

# List containers
ps:
	docker compose ps

# Reset permissions for pipeline-data directory
reset-permissions:
	@echo "Resetting permissions for pipeline-data directory..."
	@mkdir -p pipeline-data
	@if [ -f .env ]; then \
		export $$(grep -v '^#' .env | xargs); \
		echo "Using APP_USER_ID=$${APP_USER_ID:-1000} and APP_GROUP_ID=$${APP_GROUP_ID:-1000}"; \
	else \
		echo "Warning: .env file not found. Using default values (1000:1000)."; \
		export APP_USER_ID=1000 APP_GROUP_ID=1000; \
	fi; \
	sudo chown -R $${APP_USER_ID:-1000}:$${APP_GROUP_ID:-1000} pipeline-data; \
	sudo chmod -R 755 pipeline-data; \
	sudo find pipeline-data -type d -exec chmod 755 {} \;; \
	sudo find pipeline-data -type f -exec chmod 644 {} \;
	@echo "Permissions reset successfully."
