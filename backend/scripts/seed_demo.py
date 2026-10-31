"""Seeds the demo workspace: the frontend mock's seven fictional documents, plus a few conversations
produced by running real turns through the stub orchestrator.

    uv run python -m scripts.seed_demo            # add what is missing
    uv run python -m scripts.seed_demo --reset    # wipe the workspace first

Seeded documents skip the upload/parse path (their page text comes from the fixtures), so they have
no original file: GET /api/documents/{id}/file returns 404 for them. Everything else behaves exactly
like an uploaded document.
"""

import argparse
import asyncio
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.core.ids import utcnow
from app.db.migrate import run_migrations
from app.db.models import Document, DocumentPage, User
from app.db.session import dispose_engine, init_engine, sessionmaker
from app.ingestion import search_index
from app.ingestion.blob_store import BlobStore
from app.orchestrator.stub.orchestrator import StubOrchestrator
from app.runtime import Runtime
from app.schemas.models import DocumentsScope, DraftParams, SendMessageRequest, WorkspaceScope
from app.services import chat_turn, conversations, documents
from app.services.auth import ensure_seed_user

FIXTURES = Path(__file__).parent / "seed_data" / "fixtures.json"
DAYS_AGO = {
    "doc_acme_msa": 12,
    "doc_helix_saas": 9,
    "doc_smith_v_jones": 7,
    "doc_bayview_v_delmar": 7,
    "doc_reyes_complaint": 3,
    "doc_exhibit_c": 2,
    "doc_board_minutes": 1,
}


class _NoQueue:
    alive = True

    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def enqueue(self, job_id: str) -> None: ...
    async def wait_idle(self, timeout: float = 30.0) -> None: ...


async def _seed_documents(fixtures: list[dict[str, Any]]) -> int:
    added = 0
    async with sessionmaker()() as db:
        for f in fixtures:
            if await db.get(Document, f["id"]):
                continue
            ready = f["status"] == "ready"
            low = set(f["lowOcrPages"])
            uploaded = utcnow() - timedelta(days=DAYS_AGO.get(f["id"], 1))
            db.add(
                Document(
                    id=f["id"],
                    name=f["name"],
                    mime_type=f["mimeType"],
                    size_bytes=f["sizeBytes"],
                    sha256=f"seed-{f['id']}",
                    blob_path=None,
                    pages=len(f["pages"]) if ready else None,
                    type=f["type"],
                    type_confidence=f["typeConfidence"],
                    status=f["status"],
                    progress=100 if ready else 0,
                    error=f["error"],
                    uploaded_at=uploaded,
                    ready_at=uploaded if ready else None,
                    parse_engine="seed-fixture" if ready else None,
                )
            )
            await db.flush()
            for n, text in enumerate(f["pages"], start=1):
                db.add(
                    DocumentPage(
                        document_id=f["id"],
                        page_no=n,
                        text=text,
                        ocr_confidence=0.58 if n in low else 0.99,
                        low_ocr=n in low,
                        char_count=len(text),
                    )
                )
            await search_index.add_pages(
                db, f["id"], [(n, t) for n, t in enumerate(f["pages"], start=1) if n not in low]
            )
            added += 1
        await db.commit()
    return added


async def _seed_conversations(rt: Runtime, user: User) -> int:
    turns = [
        SendMessageRequest(
            text="What are the termination rights under the Acme–Northwind MSA?",
            mode="ask",
            scope=DocumentsScope(kind="documents", document_ids=["doc_acme_msa"]),
        ),
        SendMessageRequest(
            text="Summarize the Acme–Northwind Master Services Agreement",
            mode="summary",
            scope=WorkspaceScope(kind="workspace"),
            summary_document_id="doc_acme_msa",
        ),
        SendMessageRequest(
            text="Draft a case brief of Smith v. Jones",
            mode="draft",
            scope=WorkspaceScope(kind="workspace"),
            draft_params=DraftParams(
                draft_type="brief",
                question_presented="Was email notice sufficient under Section 12?",
                audience="Supervising partner",
                source_document_ids=["doc_smith_v_jones"],
            ),
        ),
        SendMessageRequest(
            text="What does the workspace say about cryptocurrency mining rigs?",
            mode="ask",
            scope=WorkspaceScope(kind="workspace"),
        ),
    ]
    for req in turns:
        async with sessionmaker()() as db:
            conv = await conversations.create(db, user.id)
            turn = await chat_turn.prepare(db, rt, user.id, conv.id, req)
        async for _frame in chat_turn.run(rt, turn):
            pass
    return len(turns)


async def main(reset: bool) -> None:
    settings = get_settings()
    await asyncio.to_thread(run_migrations, settings)
    init_engine(settings)
    try:
        async with sessionmaker()() as db:
            user = await ensure_seed_user(db, settings)
        blobs = BlobStore(settings)
        rt = Runtime(
            settings=settings,
            blobs=blobs,
            queue=_NoQueue(),
            orchestrator=StubOrchestrator(sessionmaker(), lambda: 0),
        )
        if reset:
            async with sessionmaker()() as db:
                await documents.delete_workspace(db, rt, user.id)
            print("workspace wiped")

        fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))["documents"]
        added = await _seed_documents(fixtures)
        print(f"documents added: {added} (of {len(fixtures)})")

        async with sessionmaker()() as db:
            existing = (await db.execute(select(conversations.Conversation.id).limit(1))).first()
        if existing is None:
            print(f"conversations added: {await _seed_conversations(rt, user)}")
        else:
            print("conversations exist; skipped (use --reset to start over)")
        print(f"sign in as {settings.user_email} / password from LL_USER_PASSWORD")
    finally:
        await dispose_engine()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--reset", action="store_true", help="delete every document and conversation first")
    asyncio.run(main(parser.parse_args().reset))
