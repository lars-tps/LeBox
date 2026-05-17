"""Cognito JWT verification using PyJWT's built-in JWKS client.

PyJWKClient fetches the User Pool's JWKS once, caches it in memory, and
hands back the right signing key by `kid`. Verifies signature, issuer,
audience (app client id), and expiry.
"""

import jwt
from jwt import PyJWKClient

from app.config import settings


_JWK_CLIENT: PyJWKClient | None = None


def _issuer() -> str:
    return f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/{settings.cognito_user_pool_id}"


def _get_jwk_client() -> PyJWKClient:
    global _JWK_CLIENT
    if _JWK_CLIENT is None:
        _JWK_CLIENT = PyJWKClient(f"{_issuer()}/.well-known/jwks.json")
    return _JWK_CLIENT


async def verify_cognito_token(token: str) -> dict:
    if not (settings.cognito_region and settings.cognito_user_pool_id and settings.cognito_app_client_id):
        raise RuntimeError("Cognito settings incomplete")

    signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.cognito_app_client_id,
        issuer=_issuer(),
    )
