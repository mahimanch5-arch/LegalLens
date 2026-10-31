"""Contract tests: the backend is judged by the frontend's own definitions.

1. Response JSON is checked against the interfaces in ``frontend/src/api/types.ts`` — every
   required key present, no unknown keys, and optional (``key?``) fields omitted rather than null.
2. Recorded SSE bodies are parsed by the frontend's real ``parseSseChunk`` (via vite-node).

Both skip cleanly when the frontend folder (or Node) is not available.
"""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import doc_by_name, new_conversation, parse_sse, turn, upload

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
TYPES_TS = FRONTEND / "src" / "api" / "types.ts"

pytestmark = pytest.mark.skipif(not TYPES_TS.exists(), reason="frontend/src/api/types.ts not found")


def _interfaces() -> dict[str, dict[str, bool]]:
    """{interface: {field: optional}} for the flat interfaces in types.ts (extends is followed)."""
    src = TYPES_TS.read_text(encoding="utf-8")
    out: dict[str, dict[str, bool]] = {}
    parents: dict[str, str] = {}
    for m in re.finditer(r"export interface (\w+)(?: extends (\w+))? \{(.*?)\n\}", src, re.S):
        name, parent, body = m.groups()
        fields: dict[str, bool] = {}
        depth = 0
        for line in body.split("\n"):
            stripped = line.strip()
            if depth == 0:
                fm = re.match(r"(\w+)(\?)?:", stripped)
                if fm:
                    fields[fm.group(1)] = bool(fm.group(2))
            depth += stripped.count("{") - stripped.count("}")
        out[name] = fields
        if parent:
            parents[name] = parent
    for child, parent in parents.items():
        out[child] = {**out[parent], **out[child]}
    return out


IFACES = _interfaces()


def check(obj: dict[str, Any], iface: str) -> None:
    spec = IFACES[iface]
    keys = set(obj)
    required = {k for k, optional in spec.items() if not optional}
    assert required <= keys, f"{iface}: missing {required - keys}"
    assert keys <= set(spec), f"{iface}: unexpected {keys - set(spec)}"
    for k, optional in spec.items():
        if optional and k in obj:
            assert obj[k] is not None, f"{iface}.{k} is optional: omit it instead of sending null"


def test_parser_found_interfaces() -> None:
    for name in ("LegalDocument", "Conversation", "AssistantMessage", "Citation", "SummaryResult", "User"):
        assert name in IFACES
    assert IFACES["LegalDocument"]["error"] is True and IFACES["LegalDocument"]["pages"] is False


def test_rest_shapes_match_types_ts(client: TestClient, files: dict[str, bytes]) -> None:
    check(client.get("/api/auth/me").json(), "User")
    upload(client, ("Acme MSA.pdf", files["contract_pdf"]), ("minutes.pdf", files["encrypted_pdf"]))
    for d in client.get("/api/documents").json()["items"]:
        check(d, "LegalDocument")
    acme = doc_by_name(client, "Acme MSA.pdf")
    check(client.get(f"/api/documents/{acme['id']}/pages/1").json(), "DocumentPage")

    conv = new_conversation(client)
    check(client.get("/api/conversations").json()["items"][0], "Conversation")
    turn(client, conv, text="What are the termination rights?")
    turn(client, conv, text="Summarize it", mode="summary", summaryDocumentId=acme["id"])
    turn(
        client,
        conv,
        text="Draft",
        mode="draft",
        draftParams={
            "draftType": "memo",
            "questionPresented": "Termination?",
            "sourceDocumentIds": [acme["id"]],
        },
    )
    turn(client, conv, text="cryptocurrency mining rigs policy")

    detail = client.get(f"/api/conversations/{conv}").json()
    check(detail, "ConversationDetail")
    for m in detail["messages"]:
        if m["role"] == "user":
            check(m, "UserMessage")
            continue
        check(m, "AssistantMessage")
        for c in m["citations"]:
            check(c, "Citation")
        for e in m["excerpts"]:
            check(e, "Excerpt")
        for key, iface in (
            ("refusal", "Refusal"),
            ("usage", "Usage"),
            ("draft", "DraftMeta"),
            ("summary", "SummaryResult"),
        ):
            if key in m:
                check(m[key], iface)
        if "summary" in m:
            # `coverage` is an inline type in SummaryResult: { pagesTotal, pagesCovered, skippedPages, note? }
            coverage = m["summary"]["coverage"]
            assert (
                {"pagesTotal", "pagesCovered", "skippedPages"}
                <= set(coverage)
                <= {
                    "pagesTotal",
                    "pagesCovered",
                    "skippedPages",
                    "note",
                }
            )
            for section in m["summary"]["sections"]:
                check(section, "SummarySection")
                for f in section["fields"]:
                    check(f, "SummaryField")
        if "draft" in m:
            check(m["draft"]["params"], "DraftParams")


@pytest.mark.skipif(
    shutil.which("npx") is None or not (FRONTEND / "node_modules" / ".bin").exists(),
    reason="Node or frontend node_modules not available",
)
def test_frontend_parser_reads_backend_streams(client: TestClient, files: dict[str, bytes]) -> None:
    upload(client, ("Acme MSA.pdf", files["contract_pdf"]))
    acme = doc_by_name(client, "Acme MSA.pdf")
    bodies: dict[str, str] = {}

    def record(name: str, **body: Any) -> None:
        conv = new_conversation(client)
        body.setdefault("mode", "auto")
        body.setdefault("scope", {"kind": "workspace"})
        with client.stream("POST", f"/api/conversations/{conv}/messages", json=body) as r:
            bodies[name] = "".join(r.iter_text())

    record("ask", text="What are the termination rights?")
    record("refusal", text="cryptocurrency mining rigs policy")
    record("summary", text="Summarize", mode="summary", summaryDocumentId=acme["id"])
    client.put("/api/dev/scenario", json={"nextReply": "llm_unavailable"})
    record("error", text="What are the termination rights?")
    client.put("/api/dev/scenario", json={"nextReply": "interrupted"})
    record("interrupted", text="What are the termination rights?")

    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp) / "in.json", Path(tmp) / "out.json"
        src.write_text(json.dumps(bodies), encoding="utf-8")
        script = Path(__file__).parent / "contract" / "parse_sse.ts"
        proc = subprocess.run(
            ["npx", "vite-node", "--config", "vite.config.ts", str(script), str(src), str(dst)],
            cwd=FRONTEND,
            capture_output=True,
            text=True,
            timeout=180,
            shell=shutil.which("npx.cmd") is not None,  # Windows needs the shell to find npx.cmd
        )
        assert proc.returncode == 0, proc.stderr[-2000:]
        parsed = json.loads(dst.read_text(encoding="utf-8"))

    for name, body in bodies.items():
        ours = [{"event": e, "data": d} for e, d in parse_sse(body)]
        assert parsed[name]["events"] == ours, f"{name}: the frontend parser saw a different stream"
    assert parsed["ask"]["terminated"] and parsed["refusal"]["terminated"] and parsed["error"]["terminated"]
    assert parsed["interrupted"]["terminated"] is False  # → the UI marks it incomplete (NFR-7)
    tokens = "".join(e["data"]["text"] for e in parsed["ask"]["events"] if e["event"] == "token")
    assert "[1]" in tokens
