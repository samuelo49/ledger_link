# LedgerLink

<div align="center">

LedgerLink is a modular, cloud‑native fintech backend built with FastAPI and PostgreSQL, with Redis included for local development (caching/streams integration planned) — designed to power secure payment flows, digital wallets, and risk analytics across distributed services.

<br/>

<!-- Badges: tech & tooling -->
<img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" />
<img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.x-009688?logo=fastapi&logoColor=white" />
<img alt="SQLAlchemy" src="https://img.shields.io/badge/SQLAlchemy-2.x-D71F00?logo=sqlalchemy&logoColor=white" />
<img alt="Alembic" src="https://img.shields.io/badge/Alembic-migrations-6C757D" />
<img alt="Pydantic" src="https://img.shields.io/badge/Pydantic-v2-027DFD?logo=pydantic&logoColor=white" />
<img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white" />
<img alt="Redis" src="https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white" />
<img alt="Docker" src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" />
<img alt="GitHub Actions" src="https://img.shields.io/badge/GitHub%20Actions-CI/CD-2088FF?logo=githubactions&logoColor=white" />
<img alt="OpenTelemetry" src="https://img.shields.io/badge/OpenTelemetry-tracing-683D87?logo=opentelemetry&logoColor=white" />
<img alt="Prometheus" src="https://img.shields.io/badge/Prometheus-metrics-E6522C?logo=prometheus&logoColor=white" />
<img alt="Grafana" src="https://img.shields.io/badge/Grafana-dashboards-F46800?logo=grafana&logoColor=white" />
<img alt="Jaeger" src="https://img.shields.io/badge/Jaeger-traces-ED772D?logo=jaeger&logoColor=white" />
<img alt="Postman" src="https://img.shields.io/badge/Postman-E2E%20tests-FF6C37?logo=postman&logoColor=white" />
<img alt="Marp" src="https://img.shields.io/badge/Marp-slides-28A9E0?logo=markdown&logoColor=white" />

<br/>

<b>Microservices • Async Python • JWT Auth • Observability‑first • CI‑backed E2E</b>

</div>

---

## ✅ Highlights & Progress
- Full FastAPI service suite (gateway, identity, wallet, payments, risk) with isolated Postgres schemas, Redis included in Compose (integration/streams planned), and OTEL instrumentation.
- Identity service upgraded to RS256 + JWKS with refresh rotation, logout revocation, and async pytest coverage.
- Wallet service delivers row-locked credit/debit flows with idempotency, Prometheus metrics, and JWT-validated ownership.
- Payments service orchestrates intents, risk decisions, and wallet debits with async test coverage.
- Payment intent confirmation saga enforces risk timeouts, wallet retry/backoff, explicit status transitions (pending/confirmed/declined/review), and idempotent downstream calls with pytest coverage.
- Risk service ships a rules engine, seedable ruleset, and REST evaluation endpoints consumed by payments and wallet domains.
- Shared library provides request-id middleware, JWKS client, schemas, and structured error handlers (gateway assigns/forwards `x-request-id`).
- GitHub Actions runs `make test` (uv + pytest) via `backend-tests` and runs Newman Postman jobs for Identity (direct + via gateway) and Wallet (via gateway).
- Dockerized Postman collections exist for identity, wallet, payments, and risk (CI currently runs identity + wallet).
- Observability parity: every service exposes `/api/v1/healthz` and `/api/v1/metrics`, with Grafana/Prometheus/Jaeger wired via Docker Compose.
- Developer docs: ADRs, architecture diagrams, Marp slides, and runbooks kept current with the above changes.

## 🧩 Core Domains
| Service | Description |
|----------|--------------|
| **API Gateway** | Ingress and routing layer handling proxy routing, rate limiting, and observability. |
| **Identity Service** | OAuth2/JWT authentication, RBAC, and session management. |
| **Wallet Service** | Double-entry ledger and wallet operations with transaction integrity. |
| **Payments Service** | Payment intent lifecycle and orchestration (webhooks planned). |
| **Risk Service** | Rules engine and risk scoring for fraud detection and compliance. |
| **Shared Library** | Common Pydantic schemas, middleware, and utilities across all services. |


---

## 🧰 Tech Stack (at a glance)

