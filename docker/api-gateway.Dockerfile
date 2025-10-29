FROM python:3.11-slim AS base

WORKDIR /app

# 🧩 Copy root workspace metadata so uv can resolve dependencies
COPY pyproject.toml uv.lock ./

# 🧩 Copy subproject manifests
COPY services/api_gateway/pyproject.toml services/api_gateway/pyproject.toml
COPY libs/shared/pyproject.toml libs/shared/pyproject.toml

# 🧩 Install uv and sync workspace packages for this service
RUN pip install --no-cache-dir uv \
    && uv sync --package api-gateway --package shared-lib --no-editable --compile-bytecode

# 🧩 Copy actual source code (after dependency sync for Docker caching)
COPY services/api_gateway /app/services/api_gateway
COPY libs/shared /app/libs/shared

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "services.api_gateway.app:app", "--host", "0.0.0.0", "--port", "8080"]