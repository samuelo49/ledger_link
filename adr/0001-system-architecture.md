# 0001. System Architecture Overview

- Status: Accepted
- Date: 2025-10-28
- Owners: Practice Stack Engineering

## Context

The goal is to simulate a production-grade fintech backend that exercises identity, wallet, payments, and risk workflows within a constrained three-day window. We require clear separation of concerns, realistic infrastructure (Postgres per service, Redis, observability), and incremental extensibility for future services (KYC, FX, notifications).

## Decision

Adopt a mono-repo hosting multiple FastAPI microservices with independent Postgres schemas and Docker Compose orchestration. Each service owns its data store, exposes an internal REST API, and communicates asynchronously through Redis Streams. An API gateway fronts all external traffic, performs authn/z, rate limiting, and observability enrichment. Shared code (schemas, middleware) lives in a dedicated `libs/shared` package.

## Consequences

- Positive: Mirrors production microservice patterns, enforces clear domain boundaries, facilitates independent deployment, and supports per-service scaling strategies.
- Positive: Docker Compose keeps the environment reproducible while leaving room to export manifests to Kubernetes later.
- Negative: Increased local resource usage (multiple Postgres instances) and additional coordination overhead between services during development.
- Negative: Requires robust tooling (workspace dependency management, migrations) to maintain developer velocity.

## Alternatives Considered

- **Single FastAPI monolith with domain modules** – Faster to ship, simpler local setup, but offers less practice with cross-service contracts and operational concerns.
- **Serverless-style architecture** – Interesting for pay-per-use design but diverges from the hands-on production service management desired for interview prep.

## References

- docs/architecture/high-level-diagram.md
- docker-compose.yml
