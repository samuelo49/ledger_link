# 0002. Authentication and Authorization Model

- Status: Accepted
- Date: 2026-01-02
- Owners: Practice Stack Engineering

## Context

The platform must support customer, merchant, and admin personas with secure API access through the gateway. Requirements include OAuth2 login, short-lived access tokens, refresh token rotation, service-to-service authentication, and future integration with partner-issued API keys.

## Decision

Implement an OAuth2 password grant for initial bootstrap, issuing signed JWT access and refresh tokens from the Identity service.

- Access tokens are short-lived (15 minutes) and carry a `scope` claim (e.g. `access`) for authorization decisions.
- Refresh tokens are longer-lived (24 hours) and are rotated on use. Refresh token records are persisted and can be revoked on logout to block replays.
- Tokens are signed with RS256. The Identity service publishes a JWKS endpoint so downstream services can fetch public keys by `kid` and verify tokens locally.

Enforcement model:
- Downstream domain services (e.g. wallet/payments) validate JWTs at the service boundary using cached JWKS.
- The API Gateway is intentionally thin: it proxies requests and forwards the bearer token to downstream services rather than acting as the single enforcement point.

Service-to-service authentication (minted service tokens) and partner API keys remain planned enhancements.

## Consequences

- Positive: No shared secret distribution across services; public-key verification via JWKS reduces coordination overhead.
- Positive: Services can verify tokens locally (no synchronous call to Identity per request), improving latency and resilience.
- Positive: Refresh rotation + revocation provides replay resistance for refresh tokens.
- Negative: Requires JWKS caching and a key rotation strategy (multiple `kid` values over time).
- Negative: Password grant assumes first-party clients; partner onboarding will need additional flows (client credentials/API keys).
- Negative: Refresh-token revocation does not revoke already-issued access tokens (access-token revocation would require an allow/deny list or very short expirations).

## Alternatives Considered

- **OIDC Authorization Code with PKCE** – More secure for public clients but adds time overhead; still a planned enhancement.
- **Session cookies + stateful auth** – Easier revocation but complicates API consumption by server-to-server clients.
- **HS256 shared secret** – Simpler initial setup but requires distributing/rotating a secret across services.

## References

- services/identity_service/app/routes/auth.py
- services/identity_service/app/core/security.py
- libs/shared/src/shared/jwks.py
- services/payments_service/app/dependencies.py
- services/wallet_service/app/dependencies.py
