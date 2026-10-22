from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import Settings

password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: UUID, settings: Settings) -> tuple[str, int]:
    expires_in = settings.access_token_minutes * 60
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "iat": datetime.now(UTC),
        "exp": expires_at,
        "type": "access",
    }
    return jwt.encode(claims, settings.app_secret_key, algorithm=ALGORITHM), expires_in


def decode_access_token(token: str, settings: Settings) -> UUID:
    payload = jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Unexpected token type")
    return UUID(payload["sub"])
