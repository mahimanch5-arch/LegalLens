"""Ingestion worker: queued → parsing → indexing → ready | failed (FR-3).

``InProcessQueue`` runs jobs on asyncio tasks inside the API process, reading a DB-backed job
table so work survives a restart. It sits behind the ``JobQueue`` protocol, so Celery + Redis
(the diagram's target) can replace it without touching the routes.
"""

import asyncio
import logging
from typing import Any, Protocol

from sqlalchemy import select, update

from app.core.config import Settings
from app.core.ids import utcnow
from app.db.models import Document, DocumentPage, IngestionJob
from app.db.session import sessionmaker
from app.ingestion import search_index
from app.ingestion.blob_store import BlobStore
from app.ingestion.classify import classify
from app.ingestion.parsers import ParsedPage, ParseFailure, open_document
from app.ingestion.parsers.pdf import PASSWORD_PROTECTED

log = logging.getLogger("legallens.ingestion")

MAX_ATTEMPTS = 3
GENERIC_FAILURE = (
    "Something went wrong while processing this file. Delete it and upload it again; if it keeps "
    "failing, re-export it from the original application."
)


class JobQueue(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    def enqueue(self, job_id: str) -> None: ...
    async def wait_idle(self, timeout: float = 30.0) -> None: ...
    @property
    def alive(self) -> bool: ...


class _Gone(Exception):
    """The document was deleted while it was being processed."""


class InProcessQueue:
    def __init__(self, settings: Settings, blobs: BlobStore) -> None:
        self.settings = settings
        self.blobs = blobs
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._tasks: list[asyncio.Task[None]] = []
        self._pending = 0
        self._idle = asyncio.Event()
        self._idle.set()

    @property
    def alive(self) -> bool:
        return bool(self._tasks) and all(not t.done() for t in self._tasks)

    async def start(self) -> None:
        # Resume anything a previous process left behind.
        async with sessionmaker()() as db:
            await db.execute(
                update(IngestionJob).where(IngestionJob.state == "running").values(state="queued")
            )
            await db.commit()
            ids = (
                await db.execute(
                    select(IngestionJob.id)
                    .where(IngestionJob.state == "queued")
                    .order_by(IngestionJob.queued_at)
                )
            ).scalars()
            for job_id in ids:
                self.enqueue(job_id)
        self._tasks = [
            asyncio.create_task(self._run(), name=f"ingest-worker-{i}")
            for i in range(self.settings.worker_concurrency)
        ]

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []

    def enqueue(self, job_id: str) -> None:
        self._pending += 1
        self._idle.clear()
        self._queue.put_nowait(job_id)

    async def wait_idle(self, timeout: float = 30.0) -> None:
        await asyncio.wait_for(self._idle.wait(), timeout)

    async def _run(self) -> None:
        while True:
            job_id = await self._queue.get()
            try:
                await self._process(job_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("ingestion job %s crashed", job_id)
            finally:
                self._pending -= 1
                if self._pending == 0:
                    self._idle.set()

    # ---------- one job ----------

    async def _process(self, job_id: str) -> None:
        async with sessionmaker()() as db:
            job = await db.get(IngestionJob, job_id)
            doc = await db.get(Document, job.document_id) if job else None
            if job is None or doc is None or job.state in ("done", "failed"):
                return
            job.state = "running"
            job.attempts += 1
            job.started_at = utcnow()
            doc.status, doc.progress, doc.error = "parsing", 0, None
            await db.commit()
            doc_id, name, mime, blob = doc.id, doc.name, doc.mime_type, doc.blob_path
            simulate_failure, attempts = job.simulate_failure, job.attempts

        log.info("ingest start doc=%s attempt=%d", doc_id, attempts)
        try:
            await self._pause()
            if simulate_failure:
                raise ParseFailure(PASSWORD_PROTECTED)
            if not blob:
                raise ParseFailure(GENERIC_FAILURE)
            data = await asyncio.to_thread(self.blobs.get, blob)
            source = await asyncio.to_thread(open_document, data, mime)
            if source.count > self.settings.max_pages:
                raise ParseFailure(
                    f"This document has {source.count} pages; the limit is {self.settings.max_pages}. "
                    "Split it into smaller files and upload them separately."
                )

            pages: list[ParsedPage] = []
            last_reported = 0
            for i in range(source.count):
                pages.append(await asyncio.to_thread(source.get, i))
                pct = int((i + 1) * 100 / source.count)
                if pct - last_reported >= 5 or i + 1 == source.count:
                    last_reported = pct
                    await self._set(doc_id, progress=pct)
                    await self._pause(0.1)

            if all(p.low_ocr for p in pages):
                raise ParseFailure(
                    "No readable text was found — this looks like a scanned document, and OCR is not "
                    "available yet. Upload a version with a text layer (for example, run OCR in Acrobat)."
                )

            await self._set(doc_id, status="indexing", progress=0, pages=len(pages))
            await self._pause()
            await self._index(doc_id, name, source.engine, pages)
            await self._finish_job(job_id, "done")
            log.info("ingest ready doc=%s pages=%d", doc_id, len(pages))
        except _Gone:
            log.info("ingest abandoned doc=%s (deleted)", doc_id)
        except ParseFailure as exc:
            await self._fail(job_id, doc_id, str(exc))
        except Exception as exc:
            log.warning("ingest error doc=%s attempt=%d: %s", doc_id, attempts, type(exc).__name__)
            if attempts < MAX_ATTEMPTS:
                await self._requeue(job_id, doc_id, type(exc).__name__, delay=2.0 * attempts)
            else:
                await self._fail(job_id, doc_id, GENERIC_FAILURE)

    async def _index(self, doc_id: str, name: str, engine: str, pages: list[ParsedPage]) -> None:
        async with sessionmaker()() as db:
            doc = await db.get(Document, doc_id)
            if doc is None:
                raise _Gone
            if not doc.type_overridden:
                opening = "\n".join(p.text for p in pages[:3])
                doc.type, doc.type_confidence = classify(name, opening)
            db.add_all(
                DocumentPage(
                    document_id=doc_id,
                    page_no=n,
                    text=p.text,
                    ocr_confidence=p.ocr_confidence,
                    low_ocr=p.low_ocr,
                    char_count=len(p.text),
                )
                for n, p in enumerate(pages, start=1)
            )
            # Low-OCR pages are kept for the viewer but not indexed for retrieval.
            await search_index.add_pages(
                db, doc_id, [(n, p.text) for n, p in enumerate(pages, 1) if not p.low_ocr]
            )
            doc.pages = len(pages)
            doc.parse_engine = engine
            doc.status, doc.progress, doc.ready_at = "ready", 100, utcnow()  # now retrievable (FR-7)
            await db.commit()

    async def _set(self, doc_id: str, **fields: Any) -> None:
        async with sessionmaker()() as db:
            result = await db.execute(update(Document).where(Document.id == doc_id).values(**fields))
            await db.commit()
            if result.rowcount == 0:  # type: ignore[attr-defined]
                raise _Gone

    async def _fail(self, job_id: str, doc_id: str, message: str) -> None:
        log.info("ingest failed doc=%s", doc_id)
        async with sessionmaker()() as db:
            await db.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(status="failed", progress=0, error=message, pages=None)
            )
            await db.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job_id)
                .values(state="failed", last_error=message, finished_at=utcnow())
            )
            await db.commit()

    async def _finish_job(self, job_id: str, state: str) -> None:
        async with sessionmaker()() as db:
            await db.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job_id)
                .values(state=state, finished_at=utcnow())
            )
            await db.commit()

    async def _requeue(self, job_id: str, doc_id: str, error: str, delay: float) -> None:
        async with sessionmaker()() as db:
            await db.execute(
                update(IngestionJob).where(IngestionJob.id == job_id).values(state="queued", last_error=error)
            )
            await db.execute(
                update(Document).where(Document.id == doc_id).values(status="queued", progress=0)
            )
            await db.commit()
        await asyncio.sleep(delay)
        self.enqueue(job_id)

    async def _pause(self, fraction: float = 1.0) -> None:
        if self.settings.ingest_stage_delay_ms > 0:
            await asyncio.sleep(self.settings.ingest_stage_delay_ms * fraction / 1000)
