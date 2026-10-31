from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import unauthorized
from app.core.ratelimit import limiter
from app.db.models import User
from app.db.session import get_db
from app.services import auth as auth_service

DB = Annotated[AsyncSession, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def current_user(request: Request, db: DB, settings: SettingsDep) -> User:
    token = request.cookies.get(settings.session_cookie)
    if not token:
        raise unauthorized()
    user = await auth_service.resolve_session(db, settings, token)
    if user is None:
        raise unauthorized()
    request.state.user_id = user.id
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def rate_limit(bucket: str, setting: str):  # type: ignore[no-untyped-def]
    """Dependency factory: per-session sliding-window limit, read from a Settings field."""

    async def _check(request: Request, settings: SettingsDep) -> None:
        key = request.cookies.get(settings.session_cookie) or (request.client.host if request.client else "?")
        limiter.check(bucket, key, int(getattr(settings, setting)))

    return Depends(_check)
