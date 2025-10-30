from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, status, Request
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import create_token, hash_password, verify_password
from ..dependencies import get_session
from ..models import User
from ..schemas import (
    LoginRequest,
    RefreshRequest,
    Token,
    UserResponse,
    VerificationRequest,
    VerificationConfirmRequest,
    VerificationTokenResponse,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    PasswordResetTokenResponse,
)
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
    settings = identity_settings()
    user = await session.scalar(select(User).where(User.email == payload.email))

    # Handle invalid credentials with minimal enumeration risk
    if not user or not verify_password(payload.password, user.hashed_password):
        # Increment failed attempts for existing user and lock if threshold exceeded
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= settings.max_failed_login_attempts and not user.locked_at:
                user.locked_at = datetime.now(tz=timezone.utc)
            session.add(user)
            await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Check lockout window
    if user.locked_at:
        lockout_until = user.locked_at + timedelta(minutes=settings.lockout_minutes)
        if datetime.now(tz=timezone.utc) < lockout_until:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account locked. Try again later.")
        # Lockout expired: reset
        user.locked_at = None
        user.failed_login_attempts = 0

    # Additional account checks
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")
    if settings.require_verified_for_login and not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    # Successful login: issue tokens and update audit fields
    access_delta = timedelta(minutes=settings.access_token_expires_minutes)
    refresh_delta = timedelta(minutes=settings.refresh_token_expires_minutes)
    access_token = create_token(str(user.id), scope="access", expires_delta=access_delta, token_type="access")
    refresh_token = create_token(
        str(user.id),
        scope="refresh",
        expires_delta=refresh_delta,
        token_type="refresh",
    )

    user.last_login_at = datetime.now(tz=timezone.utc)
    user.failed_login_attempts = 0
    user.locked_at = None
    session.add(user)
    await session.commit()

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


@router.get("/me", response_model=UserResponse)
async def me(request: Request, session: AsyncSession = Depends(get_session)) -> UserResponse:
    settings = identity_settings()
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    try:
        decoded = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    if decoded.get("scope") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token scope")
    user_id = decoded.get("sub")
    user = await session.get(User, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return UserResponse.model_validate(user)


@router.post("/verification/request", response_model=VerificationTokenResponse, status_code=status.HTTP_202_ACCEPTED)
async def verification_request(payload: VerificationRequest, session: AsyncSession = Depends(get_session)) -> VerificationTokenResponse:
    # For privacy, do not reveal whether email exists; if not found, mint a dummy token
    user = await session.scalar(select(User).where(User.email == payload.email))
    token = secrets.token_urlsafe(32)
    if user:
        user.verification_token = token
        session.add(user)
        await session.commit()
    return VerificationTokenResponse(verification_token=token)


@router.post("/verification/confirm", response_model=UserResponse)
async def verification_confirm(payload: VerificationConfirmRequest, session: AsyncSession = Depends(get_session)) -> UserResponse:
    user = await session.scalar(select(User).where(User.verification_token == payload.token))
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")
    user.is_verified = True
    user.verified_at = datetime.now(tz=timezone.utc)
    user.verification_token = None
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/password-reset/request", response_model=PasswordResetTokenResponse, status_code=status.HTTP_202_ACCEPTED)
async def password_reset_request(payload: PasswordResetRequest, session: AsyncSession = Depends(get_session)) -> PasswordResetTokenResponse:
    user = await session.scalar(select(User).where(User.email == payload.email))
    token = secrets.token_urlsafe(32)
    if user:
        user.password_reset_token = token
        user.password_reset_sent_at = datetime.now(tz=timezone.utc)
        session.add(user)
        await session.commit()
    return PasswordResetTokenResponse(password_reset_token=token)


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def password_reset_confirm(payload: PasswordResetConfirmRequest, session: AsyncSession = Depends(get_session)) -> None:
    user = await session.scalar(select(User).where(User.password_reset_token == payload.token))
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password reset token")
    user.hashed_password = hash_password(payload.new_password)
    user.password_reset_token = None
    user.password_reset_sent_at = None
    # Recover from lockout upon successful password reset
    user.failed_login_attempts = 0
    user.locked_at = None
    session.add(user)
    await session.commit()
