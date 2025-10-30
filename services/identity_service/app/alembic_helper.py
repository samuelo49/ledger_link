from loguru import logger
from alembic import command
from alembic.config import Config
import os


async def run_alembic_migrations(database_dsn: str) -> None:
    """
    Runs Alembic migrations programmatically using the configured DSN.
    This ensures migrations are automatically applied during service startup.
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Points to: services/identity_service/app/db/migrations/alembic.ini
        alembic_ini_path = os.path.join(base_dir, "db", "migrations", "alembic.ini")

        # Make sure Alembic config exists
        if not os.path.exists(alembic_ini_path):
            logger.warning(f"Alembic config not found at {alembic_ini_path}, skipping migrations.")
            return

        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("sqlalchemy.url", database_dsn)

        logger.info("🚀 Running Alembic migrations...")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Alembic migrations applied successfully.")
    except Exception as e:
        logger.error(f"❌ Alembic migration failed: {e}")
        raise