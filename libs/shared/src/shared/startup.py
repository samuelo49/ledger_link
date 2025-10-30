import asyncio
import logging
import asyncpg
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import command
from alembic.config import Config

logger = logging.getLogger("startup")
logging.basicConfig(level=logging.INFO)

async def wait_for_db(dsn: str, retries: int = 10, delay: int = 3):
    """Wait until the database is available before starting the service."""
    for attempt in range(retries):
        try:
            conn = await asyncpg.connect(dsn)
            await conn.close()
            logger.info("✅ Database is ready")
            return
        except Exception as e:
            logger.warning(f"DB not ready yet ({attempt + 1}/{retries}): {e}")
            await asyncio.sleep(delay)
    raise RuntimeError("❌ Database connection failed after retries")

def run_migrations(engine: AsyncEngine, migrations_path: str = "alembic.ini"):
    """Run Alembic migrations for the given service."""
    try:
        logger.info("🚀 Running Alembic migrations...")
        alembic_cfg = Config(migrations_path)
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Database migrations complete")
    except Exception as e:
        logger.error(f"Migration error: {e}")
        raise

async def startup_sequence(dsn: str, engine: AsyncEngine | None = None):
    """Run the common startup sequence for services."""
    await wait_for_db(dsn)
    if engine:
        run_migrations(engine)
    logger.info("✨ Service startup completed successfully")