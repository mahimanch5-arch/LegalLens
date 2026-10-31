"""Audit log (DR-4). Records IDs and counts, never document or answer text (DR-5).

Writes are added to the caller's session, so they commit (or roll back) with the action itself.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import request_id_var
from app.db.models import AuditLog


def record(
    db: AsyncSession,
    action: str,
    entity: str,
    entity_id: str | None = None,
    user_id: str | None = None,
    **detail: Any,
) -> None:
    db.add(
        AuditLog(
            action=action,
            entity=entity,
            entity_id=entity_id,
            user_id=user_id,
            request_id=request_id_var.get(),
            detail_json=detail or None,
        )
    )
