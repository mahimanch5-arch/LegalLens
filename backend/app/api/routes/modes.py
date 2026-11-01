"""Explicit mode endpoints (diagram "MODE ENDPOINTS"): the same turn with the intent fixed and the
router skipped. The current frontend uses the conversation endpoint instead."""

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.api.deps import DB, CurrentUser, rate_limit
from app.api.routes.conversations import SSE_HEADERS, STREAM_DOC
from app.runtime import RuntimeDep
from app.schemas.common import Intent
from app.schemas.models import ModeTurnRequest, SendMessageRequest
from app.services import chat_turn

router = APIRouter(prefix="/api", tags=["modes"])


async def _turn(
    intent: Intent, body: ModeTurnRequest, db: DB, rt: RuntimeDep, user_id: str
) -> EventSourceResponse:
    req = SendMessageRequest.model_validate(body.model_dump(exclude={"conversation_id"}))
    req.mode = intent
    turn = await chat_turn.prepare(db, rt, user_id, body.conversation_id, req, forced=intent)
    return EventSourceResponse(chat_turn.run(rt, turn), ping=15, sep="\n", headers=SSE_HEADERS)


_COMMON = {
    "response_class": EventSourceResponse,
    "responses": {200: STREAM_DOC},
    "dependencies": [rate_limit("chat", "rate_chat_per_minute")],
}


@router.post("/ask", **_COMMON)  # type: ignore[arg-type]
async def ask(body: ModeTurnRequest, db: DB, rt: RuntimeDep, user: CurrentUser) -> EventSourceResponse:
    return await _turn("ask", body, db, rt, user.id)


@router.post("/summarize", **_COMMON)  # type: ignore[arg-type]
async def summarize(body: ModeTurnRequest, db: DB, rt: RuntimeDep, user: CurrentUser) -> EventSourceResponse:
    return await _turn("summary", body, db, rt, user.id)


@router.post("/draft", **_COMMON)  # type: ignore[arg-type]
async def draft(body: ModeTurnRequest, db: DB, rt: RuntimeDep, user: CurrentUser) -> EventSourceResponse:
    return await _turn("draft", body, db, rt, user.id)
