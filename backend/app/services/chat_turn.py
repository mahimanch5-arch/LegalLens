"""One chat turn, end to end: validate → resolve intent and scope → write both message rows →
stream the orchestrator's events as SSE → persist whatever was produced, however the turn ended.

Terminal states (NFR-7):
- ``done`` event            → ``complete``
- ``error`` event / timeout → ``error`` (body stored, rendered as an actionable card)
- client Stop / disconnect  → ``incomplete`` (partial text kept)
- stream ends with neither  → ``incomplete``
"""

import asyncio
import logging
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import anyio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.ids import new_id, utcnow
from app.db.models import (
    Conversation,
    Document,
    Message,
    MessageCitation,
    MessageExcerpt,
    Trace,
    UsageTransaction,
)
from app.db.session import sessionmaker
from app.orchestrator.interface import DocRef, HistoryTurn, TurnContext
from app.orchestrator.stub.text import display_name
from app.runtime import Runtime
from app.schemas.common import Intent
from app.schemas.models import (
    ApiError,
    Citation,
    DraftMeta,
    Excerpt,
    Refusal,
    ScopeUsed,
    SendMessageRequest,
    SummaryResult,
    Usage,
)
from app.schemas.stream import DoneData, MetaData, StageData, StreamEvent, TokenData
from app.services import audit
from app.services.conversations import get_owned
from app.services.documents import low_ocr_map
from app.services.scenario import scenario
from app.services.spans import CitationGuard

log = logging.getLogger("legallens.chat")

DEFAULT_TITLE = "New conversation"
_MARKER = re.compile(r"\[(\d+)\]")


def title_from(text: str, intent: Intent, doc_name: str | None = None) -> str:
    if intent == "summary" and doc_name:
        return f"Summary: {display_name(doc_name)}"
    t = re.sub(r"\s+", " ", text).strip().rstrip("?.!")
    return f"{t[:46].rstrip()}…" if len(t) > 48 else (t or DEFAULT_TITLE)


def draft_title(meta: DraftMeta) -> str:
    prefix = "Memo: " if meta.draft_type == "memo" else "Brief: "
    return re.sub(r"^(Memorandum|Case brief) — ", prefix, meta.title)[:120]


@dataclass
class PreparedTurn:
    ctx: TurnContext
    conversation_id: str
    user_id: str
    user_message_id: str
    assistant_id: str
    # True when the backend names the conversation (it was still "New conversation"); a title the
    # user chose is never overwritten.
    auto_title: bool


@dataclass
class Accumulator:
    status: str = "streaming"
    answer: list[str] = field(default_factory=list)
    citations: dict[int, Citation] = field(default_factory=dict)
    dropped: set[int] = field(default_factory=set)
    excerpts: list[Excerpt] = field(default_factory=list)
    refusal: Refusal | None = None
    summary: SummaryResult | None = None
    draft: DraftMeta | None = None
    usage: Usage | None = None
    error: ApiError | None = None
    done: DoneData | None = None
    stage: str | None = None

    @property
    def terminated(self) -> bool:
        return self.done is not None or self.error is not None

    def apply(self, ev: StreamEvent) -> None:
        d: Any = ev.data
        match ev.event:
            case "stage":
                self.stage = d.label
            case "token":
                self.answer.append(d.text)
            case "citation":
                self.citations[d.n] = d
            case "excerpt":
                self.excerpts.append(d)
            case "refusal":
                self.refusal = d
            case "summary":
                self.summary = d
            case "draft":
                self.draft = d
            case "usage":
                self.usage = d
            case "done":
                self.done, self.status = d, "complete"
            case "error":
                self.error, self.status = d, "error"

    def answer_md(self) -> str:
        md = "".join(self.answer)
        if self.dropped:  # remove markers whose citation failed the guard
            md = _MARKER.sub(lambda m: "" if int(m.group(1)) in self.dropped else m.group(0), md)
        return md


# ---------- prepare (before the stream opens; errors here are plain JSON) ----------


