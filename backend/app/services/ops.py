"""Traces (NFR-11, NFR-12) and the usage ledger (NFR-8)."""

from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.core.ids import iso
from app.db.models import Conversation, Trace, UsageTransaction
from app.schemas.models import TraceDetail, TraceRetrieval, TraceStage, UsageDay, UsageReport, UsageTotals


async def get_trace(db: AsyncSession, user_id: str, trace_id: str) -> TraceDetail:
    row = (
        await db.execute(
            select(Trace)
            .join(Conversation, Conversation.id == Trace.conversation_id)
            .where(Trace.trace_id == trace_id, Conversation.user_id == user_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise not_found("Trace")
    return TraceDetail(
        trace_id=row.trace_id,
        message_id=row.message_id,
        conversation_id=row.conversation_id,
        intent=row.intent,
        status=row.status,
        stages=[TraceStage.model_validate(s) for s in row.stages_json],
        retrieval=TraceRetrieval.model_validate(row.retrieval_json) if row.retrieval_json else None,
        model_version=row.model_version,
        prompt_version=row.prompt_version,
        created_at=iso(row.created_at),
    )


class _Sum:
    def __init__(self) -> None:
        self.turns = self.inp = self.out = 0
        self.cost = 0.0

    def add(self, t: UsageTransaction) -> None:
        self.turns += 1
        self.inp += t.input_tokens
        self.out += t.output_tokens
        self.cost += t.cost_usd

    def model(self) -> UsageTotals:
        return UsageTotals(
            turns=self.turns, input_tokens=self.inp, output_tokens=self.out, cost_usd=round(self.cost, 6)
        )


async def usage_report(db: AsyncSession, start: datetime | None, end: datetime | None) -> UsageReport:
    stmt = select(UsageTransaction).order_by(UsageTransaction.created_at)
    if start:
        stmt = stmt.where(UsageTransaction.created_at >= start)
    if end:
        stmt = stmt.where(UsageTransaction.created_at < end)
    total = _Sum()
    by_intent: dict[str, _Sum] = defaultdict(_Sum)
    by_day: dict[str, _Sum] = defaultdict(_Sum)
    for t in (await db.execute(stmt)).scalars():
        total.add(t)
        by_intent[t.intent or "unknown"].add(t)
        by_day[iso(t.created_at)[:10]].add(t)
    return UsageReport(
        totals=total.model(),
        by_intent={k: v.model() for k, v in by_intent.items()},
        by_day=[UsageDay(day=d, **s.model().model_dump()) for d, s in sorted(by_day.items())],
    )
