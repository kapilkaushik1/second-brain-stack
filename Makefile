# ======================================================================================
# MISCELLANEOUS
# ======================================================================================

RED     := \033[0;31m
GREEN   := \033[0;32m
YELLOW  := \033[1;33m 
BLUE    := \033[0;34m
NC      := \033[0m

# ======================================================================================
# GENERAL CONFIGURATION
# ======================================================================================

SHELL := /bin/bash

COMPOSE_FILE ?= docker-compose.yml
COMPOSE_DEV_FILE ?= docker-compose.dev.yml
COMPOSE := docker compose -f $(COMPOSE_FILE)

# ======================================================================================
# DEFAULT TARGET & SELF-DOCUMENTATION
# ======================================================================================
.DEFAULT_GOAL := help

# Phony targets - don't represent files
.PHONY: app help up down logs ps build no-cache restart re config status clean fclean prune \
        stop start ssh exec inspect list-volumes list-networks rere rebuild it backend dev monitoring \
        format lint test init-db backup-db health models cli-test brain

# ======================================================================================
# HELP & USAGE
# ======================================================================================

help:
	@echo -e "$(BLUE)========================================================================="
	@echo -e " 🧠 Second Brain Stack - Universal Docker Compose Makefile "
	@echo -e "=========================================================================$(NC)"
	@echo ""
	@echo -e "$(YELLOW)Usage: make [target] [service=SERVICE_NAME] [args=\"ARGS\"] [file=COMPOSE_FILE]$(NC)"
	@echo -e "  'service' specifies a single service for targets like logs, build, ssh, exec, inspect."
	@echo -e "  'args' specifies commands for 'exec'."
	@echo -e "  'file' specifies an alternative docker-compose file (default: docker-compose.yml)."
	@echo ""
	@echo -e "$(GREEN)🚀 Core Stack Management:$(NC)"
	@echo -e "  up                  - Start all services in detached mode (Alias: start)."
	@echo -e "  down                - Stop and remove all services and default network."
	@echo -e "  restart             - Restart all services (down + up)."
	@echo -e "  re                  - Rebuild images and restart all services (down + build + up)."
	@echo -e "  rere                - Rebuild images without cache and restart all services (down + no-cache + up)."
	@echo -e "  stop                - Stop all services without removing them."
	@echo ""
	@echo -e "$(GREEN)🔨 Building Images:$(NC)"
	@echo -e "  build [service=<name>] - Build images (all or specific service)."
	@echo -e "  no-cache [service=<name>] - Build images without cache (all or specific service)."
	@echo ""
	@echo -e "$(GREEN)📊 Information & Debugging:$(NC)"
	@echo -e "  status [service=<name>] - Show status of services (all or specific) (Alias: ps)."
	@echo -e "  logs [service=<name>]   - Follow logs (all or specific service)."
	@echo -e "  config              - Validate and display effective Docker Compose configuration."
	@echo -e "  ssh service=<name>    - Get an interactive shell into a running service (Alias: it)."
	@echo -e "  exec service=<name> args=\"<cmd>\" - Execute a command in a running service."
	@echo -e "  inspect service=<name> - Inspect a running service container."
	@echo -e "  list-volumes        - List Docker volumes (may include non-project volumes)."
	@echo -e "  list-networks       - List Docker networks (may include non-project networks)."
	@echo ""
	@echo -e "$(GREEN)🧪 Second Brain Specific:$(NC)"
	@echo -e "  brain               - Quick start the entire brain stack with health check."
	@echo -e "  test                - Run all tests in containers."
	@echo -e "  lint                - Run linting in containers."
	@echo -e "  format              - Format code in containers."
	@echo -e "  init-db             - Initialize database in container."
	@echo -e "  backup-db           - Backup database."
	@echo -e "  health              - Check service health endpoints."
	@echo -e "  models              - Download required ML models."
	@echo -e "  cli-test            - Test CLI interface in container."
	@echo ""
	@echo -e "$(GREEN)🧹 Cleaning & Pruning:$(NC)"
	@echo -e "  clean               - Remove stopped service containers and default network created by compose."
	@echo -e "  fclean              - Perform 'clean' and also remove volumes defined in compose file."
	@echo -e "  prune               - Prune unused Docker images, build cache, and dangling volumes (Docker system prune)."
	@echo ""
	@echo -e "$(YELLOW)Examples:$(NC)"
	@echo -e "  make brain                          # Start everything and check health"
	@echo -e "  make logs service=search            # Follow search service logs"
	@echo -e "  make ssh service=ingestion          # Shell into ingestion service"
	@echo -e "  make exec service=gateway args=\"ls -la\"  # Execute command in gateway"
	@echo -e "  make test                           # Run all tests"
	@echo -e "$(BLUE)========================================================================="
	@echo -e " 🧠 Help Section End "
	@echo -e "=========================================================================$(NC)"

# ======================================================================================
# CORE STACK MANAGEMENT
# ======================================================================================

brain: up health ## 🧠 Quick start the complete Second Brain stack
	@echo -e "$(GREEN)🧠 Second Brain Stack is now running!$(NC)"
	@echo -e "$(BLUE)📊 Dashboard: http://localhost:8000/dashboard$(NC)"
	@echo -e "$(BLUE)🔍 Search API: http://localhost:8002$(NC)"
	@echo -e "$(BLUE)💬 Chat API: http://localhost:8004$(NC)"

up: ## Start all services in detached mode
	@echo -e "$(GREEN)🚀 Igniting Second Brain services... All systems GO!$(NC)"
	@$(COMPOSE) up -d --remove-orphans
	@echo -e "$(GREEN)Services are now running in detached mode.$(NC)"

start: ## Alias for up
	@echo -e "$(GREEN)Starting services from $(COMPOSE_FILE)... All systems GO!$(NC)"
	@$(COMPOSE) up -d --remove-orphans $(service)

down: ## Stop and remove all services and networks defined in the compose file
	@echo -e "$(RED)🛑 Shutting down Second Brain services... Powering down.$(NC)"
	@$(COMPOSE) down --remove-orphans

stop: ## Stop all services without removing them
	@echo -e "$(YELLOW)⏸️ Halting operations for $(COMPOSE_FILE)... Services stopping.$(NC)"
	@$(COMPOSE) stop $(service)

restart: down up ## Restart all services

re: down build up ## Rebuild images and restart all services

rere: down no-cache up ## Rebuild images without cache and restart all services

rebuild: down clean build up ## Alias for re

# ======================================================================================
# BUILDING IMAGES
# ======================================================================================

build: ## Build (or rebuild) images for specified service, or all if none specified
	@echo -e "$(BLUE)🔨 Forging components... Building images for $(or $(service),all services) from $(COMPOSE_FILE).$(NC)"
	@$(COMPOSE) build $(service)

no-cache: ## Build images without using cache for specified service, or all
	@echo -e "$(YELLOW)🔥 Force-forging (no cache)... Building for $(or $(service),all services) from $(COMPOSE_FILE).$(NC)"
	@$(COMPOSE) build --no-cache $(service)

# ======================================================================================
# INFORMATION & DEBUGGING
# ======================================================================================

status: ## Show status of running services
	@echo -e "$(BLUE)📊 System Status Report for $(COMPOSE_FILE):$(NC)"
	@$(COMPOSE) ps $(service)

ps: status ## Alias for status

logs: ## Follow logs for specified service, or all if none specified
	@echo -e "$(BLUE)📋 Tapping into data stream... Logs for $(or $(service),all services) from $(COMPOSE_FILE).$(NC)"
	@$(COMPOSE) logs -f --tail="100" $(service)

config: ## Validate and display effective Docker Compose configuration
	@echo -e "$(BLUE)📋 Blueprint Configuration for $(COMPOSE_FILE):$(NC)"
	@$(COMPOSE) config

ssh: ## Get an interactive shell into a running service container
	@if [ -z "$(service)" ]; then \
		echo -e "$(RED)❌ Error: Service name required. Usage: make ssh service=<service_name>$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(GREEN)🔌 Establishing DirectConnect to $(service) from $(COMPOSE_FILE)... Standby.$(NC)"
	@$(COMPOSE) exec $(service) /bin/sh || $(COMPOSE) exec $(service) /bin/bash || echo -e "$(RED)Failed to find /bin/sh or /bin/bash in $(service).$(NC)"

it: ssh ## Alias for ssh

exec: ## Execute a command in a running service container
	@if [ -z "$(service)" ] || [ -z "$(args)" ]; then \
		echo -e "$(RED)❌ Error: Service name and command required. Usage: make exec service=<service_name> args=\"<command>\"$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(GREEN)⚡ Executing remote directive in $(service) (from $(COMPOSE_FILE)): $(args)...$(NC)"
	@$(COMPOSE) exec $(service) $(args)

inspect: ## Inspect a running service container
	@if [ -z "$(service)" ]; then \
		echo -e "$(RED)❌ Error: Service name required. Usage: make inspect service=<service_name>$(NC)"; \
		exit 1; \
	fi
	@echo -e "$(BLUE)🔍 Performing deep scan of $(service) (from $(COMPOSE_FILE)) internals...$(NC)"
	@_container_id=$$($(COMPOSE) ps -q $(service) | head -n 1); \
	if [ -z "$$_container_id" ]; then \
		echo -e "$(RED)Service $(service) not found or not running.$(NC)"; \
		exit 1; \
	fi; \
	docker inspect $$_container_id

list-volumes: ## List Docker volumes
	@echo -e "$(BLUE)💾 Global Docker Volumes:$(NC)"
	@docker volume ls
	@echo -e "$(YELLOW)Note: For project-specific volumes, Docker Compose adds labels based on project name.$(NC)"

list-networks: ## List Docker networks
	@echo -e "$(BLUE)🌐 Global Docker Networks:$(NC)"
	@docker network ls

# ======================================================================================
# SECOND BRAIN SPECIFIC OPERATIONS (CONTAINER-FIRST)
# ======================================================================================

test: ## Run all tests in containers
	@echo -e "$(GREEN)🧪 Running tests in containers...$(NC)"
	@$(COMPOSE) exec -T gateway python -m pytest /app/tests/ -v --cov=core --cov=services --cov-report=term-missing || \
		echo -e "$(YELLOW)⚠️  Gateway not running, building and running test container...$(NC)" && \
		$(COMPOSE) run --rm gateway python -m pytest /app/tests/ -v

test-fast: ## Run tests without coverage
	@echo -e "$(GREEN)🏃 Running fast tests in containers...$(NC)"
	@$(COMPOSE) exec -T gateway python -m pytest /app/tests/ -x || \
		$(COMPOSE) run --rm gateway python -m pytest /app/tests/ -x

lint: ## Run linting in containers
	@echo -e "$(GREEN)🔍 Running linters in containers...$(NC)"
	@$(COMPOSE) exec -T gateway python -m black --check /app/core/ /app/services/ /app/interfaces/ /app/connectors/ || \
		$(COMPOSE) run --rm gateway python -m black --check /app/core/ /app/services/ /app/interfaces/ /app/connectors/

format: ## Format code in containers  
	@echo -e "$(GREEN)✨ Formatting code in containers...$(NC)"
	@$(COMPOSE) exec -T gateway python -m black /app/core/ /app/services/ /app/interfaces/ /app/connectors/ || \
		$(COMPOSE) run --rm gateway python -m black /app/core/ /app/services/ /app/interfaces/ /app/connectors/

init-db: ## Initialize database in container
	@echo -e "$(GREEN)🗄️ Initializing database in container...$(NC)"
	@$(COMPOSE) exec -T gateway python -c "import asyncio; from core.database import DatabaseManager; asyncio.run((lambda: DatabaseManager().create_tables())()); print('✅ Database initialized successfully')" || \
		$(COMPOSE) run --rm gateway python -c "import asyncio; from core.database import DatabaseManager; asyncio.run((lambda: DatabaseManager().create_tables())()); print('✅ Database initialized successfully')"

backup-db: ## Backup database
	@echo -e "$(GREEN)💾 Backing up database...$(NC)"
	@mkdir -p storage/backups
	@cp storage/brain.db storage/backups/brain-backup-$$(date +%Y%m%d-%H%M%S).db 2>/dev/null || echo "No database file found yet"
	@echo -e "$(GREEN)✅ Database backup complete$(NC)"

health: ## Check service health endpoints
	@echo -e "$(GREEN)🏥 Checking service health...$(NC)"
	@sleep 2
	@echo -n "Gateway: "; curl -s http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo "DOWN"
	@echo -n "Ingestion: "; curl -s http://localhost:8001/health | jq -r '.status' 2>/dev/null || echo "DOWN"
	@echo -n "Search: "; curl -s http://localhost:8002/health | jq -r '.status' 2>/dev/null || echo "DOWN" 
	@echo -n "Knowledge: "; curl -s http://localhost:8003/health | jq -r '.status' 2>/dev/null || echo "DOWN"
	@echo -n "Chat: "; curl -s http://localhost:8004/health | jq -r '.status' 2>/dev/null || echo "DOWN"

test-stack: ## Test the complete stack functionality using curl
	@echo -e "$(GREEN)🧠 Testing Second Brain Stack...$(NC)"
	@echo "Testing ingestion..."
	@curl -s -X POST http://localhost:8001/ingest -H "Content-Type: application/json" -d '{"content":"Test content","source_type":"test","source_path":"test.txt"}' | jq .
	@echo "Testing search..."
	@curl -s -X POST http://localhost:8002/search -H "Content-Type: application/json" -d '{"query":"test"}' | jq .
	@echo "Testing chat..."
	@curl -s -X POST http://localhost:8004/message -H "Content-Type: application/json" -d '{"content":"Hello"}' | jq .

smoke: ## Run quick smoke test
	@echo -e "$(YELLOW)🔥 Running smoke test...$(NC)"
	@curl -s http://localhost:8000/health || echo "Gateway not responding"

cli: ## Start a simple CLI interface for testing
	@echo -e "$(GREEN)🧠 Second Brain CLI Interface$(NC)"
	@echo "Available endpoints:"
	@echo "  Gateway: http://localhost:8000"
	@echo "  Ingestion: http://localhost:8001" 
	@echo "  Search: http://localhost:8002"
	@echo "  Knowledge: http://localhost:8003"
	@echo "  Chat: http://localhost:8004"
	@echo ""
	@echo "Example commands:"
	@echo "  curl -X POST http://localhost:8001/ingest -H 'Content-Type: application/json' -d '{\"content\":\"Hello World\",\"source_type\":\"test\",\"source_path\":\"test.txt\"}'"
	@echo "  curl -X POST http://localhost:8002/search -H 'Content-Type: application/json' -d '{\"query\":\"hello\"}'"
	@echo "  curl -X POST http://localhost:8004/message -H 'Content-Type: application/json' -d '{\"content\":\"What do you know?\"}'"

models: ## Download required ML models in container
	@echo -e "$(GREEN)🤖 Downloading ML models in container...$(NC)"
	@$(COMPOSE) exec -T gateway python -c "import spacy; print('✅ spaCy model check complete')" || \
		$(COMPOSE) run --rm gateway python -c "import spacy; print('✅ spaCy model check complete')"

cli-test: ## Test CLI interface in container
	@echo -e "$(GREEN)💻 Testing CLI interface in container...$(NC)"
	@$(COMPOSE) exec -T gateway python -m interfaces.cli --help || \
		$(COMPOSE) run --rm gateway python -m interfaces.cli --help

stats: ## Show database statistics  
	@echo -e "$(GREEN)📊 Getting database statistics...$(NC)"
	@$(COMPOSE) exec -T gateway python -c "import asyncio; from core.database import DatabaseManager; print('📊 Database connection test successful')" || \
		echo -e "$(YELLOW)⚠️  Run 'make up' first to start services$(NC)"

# ======================================================================================
# CLEANING & PRUNING
# ======================================================================================

clean: ## Remove stopped service containers and default network
	@echo -e "$(RED)🧹 Cleaning containers and networks from $(COMPOSE_FILE)...$(NC)"
	@$(COMPOSE) down --remove-orphans 

fclean: ## Remove containers, networks, volumes defined in compose file
	@echo -e "$(RED)🔥 Deep cleaning containers, networks, and volumes from $(COMPOSE_FILE)...$(NC)"
	@$(COMPOSE) down --volumes --remove-orphans --rmi 'all'

prune: fclean ## Prune all unused Docker resources
	@echo -e "$(RED)💥 Pruning all unused Docker resources...$(NC)"
	@docker system prune -af --volumes
	@docker builder prune -af
	@docker volume prune -af 
	@echo -e "$(GREEN)✅ Docker system prune complete.$(NC)"

# ======================================================================================
# APPLICATION SPECIFIC TARGETS
# ======================================================================================

app: brain ## Start the complete Second Brain application stack

dev: up ## Start development environment  
	@echo -e "$(GREEN)🚀 Development environment ready!$(NC)"
	@make health

monitoring: ## Start monitoring stack (if available)
	@echo -e "$(YELLOW)📊 Monitoring stack not yet implemented$(NC)"

backend: ## Start only backend services
	@echo -e "$(GREEN)🔧 Starting backend services...$(NC)"
	@$(COMPOSE) up -d gateway ingestion search knowledge chat
	@make health

# ======================================================================================
# VARIABLE HANDLING
# ======================================================================================
ifeq ($(file),)
    # file is not set, use default COMPOSE_FILE
else
    COMPOSE_FILE := $(file)
    COMPOSE := docker compose -f $(COMPOSE_FILE)
endif