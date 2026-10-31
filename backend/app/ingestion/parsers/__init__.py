from app.ingestion.parsers.base import PageSource, ParsedPage, ParseFailure
from app.ingestion.parsers.docx import open_docx
from app.ingestion.parsers.pdf import open_pdf
from app.ingestion.parsers.txt import open_txt

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TXT_MIME = "text/plain"


def open_document(data: bytes, mime_type: str) -> PageSource:
    if mime_type == PDF_MIME:
        return open_pdf(data)
    if mime_type == DOCX_MIME:
        return open_docx(data)
    return open_txt(data)


__all__ = ["DOCX_MIME", "PDF_MIME", "TXT_MIME", "PageSource", "ParseFailure", "ParsedPage", "open_document"]
