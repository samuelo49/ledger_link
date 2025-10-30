# LedgerLink

LedgerLink is a modular, cloud-native fintech backend built with FastAPI, PostgreSQL, and Redis — designed to power secure payment flows, digital wallets, and risk analytics across distributed services.

---

## 🧩 Core Domains
| Service | Description |
|----------|--------------|
| **API Gateway** | Ingress and routing layer handling request aggregation, rate limiting, and observability. |
| **Identity Service** | OAuth2/JWT authentication, RBAC, and session management. |
| **Wallet Service** | Double-entry ledger and wallet operations with transaction integrity. |
| **Payments Service** | Payment intent lifecycle, orchestration, and webhook handling. |
| **Risk Service** | Rules engine and risk scoring for fraud detection and compliance. |
| **Shared Library** | Common Pydantic schemas, middleware, and utilities across all services. |

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
- [x] E2E coverage via Postman + CI (direct and gateway base, direct extended)
- [x] Co-located Alembic migrations with startup upgrade + seeding
- [ ] Add gateway proxies for extended flows (me/verification/reset) and add a gateway-extended CI job
- [ ] Start wallet service domain modeling and migrations
- [ ] Expose /metrics across services and wire Prometheus dashboards

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
- Added minimal API Gateway proxy for auth (register/token/refresh) with base URL setting.
- Authored base Postman collection and local environments (direct and gateway).

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

## 🧰 Future Improvements
- Add gateway proxies for extended identity flows and include a gateway-extended Postman job in CI.
- Refresh token rotation with replay detection; consider a token store for revocation.
- Sign JWTs with key rotation (kid headers) and add a JWKS endpoint.
- External email/SMS delivery for verification and password reset.
- Expose `/metrics` on all services; expand Grafana dashboards; OTEL metrics.
- Strengthen gateway rate limiting and add request-level correlation IDs.
- Buildx layer caching and parallelized image builds to speed up CI.
- Expand pytest coverage across services with DB fixtures and async test harness.