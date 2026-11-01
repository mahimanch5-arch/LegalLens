from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DB, CurrentUser
from app.core.config import get_settings
from app.runtime import RuntimeDep
from app.schemas.models import Health, Span, TraceDetail, UsageReport
from app.services import ops, spans

router = APIRouter(prefix="/api")


@router.get("/spans/{span_id}", response_model=Span, tags=["spans"])
async def get_span(span_id: str, db: DB, _user: CurrentUser) -> Span:
    """Resolves a citation's span to its exact text (FR-13)."""
    return await spans.resolve(db, span_id)


@router.get("/traces/{trace_id}", response_model=TraceDetail, tags=["observability"])
async def get_trace(trace_id: str, db: DB, user: CurrentUser) -> TraceDetail:
    return await ops.get_trace(db, user.id, trace_id)


@router.get("/usage", response_model=UsageReport, tags=["observability"])
async def get_usage(
    db: DB, _user: CurrentUser, start: datetime | None = None, end: datetime | None = None
) -> UsageReport:
    return await ops.usage_report(db, start, end)


@router.get("/health", response_model=Health, tags=["health"])
async def health() -> Health:
    return Health(status="ok", version=get_settings().version)


@router.get("/health/ready", response_model=Health, tags=["health"])
async def ready(db: DB, rt: RuntimeDep) -> Health:
    checks = {"database": False, "migrations": False, "worker": rt.queue.alive}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
        head = (await db.execute(text("SELECT version_num FROM alembic_version"))).scalar_one_or_none()
        checks["migrations"] = head is not None
    except Exception:
        pass
    return Health(
        status="ok" if all(checks.values()) else "degraded", version=rt.settings.version, checks=checks
    )
