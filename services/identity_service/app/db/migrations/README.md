# Identity Service Migrations

This folder contains Alembic configuration colocated with the service so migrations can be run programmatically at startup.

Quick commands (from repo root):

```zsh
# Upgrade to latest (uses this folder's alembic.ini)
uv run alembic -c services/identity_service/app/db/migrations/alembic.ini upgrade head

# Generate a new revision from models (autogenerate)
uv run alembic -c services/identity_service/app/db/migrations/alembic.ini revision --autogenerate -m "add something"

# Downgrade one step
uv run alembic -c services/identity_service/app/db/migrations/alembic.ini downgrade -1
```

Notes:
- The startup code sets the database URL at runtime. For CLI usage, ensure `IDENTITY_DATABASE_SYNC_URL` is set or update `alembic.ini` temporarily.
- `env.py` uses `Base.metadata` for autogenerate.
