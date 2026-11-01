"""SSE events on a chat turn — the ``StreamEvent`` union in ``types.ts``.

The orchestrator yields these; the turn service persists them and forwards them as frames.
"""

from dataclasses import dataclass
from typing import Literal

from app.schemas.common import CamelModel, Intent
from app.schemas.models import (
    ApiError,
    Citation,
    DraftMeta,
    Excerpt,
    Refusal,
    ScopeUsed,
    SummaryResult,
    Usage,
)


class MetaData(CamelModel):
    user_message_id: str
    message_id: str
    intent: Intent
    scope_used: ScopeUsed
    trace_id: str


class StageData(CamelModel):
    label: str


class TokenData(CamelModel):
    text: str


class DoneData(CamelModel):
    model_version: str
    prompt_version: str


EventName = Literal[
    "meta", "stage", "token", "citation", "excerpt", "summary", "draft", "refusal", "usage", "done", "error"
]

Payload = (
    MetaData
    | StageData
    | TokenData
    | Citation
    | Excerpt
    | SummaryResult
    | DraftMeta
    | Refusal
    | Usage
    | DoneData
    | ApiError
)


@dataclass(frozen=True, slots=True)
class StreamEvent:
    event: EventName
    data: Payload

    def frame(self) -> dict[str, str]:
        """The dict sse-starlette turns into ``event: …\\ndata: …\\n\\n``."""
        return {"event": self.event, "data": self.data.model_dump_json(by_alias=True)}
