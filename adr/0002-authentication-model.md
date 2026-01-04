# 0002. Authentication and Authorization Model

- Status: Proposed
- Date: 2025-10-28
- Owners: Practice Stack Engineering

## Context

The platform must support customer, merchant, and admin personas with secure API access through the gateway. Requirements include OAuth2 login, short-lived access tokens, refresh token rotation, service-to-service authentication, and future integration with partner-issued API keys.

## Decision

Implement an OAuth2 password grant for initial bootstrap, issuing signed JWT access and refresh tokens from the identity service. Access tokens last 15 minutes; refresh tokens expire after 24 hours. Tokens are signed with HS256 using a rotatable shared secret (later upgradable to asymmetric keys). The gateway validates access tokens for external traffic and mints short-lived service tokens for internal requests. Role-based access control (RBAC) is encoded in JWT scopes.

## Consequences

- Positive: Simple developer experience, aligns with FastAPI tooling, and enables incremental enhancement toward OIDC.
- Positive: Supports per-request authorization decisions at the gateway and downstream services using claims.
- Negative: Shared secret management introduces coordination overhead; migrating to asymmetric keys will require JWKS exposure and key rotation strategy.
- Negative: Password grant assumes first-party clients; third-party partner onboarding will need additional flows (client credentials/API keys).

## Alternatives Considered

- **OIDC Authorization Code with PKCE** – More secure for public clients but adds time overhead; still a planned enhancement.
- **Session cookies + stateful auth** – Easier revocation but complicates API consumption by server-to-server clients.

## References

- services/identity_service/app/routes/auth.py
- services/api_gateway/app/middleware.py
