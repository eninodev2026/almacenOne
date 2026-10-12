from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.config import settings

ALGORITHM = "HS256"
COOKIE_ACCESS = "access_token"

_ph = PasswordHasher()

if len(settings.jwt_secret) < 32:
    raise RuntimeError("JWT_SECRET debe tener al menos 32 caracteres")


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def crear_access_token(user_id: int, sesion_id: int) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "sid": sesion_id,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=settings.access_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decodificar_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None