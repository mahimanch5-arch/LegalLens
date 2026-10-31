import io
import zipfile

from docx import Document as load_docx
from docx.oxml.ns import qn

from app.ingestion.parsers.base import PageSource, ParseFailure, paginate, static_source
from app.ingestion.parsers.pdf import DAMAGED

_PAGE_BREAK = "\f"


def _paragraph_text(p_el: object) -> str:
    """Text of a <w:p>, with explicit page breaks kept as form feeds."""
    parts: list[str] = []
    for node in p_el.iter():  # type: ignore[attr-defined]
        if node.tag == qn("w:t"):
            parts.append(node.text or "")
        elif node.tag == qn("w:tab"):
            parts.append("\t")
        elif node.tag == qn("w:br"):
            parts.append(_PAGE_BREAK if node.get(qn("w:type")) == "page" else "\n")
    return "".join(parts)


def open_docx(data: bytes) -> PageSource:
    try:
        doc = load_docx(io.BytesIO(data))
    except (zipfile.BadZipFile, KeyError, ValueError) as exc:
        raise ParseFailure(DAMAGED) from exc

    blocks: list[str] = []
    for el in doc.element.body.iterchildren():
        if el.tag == qn("w:p"):
            blocks.append(_paragraph_text(el))
        elif el.tag == qn("w:tbl"):
            for row in el.iter(qn("w:tr")):
                cells = [
                    " ".join(_paragraph_text(p) for p in tc.iter(qn("w:p"))) for tc in row.iter(qn("w:tc"))
                ]
                blocks.append(" | ".join(c.strip() for c in cells))

    # Split on explicit page breaks first, then size-paginate each section.
    pages: list[str] = []
    section: list[str] = []
    for block in blocks:
        pieces = block.split(_PAGE_BREAK)
        section.append(pieces[0])
        for piece in pieces[1:]:
            pages.extend(paginate(section))
            section = [piece]
    pages.extend(paginate(section))
    pages = [p for p in pages if p.strip()] or [""]
    return static_source(pages, "python-docx")
