from fastapi.testclient import TestClient

from tests.conftest import doc_by_name, upload, wait_idle


def test_batch_upload_one_failure_does_not_block_others(client: TestClient, files: dict[str, bytes]) -> None:
    res = upload(
        client,
        ("Acme MSA.pdf", files["contract_pdf"]),
        ("Smith v Jones opinion.docx", files["opinion_docx"]),
        ("Reyes complaint.txt", files["complaint_txt"]),
        ("Board minutes.pdf", files["encrypted_pdf"]),
        ("malware.exe", b"MZ\x90\x00"),
    )
    assert [d["name"] for d in res["created"]] == [
        "Board minutes.pdf",
        "Reyes complaint.txt",
        "Smith v Jones opinion.docx",
        "Acme MSA.pdf",
    ]
    assert all(d["status"] == "queued" and d["pages"] is None for d in res["created"])
    assert res["rejected"] == [
        {"name": "malware.exe", "reason": ".exe is not supported. Upload PDF, DOCX or TXT."}
    ]

    acme = doc_by_name(client, "Acme MSA.pdf")
    assert acme["status"] == "ready" and acme["progress"] == 100 and acme["pages"] == 3
    assert acme["type"] == "contract" and acme["typeConfidence"] > 0.6
    assert acme["mimeType"] == "application/pdf"
    assert "error" not in acme

    opinion = doc_by_name(client, "Smith v Jones opinion.docx")
    assert opinion["status"] == "ready" and opinion["type"] == "opinion"

    complaint = doc_by_name(client, "Reyes complaint.txt")
    assert complaint["status"] == "ready" and complaint["type"] == "pleading"

    minutes = doc_by_name(client, "Board minutes.pdf")
    assert minutes["status"] == "failed" and minutes["pages"] is None
    assert minutes["error"] == "This PDF is password-protected. Remove the password, then upload it again."


def test_size_limit_names_the_actual_size(client: TestClient) -> None:
    res = upload(client, ("huge.txt", b"a " * 150_000), wait=False)
    assert res["created"] == []
    assert res["rejected"][0]["reason"] == "File is 0.3 MB; the limit is 0.2 MB."  # test limit is 200 KB


def test_extension_must_match_content(client: TestClient) -> None:
    res = upload(client, ("fake.pdf", b"just some text"), ("fake.docx", b"not a zip"), wait=False)
    reasons = [r["reason"] for r in res["rejected"]]
    assert "not a PDF" in reasons[0] and ".docx" in reasons[1]


def test_duplicate_upload_rejected(client: TestClient, files: dict[str, bytes]) -> None:
    upload(client, ("Acme MSA.pdf", files["contract_pdf"]))
    res = upload(client, ("Acme copy.pdf", files["contract_pdf"]), wait=False)
    assert res["created"] == []
    assert "already in your library as “Acme MSA.pdf”" in res["rejected"][0]["reason"]


def test_pages_status_and_file(client: TestClient, files: dict[str, bytes]) -> None:
    upload(client, ("Acme MSA.pdf", files["contract_pdf"]))
    doc = doc_by_name(client, "Acme MSA.pdf")

    page = client.get(f"/api/documents/{doc['id']}/pages/2").json()
    assert set(page) == {"documentId", "page", "text", "ocrConfidence", "lowOcr"}
    assert "may terminate this Agreement for convenience" in " ".join(page["text"].split())
    assert page["lowOcr"] is False

    assert client.get(f"/api/documents/{doc['id']}/pages/4").status_code == 404
    assert client.get(f"/api/documents/{doc['id']}/pages/0").status_code == 404
    assert client.get(f"/api/documents/{doc['id']}/status").json() == {"status": "ready", "progress": 100}
    assert client.get(f"/api/documents/{doc['id']}").json()["id"] == doc["id"]

    r = client.get(f"/api/documents/{doc['id']}/file")
    assert r.status_code == 200 and r.content == files["contract_pdf"]
    assert r.headers["content-type"] == "application/pdf"


def test_low_text_pages_flagged_and_scans_fail(client: TestClient, files: dict[str, bytes]) -> None:
    upload(client, ("mixed.pdf", files["mixed_pdf"]), ("scan.pdf", files["blank_pdf"]))
    mixed = doc_by_name(client, "mixed.pdf")
    assert mixed["status"] == "ready" and mixed["lowOcrPages"] == [2]
    p2 = client.get(f"/api/documents/{mixed['id']}/pages/2").json()
    assert p2["lowOcr"] is True and p2["ocrConfidence"] == 0.0

    scan = doc_by_name(client, "scan.pdf")
    assert scan["status"] == "failed" and "OCR" in scan["error"]


def test_type_override(client: TestClient, files: dict[str, bytes]) -> None:
    upload(client, ("Reyes complaint.txt", files["complaint_txt"]))
    doc = doc_by_name(client, "Reyes complaint.txt")
    r = client.patch(f"/api/documents/{doc['id']}", json={"type": "other"})
    assert r.status_code == 200
    assert r.json()["type"] == "other" and r.json()["typeOverridden"] is True
    assert client.patch(f"/api/documents/{doc['id']}", json={"type": "memo"}).status_code == 422


def test_unknown_document_404(client: TestClient) -> None:
    r = client.get("/api/documents/doc_nope")
    assert r.status_code == 404 and r.json()["code"] == "unknown"
    assert client.delete("/api/documents/doc_nope").status_code == 404


def test_dev_scenario_forces_upload_failure(client: TestClient, files: dict[str, bytes]) -> None:
    client.put("/api/dev/scenario", json={"nextUploadFails": True})
    upload(client, ("a.txt", files["complaint_txt"]))
    assert doc_by_name(client, "a.txt")["status"] == "failed"
    assert client.get("/api/dev/scenario").json()["nextUploadFails"] is False


def test_pagination(client: TestClient) -> None:
    upload(
        client,
        *[(f"note{i}.txt", f"Note number {i} about the lease renewal terms.".encode()) for i in range(5)],
    )
    wait_idle(client)
    first = client.get("/api/documents?limit=2").json()
    assert len(first["items"]) == 2 and first["nextCursor"] == "2"
    last = client.get("/api/documents?limit=2&cursor=4").json()
    assert len(last["items"]) == 1 and last["nextCursor"] is None
    assert client.get("/api/documents?cursor=abc").status_code == 422
