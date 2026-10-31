import re
from typing import Any

from fastapi.testclient import TestClient

from app.runtime import Runtime
from app.schemas.models import SendMessageRequest, WorkspaceScope
from app.services import chat_turn
from tests.conftest import doc_by_name, new_conversation, turn, upload

TERMINAL = {"done", "error"}


def _names(events: list[tuple[str, Any]]) -> list[str]:
    return [e for e, _ in events]


def _assistant(client: TestClient, conv_id: str) -> dict[str, Any]:
    msgs = client.get(f"/api/conversations/{conv_id}").json()["messages"]
    return msgs[-1]


def _seed(client: TestClient, files: dict[str, bytes]) -> None:
    upload(
        client,
        ("Acme MSA.pdf", files["contract_pdf"]),
        ("Smith v Jones opinion.docx", files["opinion_docx"]),
        ("Reyes complaint.txt", files["complaint_txt"]),
    )


def test_ask_stream_order_persistence_and_citations(client: TestClient, files: dict[str, bytes]) -> None:
    _seed(client, files)
    conv = new_conversation(client)
    status, events, _ = turn(client, conv, text="What are the termination rights?")
    assert status == 200
    names = _names(events)

    # Ordering contract (types.ts StreamEvent): meta first, exactly one terminal event, last.
    assert names[0] == "meta" and names[-1] == "done" and names[-2] == "usage"
    assert sum(n in TERMINAL for n in names) == 1
    assert names.index("excerpt") < names.index("token")  # excerpts render before generation (FR-12)

    meta = events[0][1]
    assert meta["intent"] == "ask"
    assert meta["scopeUsed"] == {
        "kind": "workspace",
        "documentIds": meta["scopeUsed"]["documentIds"],
        "label": "Whole workspace (3 documents)",
    }

    # Each citation is sent before the first token that carries its marker.
    text_so_far, sent = "", set()
    for name, data in events:
        if name == "citation":
            sent.add(data["n"])
        elif name == "token":
            for n in re.findall(r"\[(\d+)\]", data["text"]):
                assert int(n) in sent
            text_so_far += data["text"]
    assert sent, "expected at least one citation"
    assert "terminate this Agreement for convenience" in " ".join(text_so_far.split())

    # What was streamed is what was stored.
    a = _assistant(client, conv)
    assert a["id"] == meta["messageId"] and a["status"] == "complete" and a["intent"] == "ask"
    assert a["answerMd"] == text_so_far
    assert [c["n"] for c in a["citations"]] == sorted(sent)
    assert len(a["excerpts"]) == names.count("excerpt")
    assert a["modelVersion"] == "stub-extractive-0.1" and a["promptVersion"] == "ask-stub-v1"
    assert a["traceId"] == meta["traceId"]
    assert "stage" not in a

    # Every citation resolves to exactly its quoted text (FR-11, FR-13, FR-21).
    for c in a["citations"]:
        span = client.get(f"/api/spans/{c['spanId']}").json()
        assert span["text"] == c["quote"]
        page = client.get(f"/api/documents/{c['documentId']}/pages/{c['page']}").json()
        assert page["text"][c["charStart"] : c["charEnd"]] == c["quote"]

    conv_row = client.get("/api/conversations").json()["items"][0]
    assert conv_row["title"] == "What are the termination rights" and conv_row["lastIntent"] == "ask"


def test_refusal_is_a_complete_answer(client: TestClient, files: dict[str, bytes]) -> None:
    _seed(client, files)
    conv = new_conversation(client)
    _, events, _ = turn(client, conv, text="What is the cryptocurrency mining policy?")
    names = _names(events)
    assert "refusal" in names and "token" not in names and names[-1] == "done"
    refusal = dict(events)["refusal"]
    assert refusal["scopeLabel"] == "Whole workspace (3 documents)" and refusal["suggestions"]
    a = _assistant(client, conv)
    assert a["status"] == "complete" and a["refusal"] == refusal and a["citations"] == []


