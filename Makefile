.PHONY: help up down status logs clean test lint install

# Default target
help:
	@echo "IM2 Audio Processing Pipeline - Make Targets"
	@echo "----------------------------------------"
	@echo "help     : Show this help message"
	@echo "up       : Start all services"
	@echo "down     : Stop all services"
	@echo "status   : Check service status"
	@echo "logs     : View logs from all services"
	@echo "clean    : Remove generated files"
	@echo "test     : Run tests"
	@echo "lint     : Run linters"
	@echo "install  : Install development dependencies"

# Start all services
up:
	docker compose up -d

# Start all services in foreground
up-fg:
	docker compose up

# Start all services and rebuild
up-build:
	docker compose up -d --build

# Stop all services
down:
	docker compose down

# Check service status
status:
	docker compose ps

# View logs from all services
logs:
	docker compose logs -f

# Clean generated files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +

# Run tests
test:
	@echo "Running tests..."
	# To be implemented

# Run linters
lint:
	@echo "Running linters..."
	# To be implemented

# Install development dependencies
install:
	pip install -r requirements-dev.txt
