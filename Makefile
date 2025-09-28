.PHONY: help setup-dev install clean test lint format build run-dev run-services stop-services logs deploy-prod backup-db stats

# Configuration
PYTHON := python3
PIP := $(PYTHON) -m pip
PROJECT_NAME := second-brain-stack
VENV_DIR := .venv
DOCKER_COMPOSE := docker-compose
DOCKER_COMPOSE_DEV := $(DOCKER_COMPOSE) -f infra/docker-compose.yml
DOCKER_COMPOSE_PROD := $(DOCKER_COMPOSE) -f infra/docker-compose.prod.yml

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)$(PROJECT_NAME) Development Commands$(NC)"
	@echo "=========================================="
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Development Setup
setup-dev: ## Setup development environment
	@echo "$(GREEN)Setting up development environment...$(NC)"
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip setuptools wheel
	$(VENV_DIR)/bin/pip install -e ".[dev,performance,monitoring]"
	$(VENV_DIR)/bin/pre-commit install
	@echo "$(GREEN)Creating initial directories...$(NC)"
	mkdir -p storage/{vectors,cache,backups,models}
	mkdir -p logs
	@echo "$(GREEN)Development environment setup complete!$(NC)"
	@echo "$(YELLOW)Activate with: source $(VENV_DIR)/bin/activate$(NC)"

install: ## Install package in development mode
	$(PIP) install -e ".[dev]"

clean: ## Clean build artifacts and caches
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -name ".pytest_cache" -type d -exec rm -rf {} +

##@ Code Quality
test: ## Run tests
	@echo "$(GREEN)Running tests...$(NC)"
	$(PYTHON) -m pytest tests/ -v --cov=core --cov=services --cov-report=term-missing --cov-report=html

test-fast: ## Run tests without coverage
	$(PYTHON) -m pytest tests/ -x

lint: ## Run linting
	@echo "$(GREEN)Running linters...$(NC)"
	$(PYTHON) -m black --check core/ services/ interfaces/ connectors/
	$(PYTHON) -m isort --check-only core/ services/ interfaces/ connectors/
	$(PYTHON) -m flake8 core/ services/ interfaces/ connectors/
	$(PYTHON) -m mypy core/ services/ interfaces/ connectors/

format: ## Format code
	@echo "$(GREEN)Formatting code...$(NC)"
	$(PYTHON) -m black core/ services/ interfaces/ connectors/
	$(PYTHON) -m isort core/ services/ interfaces/ connectors/

##@ Database
init-db: ## Initialize database
	@echo "$(GREEN)Initializing database...$(NC)"
	$(PYTHON) -c "
import asyncio
from core.database import DatabaseManager
async def init(): 
    db = DatabaseManager()
    await db.create_tables()
    print('Database initialized successfully')
asyncio.run(init())
"

backup-db: ## Backup database
	@echo "$(GREEN)Backing up database...$(NC)"
	mkdir -p storage/backups
	cp storage/brain.db storage/backups/brain-backup-$$(date +%Y%m%d-%H%M%S).db
	@echo "$(GREEN)Database backup complete$(NC)"

stats: ## Show database statistics
	@$(PYTHON) -c "
import asyncio
from core.database import DatabaseManager
async def show_stats():
    db = DatabaseManager()
    stats = await db.get_stats()
    print('Database Statistics:')
    for key, value in stats.items():
        print(f'  {key}: {value}')
asyncio.run(show_stats())
"

##@ Docker Services
build: ## Build Docker images
	@echo "$(GREEN)Building Docker images...$(NC)"
	$(DOCKER_COMPOSE_DEV) build

run-dev: ## Start development services
	@echo "$(GREEN)Starting development services...$(NC)"
	$(DOCKER_COMPOSE_DEV) up -d
	@echo "$(GREEN)Services started! Check logs with 'make logs'$(NC)"

run-services: run-dev ## Alias for run-dev

stop-services: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(NC)"
	$(DOCKER_COMPOSE_DEV) down

logs: ## Show service logs
	$(DOCKER_COMPOSE_DEV) logs -f

logs-service: ## Show logs for specific service (usage: make logs-service SERVICE=ingestion)
	$(DOCKER_COMPOSE_DEV) logs -f $(SERVICE)

restart-service: ## Restart specific service (usage: make restart-service SERVICE=search)
	$(DOCKER_COMPOSE_DEV) restart $(SERVICE)

##@ CLI Interface
cli-help: ## Show CLI help
	@$(PYTHON) -m interfaces.cli --help

cli-ingest-docs: ## Ingest sample documents
	@echo "$(GREEN)Ingesting documents...$(NC)"
	@$(PYTHON) -m interfaces.cli ingest --source filesystem --path ./docs --recursive

