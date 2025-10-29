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
