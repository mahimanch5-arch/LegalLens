"""Test harness: one app per session on a throwaway data dir, real lifespan (migrations, worker),
and an autouse reset so every test starts with an empty workspace."""

import io
import json
import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

_DATA = Path(tempfile.mkdtemp(prefix="legallens-test-"))
os.environ.update(
    {
        "LL_ENV": "test",
        "LL_DATA_DIR": str(_DATA),
        "LL_USER_EMAIL": "dana@whitfieldlaw.com",
        "LL_USER_PASSWORD": "correct horse",
        "LL_STUB_TOKEN_DELAY_MS": "0",
        "LL_MAX_UPLOAD_BYTES": str(200_000),
        "LL_RATE_CHAT_PER_MINUTE": "1000",
        "LL_RATE_UPLOAD_PER_MINUTE": "1000",
        "LL_RATE_LOGIN_PER_MINUTE": "5",
    }
)

import pytest  # noqa: E402
from docx import Document as DocxDocument  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pypdf import PdfReader, PdfWriter  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

from app.main import create_app  # noqa: E402
from app.runtime import Runtime  # noqa: E402

PASSWORD = "correct horse"
EMAIL = "dana@whitfieldlaw.com"

CONTRACT_PAGES = [
    "MASTER SERVICES AGREEMENT. This Master Services Agreement is entered into as of March 1, 2024 by and "
    "between Northwind Analytics, LLC (Provider) and Acme Industrial Holdings, Inc. (Customer).",
    "11.1 Termination for Convenience. Either party may terminate this Agreement for convenience upon one "
    "hundred twenty (120) days' prior written notice to the other party.",
    "16.1 Governing Law. This Agreement is governed by the laws of the State of Delaware. Customer shall pay "
    "all undisputed invoices within thirty (30) days of receipt.",
]


# ---------- fixture documents ----------


def make_pdf(pages: list[str]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for text in pages:
        y = 800
        words = text.split()
        line = ""
        for w in words:
            if len(line) + len(w) > 90:
                c.drawString(40, y, line)
                y -= 16
                line = ""
            line += w + " "
        if line.strip():
            c.drawString(40, y, line)
        c.showPage()
    c.save()
    return buf.getvalue()


def make_encrypted_pdf() -> bytes:
    writer = PdfWriter(
        clone_from=PdfReader(io.BytesIO(make_pdf(["Board minutes for the fourth quarter meeting."])))
    )
    writer.encrypt(user_password="secret", owner_password="owner")
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def make_docx(paragraphs: list[str]) -> bytes:
    doc = DocxDocument()
    for p in paragraphs:
        doc.add_paragraph(p)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


@pytest.fixture(scope="session")
def files() -> dict[str, bytes]:
    return {
        "contract_pdf": make_pdf(CONTRACT_PAGES),
        "opinion_docx": make_docx(
            [
                "UNITED STATES COURT OF APPEALS FOR THE NINTH CIRCUIT",
                "Smith Corp., Plaintiff-Appellee, v. Jones Holdings, Inc., Defendant-Appellant.",
                "Appeal from the United States District Court for the Northern District of California.",
                "The sole question on appeal is whether an email satisfies a contractual requirement of written notice.",
                "We hold that an email sent to the designated contact constitutes written notice.",
                "The judgment of the district court is AFFIRMED.",
            ]
        ),
        "complaint_txt": (
            b"SUPERIOR COURT OF THE STATE OF CALIFORNIA\n\nCOMPLAINT FOR DAMAGES\n\n"
            b"Plaintiff Maria Reyes alleges that she was employed by Coastal Logistics from April 2019 until "
            b"February 14, 2025.\n\nFIRST CAUSE OF ACTION: Wrongful termination in violation of public policy.\n\n"
            b"PRAYER FOR RELIEF: Plaintiff prays for compensatory damages and costs of suit."
        ),
        "encrypted_pdf": make_encrypted_pdf(),
        "blank_pdf": make_pdf(["", ""]),
        "mixed_pdf": make_pdf(
            ["This page has a real text layer describing the indemnification obligations.", ""]
        ),
    }


# ---------- app & client ----------


@pytest.fixture(scope="session")
def app_client() -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as client:
        yield client
    shutil.rmtree(_DATA, ignore_errors=True)


@pytest.fixture(scope="session")
def runtime(app_client: TestClient) -> Runtime:
    rt: Runtime = app_client.app.state.runtime  # type: ignore[attr-defined]
    return rt


@pytest.fixture
def anon(app_client: TestClient) -> TestClient:
    app_client.cookies.clear()
    return app_client


@pytest.fixture
def client(app_client: TestClient) -> TestClient:
    app_client.cookies.clear()
    r = app_client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return app_client


@pytest.fixture(autouse=True)
def _reset(app_client: TestClient) -> Iterator[None]:
    from app.core.ratelimit import limiter
    from app.services.scenario import scenario

    limiter.reset()
    scenario.reset()
    yield
    app_client.cookies.clear()
    app_client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    app_client.post("/api/dev/reset")
    limiter.reset()
    scenario.reset()


# ---------- helpers ----------


def wait_idle(client: TestClient) -> None:
    rt: Runtime = client.app.state.runtime  # type: ignore[attr-defined]
    client.portal.call(rt.queue.wait_idle, 30.0)  # type: ignore[union-attr]


def upload(client: TestClient, *items: tuple[str, bytes], wait: bool = True) -> dict[str, Any]:
    r = client.post("/api/documents", files=[("files", (name, data)) for name, data in items])
    assert r.status_code == 201, r.text
    if wait:
        wait_idle(client)
    return r.json()


def doc_by_name(client: TestClient, name: str) -> dict[str, Any]:
    items = client.get("/api/documents").json()["items"]
    return next(d for d in items if d["name"] == name)


def parse_sse(body: str) -> list[tuple[str, Any]]:
    """Mirrors frontend/src/api/sse.ts parseSseChunk closely enough for assertions."""
    events = []
    for block in body.replace("\r\n", "\n").split("\n\n"):
        name, data = "message", []
        for line in block.split("\n"):
            if line.startswith(":"):
                continue
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].lstrip(" "))
        if data:
            events.append((name, json.loads("\n".join(data))))
    return events


def turn(client: TestClient, conv_id: str, **body: Any) -> tuple[int, list[tuple[str, Any]], Any]:
    body.setdefault("mode", "auto")
    body.setdefault("scope", {"kind": "workspace"})
    with client.stream("POST", f"/api/conversations/{conv_id}/messages", json=body) as r:
        raw = "".join(r.iter_text())
        status = r.status_code
    if status != 200:
        return status, [], json.loads(raw)
    return status, parse_sse(raw), None


def new_conversation(client: TestClient) -> str:
    r = client.post("/api/conversations")
    assert r.status_code == 201
    return str(r.json()["id"])
