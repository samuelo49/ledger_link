from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import create_token, hash_password, verify_password
from ..dependencies import get_session
from ..models import User
from ..schemas import LoginRequest, RefreshRequest, Token, UserResponse
from ..settings import identity_settings

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> UserResponse:
    existing = await session.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/token", response_model=Token)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> Token:
    user = await session.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    settings = identity_settings()
    access_delta = timedelta(minutes=settings.access_token_expires_minutes)
    refresh_delta = timedelta(minutes=settings.refresh_token_expires_minutes)
    access_token = create_token(str(user.id), scope="access", expires_delta=access_delta, token_type="access")
    refresh_token = create_token(
        str(user.id),
        scope="refresh",
        expires_delta=refresh_delta,
        token_type="refresh",
    )
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_delta.total_seconds()),
    )


@router.post("/refresh", response_model=Token)
async def refresh(payload: RefreshRequest) -> Token:
    settings = identity_settings()
    try:
        decoded = jwt.decode(
            payload.refresh_token,
            settings.secret_key,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc
    if decoded.get("scope") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token scope")
    access_delta = timedelta(minutes=settings.access_token_expires_minutes)
    refresh_delta = timedelta(minutes=settings.refresh_token_expires_minutes)
    user_id = decoded["sub"]
    access_token = create_token(user_id, scope="access", expires_delta=access_delta, token_type="access")
    refresh_token = create_token(
        user_id,
        scope="refresh",
        expires_delta=refresh_delta,
        token_type="refresh",
    )
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_delta.total_seconds()),
    )
