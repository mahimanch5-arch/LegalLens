"""Conversations (sidebar, NCC), message history and feedback (FR-25)."""

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.core.ids import iso, new_id, utcnow
from app.db.models import Conversation, Feedback, Message, MessageCitation, MessageExcerpt
from app.schemas.models import (
    ApiError,
    AssistantMessage,
    Citation,
    ConversationDetail,
    DraftMeta,
    DraftParams,
    Excerpt,
    FeedbackRequest,
    Refusal,
    ScopeUsed,
    SummaryResult,
    Usage,
    UserMessage,
)
from app.schemas.models import Conversation as ConversationOut
from app.schemas.models import Feedback as FeedbackOut
from app.services import audit

TITLE_MAX = 120


def to_out(c: Conversation) -> ConversationOut:
    return ConversationOut(
        id=c.id,
        title=c.title,
        last_intent=c.last_intent,
        pinned=c.pinned,
        created_at=iso(c.created_at),
        updated_at=iso(c.updated_at),
    )


async def get_owned(db: AsyncSession, user_id: str, conv_id: str) -> Conversation:
    conv = await db.get(Conversation, conv_id)
    if conv is None or conv.user_id != user_id:
        raise not_found("Conversation")
    return conv


async def list_conversations(
    db: AsyncSession, user_id: str, offset: int, limit: int
) -> tuple[list[ConversationOut], int]:
    total = (
        await db.execute(
            select(func.count()).select_from(Conversation).where(Conversation.user_id == user_id)
        )
    ).scalar_one()
    rows = (
        await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc(), Conversation.id)
            .offset(offset)
            .limit(limit)
        )
    ).scalars()
    return [to_out(c) for c in rows], total


async def create(db: AsyncSession, user_id: str, title: str | None = None) -> ConversationOut:
    now = utcnow()
    conv = Conversation(id=new_id("conv"), user_id=user_id, created_at=now, updated_at=now)
    if title and title.strip():
        # A title set here is kept: the first message only names conversations still called
        # "New conversation".
        conv.title = " ".join(title.split())[:TITLE_MAX]
    db.add(conv)
    audit.record(db, "conversation.create", "conversation", conv.id, user_id)
    await db.commit()
    return to_out(conv)


async def update(
    db: AsyncSession, user_id: str, conv_id: str, title: str | None, pinned: bool | None
) -> ConversationOut:
    conv = await get_owned(db, user_id, conv_id)
    if title is not None and title.strip():
        conv.title = title.strip()[:TITLE_MAX]
    if pinned is not None:
        conv.pinned = pinned
    await db.commit()
    return to_out(conv)


async def delete(db: AsyncSession, user_id: str, conv_id: str) -> None:
    conv = await get_owned(db, user_id, conv_id)
    await db.delete(conv)  # messages, citations, excerpts, feedback and traces cascade
    audit.record(db, "conversation.delete", "conversation", conv_id, user_id)
    await db.commit()


# ---------- messages ----------


def _user_out(m: Message) -> UserMessage:
    return UserMessage(
        id=m.id,
        role="user",
        text=m.text or "",
        mode=m.mode or "auto",
        scope=m.scope_json or {"kind": "workspace"},
        draft_params=DraftParams.model_validate(m.draft_params_json) if m.draft_params_json else None,
        summary_document_id=m.summary_document_id,
        created_at=iso(m.created_at),
    )


def _assistant_out(
    m: Message, citations: list[Citation], excerpts: list[Excerpt], feedback: FeedbackOut | None
) -> AssistantMessage:
    return AssistantMessage(
        id=m.id,
        role="assistant",
        created_at=iso(m.created_at),
        status=m.status or "complete",
        intent=m.intent,
        stage=m.stage if m.status == "streaming" else None,
        scope_used=ScopeUsed.model_validate(m.scope_used_json) if m.scope_used_json else None,
        answer_md=m.answer_md or "",
        citations=citations,
        excerpts=excerpts,
        refusal=Refusal.model_validate(m.refusal_json) if m.refusal_json else None,
        summary=SummaryResult.model_validate(m.summary_json) if m.summary_json else None,
        draft=DraftMeta.model_validate(m.draft_json) if m.draft_json else None,
        error=ApiError.model_validate(m.error_json) if m.error_json else None,
        usage=Usage.model_validate(m.usage_json) if m.usage_json else None,
        feedback=feedback,
        trace_id=m.trace_id,
        model_version=m.model_version,
        prompt_version=m.prompt_version,
    )


async def messages_out(db: AsyncSession, msgs: list[Message]) -> list[UserMessage | AssistantMessage]:
    ids = [m.id for m in msgs if m.role == "assistant"]
    cites: dict[str, list[Citation]] = defaultdict(list)
    excerpts: dict[str, list[Excerpt]] = defaultdict(list)
    feedback: dict[str, FeedbackOut] = {}
    if ids:
        for c in (
            await db.execute(
                select(MessageCitation).where(MessageCitation.message_id.in_(ids)).order_by(MessageCitation.n)
            )
        ).scalars():
            cites[c.message_id].append(
                Citation(
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
            )
        for e in (
            await db.execute(
                select(MessageExcerpt).where(MessageExcerpt.message_id.in_(ids)).order_by(MessageExcerpt.rank)
            )
        ).scalars():
            excerpts[e.message_id].append(
                Excerpt(
                    span_id=e.span_id,
                    document_id=e.document_id,
                    document_name=e.document_name,
                    page=e.page,
                    section=e.section,
                    text=e.text,
                    score=e.score,
                )
            )
        for f in (await db.execute(select(Feedback).where(Feedback.message_id.in_(ids)))).scalars():
            feedback[f.message_id] = FeedbackOut(rating=f.rating, reason=f.reason, comment=f.comment)

    return [
        _user_out(m)
        if m.role == "user"
        else _assistant_out(m, cites[m.id], excerpts[m.id], feedback.get(m.id))
        for m in msgs
    ]


async def list_messages(
    db: AsyncSession, conv_id: str, offset: int = 0, limit: int | None = None
) -> list[UserMessage | AssistantMessage]:
    stmt = select(Message).where(Message.conversation_id == conv_id).order_by(Message.seq).offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return await messages_out(db, list((await db.execute(stmt)).scalars()))


async def count_messages(db: AsyncSession, conv_id: str) -> int:
    return (
        await db.execute(select(func.count()).select_from(Message).where(Message.conversation_id == conv_id))
    ).scalar_one()


async def detail(db: AsyncSession, user_id: str, conv_id: str) -> ConversationDetail:
    conv = await get_owned(db, user_id, conv_id)
    messages = await list_messages(db, conv_id)
    return ConversationDetail(**to_out(conv).model_dump(), messages=messages)


# ---------- feedback ----------


async def save_feedback(db: AsyncSession, user_id: str, body: FeedbackRequest) -> None:
    await get_owned(db, user_id, body.conversation_id)
    msg = await db.get(Message, body.message_id)
    if msg is None or msg.conversation_id != body.conversation_id or msg.role != "assistant":
        raise not_found("Message")
    row = (await db.execute(select(Feedback).where(Feedback.message_id == msg.id))).scalar_one_or_none()
    if row is None:
        row = Feedback(
            message_id=msg.id, conversation_id=body.conversation_id, trace_id=msg.trace_id, rating="up"
        )
        db.add(row)
    row.rating = body.rating
    row.reason = body.reason
    row.comment = body.comment
    row.updated_at = utcnow()
    audit.record(db, "feedback.submit", "message", msg.id, user_id, rating=body.rating, trace_id=msg.trace_id)
    await db.commit()
