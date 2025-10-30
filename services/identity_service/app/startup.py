from loguru import logger
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from fastapi import FastAPI
import asyncpg
import asyncio
import random

from .settings import identity_settings
from .alembic_helper import run_alembic_migrations
from .db.seed_users import seed_default_admin


def setup_logging() -> None:
    """Configure Loguru for consistent, structured service logs."""
    logger.remove()
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level=identity_settings().log_level.upper(),
        backtrace=False,
        diagnose=False,
        colorize=False,
        serialize=False,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
    )
    logger.info("🪵 Logging configured successfully.")


def setup_instrumentation(app: FastAPI) -> None:
    """Attach OpenTelemetry tracing to the FastAPI app. This function is idempotent."""
    if trace.get_tracer_provider() and not isinstance(trace.get_tracer_provider(), trace.NoOpTracerProvider):
        logger.info("📈 OpenTelemetry instrumentation already initialized. Skipping reconfiguration.")
        return

    settings = identity_settings()
    resource = Resource(attributes={SERVICE_NAME: settings.service_name})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=str(settings.otel_endpoint)))
    )
    trace.set_tracer_provider(tracer_provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
    app.state.tracer_provider = tracer_provider
    logger.info("📈 OpenTelemetry instrumentation configured.")


async def _check_database_ready(dsn: str, max_retries: int = 5, base_delay: int = 2) -> None:
    """Poll the database connection until ready with exponential backoff and jitter."""
    # Normalize SQLAlchemy async URL to asyncpg-compatible DSN
    if dsn.startswith("postgresql+asyncpg://"):
        dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("db.readiness_check"):
        for attempt in range(max_retries):
            try:
                conn = await asyncpg.connect(dsn=dsn)
                await conn.close()
                logger.info("✅ Database connection successful.")
                return
            except Exception as e:
                wait_time = base_delay * (2 ** attempt)
                jitter = random.uniform(0, 0.5)
                total_wait = wait_time + jitter
                logger.warning(f"Database not ready (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {total_wait:.2f}s...")
                await asyncio.sleep(total_wait)
        raise RuntimeError("❌ Database not ready after multiple attempts.")


async def init_service_startup(app: FastAPI) -> None:
    """Initialize service dependencies, database, migrations, and instrumentation."""
    app.state.is_ready = False
    settings = identity_settings()
    tracer = trace.get_tracer(__name__)
    logger.info(f"🚀 Initializing {settings.service_name} ({settings.environment})...")

    # Log configuration summary safely
    safe_info = settings.safe_dict()
    for key, value in safe_info.items():
        logger.info(f"    {key}: {value}")

    # Step 1: Check DB readiness
    with tracer.start_as_current_span("db.readiness_check"):
        await _check_database_ready(settings.async_db_url)

    # Step 2: Run Alembic migrations (sync engine)
    with tracer.start_as_current_span("db.run_migrations"):
        try:
            await run_alembic_migrations(settings.sync_db_url)
            logger.info("🗂️ Alembic migrations completed successfully.")
        except Exception as e:
            if "Target database is already up to date" in str(e):
                logger.info("Alembic migrations: Target database is already up to date. Continuing.")
            else:
                logger.error(f"❌ Alembic migrations failed: {e}")
                raise

    # Step 2b: Seed default admin (idempotent) after schema is applied
    with tracer.start_as_current_span("db.seed_default_admin"):
        try:
            await seed_default_admin()
            logger.info("🌱 Default admin seeding completed (idempotent).")
        except Exception as e:
            logger.warning(f"⚠️ Admin seeding skipped due to error: {e}")

    # Step 3: Setup instrumentation after DB is ready
    with tracer.start_as_current_span("instrumentation.setup"):
        setup_instrumentation(app)

    app.state.is_ready = True
    logger.info(f"✅ {settings.service_name} startup completed successfully.")


async def shutdown_instrumentation(app: FastAPI) -> None:
    """Gracefully shutdown OpenTelemetry span processors."""
    tracer_provider = getattr(app.state, "tracer_provider", None)
    if tracer_provider:
        for processor in getattr(tracer_provider, "_active_span_processors", []):
            try:
                await processor.shutdown()
            except Exception as e:
                logger.warning(f"⚠️ Error shutting down span processor: {e}")
        logger.info("🧹 OpenTelemetry instrumentation shut down gracefully.")