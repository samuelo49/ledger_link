from datetime import datetime, timedelta, timezone
import secrets
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Request
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.keys import build_jwk
from ..core.security import create_token, hash_password, verify_password, decode_token
from ..dependencies import get_session
from ..models import User, RefreshToken
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
from ..metrics import (
    registration_total,
    login_attempt_total,
    token_refresh_total,
    verification_request_total,
    verification_confirm_total,
    password_reset_request_total,
    password_reset_confirm_total,
)
from ..services.refresh_tokens import (
    create_refresh_token_record,
    get_refresh_token,
    hash_token,
    revoke_refresh_token,
)

router = APIRouter(prefix="/auth")


def _as_utc(dt: datetime) -> datetime:
    """Normalize datetimes from SQLite (naive) or Postgres (aware) into UTC for comparisons."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def _mint_refresh_token(session: AsyncSession, user: User, refresh_delta: timedelta) -> tuple[str, UUID]:
    refresh_id = uuid4()
    refresh_token = create_token(
        str(user.id),
        scope="refresh",
        expires_delta=refresh_delta,
        token_type="refresh",
        jti=str(refresh_id),
    )
    expires_at = datetime.now(tz=timezone.utc) + refresh_delta
    await create_refresh_token_record(
        session,
        token_id=refresh_id,
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )
    return refresh_token, refresh_id


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> UserResponse:
    existing = await session.scalar(select(User).where(User.email == payload.email))
    if existing:
        registration_total.labels(outcome="conflict").inc()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    registration_total.labels(outcome="created").inc()
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
        login_attempt_total.labels(outcome="invalid_credentials").inc()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Check lockout window
    if user.locked_at:
        lockout_until = user.locked_at + timedelta(minutes=settings.lockout_minutes)
        if datetime.now(tz=timezone.utc) < lockout_until:
            login_attempt_total.labels(outcome="locked_out").inc()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account locked. Try again later.")
        # Lockout expired: reset
        user.locked_at = None
        user.failed_login_attempts = 0

    # Additional account checks
    if not user.is_active:
        login_attempt_total.labels(outcome="inactive").inc()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")
    if settings.require_verified_for_login and not user.is_verified:
        login_attempt_total.labels(outcome="unverified").inc()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    # Successful login: issue tokens and update audit fields
    access_delta = timedelta(minutes=settings.access_token_expires_minutes)
    refresh_delta = timedelta(minutes=settings.refresh_token_expires_minutes)
    access_token = create_token(str(user.id), scope="access", expires_delta=access_delta, token_type="access")
    refresh_token, _ = await _mint_refresh_token(session, user, refresh_delta)

    user.last_login_at = datetime.now(tz=timezone.utc)
    user.failed_login_attempts = 0
    user.locked_at = None
    session.add(user)
    await session.commit()

    login_attempt_total.labels(outcome="success").inc()
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_delta.total_seconds()),
        refresh_expires_in=int(refresh_delta.total_seconds()),
    )


@router.post("/refresh", response_model=Token)
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_session)) -> Token:
    settings = identity_settings()
    try:
        decoded = decode_token(payload.refresh_token, expected_scope="refresh", token_type="refresh")
    except JWTError as exc:
        token_refresh_total.labels(outcome="invalid_token").inc()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    token_id = decoded.get("jti")
    if not token_id:
        token_refresh_total.labels(outcome="invalid_token").inc()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing jti")

    try:
        token_uuid = UUID(token_id)
    except ValueError as exc:
        token_refresh_total.labels(outcome="invalid_token").inc()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token identifier") from exc

    token_record = await get_refresh_token(session, token_uuid)
    if not token_record:
        token_refresh_total.labels(outcome="revoked").inc()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is not recognized")

    if token_record.revoked_at:
        token_refresh_total.labels(outcome="revoked").inc()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is revoked")

    now = datetime.now(tz=timezone.utc)
    expires_at = _as_utc(token_record.expires_at)
    if expires_at <= now:
        token_refresh_total.labels(outcome="expired").inc()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    if token_record.token_hash != hash_token(payload.refresh_token):
        token_refresh_total.labels(outcome="invalid_token").inc()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token signature mismatch")

    user = await session.get(User, int(decoded["sub"]))
    if not user or not user.is_active:
        token_refresh_total.labels(outcome="invalid_user").inc()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive or missing")

    access_delta = timedelta(minutes=settings.access_token_expires_minutes)
    refresh_delta = timedelta(minutes=settings.refresh_token_expires_minutes)
    access_token = create_token(str(user.id), scope="access", expires_delta=access_delta, token_type="access")
    new_refresh_token, replacement_id = await _mint_refresh_token(session, user, refresh_delta)
    await revoke_refresh_token(session, token_record, replaced_by=replacement_id)
    await session.commit()

    token_refresh_total.labels(outcome="success").inc()
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=int(access_delta.total_seconds()),
        refresh_expires_in=int(refresh_delta.total_seconds()),
    )


@router.get("/me", response_model=UserResponse)
async def me(request: Request, session: AsyncSession = Depends(get_session)) -> UserResponse:
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    try:
        decoded = decode_token(token, expected_scope="access", token_type="access")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    user_id = decoded.get("sub")
    user = await session.get(User, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return UserResponse.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, session: AsyncSession = Depends(get_session)) -> None:
    try:
        decoded = decode_token(payload.refresh_token, expected_scope="refresh", token_type="refresh")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    token_id = decoded.get("jti")
    if not token_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing identifier")
    try:
        token_uuid = UUID(token_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token identifier")
    token_record = await get_refresh_token(session, token_uuid)
    if token_record:
        await revoke_refresh_token(session, token_record)
        await session.commit()


@router.post("/verification/request", response_model=VerificationTokenResponse, status_code=status.HTTP_202_ACCEPTED)
async def verification_request(payload: VerificationRequest, session: AsyncSession = Depends(get_session)) -> VerificationTokenResponse:
    # For privacy, do not reveal whether email exists; if not found, mint a dummy token
    user = await session.scalar(select(User).where(User.email == payload.email))
    token = secrets.token_urlsafe(32)
    if user:
        user.verification_token = token
        session.add(user)
        await session.commit()
        verification_request_total.labels(outcome="issued").inc()
    else:
        verification_request_total.labels(outcome="unknown_user").inc()
    return VerificationTokenResponse(verification_token=token)


@router.post("/verification/confirm", response_model=UserResponse)
async def verification_confirm(payload: VerificationConfirmRequest, session: AsyncSession = Depends(get_session)) -> UserResponse:
    user = await session.scalar(select(User).where(User.verification_token == payload.token))
    if not user:
        verification_confirm_total.labels(outcome="invalid_token").inc()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")
    user.is_verified = True
    user.verified_at = datetime.now(tz=timezone.utc)
    user.verification_token = None
    session.add(user)
    await session.commit()
    await session.refresh(user)
    verification_confirm_total.labels(outcome="success").inc()
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
        password_reset_request_total.labels(outcome="issued").inc()
    else:
        password_reset_request_total.labels(outcome="unknown_user").inc()
    return PasswordResetTokenResponse(password_reset_token=token)


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def password_reset_confirm(payload: PasswordResetConfirmRequest, session: AsyncSession = Depends(get_session)) -> None:
    user = await session.scalar(select(User).where(User.password_reset_token == payload.token))
    if not user:
        password_reset_confirm_total.labels(outcome="invalid_token").inc()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password reset token")
    user.hashed_password = hash_password(payload.new_password)
    user.password_reset_token = None
    user.password_reset_sent_at = None
    # Recover from lockout upon successful password reset
    user.failed_login_attempts = 0
    user.locked_at = None
    session.add(user)
    await session.commit()
    password_reset_confirm_total.labels(outcome="success").inc()


@router.get("/jwks")
async def jwks() -> dict[str, list[dict[str, str]]]:
    """Expose the public signing keys for downstream services."""
    return {"keys": [build_jwk()]}
