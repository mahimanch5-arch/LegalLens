"""Document library: upload, listing, pages, type override and hard delete (FR-1 … FR-7, FR-26)."""

import asyncio
import hashlib
import logging
from collections import defaultdict

from fastapi import UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.core.ids import iso, new_id
from app.db.models import ChunkMeta, Conversation, Document, DocumentPage, IngestionJob
from app.ingestion import search_index, validate
from app.ingestion.blob_store import BlobStore
from app.runtime import Runtime
from app.schemas.models import DocumentPage as DocumentPageOut
from app.schemas.models import DocumentStatus, LegalDocument, RejectedUpload, UploadResult
from app.services import audit
from app.services.scenario import scenario

log = logging.getLogger("legallens.documents")

_READ_CHUNK = 1024 * 1024


# ---------- read ----------


async def low_ocr_map(db: AsyncSession, doc_ids: list[str]) -> dict[str, list[int]]:
    if not doc_ids:
        return {}
    rows = await db.execute(
        select(DocumentPage.document_id, DocumentPage.page_no)
        .where(DocumentPage.document_id.in_(doc_ids), DocumentPage.low_ocr.is_(True))
        .order_by(DocumentPage.page_no)
    )
    out: dict[str, list[int]] = defaultdict(list)
    for doc_id, page_no in rows:
        out[doc_id].append(page_no)
    return out


def to_out(doc: Document, low_ocr_pages: list[int] | None = None) -> LegalDocument:
    return LegalDocument(
        id=doc.id,
        name=doc.name,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        pages=doc.pages,
        type=doc.type,
        type_confidence=doc.type_confidence,
        type_overridden=doc.type_overridden,
        status=doc.status,
        progress=doc.progress,
        error=doc.error,
        low_ocr_pages=low_ocr_pages or [],
        uploaded_at=iso(doc.uploaded_at),
    )


