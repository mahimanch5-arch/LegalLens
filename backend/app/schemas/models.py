"""API models — a one-for-one mirror of ``frontend/src/api/types.ts``.

Keep the section order and names aligned with that file so drift is easy to spot.
"""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.common import CamelModel, DocStatus, DocType, ErrorCode, Intent, Mode, omitted

# ---------- Documents ----------


class LegalDocument(CamelModel):
    id: str
    name: str
    mime_type: str
    size_bytes: int
    pages: int | None
    type: DocType
    type_confidence: float
    type_overridden: bool
    status: DocStatus
    progress: int
    error: str | None = omitted()
    low_ocr_pages: list[int]
    uploaded_at: str


class DocumentPage(CamelModel):
    document_id: str
    page: int
    text: str
    ocr_confidence: float
    low_ocr: bool


class DocumentStatus(CamelModel):
    status: DocStatus
    progress: int
    error: str | None = omitted()


class RejectedUpload(CamelModel):
    name: str
    reason: str


class UploadResult(CamelModel):
    created: list[LegalDocument]
    rejected: list[RejectedUpload]


class UpdateDocumentRequest(CamelModel):
    type: DocType


# ---------- Conversations & messages ----------


class WorkspaceScope(CamelModel):
    kind: Literal["workspace"]


class DocumentsScope(CamelModel):
    kind: Literal["documents"]
    document_ids: list[str]


Scope = Annotated[WorkspaceScope | DocumentsScope, Field(discriminator="kind")]


class ScopeUsed(CamelModel):
    kind: Literal["workspace", "documents"]
    document_ids: list[str]
    label: str


DraftType = Literal["memo", "brief"]
DraftTone = Literal["neutral", "persuasive", "formal"]


class DraftParams(CamelModel):
    draft_type: DraftType
    question_presented: str = Field(max_length=4000)
    audience: str = Field(default="", max_length=300)
    position: str = Field(default="", max_length=4000)
    tone: DraftTone = "neutral"
    source_document_ids: list[str] = Field(default_factory=list, max_length=50)


class Conversation(CamelModel):
    id: str
    title: str
    last_intent: Intent | None
    pinned: bool
    created_at: str
    updated_at: str


class CreateConversationRequest(CamelModel):
    """Optional body of POST /api/conversations. Without a title the conversation is named after its
    first message, as the frontend's "New chat" expects."""

    title: str | None = Field(default=None, max_length=500)


class UpdateConversationRequest(CamelModel):
    title: str | None = Field(default=None, max_length=500)
    pinned: bool | None = None


class Citation(CamelModel):
    n: int
    span_id: str
    document_id: str
    document_name: str
    page: int
    char_start: int
    char_end: int
    quote: str
    section: str | None = omitted()


class Excerpt(CamelModel):
    span_id: str
    document_id: str
    document_name: str
    page: int
    section: str | None = omitted()
    text: str
    score: float


class Refusal(CamelModel):
    reason: str
    scope_label: str
    suggestions: list[str]


class ApiError(CamelModel):
    code: ErrorCode
    message: str
    retry_after_sec: int | None = omitted()


class SummaryField(CamelModel):
    label: str
    value: str | None
    citations: list[int]
    flag: str | None = omitted()


class SummarySection(CamelModel):
    title: str
    fields: list[SummaryField]


class Coverage(CamelModel):
    pages_total: int
    pages_covered: int
    skipped_pages: list[int]
    note: str | None = omitted()


class SummaryResult(CamelModel):
    document_id: str
    document_name: str
    doc_type: DocType
    sections: list[SummarySection]
    coverage: Coverage


class DraftSource(CamelModel):
    document_id: str
    document_name: str


class DraftMeta(CamelModel):
    draft_type: DraftType
    title: str
    params: DraftParams
    sources: list[DraftSource]


class Usage(CamelModel):
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int


FeedbackRating = Literal["up", "down"]


class Feedback(CamelModel):
    rating: FeedbackRating
    reason: str | None = omitted()
    comment: str | None = omitted()


class UserMessage(CamelModel):
    id: str
    role: Literal["user"]
    text: str
    mode: Mode
    scope: Scope
    draft_params: DraftParams | None = omitted()
    summary_document_id: str | None = omitted()
    created_at: str


AssistantStatus = Literal["streaming", "complete", "incomplete", "error"]


class AssistantMessage(CamelModel):
    id: str
    role: Literal["assistant"]
    created_at: str
    status: AssistantStatus
    intent: Intent | None
    stage: str | None = omitted()
    scope_used: ScopeUsed | None = omitted()
    answer_md: str
    citations: list[Citation]
    excerpts: list[Excerpt]
    refusal: Refusal | None = omitted()
    summary: SummaryResult | None = omitted()
    draft: DraftMeta | None = omitted()
    error: ApiError | None = omitted()
    usage: Usage | None = omitted()
    feedback: Feedback | None = omitted()
    trace_id: str | None = omitted()
    model_version: str | None = omitted()
    prompt_version: str | None = omitted()


Message = Annotated[UserMessage | AssistantMessage, Field(discriminator="role")]


class ConversationDetail(Conversation):
    messages: list[Message]


# ---------- Chat turn request ----------


class SendMessageRequest(CamelModel):
    text: str = Field(min_length=1, max_length=8000)
    mode: Mode = "auto"
    scope: Scope = Field(default_factory=lambda: WorkspaceScope(kind="workspace"))
    draft_params: DraftParams | None = None
    summary_document_id: str | None = None

    @model_validator(mode="after")
    def _strip(self) -> "SendMessageRequest":
        self.text = self.text.strip()
        if not self.text:
            raise ValueError("text must not be blank")
        return self


class ModeTurnRequest(SendMessageRequest):
    """Body of the explicit mode endpoints (/api/ask, /api/summarize, /api/draft)."""

    conversation_id: str


# ---------- Feedback ----------


class FeedbackRequest(CamelModel):
    conversation_id: str
    message_id: str
    rating: FeedbackRating
    reason: str | None = Field(default=None, max_length=120)
    comment: str | None = Field(default=None, max_length=4000)


# ---------- Spans ----------


class Span(CamelModel):
    span_id: str
    document_id: str
    document_name: str
    page: int
    char_start: int
    char_end: int
    text: str


# ---------- Auth ----------


class LoginRequest(CamelModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=1000)


class User(CamelModel):
    id: str
    name: str
    email: str
    initials: str


# ---------- Traces & usage ----------


class TraceStage(CamelModel):
    name: str
    started_at: str
    latency_ms: int
    cost_usd: float = 0.0
    detail: str | None = omitted()


class RetrievalCandidate(CamelModel):
    span_id: str
    score: float


class TraceRetrieval(CamelModel):
    query: str
    candidates: list[RetrievalCandidate]


class TraceDetail(CamelModel):
    trace_id: str
    message_id: str
    conversation_id: str
    intent: Intent | None
    status: str
    stages: list[TraceStage]
    retrieval: TraceRetrieval | None
    model_version: str | None
    prompt_version: str | None
    created_at: str


class UsageTotals(CamelModel):
    turns: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


class UsageDay(UsageTotals):
    day: str


class UsageReport(CamelModel):
    totals: UsageTotals
    by_intent: dict[str, UsageTotals]
    by_day: list[UsageDay]


class Health(CamelModel):
    status: Literal["ok", "degraded"]
    version: str
    checks: dict[str, bool] | None = omitted()
