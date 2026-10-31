"""Upload checks that run before anything is stored (FR-1, FR-2)."""

import io
import zipfile
from pathlib import PurePath

from app.ingestion.parsers import DOCX_MIME, PDF_MIME, TXT_MIME

EXT_MIME = {".pdf": PDF_MIME, ".docx": DOCX_MIME, ".txt": TXT_MIME}


class Rejected(Exception):
    pass


def human_mb(n: int) -> str:
    return f"{n / 1048576:.1f} MB"


def safe_name(filename: str | None) -> str:
    name = PurePath((filename or "").replace("\\", "/")).name.strip()
    name = "".join(ch for ch in name if ch.isprintable())
    return name[:255] or "Untitled"


def check_extension(name: str) -> str:
    """Returns the MIME type for an accepted extension, or raises ``Rejected``."""
    ext = PurePath(name).suffix.lower()
    if ext not in EXT_MIME:
        label = ext or "This file type"
        raise Rejected(f"{label} is not supported. Upload PDF, DOCX or TXT.")
    return EXT_MIME[ext]


def check_size(size: int, limit: int) -> None:
    if size == 0:
        raise Rejected("The file is empty.")
    if size > limit:
        limit_text = f"{limit // 1048576} MB" if limit % 1048576 == 0 else human_mb(limit)
        raise Rejected(f"File is {human_mb(size)}; the limit is {limit_text}.")


def check_content(mime: str, data: bytes) -> None:
    """The extension must agree with the bytes, so a renamed file can't slip through."""
    if mime == PDF_MIME:
        if b"%PDF-" not in data[:1024]:
            raise Rejected("This file has a .pdf extension but is not a PDF. Re-export it as PDF.")
    elif mime == DOCX_MIME:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if "word/document.xml" not in z.namelist():
                    raise Rejected(
                        "This file is not a Word .docx document. Save it as .docx and upload again."
                    )
        except zipfile.BadZipFile as exc:
            raise Rejected(
                "This file is not a Word .docx document. Older .doc files must be saved as .docx first."
            ) from exc
    elif mime == TXT_MIME and b"\x00" in data[:8192]:
        raise Rejected("This file has a .txt extension but contains binary data.")
