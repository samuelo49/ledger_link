from loguru import logger
from alembic import command
from alembic.config import Config
import os


async def run_alembic_migrations(database_dsn: str) -> None:
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        alembic_ini_path = os.path.join(base_dir, "db", "migrations", "alembic.ini")
        if not os.path.exists(alembic_ini_path):
            logger.warning(f"Alembic config not found at {alembic_ini_path}, skipping migrations.")
            return
        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("sqlalchemy.url", database_dsn)
        logger.info("🚀 Running Alembic migrations (risk)...")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Alembic migrations applied successfully (risk).")
    except Exception as e:
        logger.error(f"❌ Alembic migration failed (risk): {e}")
        raise
