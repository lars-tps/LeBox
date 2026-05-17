"""Dev-mode auth shim: issues + verifies HS256 JWTs that mimic Cognito's claim shape.

NOT FOR PRODUCTION. Enabled only when AUTH_MODE=dev.
"""

import hashlib
import time
import uuid

import jwt

from app.config import settings


def _stable_sub(email: str) -> str:
    # Deterministic sub from email so repeat logins return the same user row.
    return "dev-" + hashlib.sha256(email.lower().encode()).hexdigest()[:24]


def issue_dev_token(email: str, display_name: str | None = None, ttl_seconds: int = 24 * 3600) -> str:
    now = int(time.time())
    claims = {
        "sub": _stable_sub(email),
        "email": email,
        "name": display_name or email.split("@")[0],
        "iat": now,
        "exp": now + ttl_seconds,
        "iss": settings.dev_jwt_issuer,
        "aud": settings.dev_jwt_audience,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(claims, settings.dev_jwt_secret, algorithm="HS256")


def verify_dev_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.dev_jwt_secret,
        algorithms=["HS256"],
        audience=settings.dev_jwt_audience,
        issuer=settings.dev_jwt_issuer,
    )
