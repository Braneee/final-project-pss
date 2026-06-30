"""
JWT Helper - Utility untuk generate dan verify JWT token

Fungsi utama:
- create_access_token()  : buat access token (expired 1 jam)
- create_refresh_token() : buat refresh token (expired 7 hari)
- decode_token()         : decode & verifikasi token
"""

import jwt
from datetime import datetime, timedelta, timezone
from django.conf import settings


def create_access_token(user_id: int, username: str, role: str) -> str:
    """Buat JWT access token dengan payload user info."""
    payload = {
        "sub":      str(user_id),
        "username": username,
        "role":     role,
        "type":     "access",
        "exp":      datetime.now(timezone.utc) + timedelta(
                        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
                    ),
        "iat":      datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Buat JWT refresh token (hanya berisi user_id, tidak ada role)."""
    payload = {
        "sub":  str(user_id),
        "type": "refresh",
        "exp":  datetime.now(timezone.utc) + timedelta(
                    days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
                ),
        "iat":  datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode dan verifikasi JWT token.
    Raise exception jika token invalid atau expired.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
