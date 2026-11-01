"""Stub orchestrator quality: the cases that made answers look broken in manual testing."""

from typing import Any

from fastapi.testclient import TestClient

from app.orchestrator.stub.text import is_caps_heading, is_meta_question, name_terms, sentences, stem
from tests.conftest import doc_by_name, new_conversation, turn, upload

HELIX = (
    b"SAAS SUBSCRIPTION AGREEMENT\n\nThis SaaS Subscription Agreement is made on January 15, 2025 between "
    b"Helix Cloud Software, Inc. (Helix) and Brightwater Legal LLP (Subscriber).\n\n"
    b"9.1 Amendments. Any amendment must be in writing and signed by authorized representatives of both parties."
)


def _ask(client: TestClient, text: str, **scope: Any) -> dict[str, Any]:
    conv = new_conversation(client)
    _, events, _ = turn(client, conv, text=text, **scope)
    return {"events": dict(events), "citations": [d for e, d in events if e == "citation"]}


def test_stem_meets_singular_and_plural() -> None:
    assert stem("invoice") == stem("invoices")
    assert stem("party") == stem("parties")
    assert stem("terminate") == stem("termination") == stem("terminated")
    assert stem("notice") == stem("notices")


def test_document_names_and_acronyms() -> None:
    distinctive, acronyms = name_terms("Acme–Northwind Master Services Agreement.pdf")
    assert {"acme", stem("northwind")} <= distinctive
    assert "agreement" not in distinctive and "master" not in distinctive
    assert "msa" in acronyms


def test_headings_are_not_quoted() -> None:
    assert is_caps_heading("UNITED STATES COURT OF APPEALS")
    assert not is_caps_heading(
        "IN NO EVENT SHALL EITHER PARTY'S AGGREGATE LIABILITY ARISING OUT OF THIS AGREEMENT EXCEED THE FEES PAID"
    )
    page = "UNITED STATES COURT OF APPEALS\n\nThe district court granted summary judgment to the plaintiff."
    assert [s.text for s in sentences(page)] == [
        "The district court granted summary judgment to the plaintiff."
    ]


def test_meta_questions() -> None:
    for q in ("hi", "Test", "what can you do?", "what all legal questions you can answer?", "help"):
        assert is_meta_question(q), q
    for q in ("What are the termination rights?", "Who is the judge?", "testing obligations under the SOW"):
        assert not is_meta_question(q), q


def test_meta_question_gets_guidance_not_refusal(client: TestClient, files: dict[str, bytes]) -> None:
    upload(client, ("Acme MSA.pdf", files["contract_pdf"]))
    r = _ask(client, "what can you do?")
    assert "refusal" not in r["events"] and r["citations"] == []
    assert "done" in r["events"]


def test_abbreviated_document_name_still_answers(client: TestClient, files: dict[str, bytes]) -> None:
    """'…under the Acme MSA' must not be refused just because 'MSA' never appears in the text."""
    upload(client, ("Acme–Northwind Master Services Agreement.pdf", files["contract_pdf"]))
    r = _ask(client, "What are the termination rights under the Acme–Northwind MSA?")
    assert "refusal" not in r["events"]
    assert "terminate this Agreement for convenience" in " ".join(r["citations"][0]["quote"].split())


def test_named_document_is_searched_and_concept_found(client: TestClient, files: dict[str, bytes]) -> None:
    upload(client, ("Helix SaaS Subscription Agreement.txt", HELIX), ("Acme MSA.pdf", files["contract_pdf"]))
    helix = doc_by_name(client, "Helix SaaS Subscription Agreement.txt")
    r = _ask(client, "Who are the parties to the Helix agreement?")
    assert {c["documentId"] for c in r["citations"]} == {helix["id"]}
    # The clause that names the parties never uses the word "parties" — the concept boost finds it.
    assert "between Helix Cloud Software" in r["citations"][0]["quote"]


def test_filler_words_do_not_block_answers(client: TestClient, files: dict[str, bytes]) -> None:
    upload(client, ("Acme MSA.pdf", files["contract_pdf"]))
    r = _ask(client, "How long do I have to pay an invoice?")
    assert "refusal" not in r["events"]
    assert "undisputed invoices" in " ".join(r["citations"][0]["quote"].split())


def test_off_topic_still_refused(client: TestClient, files: dict[str, bytes]) -> None:
    upload(client, ("Acme MSA.pdf", files["contract_pdf"]))
    for q in ("What is the capital of France?", "What does it say about cryptocurrency mining rigs?"):
        assert "refusal" in _ask(client, q)["events"], q
