from datetime import datetime

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int


class TokenPayload(BaseModel):
    sub: str
    aud: str
    iss: str
    exp: int
    scope: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_verified: bool
    roles: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# New flows: verification & password reset
class VerificationRequest(BaseModel):
    email: EmailStr


class VerificationConfirmRequest(BaseModel):
    token: str


class VerificationTokenResponse(BaseModel):
    verification_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str


class PasswordResetTokenResponse(BaseModel):
    password_reset_token: str