- Languages & Runtimes: Python 3.11+, asyncio
- Frameworks: FastAPI, Pydantic v2
- Data & Migrations: PostgreSQL 16, SQLAlchemy 2.x, Alembic
- Caching/Queue: Redis 7 (ElastiCache‑ready)
- Auth & Security: OAuth2/JWT (RS256 + JWKS via python‑jose), Passlib[bcrypt]
- Packaging & Build: Docker & Compose, Astral uv (uv.lock)
- CI/CD: GitHub Actions (pytest via `backend-tests`, Newman E2E, Marp slide export)
- Observability: OpenTelemetry, Prometheus, Grafana, Jaeger
- API & Testing: OpenAPI/Swagger, Postman/Newman, pytest
- Docs & DX: ADRs, diagrams (Excalidraw+SVG), slides (Marp), runbooks

Quick links:
- Architecture: `docs/architecture/`
- Postman collections: `docs/postman/`
- Wallet E2E via gateway (collection): `docs/postman/wallet-gateway.postman_collection.json`
- Slides: `docs/slides/`
- Runbooks: `docs/runbooks/`
- ADRs: `adr/`


---

## 🧱 Architecture Overview
- **Language:** Python (FastAPI)
- **Databases:** PostgreSQL per service (via AWS RDS)
- **Cache & Queue:** Redis (AWS ElastiCache)
- **Containerization:** Docker & Docker Compose
- **Deployment:** AWS ECS Fargate + ECR
- **Observability:** OpenTelemetry, Prometheus, Grafana, Jaeger, CloudWatch

Each domain runs independently and communicates through internal APIs, promoting scalability and fault isolation.

---

## 🚀 Local Development

```bash
# Bootstrap environment and dependencies
make bootstrap

# Start all services and dependencies
make up

# Run tests
make test

# Run wallet E2E flow via gateway (dockerized Newman)
make wallet-gateway
```

