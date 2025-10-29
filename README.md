# Fintech Platform Practice Stack

An accelerated three-day project to practice building and consuming production-grade backend APIs with FastAPI, Postgres, Redis, and observability tooling. The stack simulates a multi-service fintech payments platform with identity, wallet, payments, and risk domains routed via an API gateway.

## Goals
- Exercise senior-level backend skills: auth, rate limiting, distributed transactions, observability, and deployment practices.
- Use real Postgres databases per service, Redis for messaging, and containerized dependencies to mirror production workflows.
- Produce documentation (ADRs, runbooks, diagrams) alongside tests and automation to discuss confidently in interviews.

## High-Level Services
- `api_gateway`: ingress, routing, rate limiting, observability.
- `identity_service`: OAuth2/JWT, RBAC, session management.
- `wallet_service`: double-entry ledger, wallet operations.
- `payments_service`: payment intents, webhooks, orchestration.
- `risk_service`: rules engine, case management.
- `libs/shared`: shared Pydantic schemas, middleware, and utilities.

## Development Workflow
1. Ensure Docker and Docker Compose are available.
2. Copy `.env.example` to `.env` and adjust secrets.
3. Run `make bootstrap` to set up virtual environments and pre-commit hooks.
4. Start the stack with `make up`; access services via the gateway.
5. Use `make test` for the full test suite and `make lint` before commits.

Detailed milestones and learning notes live in `docs/` and ADRs in `adr/`.

## Next Steps
Day 1 focuses on scaffolding, ADRs, identity service foundations, and gateway rate limiting. Progress is tracked in `docs/daily-notes`.

# Fintech Platform Practice Stack

A multi-service FastAPI platform simulating a fintech payments ecosystem with production-ready architecture — complete with Postgres databases, Redis messaging, observability, and containerized workflows.  
This stack serves as both a **learning lab** and a **portfolio-grade project** for mastering backend system design, service orchestration, and deployment patterns.

---

## 🧩 Core Services
| Service | Purpose |
|----------|----------|
| **api_gateway** | Entry point for all requests — handles ingress, routing, rate limiting, and observability. |
| **identity_service** | OAuth2/JWT authentication, RBAC, session management, and user identity. |
| **wallet_service** | Double-entry ledger, wallet operations, and balance tracking. |
| **payments_service** | Payment intents, webhooks, orchestration, and transaction workflows. |
| **risk_service** | Rules engine, scoring, and case management for fraud and compliance. |
| **libs/shared** | Shared Pydantic schemas, middleware, and core utilities used across services. |

---

## 🏗️ Development Workflow

1. **Prerequisites**
   - Install **Docker** and **Docker Compose**.
   - Copy `.env.example` to `.env` and configure secrets.

2. **Bootstrap dependencies**
   ```bash
   make bootstrap
   ```
   This creates a `.venv`, installs dependencies using `uv`, and links all workspace packages.

3. **Start the platform**
   ```bash
   make up
   ```
   Launches all services (API gateway, databases, Redis, observability stack).

4. **Run tests and lint**
   ```bash
   make test
   make lint
   ```

---

## 🧠 Observability Stack
- **Prometheus** for metrics.
- **Grafana** for dashboards.
- **Jaeger** for distributed tracing.
- Built-in OpenTelemetry instrumentation for FastAPI services.

---

## 🧱 Architecture Highlights
- Fully containerized with Docker Compose.
- Workspace managed by **uv** and `setuptools`.
- Independent **service Dockerfiles** leveraging `uv.lock` for reproducible builds.
- PostgreSQL per service for realistic data isolation.
- Shared Redis instance for caching and inter-service communication.

---

## 📘 Documentation
- **ADRs** (Architecture Decision Records): `adr/`
- **Runbooks, diagrams, and notes**: `docs/`
- **Daily progress**: `docs/daily-notes/`

---

## 🚀 Next Steps
- Extend the **identity** and **wallet** services to perform real distributed transactions.
- Add async event processing or background jobs with Redis streams or Celery.
- Deploy to **Azure Container Apps** or **AWS ECS Fargate** for cloud deployment practice.

---

> 💡 _This project is designed for senior-level backend practice — showcasing architecture, observability, and maintainable service design._