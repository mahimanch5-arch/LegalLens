"""
Document Loader for LegalLens

Loads and extracts text from PDF, DOCX, and TXT files.
Handles both scanned and unscanned PDFs with automatic detection.
"""

from typing import Optional, Tuple, List
from dataclasses import dataclass
from pathlib import Path
import mimetypes
import logging

try:
    from PyPDF2 import PdfReader
    import pypdf
except ImportError:
    raise ImportError("Please install PyPDF2: pip install PyPDF2")

try:
    from docx import Document as DocxDocument
except ImportError:
    raise ImportError("Please install python-docx: pip install python-docx")

logger = logging.getLogger(__name__)


@dataclass
class LoadedDocument:
    """Represents a loaded document with text and metadata"""
    filename: str
    file_type: str  # "pdf", "docx", "txt"
    text: str
    is_scanned: bool
    page_count: int
    character_count: int
    pages: List[str]  # Text per page
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DocumentLoader:
    """
    Load documents from various formats.

    Supports:
    - PDF (both scanned and unscanned)
    - DOCX
    - TXT
    """

    SUPPORTED_FORMATS = {".pdf", ".docx", ".txt"}
    SCANNED_DETECTION_THRESHOLD = 50  # Characters - if less, likely scanned

    @staticmethod
    def load(file_path: str) -> LoadedDocument:
        """
        Load a document and return its content.

        Args:
            file_path: Path to the document

        Returns:
            LoadedDocument with extracted text and metadata

        Raises:
            ValueError: If file format is not supported
            IOError: If file cannot be read
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise IOError(f"File not found: {file_path}")

        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            return DocumentLoader._load_pdf(file_path)
        elif suffix == ".docx":
            return DocumentLoader._load_docx(file_path)
        elif suffix == ".txt":
            return DocumentLoader._load_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Supported: {DocumentLoader.SUPPORTED_FORMATS}")

    @staticmethod
    def _load_pdf(file_path: Path) -> LoadedDocument:
        """Load PDF and detect if scanned or unscanned"""
        try:
            reader = PdfReader(str(file_path))
        except Exception as e:
            raise IOError(f"Failed to read PDF: {e}")

        page_count = len(reader.pages)
        pages = []
        full_text = []

        # Extract text from all pages
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                pages.append(page_text or "")
                full_text.append(page_text or "")
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {e}")
                pages.append("")
                full_text.append("")

        combined_text = "\n\n".join(full_text)

        # Detect if scanned (very little text extracted)
        is_scanned = len(combined_text.strip()) < DocumentLoader.SCANNED_DETECTION_THRESHOLD

        if is_scanned:
            logger.info(f"PDF detected as scanned: {file_path.name}")

        return LoadedDocument(
            filename=file_path.name,
            file_type="pdf",
            text=combined_text,
            is_scanned=is_scanned,
            page_count=page_count,
            character_count=len(combined_text),
            pages=pages,
            metadata={
                "file_path": str(file_path),
                "file_size_bytes": file_path.stat().st_size,
            }
        )

    @staticmethod
    def _load_docx(file_path: Path) -> LoadedDocument:
        """Load DOCX file"""
        try:
            doc = DocxDocument(str(file_path))
        except Exception as e:
            raise IOError(f"Failed to read DOCX: {e}")

        # Extract all paragraphs
        paragraphs = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append(para.text)

        combined_text = "\n\n".join(paragraphs)

        # For DOCX, estimate pages (rough estimate: ~400 words per page)
        word_count = len(combined_text.split())
        estimated_pages = max(1, word_count // 400)

        # DOCX is never scanned
        return LoadedDocument(
            filename=file_path.name,
            file_type="docx",
            text=combined_text,
            is_scanned=False,
            page_count=estimated_pages,
            character_count=len(combined_text),
            pages=[combined_text],  # DOCX doesn't have real pages
            metadata={
                "file_path": str(file_path),
                "file_size_bytes": file_path.stat().st_size,
                "estimated_pages": estimated_pages,
                "word_count": word_count,
            }
        )

    @staticmethod
    def _load_txt(file_path: Path) -> LoadedDocument:
        """Load TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except UnicodeDecodeError:
            # Try with latin-1 encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    text = f.read()
            except Exception as e:
                raise IOError(f"Failed to read TXT file: {e}")
        except Exception as e:
            raise IOError(f"Failed to read TXT file: {e}")

        # Estimate pages
        word_count = len(text.split())
        estimated_pages = max(1, word_count // 400)

        return LoadedDocument(
            filename=file_path.name,
            file_type="txt",
            text=text,
            is_scanned=False,
            page_count=estimated_pages,
            character_count=len(text),
            pages=[text],  # TXT is single page
            metadata={
                "file_path": str(file_path),
                "file_size_bytes": file_path.stat().st_size,
                "estimated_pages": estimated_pages,
                "word_count": word_count,
            }
        )


if __name__ == "__main__":
    # Test
    import sys

    if len(sys.argv) < 2:
        print("Usage: python document_loader.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    logging.basicConfig(level=logging.INFO)

    try:
        doc = DocumentLoader.load(file_path)
        print(f"\n✅ Loaded: {doc.filename}")
        print(f"Type: {doc.file_type}")
        print(f"Is scanned: {doc.is_scanned}")
        print(f"Pages: {doc.page_count}")
        print(f"Characters: {doc.character_count}")
        print(f"\nFirst 200 characters:\n{doc.text[:200]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
