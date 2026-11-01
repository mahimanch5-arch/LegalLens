import io
import logging

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

from app.ingestion.parsers.base import PageSource, ParsedPage, ParseFailure, page_from_text

log = logging.getLogger("legallens.ingestion")

PASSWORD_PROTECTED = "This PDF is password-protected. Remove the password, then upload it again."
DAMAGED = (
    "The file couldn't be read — it may be damaged. Re-export it from the original application "
    "and upload again."
)


def open_pdf(data: bytes) -> PageSource:
    """Reads the PDF's text layer page by page. Layout-aware parsing and OCR are deferred to the
    ingestion lane of the AI layer; pages with no usable text layer are flagged instead (DR-1)."""
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            # Owner-password-only PDFs open with an empty user password; anything else cannot.
            try:
                if not reader.decrypt(""):
                    raise ParseFailure(PASSWORD_PROTECTED)
            except (FileNotDecryptedError, NotImplementedError) as exc:
                raise ParseFailure(PASSWORD_PROTECTED) from exc
        count = len(reader.pages)
    except ParseFailure:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, OSError) as exc:
        raise ParseFailure(DAMAGED) from exc

    def get(i: int) -> ParsedPage:
        try:
            text = reader.pages[i].extract_text() or ""
        except Exception:  # one unreadable page must not fail the document
            log.warning("text extraction failed on page %d", i + 1)
            text = ""
        return page_from_text(text)

    return PageSource(count=count, engine="pypdf-textlayer", get=get)
