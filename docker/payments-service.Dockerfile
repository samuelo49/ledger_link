FROM python:3.11-slim AS base

WORKDIR /app

# 🧩 Copy root workspace metadata so uv can resolve dependencies
COPY pyproject.toml uv.lock ./

# 🧩 Copy subproject manifests
COPY services/payments_service/pyproject.toml services/payments_service/pyproject.toml
COPY libs/shared/pyproject.toml libs/shared/pyproject.toml

# 🧩 Install uv and sync workspace packages for this service
RUN pip install --no-cache-dir uv \
    && uv sync --no-editable --compile-bytecode

# 🧩 Copy actual source code (after dependency sync for Docker caching)
COPY services/payments_service /app/services/payments_service
COPY libs/shared /app/libs/shared

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "services.payments_service.app:app", "--host", "0.0.0.0", "--port", "8000"]
