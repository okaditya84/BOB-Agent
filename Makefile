# BOBAI — orchestration shortcuts. Backend services run in the root compose;
# the branded LibreChat stack runs from platform/librechat (its own compose).

.PHONY: up down ps logs test backend-up librechat-up

up: backend-up librechat-up ## Start the entire BOBAI stack
	@echo "BOBAI is up:  UI http://localhost:3080  ·  Risk dashboard http://localhost:8001/dashboard"

backend-up: ## Start backend services (identity-trust, kyc, assistant, mcp)
	docker-compose up -d --build

librechat-up: ## Start the branded LibreChat stack
	cd platform/librechat && UID=$$(id -u) GID=$$(id -g) docker-compose up -d

down: ## Stop everything
	-cd platform/librechat && docker-compose down
	-docker-compose down

ps: ## Show all running containers
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

logs: ## Tail backend logs
	docker-compose logs -f

test: ## Run all service test suites
	cd services/identity-trust && uv run pytest -q
	cd services/kyc && uv run pytest -q
	cd services/assistant && uv run pytest -q
