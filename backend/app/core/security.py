"""Password hashing (bcrypt) and JWT encode/decode for access + refresh tokens."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def _create_token(subject: str, token_type: TokenType, expires: timedelta, **extra: Any) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires,
        **extra,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID, organization_id: uuid.UUID, role: str) -> str:
    return _create_token(
        str(user_id),
        "access",
        timedelta(minutes=settings.access_token_minutes),
        org=str(organization_id),
        role=role,
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(
        str(user_id), "refresh", timedelta(days=settings.refresh_token_days)
    )


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """Decode and validate a JWT; raises JWTError on any problem (incl. wrong type)."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != expected_type:
        raise JWTError(f"expected {expected_type} token")
    return payload
