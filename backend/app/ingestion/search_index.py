"""SQLite FTS5 page index — the stub orchestrator's retrieval. Replaced by Qdrant later."""

import re
from dataclasses import dataclass

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-]*")


@dataclass(slots=True)
class PageHit:
    document_id: str
    page_no: int
    text: str
    score: float  # higher is better


async def add_pages(db: AsyncSession, document_id: str, pages: list[tuple[int, str]]) -> None:
    if not pages:
        return
    await db.execute(
        text("INSERT INTO page_fts (text, document_id, page_no) VALUES (:text, :doc, :page)"),
        [{"text": t, "doc": document_id, "page": n} for n, t in pages],
    )


async def remove_document(db: AsyncSession, document_id: str) -> None:
    await db.execute(text("DELETE FROM page_fts WHERE document_id = :doc"), {"doc": document_id})


def fts_query(terms: list[str]) -> str:
    """OR of quoted terms — quoting neutralises FTS5 syntax in user input."""
    return " OR ".join('"' + t.replace('"', "") + '"' for t in terms)


async def search_pages(
    db: AsyncSession, terms: list[str], document_ids: list[str], limit: int = 20
) -> list[PageHit]:
    if not terms or not document_ids:
        return []
    stmt = text(
        "SELECT document_id, page_no, text, -bm25(page_fts) AS score FROM page_fts "
        "WHERE page_fts MATCH :q AND document_id IN :docs ORDER BY bm25(page_fts) LIMIT :limit"
    ).bindparams(bindparam("docs", expanding=True))
    rows = await db.execute(stmt, {"q": fts_query(terms), "docs": document_ids, "limit": limit})
    return [PageHit(r.document_id, int(r.page_no), r.text, float(r.score)) for r in rows]


async def count_rows(db: AsyncSession, document_id: str) -> int:
    row = await db.execute(
        text("SELECT count(*) FROM page_fts WHERE document_id = :doc"), {"doc": document_id}
    )
    return int(row.scalar_one())
