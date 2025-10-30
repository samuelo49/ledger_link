# Identity Service — Confluence-ready Overview

This page summarizes the Identity Service for documentation portals (e.g., Confluence). Copy/paste sections as needed.

## Purpose
- Source of truth for user identities and credentials
- Issues access and refresh JWTs with claims for downstream authorization
- Runs DB migrations and seeds a default admin on startup

## Architecture
- Client → API Gateway → Identity Service → Postgres
- OpenTelemetry traces to Jaeger
- Startup: DB readiness → Alembic migrations → Seed default admin → Instrumentation

Diagram (SVG): `docs/architecture/identity-service-flows.svg`

## Endpoints
Base path: `/api/v1`

### Health — GET /api/v1/healthz
- Request: none
- Response 200:
```
{ "status": "ok", "service": "identity-service" }
```

### Register — POST /api/v1/auth/register
- Request body:
```
{ "email": "user@example.com", "password": "StrongPassword123!" }
```
- Response 201:
```
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "is_verified": false,
  "roles": "customer",
  "created_at": "2025-10-30T12:34:56Z",
  "updated_at": "2025-10-30T12:34:56Z"
}
```
- Error 409:
```
{ "detail": "User already exists" }
```

### Token — POST /api/v1/auth/token
- Request body:
```
{ "email": "user@example.com", "password": "StrongPassword123!" }
```
- Response 200:
```
{ "access_token": "<JWT>", "refresh_token": "<JWT>", "token_type": "bearer", "expires_in": 900 }
```
- Error 401:
```
{ "detail": "Invalid credentials" }
```

- Policy 403s:
```
{ "detail": "Account locked. Try again later." }
{ "detail": "User account is inactive" }
{ "detail": "Email not verified" }
```

### Refresh — POST /api/v1/auth/refresh
- Request body:
```
{ "refresh_token": "<JWT>" }
```
- Response 200:
```
{ "access_token": "<JWT>", "refresh_token": "<JWT>", "token_type": "bearer", "expires_in": 900 }
```
- Errors 401:
```
{ "detail": "Invalid refresh token" }
{ "detail": "Invalid token scope" }
```

### Me — GET /api/v1/auth/me
- Headers: `Authorization: Bearer <access_jwt>`
- Response 200: UserResponse
- Errors: 401 invalid/missing token or wrong scope

### Verification
- Request token:
```
POST /api/v1/auth/verification/request
{ "email": "user@example.com" }
```
- Response 202:
```
{ "verification_token": "<token>" }
```
- Confirm:
```
POST /api/v1/auth/verification/confirm
{ "token": "<token>" }
```
- Response 200: UserResponse (is_verified true)

### Password Reset
- Request token:
```
POST /api/v1/auth/password-reset/request
{ "email": "user@example.com" }
```
- Response 202:
```
{ "password_reset_token": "<token>" }
```
- Confirm new password:
```
POST /api/v1/auth/password-reset/confirm
{ "token": "<token>", "new_password": "StrongerPass123!" }
```
- Response 204: password updated; lockout counters cleared

## JWT Claims
```
{
  "sub": "<user_id>",
  "scope": "access|refresh",
  "iss": "http://identity-service:8000",
  "aud": "fintech-platform",
  "iat": 1698662400,
  "exp": 1698663300,
  "typ": "access|refresh"
}
```

## Operational Notes
- Password hashing: bcrypt via Passlib
- DB: SQLAlchemy async runtime; Alembic (psycopg) for migrations
- Observability: OTLP exporter → Jaeger; structured logs via Loguru

## Login Policy
- `max_failed_login_attempts` (default 5): lock account after repeated failures
- `lockout_minutes` (default 15): temporary lock window
- `require_verified_for_login` (default false): enforce verification before login
- On successful login: reset counters; update `last_login_at`

## Next Steps
- Enforce is_active/is_verified checks on login
- Implement verification & reset flows
- MFA and lockout policy
- Add curl examples and Postman collection
