from fastapi.testclient import TestClient

from tests.conftest import new_conversation, turn, upload


def test_ncc_list_patch_delete(client: TestClient) -> None:
    r = client.post("/api/conversations")
    assert r.status_code == 201
    conv = r.json()
    assert set(conv) == {"id", "title", "lastIntent", "pinned", "createdAt", "updatedAt"}
    assert conv["title"] == "New conversation" and conv["lastIntent"] is None and conv["pinned"] is False
    assert conv["createdAt"].endswith("Z")

    second = new_conversation(client)
    items = client.get("/api/conversations").json()
    assert [c["id"] for c in items["items"][:2]] == [second, conv["id"]]  # newest first
    assert items["nextCursor"] is None

    r = client.patch(f"/api/conversations/{conv['id']}", json={"title": "  Renamed thread  ", "pinned": True})
    assert r.json()["title"] == "Renamed thread" and r.json()["pinned"] is True
    r = client.patch(f"/api/conversations/{conv['id']}", json={"title": "x" * 300})
    assert len(r.json()["title"]) == 120
    r = client.patch(f"/api/conversations/{conv['id']}", json={"title": "   "})
    assert r.json()["title"] == "x" * 120  # blank titles are ignored

    detail = client.get(f"/api/conversations/{conv['id']}").json()
    assert detail["messages"] == [] and detail["pinned"] is True

    assert client.delete(f"/api/conversations/{conv['id']}").status_code == 204
    assert client.get(f"/api/conversations/{conv['id']}").status_code == 404


def test_messages_feedback_trace_usage(client: TestClient, files: dict[str, bytes]) -> None:
    upload(client, ("Acme MSA.pdf", files["contract_pdf"]))
    before = client.get("/api/usage").json()["totals"]["turns"]
    conv = new_conversation(client)
    turn(client, conv, text="What are the termination rights?")

    page = client.get(f"/api/conversations/{conv}/messages").json()
    user, assistant = page["items"]
    assert user["role"] == "user" and user["mode"] == "auto" and user["scope"] == {"kind": "workspace"}
    assert "draftParams" not in user and "summaryDocumentId" not in user
    assert assistant["role"] == "assistant" and "feedback" not in assert_keys(assistant)

    r = client.post(
        "/api/feedback",
        json={
            "conversationId": conv,
            "messageId": assistant["id"],
            "rating": "down",
            "reason": "Wrong citation",
        },
    )
    assert r.status_code == 204
    client.post("/api/feedback", json={"conversationId": conv, "messageId": assistant["id"], "rating": "up"})
    after = client.get(f"/api/conversations/{conv}").json()["messages"][1]
    assert after["feedback"] == {"rating": "up"}  # upserted, reason cleared

    bad = client.post("/api/feedback", json={"conversationId": conv, "messageId": user["id"], "rating": "up"})
    assert bad.status_code == 404

    trace = client.get(f"/api/traces/{assistant['traceId']}").json()
    assert trace["status"] == "complete" and trace["intent"] == "ask"
    assert any(s["name"] == "retrieval" for s in trace["stages"])
    assert trace["retrieval"]["candidates"]
    assert all("~p" in c["spanId"] for c in trace["retrieval"]["candidates"])

    usage = client.get("/api/usage").json()
    assert usage["totals"]["turns"] == before + 1
    assert "ask" in usage["byIntent"] and usage["byDay"]


def assert_keys(message: dict[str, object]) -> dict[str, object]:
    required = {"id", "role", "createdAt", "status", "intent", "answerMd", "citations", "excerpts"}
    assert required <= set(message)
    return message


def test_delete_conversation_cascades(client: TestClient, files: dict[str, bytes]) -> None:
    upload(client, ("Acme MSA.pdf", files["contract_pdf"]))
    conv = new_conversation(client)
    turn(client, conv, text="What are the termination rights?")
    trace_id = client.get(f"/api/conversations/{conv}").json()["messages"][1]["traceId"]
    client.delete(f"/api/conversations/{conv}")
    assert client.get(f"/api/traces/{trace_id}").status_code == 404


def test_messages_pagination(client: TestClient) -> None:
    conv = new_conversation(client)
    for i in range(3):
        turn(client, conv, text=f"Question {i}")
    first = client.get(f"/api/conversations/{conv}/messages?limit=4").json()
    assert len(first["items"]) == 4 and first["nextCursor"] == "4"
    rest = client.get(f"/api/conversations/{conv}/messages?cursor=4").json()
    assert len(rest["items"]) == 2 and rest["nextCursor"] is None


def test_create_with_optional_title(client: TestClient, files: dict[str, bytes]) -> None:
    upload(client, ("Acme MSA.pdf", files["contract_pdf"]))
    acme = client.get("/api/documents").json()["items"][0]

    # No body at all — exactly what the frontend's "New chat" sends.
    r = client.post("/api/conversations")
    assert r.status_code == 201 and r.json()["title"] == "New conversation"
    # Empty object and blank title behave the same.
    assert client.post("/api/conversations", json={}).json()["title"] == "New conversation"
    assert client.post("/api/conversations", json={"title": "   "}).json()["title"] == "New conversation"
    # Whitespace is normalised and long titles are trimmed to 120 characters.
    assert (
        client.post("/api/conversations", json={"title": "  Acme   review  "}).json()["title"]
        == "Acme review"
    )
    assert len(client.post("/api/conversations", json={"title": "x" * 300}).json()["title"]) == 120
    assert client.post("/api/conversations", json={"title": "x" * 501}).status_code == 422

    # A chosen title survives the first message — for Ask, and for Draft, which titles itself on completion.
    asked = client.post("/api/conversations", json={"title": "Acme MSA — termination review"}).json()["id"]
    turn(client, asked, text="What are the termination rights?")
    drafted = client.post("/api/conversations", json={"title": "My memo"}).json()["id"]
    params = {"draftType": "memo", "questionPresented": "Termination?", "sourceDocumentIds": [acme["id"]]}
    turn(client, drafted, text="Draft", mode="draft", draftParams=params)
    titles = {c["id"]: c["title"] for c in client.get("/api/conversations").json()["items"]}
    assert titles[asked] == "Acme MSA — termination review"
    assert titles[drafted] == "My memo"

    # Untitled conversations are still named after their first message.
    untitled = client.post("/api/conversations").json()["id"]
    turn(client, untitled, text="What are the termination rights?")
    assert client.get(f"/api/conversations/{untitled}").json()["title"] == "What are the termination rights"
