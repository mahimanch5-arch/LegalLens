import re

from app.ingestion.parsers.base import PageSource, paginate, static_source


def decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def open_txt(data: bytes) -> PageSource:
    text = decode_text(data).replace("\r\n", "\n")
    pages: list[str] = []
    for section in text.split("\f"):  # form feed = explicit page break
        pages.extend(paginate(re.split(r"\n\s*\n", section)))
    pages = [p for p in pages if p.strip()] or [""]
    return static_source(pages, "plaintext")
