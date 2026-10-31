"""Span ids and their resolution (FR-11, FR-13).

A span id encodes its own location — ``{documentId}~p{page}~{charStart}-{charEnd}`` — the same
format the frontend mock uses. Resolving one is a slice of stored page text, so a span can never
point at text that does not exist.
"""

import re
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.db.models import Document, DocumentPage
from app.schemas.models import Citation, Span

_SPAN = re.compile(r"^(.+)~p(\d+)~(\d+)-(\d+)$")


@dataclass(frozen=True, slots=True)
class SpanRef:
    document_id: str
    page: int
    start: int
    end: int


def make_span_id(document_id: str, page: int, start: int, end: int) -> str:
    return f"{document_id}~p{page}~{start}-{end}"


def parse_span_id(span_id: str) -> SpanRef | None:
    m = _SPAN.match(span_id)
    if not m:
        return None
    ref = SpanRef(m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)))
    return ref if ref.start < ref.end else None


async def resolve(db: AsyncSession, span_id: str) -> Span:
    ref = parse_span_id(span_id)
    if ref is None:
        raise not_found("Source passage")
    doc = await db.get(Document, ref.document_id)
    page = await db.get(DocumentPage, (ref.document_id, ref.page)) if doc else None
    if doc is None or page is None or doc.status != "ready" or ref.end > len(page.text):
        raise not_found("Source passage")
    return Span(
        span_id=span_id,
        document_id=doc.id,
        document_name=doc.name,
        page=ref.page,
        char_start=ref.start,
        char_end=ref.end,
        text=page.text[ref.start : ref.end],
    )


class CitationGuard:
    """Checks every citation against stored page text before it is streamed or saved.

    This enforces at the API boundary the contract the AI layer's verification gate will also
    guarantee (FR-21): a citation that does not resolve exactly is dropped, never shown.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._pages: dict[tuple[str, int], str | None] = {}

    async def _page_text(self, doc_id: str, page: int) -> str | None:
        key = (doc_id, page)
        if key not in self._pages:
            doc = await self.db.get(Document, doc_id)
            row = await self.db.get(DocumentPage, key) if doc and doc.status == "ready" else None
            self._pages[key] = row.text if row else None
        return self._pages[key]

    async def check(self, c: Citation) -> bool:
        ref = parse_span_id(c.span_id)
        if ref is None or (ref.document_id, ref.page, ref.start, ref.end) != (
            c.document_id,
            c.page,
            c.char_start,
            c.char_end,
        ):
            return False
        text = await self._page_text(c.document_id, c.page)
        return text is not None and c.char_end <= len(text) and text[c.char_start : c.char_end] == c.quote