Access the API Gateway at: [http://localhost:8080/docs](http://localhost:8080/docs)

---

## 📊 Observability Stack
- **Prometheus** → Metrics collection  
- **Grafana** → Dashboards  
- **Jaeger** → Distributed tracing  
- **OpenTelemetry** → Service instrumentation  

---

## 🌩️ AWS Deployment (in progress)
- Each service containerized and deployed via **AWS ECS Fargate**
- Images hosted in **ECR**
- Databases in **RDS PostgreSQL**
- Redis via **ElastiCache**
- CI/CD pipeline via **GitHub Actions** → ECR → ECS

---

## 📘 Documentation
Detailed architecture notes, ADRs, and operational runbooks are available in the `/docs` directory.

---

> _LedgerLink showcases clean service boundaries, strong observability, and scalable backend engineering on AWS._

---

# LedgerLink Developer Notes

> Internal engineering notes and daily learnings — not for public release.

## 🧩 Current Focus
- [x] Identity v1 endpoints shipped (register, token/refresh, me, verification, password reset)
- [x] E2E coverage via Postman + CI for Identity (direct + gateway) and Wallet (via gateway)
- [x] uv-based pytest suites run in CI (backend-tests workflow) for identity, gateway, wallet, payments, and risk
- [x] Co-located Alembic migrations with startup upgrade + seeding
- [x] API Gateway proxies for identity extended flows (me/verification/reset)
- [x] Wallet service v1: models, migrations, endpoints (create/credit/debit/balance) with idempotency and row locking
- [x] Wallet auth at service boundary (JWT validate, owner derived from token)
- [x] Wallet Postman flow via gateway + CI job
- [x] Expose /api/v1/metrics on wallet service with Prometheus counters
- [x] Expose /api/v1/metrics on remaining services and wire Prometheus dashboards
- [x] Standardized request-id middleware and JSON error responses across gateway + all services

## 🧠 Lessons / Insights
- Alembic "config not found" was solved by co-locating `alembic.ini`, `env.py`, and `versions/` inside each service and doing programmatic upgrades on startup.
- Use `psycopg` for sync migrations and `asyncpg` for runtime SQLAlchemy; keep separate DSNs in settings.
- Make registration idempotent (treat 201/409 as pass) to stabilize E2E runs on replays.
- CI needed longer health checks and a stub `.env` to satisfy docker compose's `env_file`.
- Start migrations before seeding; seed admin idempotently to avoid duplicate insert races.
- Keep gateway minimal; only proxy what's necessary and push business logic to services.

## 📅 Daily / Weekly Logs
### Day 1
- Set up initial FastAPI skeletons for services.
- Created unified `docker-compose.yml`.

### Day 2
- Added Prometheus and Grafana setup.
- Fixed `uv sync` issue in Dockerfiles.

### Day 3
- Fixed Alembic "config not found" by co-locating migrations under `identity_service/app/db/migrations`.
- Wired programmatic `upgrade head` on startup and added idempotent admin seeding.

### Day 4
- Extended `User` model with audit/security/verification/reset fields.
- Wrote `0002` migration and verified forward/backward compatibility.

### Day 5
- API Gateway base:
  - Proxies for auth (register/token/refresh) with base URL setting
  - Health endpoint under /api/v1/healthz
  - Rate limiting and x-request-id middleware
- Authored base Postman collection and local environments (direct and gateway)

### Day 6
- Implemented `/auth/me`, verification request/confirm, and password reset request/confirm.
- Added login policy: failed-attempts, lockout, last_login_at tracking, optional verified requirement.

### Day 7
- Wrote architecture notes for identity, plus Excalidraw diagram and exported SVG.
- Drafted slide deck and a Confluence-ready doc.

### Day 8
- Added CI workflows: slide export and Postman E2E (direct base, gateway base, direct extended).
- Made registration idempotent for CI; increased compose wait times; ensured `.env` exists in CI.

### Day 9
- Bootstrapped Alembic scaffolds for wallet, payments, and risk services (+ startup hooks).
- Updated service settings and pyprojects; verified compose wiring.

### Day 10
- Extended API Gateway:
  - Added wallet and payments proxy routers; configured wallet_base_url and payments_base_url
  - Routed identity extended flows (me/verification/reset) through the gateway
  - Added module/function docstrings for clarity (internal code docs)
  - Payments service endpoints are implemented (payment intents + confirmation orchestration); gateway proxies are in place

### Day 11
- Implemented Wallet service v1:
  - SQLAlchemy models: Wallet, LedgerEntry; constraints, indexes, and (wallet_id, idempotency_key) uniqueness.
  - Alembic migration creating wallets and ledger_entries tables.
  - Endpoints: POST /wallets, POST /wallets/{id}/credit, POST /wallets/{id}/debit, GET /wallets/{id}/balance.
  - Transactional balance updates with SELECT … FOR UPDATE; idempotent mutations; 409 on insufficient funds.
  - Minimal auth at boundary: validate JWT (issuer/audience/scope) and derive owner from token subject.
- Added Prometheus metrics and /api/v1/metrics endpoint for wallet (credit/debit/idempotency/insufficient_funds counters).
- Authored Postman collection to run register → token → create wallet → credit → debit → balance via gateway.
- CI: Added a gateway Wallet job to run the new collection; added a Makefile target to run the flow locally with dockerized Newman.

### Day 12
- Built out the Risk service with async DB sessions, Alembic migrations, SQLAlchemy models for `risk_rules` and `risk_evaluations`, and seeded baseline rules on startup.
- Implemented a configurable rule engine (amount thresholds, country mismatch, country/email blocklists) plus REST endpoints under `/api/v1/risk` for evaluations, lookups, and Prometheus metrics.
- Payments confirmation now calls the risk engine before debiting wallets; declines/reviews abort confirmation with clear HTTP errors.
- Added optional wallet risk hooks (`WALLET_RISK_CHECKS_ENABLED`) to prepare future direct wallet flows to reuse the same risk service.

### Day 13
- Upgraded Identity tokens to RS256, added an auto-generated RSA key pair with JWKS exposure, and switched services to consume/validate tokens via cached JWKS instead of shared secrets.
- Implemented refresh-token rotation with a persistent `refresh_tokens` table plus logout-driven revocation to block replays.
- Added async pytest coverage to exercise registration/login, refresh rotation, logout, and JWKS responses against an in-memory database.
- CI: Added a dedicated `backend-tests` workflow that installs uv, syncs dev extras, and runs pytest suites (identity/gateway/wallet/payments/risk) to complement the Newman smoke tests.
- Shared library now provides request-id middleware and structured error handlers; gateway and every service emit consistent `{error, detail, request_id}` JSON responses while forwarding/assigning `x-request-id`.

### Day 14
- Hardened the payment confirm saga: risk calls include timeouts + idempotency keys, wallet debits use bounded retries/backoff, and `PaymentIntent` statuses now record `pending/confirmed/review/declined`.
- Added pytest coverage for risk declines/reviews/timeouts and wallet retry behavior with stubbed `httpx.AsyncClient`.

## 🧰 Future Improvements
- Sign JWTs with automated key rotation (multiple `kid` values) and publish a JWKS history.
- External email/SMS delivery for verification and password reset.
- Expand Grafana dashboards and OTEL metrics coverage now that all services expose `/api/v1/metrics`.
- Strengthen gateway rate limiting and improve request correlation (e.g., consistent `x-request-id` + trace/log linkage).
- Buildx layer caching and parallelized image builds to speed up CI.
- Expand pytest coverage across services with DB fixtures and async test harness.