async def _history(db: AsyncSession, conv_id: str, turns: int) -> list[HistoryTurn]:
    rows = (
        await db.execute(
            select(Message.role, Message.text, Message.answer_md)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.seq.desc())
            .limit(turns * 2)
        )
    ).all()
    return [HistoryTurn(r.role, (r.text if r.role == "user" else r.answer_md) or "") for r in reversed(rows)]


def _refs(docs: list[Document], low: dict[str, list[int]]) -> list[DocRef]:
    return [DocRef(d.id, d.name, d.type, d.pages or 0, tuple(low.get(d.id, ()))) for d in docs]  # type: ignore[arg-type]


def _plural_docs(n: int) -> str:
    return f"{n} document{'' if n == 1 else 's'}"


async def prepare(
    db: AsyncSession,
    rt: Runtime,
    user_id: str,
    conv_id: str,
    req: SendMessageRequest,
    forced: Intent | None = None,
) -> PreparedTurn:
    conv = await get_owned(db, user_id, conv_id)
    outcome = scenario.consume_reply() if rt.settings.is_dev else "normal"
    if outcome == "rate_limited":
        raise AppError(
            429,
            "You have sent several requests in a short time. Please wait a moment before trying again.",
            code="rate_limited",
            retry_after_sec=20,
        )

    history = await _history(db, conv_id, rt.settings.history_turns)
    intent: Intent = forced or (
        req.mode if req.mode != "auto" else await rt.orchestrator.route(req.text, history)
    )

    ready = list(
        (await db.execute(select(Document).where(Document.status == "ready").order_by(Document.uploaded_at)))
        .scalars()
        .all()
    )
    low = await low_ocr_map(db, [d.id for d in ready])
    by_id = {d.id: d for d in ready}

    # Scope (FR-8, FR-9): only ready documents are ever in scope (FR-7).
    if req.scope.kind == "workspace":
        in_scope = ready
        scope_used = ScopeUsed(
            kind="workspace",
            document_ids=[d.id for d in ready],
            label=f"Whole workspace ({_plural_docs(len(ready))})",
        )
    else:
        in_scope = [by_id[i] for i in dict.fromkeys(req.scope.document_ids) if i in by_id]
        label = (
            display_name(in_scope[0].name) if len(in_scope) == 1 else f"{len(in_scope)} selected documents"
        )
        scope_used = ScopeUsed(kind="documents", document_ids=[d.id for d in in_scope], label=label)

    summary_doc: Document | None = None
    documents = in_scope
    if intent == "summary":
        named = next(
            (d for d in in_scope if display_name(d.name).split()[0].lower() in req.text.lower()), None
        )
        summary_doc = (
            by_id.get(req.summary_document_id or "")
            or (in_scope[0] if len(in_scope) == 1 else None)
            or named
            or (in_scope[0] if in_scope else None)
        )
        if summary_doc is not None:
            documents = [summary_doc]
            scope_used = ScopeUsed(
                kind="documents", document_ids=[summary_doc.id], label=display_name(summary_doc.name)
            )
    elif intent == "draft":
        wanted = req.draft_params.source_document_ids if req.draft_params else [d.id for d in in_scope]
        documents = [by_id[i] for i in dict.fromkeys(wanted) if i in by_id]
        label = (
            display_name(documents[0].name) if len(documents) == 1 else f"{len(documents)} source documents"
        )
        scope_used = ScopeUsed(kind="documents", document_ids=[d.id for d in documents], label=label)

    # Write the user turn and a streaming assistant row before anything is sent (FR-25 needs the id).
    now = utcnow()
    seq = (
        await db.execute(
            select(Message.seq)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.seq.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    seq = -1 if seq is None else seq
    auto_title = seq < 0 and conv.title == DEFAULT_TITLE
    trace_id = new_id("trace")
    user_msg = Message(
        id=new_id("msg"),
        conversation_id=conv_id,
        seq=seq + 1,
        role="user",
        created_at=now,
        text=req.text,
        mode=req.mode if forced is None else forced,
        scope_json=req.scope.dump(),
        draft_params_json=req.draft_params.dump() if req.draft_params else None,
        summary_document_id=req.summary_document_id,
    )
    assistant = Message(
        id=new_id("msg"),
        conversation_id=conv_id,
        seq=seq + 2,
        role="assistant",
        created_at=now,
        status="streaming",
        intent=intent,
        stage="Starting…",
        scope_used_json=scope_used.dump(),
        answer_md="",
        trace_id=trace_id,
    )
    db.add_all([user_msg, assistant])
    conv.updated_at = now
    conv.last_intent = intent
    if auto_title:
        conv.title = title_from(req.text, intent, summary_doc.name if summary_doc else None)
    audit.record(
        db,
        "chat.turn",
        "message",
        assistant.id,
        user_id,
        conversation_id=conv_id,
        intent=intent,
        mode=req.mode,
        documents=[d.id for d in documents],
        trace_id=trace_id,
    )
    await db.commit()

    refs = _refs(documents, low)
    ctx = TurnContext(
        trace_id=trace_id,
        text=req.text,
        mode=req.mode,
        intent=intent,
        scope_used=scope_used,
        documents=refs,
        summary_document=refs[0] if summary_doc is not None else None,
        draft_params=req.draft_params,
        history=history,
        scenario=outcome,
    )
    return PreparedTurn(ctx, conv_id, user_id, user_msg.id, assistant.id, auto_title)


# ---------- stream ----------


async def run(rt: Runtime, turn: PreparedTurn) -> AsyncIterator[dict[str, str]]:
    ctx = turn.ctx
    acc = Accumulator()
    method = {
        "ask": rt.orchestrator.answer,
        "summary": rt.orchestrator.summarize,
        "draft": rt.orchestrator.draft,
    }[ctx.intent]
    deadline = time.monotonic() + rt.settings.turn_timeout_s
    started = time.perf_counter()

    meta = StreamEvent(
        "meta",
        MetaData(
            user_message_id=turn.user_message_id,
            message_id=turn.assistant_id,
            intent=ctx.intent,
            scope_used=ctx.scope_used,
            trace_id=ctx.trace_id,
        ),
    )
    try:
        yield meta.frame()
        async with sessionmaker()() as db:
            guard = CitationGuard(db)
            events = method(ctx)
            try:
                while not acc.terminated:
                    try:
                        async with asyncio.timeout(max(0.0, deadline - time.monotonic())):
                            ev = await anext(events)
                    except StopAsyncIteration:
                        break
                    except TimeoutError:
                        ev = StreamEvent(
                            "error",
                            ApiError(
                                code="timeout",
                                message="The answer took too long to generate and was stopped. "
                                "This is usually temporary — try again.",
                            ),
                        )

                    if ev.event == "citation":
                        c: Citation = ev.data  # type: ignore[assignment]
                        if c.n in acc.citations:
                            continue
                        if not await guard.check(c):
                            log.warning("citation %d dropped by guard trace=%s", c.n, ctx.trace_id)
                            acc.dropped.add(c.n)
                            continue
                    elif ev.event == "summary" and acc.dropped:
                        ev = StreamEvent("summary", _strip_summary(ev.data, acc.dropped))  # type: ignore[arg-type]

                    acc.apply(ev)
                    yield ev.frame()
            finally:
                await events.aclose()
    except Exception:
        log.exception("turn failed trace=%s", ctx.trace_id)
        if not acc.terminated:
            err = StreamEvent(
                "error", ApiError(code="unknown", message="Something went wrong while answering. Try again.")
            )
            acc.apply(err)
            yield err.frame()
    finally:
        if acc.status == "streaming":
            acc.status = "incomplete"  # Stop, disconnect, or a stream that ended without done/error
        with anyio.CancelScope(shield=True):
            await _finalize(rt, turn, acc, int((time.perf_counter() - started) * 1000))


def _strip_summary(summary: SummaryResult, dropped: set[int]) -> SummaryResult:
    s = summary.model_copy(deep=True)
    for section in s.sections:
        for f in section.fields:
            f.citations = [n for n in f.citations if n not in dropped]
            if f.value and not f.citations:
                f.value = None  # an uncited value is never shown (FR-16)
    return s


async def _finalize(rt: Runtime, turn: PreparedTurn, acc: Accumulator, latency_ms: int) -> None:
    ctx = turn.ctx
    ctx.trace.end()
    try:
        async with sessionmaker()() as db:
            msg = await db.get(Message, turn.assistant_id)
            if msg is None:  # conversation deleted mid-stream
                return
            msg.status = acc.status
            msg.stage = None
            msg.answer_md = acc.answer_md()
            msg.refusal_json = acc.refusal.dump() if acc.refusal else None
            msg.summary_json = acc.summary.dump() if acc.summary else None
            msg.draft_json = acc.draft.dump() if acc.draft else None
            msg.error_json = acc.error.dump() if acc.error else None
            msg.usage_json = acc.usage.dump() if acc.usage else None
            msg.model_version = acc.done.model_version if acc.done else rt.orchestrator.model_version
            msg.prompt_version = acc.done.prompt_version if acc.done else None
            db.add_all(
                MessageCitation(
                    message_id=msg.id,
                    n=c.n,
                    span_id=c.span_id,
                    document_id=c.document_id,
                    document_name=c.document_name,
                    page=c.page,
                    char_start=c.char_start,
                    char_end=c.char_end,
                    quote=c.quote,
                    section=c.section,
                )
                for c in sorted(acc.citations.values(), key=lambda c: c.n)
            )
            db.add_all(
                MessageExcerpt(
                    message_id=msg.id,
                    rank=i,
                    span_id=e.span_id,
                    document_id=e.document_id,
                    document_name=e.document_name,
                    page=e.page,
                    section=e.section,
                    text=e.text,
                    score=e.score,
                )
                for i, e in enumerate(acc.excerpts)
            )

            values: dict[str, Any] = {"updated_at": utcnow()}
            if turn.auto_title and acc.draft is not None:
                values["title"] = draft_title(acc.draft)
            await db.execute(
                update(Conversation).where(Conversation.id == turn.conversation_id).values(**values)
            )

            usage = acc.usage or Usage(input_tokens=0, output_tokens=0, cost_usd=0.0, latency_ms=latency_ms)
            db.add(
                UsageTransaction(
                    message_id=msg.id,
                    trace_id=ctx.trace_id,
                    intent=ctx.intent,
                    status=acc.status,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cost_usd=usage.cost_usd,
                    latency_ms=usage.latency_ms or latency_ms,
                )
            )
            db.add(
                Trace(
                    trace_id=ctx.trace_id,
                    message_id=msg.id,
                    conversation_id=turn.conversation_id,
                    intent=ctx.intent,
                    status=acc.status,
                    stages_json=[s.dump() for s in ctx.trace.stages],
                    retrieval_json=ctx.trace.retrieval.dump() if ctx.trace.retrieval else None,
                    model_version=msg.model_version,
                    prompt_version=msg.prompt_version,
                )
            )
            audit.record(
                db,
                "chat.turn_finished",
                "message",
                msg.id,
                turn.user_id,
                status=acc.status,
                citations=len(acc.citations),
                dropped_citations=len(acc.dropped),
                refused=acc.refusal is not None,
                trace_id=ctx.trace_id,
            )
            await db.commit()
    except Exception:
        log.exception("failed to persist turn trace=%s", ctx.trace_id)


async def recover_interrupted() -> int:
    """At startup: any turn still 'streaming' was cut off by a restart."""
    async with sessionmaker()() as db:
        result = await db.execute(
            update(Message).where(Message.status == "streaming").values(status="incomplete", stage=None)
        )
        await db.commit()
        return int(result.rowcount or 0)  # type: ignore[attr-defined]


__all__ = ["PreparedTurn", "prepare", "recover_interrupted", "run", "StageData", "TokenData"]
