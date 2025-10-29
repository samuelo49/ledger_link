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
- [ ] Finalize JWT and refresh token flow in `identity_service`
- [ ] Add metrics endpoints to all services
- [ ] Configure ECS task definitions for deployment

## 🧠 Lessons / Insights
- Observability setup with OTEL + Jaeger needs explicit exporter config per container.
- Docker build caching improved by copying `uv.lock` before source code.
- ECS Fargate task definitions benefit from explicit CPU/memory reservations per service.

## 📅 Daily / Weekly Logs
### Day 1
- Set up initial FastAPI skeletons for services.
- Created unified `docker-compose.yml`.

### Day 2
- Added Prometheus and Grafana setup.
- Fixed `uv sync` issue in Dockerfiles.

...

## 🧰 Future Improvements
- Async background workers (Celery or FastAPI BackgroundTasks)
- Global error handler middleware
- Implement correlation IDs in logs