import re
from collections.abc import Callable
from dataclasses import dataclass

# A page with less extractable text than this is treated as unreadable (likely a scan).
MIN_TEXT_CHARS = 40
# DOCX and TXT have no physical pages; text is split into pages of about this size.
VIRTUAL_PAGE_CHARS = 3000


class ParseFailure(Exception):
    """A parse error whose message is shown to the attorney and names the next action (FR-28)."""


@dataclass(slots=True)
class ParsedPage:
    text: str
    ocr_confidence: float
    low_ocr: bool


@dataclass(slots=True)
class PageSource:
    """Pages are produced one at a time so the worker can report progress while parsing."""

    count: int
    engine: str
    get: Callable[[int], ParsedPage]  # 0-based index


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def page_from_text(text: str) -> ParsedPage:
    text = normalize(text)
    readable = len(re.sub(r"\s", "", text)) >= MIN_TEXT_CHARS
    return ParsedPage(text=text, ocr_confidence=1.0 if readable else 0.0, low_ocr=not readable)


def paginate(paragraphs: list[str], size: int = VIRTUAL_PAGE_CHARS) -> list[str]:
    """Groups paragraphs into pages of roughly ``size`` characters, never splitting a paragraph
    unless it alone is longer than a page."""
    pages: list[str] = []
    current: list[str] = []
    length = 0
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        while len(para) > size:
            if current:
                pages.append("\n\n".join(current))
                current, length = [], 0
            cut = para.rfind(" ", 0, size)
            cut = cut if cut > size // 2 else size
            pages.append(para[:cut].strip())
            para = para[cut:].strip()
        if current and length + len(para) > size:
            pages.append("\n\n".join(current))
            current, length = [], 0
        current.append(para)
        length += len(para) + 2
    if current:
        pages.append("\n\n".join(current))
    return pages or [""]


def static_source(pages: list[str], engine: str) -> PageSource:
    parsed = [page_from_text(p) for p in pages]
    return PageSource(count=len(parsed), engine=engine, get=lambda i: parsed[i])
