"""Prometheus metrics for the Risk service."""

from __future__ import annotations

from prometheus_client import Counter

risk_service_startup_total = Counter(
    "risk_service_startup_total",
    "Number of times the risk service lifespan has executed",
)

risk_service_migration_total = Counter(
    "risk_service_migration_total",
    "Outcome of Alembic migration attempts",
    ["outcome"],
)

risk_health_checks_total = Counter(
    "risk_service_health_checks_total",
    "Health checks served by the risk service",
)
