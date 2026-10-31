"""SQLite schema — the "conversation DB" of the architecture diagram (lane 6).

Structured outputs (summary, draft, refusal, error, usage) are stored whole as JSON on the
message; citations and excerpts get their own rows because they are queried (span checks,
deletion, evaluation).
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.ids import utcnow


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, list[Any]: JSON, datetime: DateTime(timezone=True)}


# ---------- identity ----------


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256 of the cookie token
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime]


# ---------- documents ----------


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    blob_path: Mapped[str | None] = mapped_column(String(255))
    pages: Mapped[int | None] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(16), default="other")
    type_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    type_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    ready_at: Mapped[datetime | None]
    parse_engine: Mapped[str | None] = mapped_column(String(64))


class DocumentPage(Base):
    __tablename__ = "document_pages"
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    page_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    ocr_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    low_ocr: Mapped[bool] = mapped_column(Boolean, default=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0)


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    state: Mapped[str] = mapped_column(String(16), default="queued", index=True)  # queued|running|done|failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    simulate_failure: Mapped[bool] = mapped_column(Boolean, default=False)  # dev scenario switch
    queued_at: Mapped[datetime] = mapped_column(default=utcnow)
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]


class ChunkMeta(Base):
    """Created now, filled by the AI layer's ingestion later — so hard delete already covers it."""

    __tablename__ = "chunk_meta"
    chunk_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    page: Mapped[int] = mapped_column(Integer)
    char_start: Mapped[int] = mapped_column(Integer)
    char_end: Mapped[int] = mapped_column(Integer)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(64))
    index_version: Mapped[str | None] = mapped_column(String(32))


# ---------- conversations ----------


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    last_intent: Mapped[str | None] = mapped_column(String(16))
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conv_seq", "conversation_id", "seq", unique=True),)

    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    # user turn
    text: Mapped[str | None] = mapped_column(Text)
    mode: Mapped[str | None] = mapped_column(String(16))
    scope_json: Mapped[dict[str, Any] | None]
    draft_params_json: Mapped[dict[str, Any] | None]
    summary_document_id: Mapped[str | None] = mapped_column(String(48))
    # assistant turn
    status: Mapped[str | None] = mapped_column(String(16))
    intent: Mapped[str | None] = mapped_column(String(16))
    stage: Mapped[str | None] = mapped_column(String(200))
    scope_used_json: Mapped[dict[str, Any] | None]
    answer_md: Mapped[str | None] = mapped_column(Text)
    refusal_json: Mapped[dict[str, Any] | None]
    summary_json: Mapped[dict[str, Any] | None]
    draft_json: Mapped[dict[str, Any] | None]
    error_json: Mapped[dict[str, Any] | None]
    usage_json: Mapped[dict[str, Any] | None]
    trace_id: Mapped[str | None] = mapped_column(String(48), index=True)
    model_version: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[str | None] = mapped_column(String(64))


class MessageCitation(Base):
    __tablename__ = "message_citations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    n: Mapped[int] = mapped_column(Integer)
    span_id: Mapped[str] = mapped_column(String(160))
    # No FK: a deleted document's citations stay readable as text; the span itself stops resolving.
    document_id: Mapped[str] = mapped_column(String(48), index=True)
    document_name: Mapped[str] = mapped_column(String(255))
    page: Mapped[int] = mapped_column(Integer)
    char_start: Mapped[int] = mapped_column(Integer)
    char_end: Mapped[int] = mapped_column(Integer)
    quote: Mapped[str] = mapped_column(Text)
    section: Mapped[str | None] = mapped_column(String(120))


class MessageExcerpt(Base):
    __tablename__ = "message_excerpts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    span_id: Mapped[str] = mapped_column(String(160))
    document_id: Mapped[str] = mapped_column(String(48), index=True)
    document_name: Mapped[str] = mapped_column(String(255))
    page: Mapped[int] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float)


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), unique=True)
    conversation_id: Mapped[str] = mapped_column(String(48), index=True)
    trace_id: Mapped[str | None] = mapped_column(String(48))
    rating: Mapped[str] = mapped_column(String(8))
    reason: Mapped[str | None] = mapped_column(String(120))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)


# ---------- operations ----------


class UsageTransaction(Base):
    """Cost ledger (NFR-8). Holds numbers only, so it survives conversation deletion."""

    __tablename__ = "usage_transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str | None] = mapped_column(String(48))
    trace_id: Mapped[str | None] = mapped_column(String(48), index=True)
    intent: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)


class Trace(Base):
    """Per-turn trace (NFR-11, NFR-12). Deleted with its conversation, since it holds the query."""

    __tablename__ = "traces"
    trace_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    message_id: Mapped[str] = mapped_column(String(48), index=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    intent: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    stages_json: Mapped[list[Any]]
    retrieval_json: Mapped[dict[str, Any] | None]
    model_version: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AuditLog(Base):
    """Who did what, when (DR-4). IDs and counts only — never document or answer text."""

    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    user_id: Mapped[str | None] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str | None] = mapped_column(String(160))
    request_id: Mapped[str | None] = mapped_column(String(64))
    detail_json: Mapped[dict[str, Any] | None]
