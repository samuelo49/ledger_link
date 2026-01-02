from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import RefreshToken


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def create_refresh_token_record(
    session: AsyncSession,
    *,
    token_id: UUID,
    user_id: int,
    refresh_token: str,
    expires_at: datetime,
) -> RefreshToken:
    record = RefreshToken(
        id=token_id,
        user_id=user_id,
        token_hash=hash_token(refresh_token),
        expires_at=expires_at,
    )
    session.add(record)
    await session.flush()
    return record


async def get_refresh_token(session: AsyncSession, token_id: UUID) -> RefreshToken | None:
    return await session.get(RefreshToken, token_id)


async def revoke_refresh_token(
    session: AsyncSession,
    token: RefreshToken,
    *,
    replaced_by: UUID | None = None,
) -> None:
    token.revoked_at = datetime.now(tz=timezone.utc)
    token.replaced_by_token_id = replaced_by
    session.add(token)
    await session.flush()