def test_scope_limits_retrieval(client: TestClient, files: dict[str, bytes]) -> None:
    _seed(client, files)
    complaint = doc_by_name(client, "Reyes complaint.txt")
    conv = new_conversation(client)
    _, events, _ = turn(
        client,
        conv,
        text="What are the termination rights?",
        scope={"kind": "documents", "documentIds": [complaint["id"]]},
    )
    meta = events[0][1]
    assert meta["scopeUsed"] == {
        "kind": "documents",
        "documentIds": [complaint["id"]],
        "label": "Reyes complaint",
    }
    assert all(d["documentId"] == complaint["id"] for n, d in events if n in ("citation", "excerpt"))


def test_no_ready_documents_refuses(client: TestClient) -> None:
    conv = new_conversation(client)
    _, events, _ = turn(client, conv, text="Anything about indemnity?")
    refusal = dict(events)["refusal"]
    assert refusal["reason"] == "There are no ready documents in this scope to search."
    assert refusal["scopeLabel"] == "Whole workspace (0 documents)"


def test_auto_mode_routes_to_summary(client: TestClient, files: dict[str, bytes]) -> None:
    _seed(client, files)
    acme = doc_by_name(client, "Acme MSA.pdf")
    conv = new_conversation(client)
    _, events, _ = turn(client, conv, text="Summarize the Acme agreement", summaryDocumentId=acme["id"])
    names = _names(events)
    assert events[0][1]["intent"] == "summary" and names[-1] == "done"
    assert names.index("citation") < names.index("summary")
    summary = dict(events)["summary"]
    assert summary["documentId"] == acme["id"] and summary["docType"] == "contract"
    fields = {f["label"]: f for s in summary["sections"] for f in s["fields"]}
    assert "Governing law" in fields and "Delaware" in fields["Governing law"]["value"]
    assert (
        fields["Indemnification"]["value"] is None and fields["Indemnification"]["citations"] == []
    )  # FR-16
    cited = {c["n"] for n, c in events if n == "citation"}
    for f in fields.values():
        assert (f["value"] is None) == (not f["citations"])
        assert set(f["citations"]) <= cited
    assert summary["coverage"] == {"pagesTotal": 3, "pagesCovered": 3, "skippedPages": []}
    assert client.get("/api/conversations").json()["items"][0]["title"] == "Summary: Acme MSA"
    assert _assistant(client, conv)["summary"] == summary


def test_memo_draft(client: TestClient, files: dict[str, bytes]) -> None:
    _seed(client, files)
    acme = doc_by_name(client, "Acme MSA.pdf")
    conv = new_conversation(client)
    params = {
        "draftType": "memo",
        "questionPresented": "Can the customer terminate for convenience?",
        "audience": "Partner",
        "position": "",
        "tone": "neutral",
        "sourceDocumentIds": [acme["id"]],
    }
    _, events, _ = turn(client, conv, text="Draft a memo", mode="draft", draftParams=params)
    names = _names(events)
    assert names[-1] == "done" and names.index("draft") < names.index("token")
    draft = dict(events)["draft"]
    assert draft["draftType"] == "memo" and draft["params"] == params
    assert draft["sources"] == [{"documentId": acme["id"], "documentName": "Acme MSA.pdf"}]
    body = "".join(d["text"] for n, d in events if n == "token")
    for heading in (
        "## Question Presented",
        "## Short Answer",
        "## Statement of Facts",
        "## Discussion",
        "## Conclusion",
    ):
        assert heading in body
    assert client.get("/api/conversations").json()["items"][0]["title"].startswith("Memo: Can the customer")


def test_brief_without_opinion_refuses(client: TestClient, files: dict[str, bytes]) -> None:
    _seed(client, files)
    acme = doc_by_name(client, "Acme MSA.pdf")
    conv = new_conversation(client)
    params = {"draftType": "brief", "questionPresented": "x", "sourceDocumentIds": [acme["id"]]}
    _, events, _ = turn(client, conv, text="Brief it", mode="draft", draftParams=params)
    assert "opinion" in dict(events)["refusal"]["reason"]


def test_case_brief(client: TestClient, files: dict[str, bytes]) -> None:
    _seed(client, files)
    opinion = doc_by_name(client, "Smith v Jones opinion.docx")
    conv = new_conversation(client)
    params = {
        "draftType": "brief",
        "questionPresented": "Is email notice?",
        "sourceDocumentIds": [opinion["id"]],
    }
    _, events, _ = turn(client, conv, text="Brief Smith", mode="draft", draftParams=params)
    body = "".join(d["text"] for n, d in events if n == "token")
    assert "## Holding" in body and "We hold that an email" in body


