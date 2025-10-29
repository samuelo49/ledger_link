# Authentication Incident Runbook

## Trigger
- Multiple 401/403 errors from partner traffic.
- Auth latency above SLO or token issuance failures.

## Immediate Actions
1. Check API gateway metrics (`/metrics`) for rate-limit spikes and JWT validation errors.
2. Inspect identity service logs (`docker compose logs identity-service`) for DB or Redis connectivity issues.
3. Validate Postgres health (`docker compose exec identity-db pg_isready`).
4. Review Redis latency and key eviction stats.

## Mitigation
- If rate limiting is throttling legitimate traffic, temporarily raise thresholds via environment variables and redeploy.
- Flush compromised refresh tokens by rotating `IDENTITY_SECRET_KEY` and invalidating sessions.
- Fail over to cached JWKS if the identity service is unreachable.

## Follow-Up
- Create incident timeline, root cause analysis, and prevention tasks.
- Update ADRs if architecture adjustments are required.