cli-search: ## Interactive search (usage: make cli-search QUERY="machine learning")
	@$(PYTHON) -m interfaces.cli search "$(QUERY)"

cli-chat: ## Start interactive chat
	@$(PYTHON) -m interfaces.cli chat

##@ Production Deployment
deploy-prod: ## Deploy to production
	@echo "$(GREEN)Deploying to production...$(NC)"
	$(DOCKER_COMPOSE_PROD) up -d
	@echo "$(GREEN)Production deployment complete!$(NC)"

prod-logs: ## Show production logs
	$(DOCKER_COMPOSE_PROD) logs -f

stop-prod: ## Stop production services
	$(DOCKER_COMPOSE_PROD) down

##@ Monitoring
health-check: ## Check service health
	@echo "$(GREEN)Checking service health...$(NC)"
	@curl -f http://localhost:8000/health || echo "$(RED)Gateway not responding$(NC)"
	@curl -f http://localhost:8001/health || echo "$(RED)Ingestion service not responding$(NC)"
	@curl -f http://localhost:8002/health || echo "$(RED)Search service not responding$(NC)"
	@curl -f http://localhost:8003/health || echo "$(RED)Knowledge service not responding$(NC)"
	@curl -f http://localhost:8004/health || echo "$(RED)Chat service not responding$(NC)"

performance-test: ## Run performance tests
	@echo "$(GREEN)Running performance tests...$(NC)"
	$(PYTHON) -m tools.benchmarking.load_test

##@ Data Management
create-sample-config: ## Create sample configuration file
	@echo "$(GREEN)Creating sample configuration...$(NC)"
	@cat > brain.yml << 'EOF'
database:
  path: "storage/brain.db"
  wal_mode: true
  fts_enabled: true

services:
  ingestion:
    port: 8001
    workers: 4
    batch_size: 100
  
  search:
    port: 8002
    embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
    vector_dimensions: 384
  
  knowledge:
    port: 8003
    entity_model: "en_core_web_sm"
    min_confidence: 0.8
    
  chat:
    port: 8004
    context_window: 4000

interfaces:
  cli:
    colors: true
    pager: "less"
  
  web:
    debug: false
    port: 8000

embeddings:
  model_path: "storage/models/"
  cache_size: 1000
  batch_size: 32

connectors:
  supported_file_types: [".txt", ".md", ".pdf", ".docx", ".py"]
  max_file_size: "50MB"
  ignore_patterns: ["*.pyc", "__pycache__", ".git"]
EOF
	@echo "$(GREEN)Configuration created: brain.yml$(NC)"

download-models: ## Download required NLP models
	@echo "$(GREEN)Downloading NLP models...$(NC)"
	$(PYTHON) -c "
import spacy
try:
    nlp = spacy.load('en_core_web_sm')
    print('spaCy model already installed')
except OSError:
    print('Downloading spaCy model...')
    import subprocess
    subprocess.run(['$(PYTHON)', '-m', 'spacy', 'download', 'en_core_web_sm'])
"
	$(PYTHON) -c "
from sentence_transformers import SentenceTransformer
import os
os.makedirs('storage/models', exist_ok=True)
print('Downloading sentence transformer model...')
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', cache_folder='storage/models')
print('Model downloaded successfully')
"

##@ Utilities
install-dev-tools: ## Install additional development tools
	$(PIP) install jupyter jupyterlab ipython
	$(PIP) install pytest-xdist pytest-benchmark
	$(PIP) install memory-profiler line-profiler

jupyter: ## Start Jupyter Lab
	$(VENV_DIR)/bin/jupyter lab --ip=0.0.0.0 --port=8888 --no-browser

shell: ## Start Python shell with environment loaded
	@$(PYTHON) -c "
from core.utils import settings
from core.database import DatabaseManager
import asyncio
print('Second Brain Stack Shell')
print('Available: settings, DatabaseManager, asyncio')
print('Example: db = DatabaseManager()')
" -i

##@ Documentation
docs-serve: ## Serve documentation locally
	@echo "$(GREEN)Starting documentation server...$(NC)"
	@echo "Visit http://localhost:8080"
	$(PYTHON) -m http.server 8080 --directory docs/

##@ Cleanup
purge: clean ## Complete cleanup including Docker
	$(DOCKER_COMPOSE_DEV) down --volumes --rmi all
	$(DOCKER_COMPOSE_PROD) down --volumes --rmi all
	docker system prune -f

reset-db: ## Reset database (WARNING: deletes all data)
	@read -p "Are you sure you want to delete all data? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -f storage/brain.db*; \
		rm -rf storage/cache/*; \
		echo "$(YELLOW)Database reset complete$(NC)"; \
		make init-db; \
	fi