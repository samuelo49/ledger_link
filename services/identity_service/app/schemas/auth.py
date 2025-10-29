from datetime import datetime

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


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