async def list_documents(db: AsyncSession, offset: int, limit: int) -> tuple[list[LegalDocument], int]:
    total = (await db.execute(select(func.count()).select_from(Document))).scalar_one()
    docs = (
        (
            await db.execute(
                select(Document)
                .order_by(Document.uploaded_at.desc(), Document.id)
                .offset(offset)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    low = await low_ocr_map(db, [d.id for d in docs])
    return [to_out(d, low.get(d.id)) for d in docs], total


async def get_document(db: AsyncSession, doc_id: str) -> Document:
    doc = await db.get(Document, doc_id)
    if doc is None:
        raise not_found("Document")
    return doc


async def document_out(db: AsyncSession, doc: Document) -> LegalDocument:
    return to_out(doc, (await low_ocr_map(db, [doc.id])).get(doc.id))


def status_out(doc: Document) -> DocumentStatus:
    return DocumentStatus(status=doc.status, progress=doc.progress, error=doc.error)


async def get_page(db: AsyncSession, doc_id: str, n: int) -> DocumentPageOut:
    doc = await db.get(Document, doc_id)
    if doc is None or doc.status != "ready" or not doc.pages or not 1 <= n <= doc.pages:
        raise not_found("Page")
    page = await db.get(DocumentPage, (doc_id, n))
    if page is None:
        raise not_found("Page")
    return DocumentPageOut(
        document_id=doc_id, page=n, text=page.text, ocr_confidence=page.ocr_confidence, low_ocr=page.low_ocr
    )


async def ready_documents(db: AsyncSession, ids: list[str] | None = None) -> list[Document]:
    """Only ready documents are ever retrievable (FR-7)."""
    stmt = select(Document).where(Document.status == "ready").order_by(Document.uploaded_at)
    if ids is not None:
        stmt = stmt.where(Document.id.in_(ids))
    return list((await db.execute(stmt)).scalars().all())


# ---------- upload ----------


async def _read_upload(file: UploadFile, limit: int) -> tuple[bytes, int, str]:
    """Reads in chunks, stopping as soon as the size limit is crossed."""
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(_READ_CHUNK):
        size += len(chunk)
        if size > limit:
            # Keep counting so the message can state the actual size (FR-2), but stop buffering.
            while more := await file.read(_READ_CHUNK):
                size += len(more)
            return b"", size, ""
        digest.update(chunk)
        chunks.append(chunk)
    return b"".join(chunks), size, digest.hexdigest()


async def upload(db: AsyncSession, rt: Runtime, user_id: str, files: list[UploadFile]) -> UploadResult:
    settings = rt.settings
    created: list[Document] = []
    rejected: list[RejectedUpload] = []
    job_ids: list[str] = []

    active = (
        await db.execute(select(func.count()).select_from(Document).where(Document.status != "failed"))
    ).scalar_one()

    for file in files:
        name = validate.safe_name(file.filename)
        try:
            mime = validate.check_extension(name)
            data, size, sha = await _read_upload(file, settings.max_upload_bytes)
            validate.check_size(size, settings.max_upload_bytes)
            validate.check_content(mime, data)
            dupe = (
                await db.execute(
                    select(Document.name).where(Document.sha256 == sha, Document.status != "failed").limit(1)
                )
            ).scalar_one_or_none()
            if dupe is None:
                dupe = next((d.name for d in created if d.sha256 == sha), None)
            if dupe is not None:
                raise validate.Rejected(f"This file is already in your library as “{dupe}”.")
            if active + len(created) >= settings.max_documents:
                raise validate.Rejected(
                    f"Your workspace holds the maximum of {settings.max_documents} documents. "
                    "Delete a document to make room."
                )
        except validate.Rejected as exc:
            rejected.append(RejectedUpload(name=name, reason=str(exc)))
            continue
        finally:
            await file.close()

        doc_id = new_id("doc")
        blob = await asyncio.to_thread(rt.blobs.put, doc_id, data)
        doc = Document(
            id=doc_id,
            name=name,
            mime_type=mime,
            size_bytes=size,
            sha256=sha,
            blob_path=blob,
            status="queued",
            progress=0,
        )
        job = IngestionJob(
            id=new_id("job"), document_id=doc_id, simulate_failure=scenario.consume_upload_failure()
        )
        db.add_all([doc, job])
        created.append(doc)
        job_ids.append(job.id)
        audit.record(db, "document.upload", "document", doc_id, user_id, size_bytes=size, mime_type=mime)

    for r in rejected:
        audit.record(db, "document.upload_rejected", "document", None, user_id, reason=r.reason)
    await db.commit()

    for job_id in job_ids:
        rt.queue.enqueue(job_id)
    # Newest first, matching the list order.
    return UploadResult(created=[to_out(d) for d in reversed(created)], rejected=rejected)


# ---------- update ----------


async def set_type(db: AsyncSession, user_id: str, doc_id: str, doc_type: str) -> LegalDocument:
    doc = await get_document(db, doc_id)
    doc.type = doc_type
    doc.type_overridden = True
    audit.record(db, "document.type_override", "document", doc_id, user_id, type=doc_type)
    await db.commit()
    return await document_out(db, doc)


# ---------- hard delete (FR-26, TS-6) ----------


async def _purge(db: AsyncSession, doc_ids: list[str]) -> None:
    for doc_id in doc_ids:
        await search_index.remove_document(db, doc_id)
    await db.execute(delete(DocumentPage).where(DocumentPage.document_id.in_(doc_ids)))
    await db.execute(delete(ChunkMeta).where(ChunkMeta.document_id.in_(doc_ids)))
    await db.execute(delete(IngestionJob).where(IngestionJob.document_id.in_(doc_ids)))
    await db.execute(delete(Document).where(Document.id.in_(doc_ids)))


_BLOB_DELETE_ATTEMPTS = 20


async def _remove_blobs(blobs: BlobStore, names: list[str]) -> None:
    """Removes the encrypted files after the DB rows are gone.

    On Windows a file cannot be deleted while another thread has it open — e.g. the ingestion worker
    reading a document the attorney just deleted. That is a moment, not a failure: retry briefly. If a
    file is still locked after that, finish in the background rather than fail a delete that has
    already taken effect for retrieval."""
    for name in names:
        if not await _delete_with_retry(blobs, name, _BLOB_DELETE_ATTEMPTS):
            log.warning("blob %s still locked; finishing deletion in the background", name)
            _pending_deletes.add(asyncio.create_task(_delete_with_retry(blobs, name, 600)))


_pending_deletes: set[asyncio.Task[bool]] = set()


async def _delete_with_retry(blobs: BlobStore, name: str, attempts: int) -> bool:
    for i in range(attempts):
        try:
            await asyncio.to_thread(blobs.delete, name)
            return True
        except PermissionError:
            await asyncio.sleep(min(0.05 * (i + 1), 1.0))
    log.error("blob %s could not be deleted", name)
    return False


async def delete_document(db: AsyncSession, rt: Runtime, user_id: str, doc_id: str) -> None:
    doc = await get_document(db, doc_id)
    blob = doc.blob_path
    await _purge(db, [doc_id])
    audit.record(db, "document.delete", "document", doc_id, user_id)  # tombstone: id only
    await db.commit()
    if blob:
        await _remove_blobs(rt.blobs, [blob])


async def delete_workspace(db: AsyncSession, rt: Runtime, user_id: str) -> None:
    """Every document and its derived data, plus every conversation (they quote the documents)."""
    docs = (await db.execute(select(Document.id, Document.blob_path))).all()
    ids = [d.id for d in docs]
    if ids:
        await _purge(db, ids)
    convs = (await db.execute(delete(Conversation).where(Conversation.user_id == user_id))).rowcount  # type: ignore[attr-defined]
    audit.record(db, "workspace.delete", "workspace", None, user_id, documents=len(ids), conversations=convs)
    await db.commit()
    await _remove_blobs(rt.blobs, [d.blob_path for d in docs if d.blob_path])
