"""The only door between the API and the AI layer (NFR-14, BRD §7).

The backend resolves *who may be searched* (scope, ready documents, draft sources) and persists
*what came back*; everything about *how* to retrieve and write lives behind this protocol. The
stub in ``app.orchestrator.stub`` implements it today; the LangChain orchestrator replaces it
later without touching the API.
"""

import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Protocol

from app.core.ids import iso, utcnow
from app.schemas.common import DocType, Intent, Mode
from app.schemas.models import DraftParams, ScopeUsed, TraceRetrieval, TraceStage
from app.schemas.stream import StreamEvent
from app.services.scenario import NextReply


@dataclass(frozen=True, slots=True)
class DocRef:
    id: str
    name: str
    type: DocType
    pages: int
    low_ocr_pages: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class HistoryTurn:
    role: str  # "user" | "assistant"
    text: str


@dataclass
class TraceRecorder:
    """Stage timings and retrieval candidates, written to the trace table (NFR-11)."""

    stages: list[TraceStage] = field(default_factory=list)
    retrieval: TraceRetrieval | None = None
    _open: tuple[str, float, str] | None = None

    def begin(self, name: str) -> None:
        self.end()
        self._open = (name, time.perf_counter(), iso(utcnow()))

    def end(self, detail: str | None = None) -> None:
        if self._open is None:
            return
        name, t0, started = self._open
        self.stages.append(
            TraceStage(
                name=name,
                started_at=started,
                latency_ms=int((time.perf_counter() - t0) * 1000),
                detail=detail,
            )
        )
        self._open = None


@dataclass
class TurnContext:
    trace_id: str
    text: str
    mode: Mode
    intent: Intent
    scope_used: ScopeUsed
    documents: list[DocRef]  # ready documents in scope — the only ones that may be searched (FR-7)
    summary_document: DocRef | None = None
    draft_params: DraftParams | None = None
    history: list[HistoryTurn] = field(default_factory=list)
    scenario: NextReply = "normal"  # dev-only forced outcome
    trace: TraceRecorder = field(default_factory=TraceRecorder)


class Orchestrator(Protocol):
    model_version: str

    async def route(self, text: str, history: list[HistoryTurn]) -> Intent:
        """Intent router, used only when the user left the mode on Auto."""
        ...

    def answer(self, ctx: TurnContext) -> AsyncGenerator[StreamEvent]: ...

    def summarize(self, ctx: TurnContext) -> AsyncGenerator[StreamEvent]: ...

    def draft(self, ctx: TurnContext) -> AsyncGenerator[StreamEvent]: ...
