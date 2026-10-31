from typing import Annotated, Any

from fastapi import APIRouter, Body, Response, status
from sse_starlette.sse import EventSourceResponse

from app.api.deps import DB, CurrentUser, rate_limit
from app.api.pagination import clamp_limit, next_cursor, parse_cursor
from app.runtime import RuntimeDep
from app.schemas.common import Page
from app.schemas.models import (
    AssistantMessage,
    Conversation,
    ConversationDetail,
    CreateConversationRequest,
    FeedbackRequest,
    SendMessageRequest,
    UpdateConversationRequest,
    UserMessage,
)
from app.services import chat_turn
from app.services import conversations as svc

router = APIRouter(tags=["conversations"])

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
STREAM_DOC = {
    "content": {
        "text/event-stream": {
            "schema": {
                "type": "string",
                "description": "Events in order: meta · stage* · excerpt* · refusal? · (citation* summary)? · "
                "draft? · (token | citation)* · usage · done | error. See StreamEvent in types.ts.",
            }
        }
    },
    "description": "Server-sent events. Errors detected before the stream opens are returned as JSON.",
}


@router.get("/api/conversations", response_model=Page[Conversation])
async def list_conversations(
    db: DB, user: CurrentUser, cursor: str | None = None, limit: int | None = None
) -> Page[Conversation]:
    offset, size = parse_cursor(cursor), clamp_limit(limit)
    items, total = await svc.list_conversations(db, user.id, offset, size)
    return Page(items=items, next_cursor=next_cursor(offset, size, total))


@router.post(
    "/api/conversations",
    response_model=Conversation,
    status_code=status.HTTP_201_CREATED,
    summary="New conversation (NCC) — optional title",
)
async def create_conversation(
    db: DB,
    user: CurrentUser,
    body: Annotated[
        CreateConversationRequest | None,
        Body(
            openapi_examples={
                "titled": {"summary": "With a title", "value": {"title": "Acme MSA — termination review"}},
                "untitled": {
                    "summary": "Without a title (named after the first message)",
                    "value": {},
                },
            }
        ),
    ] = None,
) -> Conversation:
    """Creates an empty conversation. The body is **optional**:

    - `{"title": "…"}` names it. That title is kept — the first message will not rename it.
    - No body, or no title, gives "New conversation", which the first message then replaces with a
      title of its own (this is what the app's **New chat** does).

    Titles are trimmed to 120 characters. Copy the `id` from the response and use it with
    **POST /api/conversations/{conversation_id}/messages** to ask the first question.
    (Sign in with POST /api/auth/login first, or this returns 401.)
    """
    return await svc.create(db, user.id, body.title if body else None)


@router.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str, db: DB, user: CurrentUser) -> ConversationDetail:
    return await svc.detail(db, user.id, conversation_id)


@router.get(
    "/api/conversations/{conversation_id}/messages", response_model=Page[UserMessage | AssistantMessage]
)
async def list_messages(
    conversation_id: str, db: DB, user: CurrentUser, cursor: str | None = None, limit: int | None = None
) -> Page[UserMessage | AssistantMessage]:
    await svc.get_owned(db, user.id, conversation_id)
    offset, size = parse_cursor(cursor), clamp_limit(limit)
    items = await svc.list_messages(db, conversation_id, offset, size)
    total = await svc.count_messages(db, conversation_id)
    return Page(items=items, next_cursor=next_cursor(offset, size, total))


@router.patch("/api/conversations/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: str, body: UpdateConversationRequest, db: DB, user: CurrentUser
) -> Conversation:
    return await svc.update(db, user.id, conversation_id, body.title, body.pinned)


@router.delete("/api/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: str, db: DB, user: CurrentUser) -> Response:
    await svc.delete(db, user.id, conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


SEND_EXAMPLES: dict[str, Any] = {
    "ask": {
        "summary": "Ask across the whole workspace",
        "value": {"text": "What are the termination rights?", "mode": "auto", "scope": {"kind": "workspace"}},
    },
    "ask_one_document": {
        "summary": "Ask about one document",
        "value": {
            "text": "How long does the customer have to pay an invoice?",
            "mode": "ask",
            "scope": {"kind": "documents", "documentIds": ["doc_acme_msa"]},
        },
    },
    "summary": {
        "summary": "Summarize a document",
        "value": {
            "text": "Summarize this agreement",
            "mode": "summary",
            "scope": {"kind": "documents", "documentIds": ["doc_acme_msa"]},
            "summaryDocumentId": "doc_acme_msa",
        },
    },
    "draft": {
        "summary": "Draft a memo",
        "value": {
            "text": "Draft a memo",
            "mode": "draft",
            "scope": {"kind": "documents", "documentIds": ["doc_acme_msa", "doc_smith_v_jones"]},
            "draftParams": {
                "draftType": "memo",
                "questionPresented": "Can a party give notice of breach by email alone?",
                "audience": "Supervising partner",
                "position": "",
                "tone": "neutral",
                "sourceDocumentIds": ["doc_acme_msa", "doc_smith_v_jones"],
            },
        },
    },
}


@router.post(
    "/api/conversations/{conversation_id}/messages",
    response_class=EventSourceResponse,
    responses={200: STREAM_DOC},
    dependencies=[rate_limit("chat", "rate_chat_per_minute")],
    summary="Send a message (ask, summarize or draft) — streamed",
)
async def send_message(
    conversation_id: str,
    body: Annotated[SendMessageRequest, Body(openapi_examples=SEND_EXAMPLES)],
    db: DB,
    rt: RuntimeDep,
    user: CurrentUser,
) -> EventSourceResponse:
    """One chat turn, streamed over server-sent events (FR-10).

    Paste the `id` returned by **POST /api/conversations** into `conversation_id`, pick an example from
    the *Examples* dropdown (or write your own), then *Execute*. Swagger shows the whole stream once it
    has finished: `meta`, `stage`s, `excerpt`s, `citation`s, `token`s, `usage`, then `done`.
    The example document ids exist when the demo data is loaded (`scripts/seed_demo`)."""
    turn = await chat_turn.prepare(db, rt, user.id, conversation_id, body)
    return EventSourceResponse(chat_turn.run(rt, turn), ping=15, sep="\n", headers=SSE_HEADERS)


@router.post("/api/feedback", status_code=status.HTTP_204_NO_CONTENT, tags=["feedback"])
async def feedback(body: FeedbackRequest, db: DB, user: CurrentUser) -> Response:
    """Thumbs up/down plus optional reason, linked to the message's trace (FR-25)."""
    await svc.save_feedback(db, user.id, body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
