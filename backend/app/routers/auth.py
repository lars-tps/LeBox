"""Auth endpoints.

In dev mode: exposes /auth/dev-login for the local dev login form.
In cognito mode: this router is empty (frontend handles login via Cognito Hosted UI).
"""

from fastapi import APIRouter, HTTPException, status

from app.auth import CurrentUser
from app.config import settings
from app.schemas import DevLoginRequest, TokenResponse, UserOut


router = APIRouter()


@router.post("/dev-login", response_model=TokenResponse)
def dev_login(req: DevLoginRequest) -> TokenResponse:
    if settings.auth_mode != "dev":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dev login disabled")
    from app.auth.dev import issue_dev_token
    token = issue_dev_token(email=req.email, display_name=req.display_name)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
