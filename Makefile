.PHONY: help install dev up down test lint format clean

help: ## Show this help message
	@echo "AI Reliability Lab - Available Commands"
	@echo "========================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install all Python packages in development mode
	@echo "Installing Python packages..."
	pip install -e packages/shared
	pip install -e packages/sdk
	pip install -e packages/tracing
	pip install -e packages/evals
	pip install -e packages/reliability
	pip install -e packages/prompts
	pip install -e apps/api
	pip install -e apps/worker
	pip install -e apps/evaluator

dev: install ## Install dev dependencies
	pip install pytest pytest-asyncio black mypy httpx

up: ## Start all services with Docker Compose
	cd infra/docker && docker-compose up -d

down: ## Stop all services
	cd infra/docker && docker-compose down

logs: ## Show logs from all services
	cd infra/docker && docker-compose logs -f

test: ## Run all tests
	pytest packages/ apps/ -v

test-cov: ## Run tests with coverage
	pytest packages/ apps/ --cov=packages --cov-report=html

lint: ## Run linters
	black --check packages/ apps/
	mypy packages/ apps/

format: ## Format code
	black packages/ apps/

clean: ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov/

api: ## Run API server locally
	cd apps/api && uvicorn src.main:app --reload --port 8000

dashboard: ## Run dashboard locally
	cd apps/dashboard && npm run dev

benchmarks: ## Export all benchmark datasets
	cd benchmarks && python runner.py

schema: ## Initialize ClickHouse schema
	cd apps/api && python -c "import asyncio; from src.db.clickhouse import ClickHouseClient; c = ClickHouseClient(); asyncio.run(c.init_schema())"
