# Identity Service — Endpoint Reference

Base path: `/api/v1`

Diagram: [identity-service-flows.svg](./identity-service-flows.svg)

## Health

GET `/api/v1/healthz`

- Request: none
- Response 200:
```json
{ "status": "ok", "service": "identity-service" }
```

---

## Register

POST `/api/v1/auth/register`

- Request body (LoginRequest):
```json
{
  "email": "user@example.com",
  "password": "StrongPassword123!"
}
```
- Responses:
  - 201 (UserResponse)
```json
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
  - 409
```json
{ "detail": "User already exists" }
```

---

## Login / Token

POST `/api/v1/auth/token`

- Request body (LoginRequest):
```json
{
  "email": "user@example.com",
  "password": "StrongPassword123!"
}
```
- Response 200 (Token):
```json
{
  "access_token": "<JWT>",
  "refresh_token": "<JWT>",
  "token_type": "bearer",
  "expires_in": 900
}
```
- Errors:
  - 401
```json
{ "detail": "Invalid credentials" }
```
  - 403 (policy blocks)
```json
{ "detail": "Account locked. Try again later." }
```
```json
{ "detail": "User account is inactive" }
```
```json
{ "detail": "Email not verified" }
```

Notes:
- `access_token` audience = `fintech-platform`, issuer = identity service.
- `expires_in` is seconds until access token expiry (default 15 minutes).

---

## Refresh Token

POST `/api/v1/auth/refresh`

- Request body (RefreshRequest):
```json
{
  "refresh_token": "<JWT>"
}
```
- Response 200 (Token):
```json
{
  "access_token": "<JWT>",
  "refresh_token": "<JWT>",
  "token_type": "bearer",
  "expires_in": 900
}
```
- Errors:
  - 401 (invalid/expired token, wrong audience/issuer, or malformed)
```json
{ "detail": "Invalid refresh token" }
```
  - 401 (wrong scope)
```json
{ "detail": "Invalid token scope" }
```

---

## Me (current user)

GET `/api/v1/auth/me`

- Headers:
  - Authorization: Bearer <access_jwt>
- Response 200 (UserResponse): same shape as Register.
- Errors: 401 for missing/invalid token or inactive user; 401 for wrong scope.

---

## Email Verification

POST `/api/v1/auth/verification/request`

- Body:
```json
{ "email": "user@example.com" }
```
- Response 202:
```json
{ "verification_token": "<token>" }
```

POST `/api/v1/auth/verification/confirm`

- Body:
```json
{ "token": "<token>" }
```
- Response 200 (UserResponse): user is_verified becomes true; verified_at set.
- Errors: 400 invalid token.

---

## Password Reset

POST `/api/v1/auth/password-reset/request`

- Body:
```json
{ "email": "user@example.com" }
```
- Response 202:
```json
{ "password_reset_token": "<token>" }
```

POST `/api/v1/auth/password-reset/confirm`

- Body:
```json
{ "token": "<token>", "new_password": "StrongerPass123!" }
```
- Response 204: password updated; lockout counters cleared.
- Errors: 400 invalid token.

---

## JWT Claims (for reference)

Issued by `core/security.create_token` (HS256):
```json
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

Downstream services validate the Access JWT and authorize via claims (e.g., roles, is_superuser) without calling identity on each request.

---

## Login Policy

Settings (see `services/identity_service/app/settings.py`):

- max_failed_login_attempts: default 5
- lockout_minutes: default 15
- require_verified_for_login: default false

Behavior:
- Each bad password attempt increments a counter; on reaching the threshold the account is locked for the lockout window.
- On successful login, counters reset and `last_login_at` is updated.
- If `require_verified_for_login` is true, unverified users get 403.
