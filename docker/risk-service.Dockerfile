FROM python:3.11-slim AS base

WORKDIR /app

# 🧩 Copy the root workspace metadata — needed for uv to resolve packages
COPY pyproject.toml uv.lock ./

# 🧩 Copy subproject manifests (so uv knows about them)
COPY services/risk_service/pyproject.toml services/risk_service/pyproject.toml
COPY libs/shared/pyproject.toml libs/shared/pyproject.toml

# 🧩 Install uv and sync this service and its shared dependency
RUN pip install --no-cache-dir uv \
    && uv sync --no-editable --compile-bytecode

# 🧩 Copy actual source code after syncing dependencies (to leverage Docker caching)
COPY services/risk_service /app/services/risk_service
COPY libs/shared /app/libs/shared

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "services.risk_service.app:app", "--host", "0.0.0.0", "--port", "8000"]