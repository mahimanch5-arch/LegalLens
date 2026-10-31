from typing import Annotated

from fastapi import APIRouter, Body, Request, Response, status

from app.api.deps import DB, CurrentUser, SettingsDep, rate_limit
from app.core.errors import AppError
from app.schemas.models import LoginRequest, User
from app.services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=User,
    dependencies=[rate_limit("login", "rate_login_per_minute")],
    summary="Sign in — start here",
)
async def login(
    body: Annotated[
        LoginRequest,
        Body(
            openapi_examples={
                "demo": {
                    "summary": "Demo user (dev defaults)",
                    "value": {"email": "dana@whitfieldlaw.com", "password": "legallens"},
                }
            }
        ),
    ],
    response: Response,
    db: DB,
    settings: SettingsDep,
) -> User:
    """Signs in and sets the session cookie. Do this first: Swagger then sends the cookie with every
    other call."""
    result = await auth_service.login(db, settings, body.email, body.password)
    if result is None:
        raise AppError(401, "That email and password combination is incorrect.")
    user, token = result
    response.set_cookie(
        settings.session_cookie,
        token,
        max_age=settings.session_max_days * 86400,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    return auth_service.user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, db: DB, settings: SettingsDep) -> Response:
    token = request.cookies.get(settings.session_cookie)
    if token:
        await auth_service.logout(db, token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.session_cookie, path="/")
    return response


@router.get("/me", response_model=User)
async def me(user: CurrentUser) -> User:
    return auth_service.user_out(user)
