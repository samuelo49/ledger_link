# Day 1 Plan & Notes

## Objectives
- Finalize scaffolding for services, shared library, Docker Compose, and observability stack.
- Implement identity service foundations (models, auth endpoints, instrumentation).
- Stand up API gateway skeleton with rate limiting and health endpoint.
- Draft ADRs for architecture, authentication, and rate limiting.

## Tasks
- [x] Repository layout & tooling (`pyproject.toml`, Makefile, .gitignore, shared lib).
- [x] Docker Compose with Postgres per service, Redis, Prometheus, Jaeger.
- [x] API gateway FastAPI app with request ID + sliding window limiter.
- [x] Identity service FastAPI app with register/login/refresh endpoints.
- [ ] Configure Alembic migrations for identity service.
- [ ] Implement JWKS endpoint and service-to-service JWT issuance.
- [ ] Integrate Redis sessions and token revocation list.
- [ ] Add pytest fixtures for async Postgres/redis.

## Reading List
- OAuth2 vs OIDC in microservices.
- Postgres advisory locks and transaction isolation.
- Redis Streams consumer groups.

## Debrief
Capture wins, challenges, and follow-ups at end of day.
