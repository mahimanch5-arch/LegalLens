"""Deletion is real (FR-26, TS-6): verified by test, not asserted."""

import asyncio
import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import sessionmaker
from app.runtime import Runtime
from tests.conftest import doc_by_name, new_conversation, turn, upload

UNIQUE = "Zanzibarian-quokka-clause"
SECRET_DOC = (
    f"CONFIDENTIAL SETTLEMENT AGREEMENT\n\nThe {UNIQUE} provides that the parties shall keep the settlement "
    "amount of four million dollars confidential and shall not disparage each other."
).encode()

TABLES = ["documents", "document_pages", "ingestion_jobs", "chunk_meta"]


def _count_references(client: TestClient, doc_id: str) -> dict[str, int]:
    async def go() -> dict[str, int]:
        async with sessionmaker()() as db:
            out = {}
            for table in TABLES:
                col = "id" if table == "documents" else "document_id"
                out[table] = (
                    await db.execute(text(f"SELECT count(*) FROM {table} WHERE {col} = :d"), {"d": doc_id})
                ).scalar_one()
            out["page_fts"] = (
                await db.execute(
                    text("SELECT count(*) FROM page_fts WHERE page_fts MATCH :q"), {"q": f'"{UNIQUE}"'}
                )
            ).scalar_one()
            return out

    return client.portal.call(go)  # type: ignore[union-attr, no-any-return]


def test_document_hard_delete(client: TestClient, runtime: Runtime) -> None:
    upload(client, ("settlement.txt", SECRET_DOC))
    doc = doc_by_name(client, "settlement.txt")
    conv = new_conversation(client)
    turn(client, conv, text=f"What does the {UNIQUE} say about confidentiality?")
    cited = client.get(f"/api/conversations/{conv}").json()["messages"][1]["citations"]
    assert cited, "expected the answer to cite the document"
    assert client.get(f"/api/spans/{cited[0]['spanId']}").status_code == 200

    blob = runtime.settings.blob_dir / f"{doc['id']}.bin"
    assert blob.exists()
    assert UNIQUE.encode() not in blob.read_bytes()  # encrypted at rest (NFR-9)
    assert _count_references(client, doc["id"])["page_fts"] == 1

    assert client.delete(f"/api/documents/{doc['id']}").status_code == 204

    assert not blob.exists()
    assert _count_references(client, doc["id"]) == dict.fromkeys([*TABLES, "page_fts"], 0)
    assert client.get(f"/api/spans/{cited[0]['spanId']}").status_code == 404
    assert client.get(f"/api/documents/{doc['id']}/pages/1").status_code == 404

    # Effective immediately for retrieval: the same question now refuses.
    conv2 = new_conversation(client)
    _, events, _ = turn(client, conv2, text=f"What does the {UNIQUE} say about confidentiality?")
    assert "refusal" in dict(events)

    # The old answer remains readable as text; its span simply no longer resolves.
    assert client.get(f"/api/conversations/{conv}").json()["messages"][1]["citations"] == cited

    async def tombstone() -> int:
        async with sessionmaker()() as db:
            q = text("SELECT count(*) FROM audit_log WHERE action = 'document.delete' AND entity_id = :d")
            return int((await db.execute(q, {"d": doc["id"]})).scalar_one())

    assert client.portal.call(tombstone) == 1  # type: ignore[union-attr]


def test_workspace_delete(client: TestClient, runtime: Runtime, files: dict[str, bytes]) -> None:
    upload(client, ("settlement.txt", SECRET_DOC), ("Acme MSA.pdf", files["contract_pdf"]))
    conv = new_conversation(client)
    turn(client, conv, text="termination")
    assert client.delete("/api/documents").status_code == 204
    assert client.get("/api/documents").json() == {"items": [], "nextCursor": None}
    assert client.get("/api/conversations").json()["items"] == []
    assert list(runtime.settings.blob_dir.glob("*.bin")) == []


def test_delete_while_processing(client: TestClient, runtime: Runtime, files: dict[str, bytes]) -> None:
    res = upload(client, ("Acme MSA.pdf", files["contract_pdf"]), wait=False)
    doc_id = res["created"][0]["id"]
    assert client.delete(f"/api/documents/{doc_id}").status_code == 204
    client.portal.call(runtime.queue.wait_idle, 30.0)  # type: ignore[union-attr]
    assert client.get(f"/api/documents/{doc_id}").status_code == 404
    assert _count_references(client, doc_id)["document_pages"] == 0


def test_no_document_content_in_logs(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """DR-5: document text never reaches logs — on upload, ingestion, chat or delete."""
    caplog.set_level(logging.DEBUG, logger="legallens")
    upload(client, ("settlement.txt", SECRET_DOC))
    conv = new_conversation(client)
    turn(client, conv, text=f"What does the {UNIQUE} say?")
    client.delete(f"/api/documents/{doc_by_name(client, 'settlement.txt')['id']}")
    asyncio.run(asyncio.sleep(0))
    for record in caplog.records:
        assert UNIQUE not in record.getMessage()
        assert "four million" not in record.getMessage()
