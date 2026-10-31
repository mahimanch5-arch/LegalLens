"""Single-user email + password auth with server-side sessions (FR-27)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.ids import new_id, utcnow
from app.core.security import (
    hash_password,
    hash_token,
    initials,
    needs_rehash,
    new_session_token,
    verify_password,
)
from app.db.models import Session, User
from app.schemas.models import User as UserOut
from app.services import audit

# Seen-at writes are throttled so polling endpoints don't write on every request.
_TOUCH_EVERY = timedelta(seconds=60)


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, initials=initials(user.name))


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


async def ensure_seed_user(db: AsyncSession, settings: Settings) -> User:
    """Creates the configured user, or brings its name and password in line with the settings."""
    email = settings.user_email.strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        user = User(
            id=new_id("usr", 10),
            email=email,
            name=settings.user_name,
            password_hash=hash_password(settings.user_password),
        )
        db.add(user)
    else:
        user.name = settings.user_name
        if not verify_password(user.password_hash, settings.user_password):
            user.password_hash = hash_password(settings.user_password)
    await db.commit()
    return user


async def login(db: AsyncSession, settings: Settings, email: str, password: str) -> tuple[User, str] | None:
    user = (await db.execute(select(User).where(User.email == email.strip().lower()))).scalar_one_or_none()
    if user is None:
        hash_password(password)  # equalise timing with the found-user path
        return None
    if not verify_password(user.password_hash, password):
        audit.record(db, "auth.login_failed", "user", user.id, user.id)
        await db.commit()
        return None
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    token = new_session_token()
    now = utcnow()
    db.add(
        Session(
            id=hash_token(token),
            user_id=user.id,
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(days=settings.session_max_days),
        )
    )
    audit.record(db, "auth.login", "user", user.id, user.id)
    await db.commit()
    return user, token


async def resolve_session(db: AsyncSession, settings: Settings, token: str) -> User | None:
    sid = hash_token(token)
    row = (await db.execute(select(Session, User).join(User).where(Session.id == sid))).first()
    if row is None:
        return None
    session, user = row
    now = utcnow()
    idle_limit = _aware(session.last_seen_at) + timedelta(hours=settings.session_idle_hours)
    if now >= _aware(session.expires_at) or now >= idle_limit:
        await db.delete(session)
        await db.commit()
        return None
    if now - _aware(session.last_seen_at) >= _TOUCH_EVERY:
        session.last_seen_at = now
        await db.commit()
    return user


async def logout(db: AsyncSession, token: str) -> None:
    await db.execute(delete(Session).where(Session.id == hash_token(token)))
    await db.commit()
