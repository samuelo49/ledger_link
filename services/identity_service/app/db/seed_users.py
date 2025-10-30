import asyncio
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from ..core.security import pwd_context
from ..db.session import async_session_factory
from ..settings import identity_settings


def get_password_hash(password: str) -> str:
    """Generate a bcrypt hash using the shared security context."""
    return pwd_context.hash(password)


async def seed_default_admin():
    """
    Seed a default admin user if it does not already exist.
    This is safe to run multiple times (idempotent).
    """
    settings = identity_settings()
    admin_email = settings.default_admin_email
    admin_password = settings.default_admin_password
    is_superuser = settings.default_admin_is_superuser

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.email == admin_email))
        existing_user = result.scalars().first()

        if existing_user:
            logger.info(f"✅ Admin user already exists: {admin_email}")
            return

        new_admin = User(
            email=admin_email,
            hashed_password=get_password_hash(admin_password),
            is_active=True,
            is_superuser=is_superuser,
        )

        session.add(new_admin)
        await session.commit()
        logger.success(f"👤 Default admin created: {admin_email}")