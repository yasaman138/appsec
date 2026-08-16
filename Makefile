.PHONY: help test test-unit test-integration test-security scan lint build up down logs clean

help:
	@echo "Available commands:"
	@echo "  make test             - Run all unit, integration, and security regression tests"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-security    - Run security exploit regression tests only"
	@echo "  make scan             - Run custom Semgrep SAST security rules"
	@echo "  make build            - Build Docker container images"
	@echo "  make up               - Boot full microservices stack via Docker Compose"
	@echo "  make down             - Stop and remove Docker Compose containers"
	@echo "  make logs             - Tail container logs"
	@echo "  make clean            - Clean cache, temporary test artifacts, and SQLite databases"

test:
	pytest -v tests/

test-unit:
	pytest -v tests/unit/

test-integration:
	pytest -v tests/integration/

test-security:
	pytest -v tests/security/

scan:
	semgrep scan --config=.semgrep/ --error

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

clean:
	rm -rf .pytest_cache __pycache__ tests/**/__pycache__ services/**/__pycache__ services/**/src/**/__pycache__ *.db
