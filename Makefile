PYTHON ?= python3

.PHONY: bootstrap
bootstrap:
	@echo "Bootstrapping workspaces..."
	@$(PYTHON) -m venv .venv
	@. .venv/bin/activate && pip install --upgrade pip uv
	@. .venv/bin/activate && uv sync

.PHONY: up
up:
	docker compose up --build

# Build all service images (cached)
.PHONY: build
build:
	docker compose build

# Rebuild all service images without using cache
.PHONY: rebuild
rebuild:
	docker compose build --no-cache

# Force recreate containers after (cached) build
.PHONY: up-clean
up-clean: build
	docker compose up --force-recreate -d

# Force recreate with no cache build (full clean spin-up)
.PHONY: up-full
up-full: rebuild
	docker compose up --force-recreate -d

# Selective build of specified SERVICES (space separated), e.g.:
# make build-services SERVICES="identity-service wallet-service api-gateway"
.PHONY: build-services
build-services:
	@if [ -z "$(SERVICES)" ]; then echo "Set SERVICES to space-separated list of compose service names"; exit 1; fi; \
	docker compose build $(SERVICES)

# Restart specific services with new images (after build/build-services)
.PHONY: restart-services
restart-services:
	@if [ -z "$(SERVICES)" ]; then echo "Set SERVICES to space-separated list of compose service names"; exit 1; fi; \
	docker compose up -d --force-recreate $(SERVICES)

.PHONY: down
down:
	docker compose down --remove-orphans

.PHONY: lint
lint:
	uv run ruff check .

.PHONY: format
format:
	uv run ruff format .

.PHONY: test
test:
	uv run pytest -q

.PHONY: generate-openapi
generate-openapi:
	uv run python scripts/generate_openapi.py

# --- Local E2E via Gateway (Wallet) ---
.PHONY: health-gateway
health-gateway:
	@echo "Waiting for api-gateway health..."
	@i=1; \
	while [ $$i -le 120 ]; do \
	  if curl -sf http://localhost:8080/api/v1/healthz >/dev/null; then \
	    echo "Gateway is healthy"; break; \
	  fi; \
	  echo "Waiting for api-gateway... ($$i)"; \
	  sleep 2; \
	  i=$$((i+1)); \
	done; \
	curl -s http://localhost:8080/api/v1/healthz || (echo "Gateway did not become healthy" && docker compose logs api-gateway --no-color | tail -n 200 && exit 1)

.PHONY: wallet-gateway-newman
wallet-gateway-newman:
	@echo "Running Wallet flow via gateway with dockerized Newman"
	docker run --rm --network fintech -v $$(pwd):/etc/newman -w /etc/newman postman/newman:alpine \
	  run docs/postman/wallet-gateway.postman_collection.json \
	  -e docs/postman/identity-gateway.local.postman_environment.json \
	  --env-var baseUrl=http://api-gateway:8080/api/v1 \
	  --reporters cli,junit \
	  --reporter-junit-export newman-wallet-gateway.xml

.PHONY: wallet-gateway
wallet-gateway: up health-gateway wallet-gateway-newman
	@echo "Wallet gateway E2E complete. Report: newman-wallet-gateway.xml"