def test_llm_unavailable_keeps_excerpts(client: TestClient, files: dict[str, bytes]) -> None:
    _seed(client, files)
    client.put("/api/dev/scenario", json={"nextReply": "llm_unavailable"})
    conv = new_conversation(client)
    _, events, _ = turn(client, conv, text="What are the termination rights?")
    names = _names(events)
    assert names[-1] == "error" and "excerpt" in names and "token" not in names  # NFR-6
    assert events[-1][1]["code"] == "llm_unavailable"
    a = _assistant(client, conv)
    assert a["status"] == "error" and a["error"]["code"] == "llm_unavailable" and a["excerpts"]
    assert client.get("/api/dev/scenario").json()["nextReply"] == "normal"  # not sticky


def test_timeout_error(client: TestClient, files: dict[str, bytes]) -> None:
    _seed(client, files)
    client.put("/api/dev/scenario", json={"nextReply": "timeout"})
    conv = new_conversation(client)
    _, events, _ = turn(client, conv, text="What are the termination rights?")
    assert events[-1] == ("error", {"code": "timeout", "message": events[-1][1]["message"]})
    assert _assistant(client, conv)["status"] == "error"


def test_interrupted_stream_is_incomplete(client: TestClient, files: dict[str, bytes]) -> None:
    _seed(client, files)
    client.put("/api/dev/scenario", json={"nextReply": "interrupted"})
    conv = new_conversation(client)
    _, events, _ = turn(client, conv, text="What are the termination rights?")
    names = _names(events)
    assert "token" in names and not TERMINAL & set(names)  # no terminal event → client marks incomplete
    a = _assistant(client, conv)
    assert a["status"] == "incomplete" and a["answerMd"]


def test_rate_limited_before_stream(client: TestClient, files: dict[str, bytes]) -> None:
    client.put("/api/dev/scenario", json={"nextReply": "rate_limited"})
    conv = new_conversation(client)
    status, _, body = turn(client, conv, text="Hello there")
    assert status == 429 and body["code"] == "rate_limited" and body["retryAfterSec"] == 20
    assert client.get(f"/api/conversations/{conv}").json()["messages"] == []


def test_pre_stream_validation(client: TestClient) -> None:
    status, _, body = turn(client, "conv_missing", text="Hello")
    assert status == 404 and body["code"] == "unknown"
    conv = new_conversation(client)
    status, _, body = turn(client, conv, text="   ")
    assert status == 422
    status, _, body = turn(client, conv, text="x", mode="banana")
    assert status == 422


def test_client_disconnect_marks_incomplete(
    client: TestClient, runtime: Runtime, files: dict[str, bytes]
) -> None:
    """Pressing Stop closes the stream mid-answer; the partial answer is kept, marked incomplete (NFR-7)."""
    _seed(client, files)
    conv = new_conversation(client)
    user_id = client.get("/api/auth/me").json()["id"]

    async def stop_after_first_token() -> str:
        from app.db.session import sessionmaker

        req = SendMessageRequest(
            text="What are the termination rights?", scope=WorkspaceScope(kind="workspace")
        )
        async with sessionmaker()() as db:
            prepared = await chat_turn.prepare(db, runtime, user_id, conv, req)
        gen = chat_turn.run(runtime, prepared)
        async for frame in gen:
            if frame["event"] == "token":
                break
        await gen.aclose()
        return prepared.assistant_id

    assistant_id = client.portal.call(stop_after_first_token)  # type: ignore[union-attr]
    a = _assistant(client, conv)
    assert a["id"] == assistant_id and a["status"] == "incomplete"
    assert a["answerMd"] and "usage" not in a
    trace = client.get(f"/api/traces/{a['traceId']}").json()
    assert trace["status"] == "incomplete"


def test_mode_endpoint(client: TestClient, files: dict[str, bytes]) -> None:
    _seed(client, files)
    conv = new_conversation(client)
    with client.stream(
        "POST",
        "/api/ask",
        json={"conversationId": conv, "text": "Summarize termination", "scope": {"kind": "workspace"}},
    ) as r:
        body = "".join(r.iter_text())
    assert r.status_code == 200
    assert '"intent":"ask"' in body  # the router would have said "summary"; the mode endpoint fixes it
