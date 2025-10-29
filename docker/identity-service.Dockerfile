FROM python:3.11-slim AS base

WORKDIR /app

# 🧩 Copy root workspace metadata so uv can resolve dependencies
COPY pyproject.toml uv.lock ./

# 🧩 Copy subproject manifests
COPY services/identity_service/pyproject.toml services/identity_service/pyproject.toml
COPY libs/shared/pyproject.toml libs/shared/pyproject.toml

# 🧩 Install uv and sync workspace packages for this service
RUN pip install --no-cache-dir uv \
    && uv sync --package identity-service --package shared-lib --no-editable --compile-bytecode

# 🧩 Copy actual source code (after dependency sync for Docker caching)
COPY services/identity_service /app/services/identity_service
COPY libs/shared /app/libs/shared

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "services.identity_service.app:app", "--host", "0.0.0.0", "--port", "8000"]
