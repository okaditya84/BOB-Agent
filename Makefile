# BOBAI — orchestration shortcuts. Backend services run in the root compose;
# the branded LibreChat stack runs from platform/librechat (its own compose).

.PHONY: up down ps logs test backend-up librechat-up

up: backend-up librechat-up ## Start the entire BOBAI stack
	@echo "BOBAI is up:  UI http://localhost:3080  ·  Risk dashboard http://localhost:8001/dashboard"

backend-up: ## Start backend services (identity-trust, kyc, assistant, mcp)
	docker-compose up -d --build

librechat-build: ## Build the BOB-orange branded LibreChat image from source (slow, ~15 min)
	cd platform/librechat && docker build --build-arg NODE_MAX_OLD_SPACE_SIZE=4096 -t bobai/librechat:branded .

librechat-up: ## Start the branded LibreChat stack (builds the branded image if missing)
	@docker image inspect bobai/librechat:branded >/dev/null 2>&1 || $(MAKE) librechat-build
	# `env` is used because UID/GID are read-only shell variables on macOS;
	# a plain `UID=... docker-compose` assignment errors under /bin/sh.
	cd platform/librechat && env UID=$$(id -u) GID=$$(id -g) docker-compose up -d

down: ## Stop everything
	-cd platform/librechat && docker-compose down
	-docker-compose down

ps: ## Show all running containers
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

logs: ## Tail backend logs
	docker-compose logs -f

seed: ## Populate the risk engine with a realistic demo scenario set
	python3 scripts/seed_demo.py

test: ## Run all service test suites
	cd services/identity-trust && uv run pytest -q
	cd services/kyc && uv run pytest -q
	cd services/assistant && uv run pytest -q
	cd services/mcp && uv run pytest -q
