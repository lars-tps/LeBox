"""Auth dependency that resolves the current user from a Bearer JWT.

Behind a single interface we have two backends:
- "dev"     : tokens issued by app.auth.dev (HS256, secret in env)
- "cognito" : tokens issued by AWS Cognito (RS256, verified against JWKS)

Both produce the same claim shape: { sub, email, name? }.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models import User


async def _verify_token(token: str) -> dict:
    if settings.auth_mode == "dev":
        from app.auth.dev import verify_dev_token
        return verify_dev_token(token)
    else:
        from app.auth.cognito import verify_cognito_token
        return await verify_cognito_token(token)


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()

    try:
        claims = await _verify_token(token)
    except Exception as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {e}")

    sub = claims.get("sub")
    email = claims.get("email")
    if not sub or not email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing sub/email")

    # Lazy provisioning: first time we see a user, create the row.
    user = (await db.execute(select(User).where(User.id == sub))).scalar_one_or_none()
    if user is None:
        user = User(id=sub, email=email, display_name=claims.get("name"))
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
