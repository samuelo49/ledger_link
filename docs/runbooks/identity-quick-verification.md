# Identity Service — Quick Verification

This short runbook helps you confirm the Identity Service is healthy, migrations are applied, and core flows work locally.

## 1) Start the stack

- Ensure Docker Desktop is running.
- From the repo root, start the services (gateway, identity, db, etc.).

Example:

```
make up
```

Wait until `identity-service` logs show: "Alembic migrations completed successfully" and "Default admin seeding completed".

## 2) Check health

Use your browser or any HTTP client:

- http://localhost:8001/api/v1/healthz (service direct)
- http://localhost:8080/api/v1/healthz (via gateway)

You should see: `{ "status": "ok", "service": "identity-service" }` (direct) and gateway’s health response.

## 3) Verify database schema

Option A — via docker compose (container psql):

- Exec into the identity-db container and inspect the `users` table:

```
docker compose exec -T identity-db psql -U identity_user -d identity_db -c "\d+ users"
```

Option B — psql from host (Postgres exposed on 5433):

- Connect and inspect:

```
psql postgresql://identity_user:identity_password@localhost:5433/identity_db -c "\d+ users"
```

You should see columns like: email, hashed_password, is_active, is_verified, roles, created_at, updated_at, last_login_at, failed_login_attempts, locked_at, verification_token, verified_at, password_reset_token, password_reset_sent_at, deleted_at, profile.

## 4) Smoke test API flows

Use the provided Postman collections (recommended):

- Import:
  - `docs/postman/identity-service.postman_collection.json`
  - `docs/postman/identity-service.local.postman_environment.json` (direct) or `docs/postman/identity-gateway.local.postman_environment.json` (gateway)
- Run in order: Health → Register → Token → Refresh → Me
- Optional flows: Verification (request/confirm), Password Reset (request/confirm), Lockout Demo

CLI option (Newman): see `docs/postman/RUN-COLLECTION.md`.

## 5) Troubleshooting tips

- If migrations fail, check the sync DB URL in env (`IDENTITY_DATABASE_SYNC_URL` uses `postgresql+psycopg://...`).
- If service can’t reach DB, ensure Docker is up and `identity-db` is healthy (compose has a healthcheck).
- For token errors via gateway, verify the gateway routes are up and forwarding `/api/v1/auth/*` to identity.

## 6) Done

Once the above checks pass, Identity is healthy and ready to be used by other services.
