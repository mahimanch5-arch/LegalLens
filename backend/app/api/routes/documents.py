import asyncio
from urllib.parse import quote

from fastapi import APIRouter, File, Response, UploadFile, status

from app.api.deps import DB, CurrentUser, rate_limit
from app.api.pagination import clamp_limit, next_cursor, parse_cursor
from app.core.errors import bad_request, not_found
from app.runtime import RuntimeDep
from app.schemas.common import Page
from app.schemas.models import (
    DocumentPage,
    DocumentStatus,
    LegalDocument,
    UpdateDocumentRequest,
    UploadResult,
)
from app.services import documents as svc

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILES_PER_UPLOAD = 50


@router.get("", response_model=Page[LegalDocument])
async def list_documents(
    db: DB, _user: CurrentUser, cursor: str | None = None, limit: int | None = None
) -> Page[LegalDocument]:
    offset, size = parse_cursor(cursor), clamp_limit(limit)
    items, total = await svc.list_documents(db, offset, size)
    return Page(items=items, next_cursor=next_cursor(offset, size, total))


@router.post(
    "",
    response_model=UploadResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[rate_limit("upload", "rate_upload_per_minute")],
)
async def upload(
    db: DB, rt: RuntimeDep, user: CurrentUser, files: list[UploadFile] = File(...)
) -> UploadResult:
    """Multipart upload, field ``files`` repeated. One bad file never rejects the batch (FR-3)."""
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise bad_request(f"Upload at most {MAX_FILES_PER_UPLOAD} files at a time.")
    return await svc.upload(db, rt, user.id, files)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(db: DB, rt: RuntimeDep, user: CurrentUser) -> Response:
    """Hard-deletes every document, its derived data, and every conversation (FR-26)."""
    await svc.delete_workspace(db, rt, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{document_id}", response_model=LegalDocument)
async def get_document(document_id: str, db: DB, _user: CurrentUser) -> LegalDocument:
    return await svc.document_out(db, await svc.get_document(db, document_id))


@router.get("/{document_id}/status", response_model=DocumentStatus)
async def get_status(document_id: str, db: DB, _user: CurrentUser) -> DocumentStatus:
    return svc.status_out(await svc.get_document(db, document_id))


@router.get("/{document_id}/pages/{n}", response_model=DocumentPage)
async def get_page(document_id: str, n: int, db: DB, _user: CurrentUser) -> DocumentPage:
    return await svc.get_page(db, document_id, n)


@router.get("/{document_id}/file", response_class=Response)
async def get_file(document_id: str, db: DB, rt: RuntimeDep, _user: CurrentUser) -> Response:
    """The original upload, decrypted — for the pdf.js viewer later."""
    doc = await svc.get_document(db, document_id)
    if not doc.blob_path or not rt.blobs.exists(doc.blob_path):
        raise not_found("File")
    data = await asyncio.to_thread(rt.blobs.get, doc.blob_path)
    return Response(
        data,
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(doc.name)}",
            "Cache-Control": "private, no-store",
        },
    )


@router.patch("/{document_id}", response_model=LegalDocument)
async def set_type(document_id: str, body: UpdateDocumentRequest, db: DB, user: CurrentUser) -> LegalDocument:
    return await svc.set_type(db, user.id, document_id, body.type)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, db: DB, rt: RuntimeDep, user: CurrentUser) -> Response:
    await svc.delete_document(db, rt, user.id, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
