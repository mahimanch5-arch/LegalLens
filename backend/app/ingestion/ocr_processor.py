"""
OCR Processor for Scanned Documents

Uses Tesseract OCR to extract text from scanned PDFs and images.
Handles per-page OCR with confidence scoring.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Result of OCR processing"""
    page_num: int
    text: str
    confidence: float  # 0.0-1.0, average confidence
    raw_confidence_scores: list[float] | None = None  # Per-word confidence


class OCRProcessor:
    """
    Process scanned documents using Tesseract OCR.

    This is a placeholder/interface. In production, requires:
    - System: tesseract-ocr (apt-get install tesseract-ocr on Linux)
    - Python: pytesseract (pip install pytesseract)
    - PDF to image: pdf2image (pip install pdf2image)
    """

    CONFIDENCE_THRESHOLD = 0.80

    def __init__(self) -> None:
        """Initialize OCR processor"""
        try:
            import pytesseract
            self.pytesseract = pytesseract
            self.available = True
            logger.info("Tesseract OCR available")
        except ImportError:
            self.pytesseract = None
            self.available = False
            logger.warning("Tesseract not installed. Install with: pip install pytesseract pdf2image")

    def process_scanned_pdf(self, pdf_path: str, pages: list[int] | None = None) -> list[OCRResult]:
        """
        Extract text from scanned PDF using OCR.

        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers to process (0-indexed). If None, process all.

        Returns:
            List of OCRResult with text and confidence per page
        """
        if not self.available:
            logger.error("Tesseract OCR not available")
            return []

        try:
            from pdf2image import convert_from_path
        except ImportError:
            logger.error("pdf2image not installed. Install with: pip install pdf2image")
            return []

        results = []

        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path)

            if pages:
                # Process only specified pages
                images = [images[i] for i in pages if i < len(images)]

            for page_num, image in enumerate(images):
                try:
                    # Extract text with confidence
                    text = self.pytesseract.image_to_string(image)

                    # Get detailed data (for confidence scoring)
                    data = self.pytesseract.image_to_data(image, output_type="dict")

                    # Calculate average confidence (skip low-confidence words)
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

                    results.append(OCRResult(
                        page_num=page_num,
                        text=text,
                        confidence=avg_confidence / 100.0,  # Convert to 0-1 scale
                        raw_confidence_scores=[float(c) for c in confidences]
                    ))

                except Exception as e:
                    logger.error(f"Failed to OCR page {page_num}: {e}")
                    results.append(OCRResult(
                        page_num=page_num,
                        text="",
                        confidence=0.0
                    ))

        except Exception as e:
            logger.error(f"Failed to convert PDF to images: {e}")
            return []

        return results

    def process_image(self, image_path: str) -> OCRResult:
        """
        Extract text from a single image using OCR.

        Args:
            image_path: Path to image file

        Returns:
            OCRResult with text and confidence
        """
        if not self.available:
            logger.error("Tesseract OCR not available")
            return OCRResult(page_num=0, text="", confidence=0.0)

        try:
            from PIL import Image
        except ImportError:
            logger.error("Pillow not installed. Install with: pip install Pillow")
            return OCRResult(page_num=0, text="", confidence=0.0)

        try:
            image = Image.open(image_path)
            text = self.pytesseract.image_to_string(image)

            # Get confidence data
            data = self.pytesseract.image_to_data(image, output_type="dict")
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return OCRResult(
                page_num=0,
                text=text,
                confidence=avg_confidence / 100.0,
                raw_confidence_scores=[float(c) for c in confidences]
            )

        except Exception as e:
            logger.error(f"Failed to OCR image: {e}")
            return OCRResult(page_num=0, text="", confidence=0.0)

    @staticmethod
    def calculate_average_confidence(results: list[OCRResult]) -> float:
        """Calculate average confidence across all OCR results"""
        if not results:
            return 0.0
        return sum(r.confidence for r in results) / len(results)

    @staticmethod
    def get_low_confidence_pages(results: list[OCRResult], threshold: float = 0.80) -> list[int]:
        """Get page numbers with confidence below threshold"""
        return [r.page_num for r in results if r.confidence < threshold]


# For development/testing without Tesseract installed
class MockOCRProcessor:
    """Mock OCR processor for testing without Tesseract"""

    def __init__(self) -> None:
        self.available = False
        logger.info("Using MockOCRProcessor (no actual OCR). Install pytesseract + tesseract for real OCR.")

    def process_scanned_pdf(self, pdf_path: str, pages: list[int] | None = None) -> list[OCRResult]:
        """Mock implementation"""
        logger.warning(f"MockOCRProcessor: Skipping OCR for {pdf_path}")
        return []

    def process_image(self, image_path: str) -> OCRResult:
        """Mock implementation"""
        logger.warning(f"MockOCRProcessor: Skipping OCR for {image_path}")
        return OCRResult(page_num=0, text="", confidence=0.0)


# Use mock by default, can switch to real when Tesseract is available
def get_ocr_processor() -> OCRProcessor | MockOCRProcessor:
    """Get OCR processor (real or mock)"""
    try:
        processor = OCRProcessor()
        if processor.available:
            return processor
    except Exception:
        pass

    # Fall back to mock
    return MockOCRProcessor()


if __name__ == "__main__":
    # Test
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python ocr_processor.py <image_or_pdf_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    processor = get_ocr_processor()

    if file_path.lower().endswith('.pdf'):
        results = processor.process_scanned_pdf(file_path)
        print(f"\nOCR Results for {file_path}:")
        for result in results:
            print(f"  Page {result.page_num}: {result.confidence:.1%} confidence")
            print(f"  Text: {result.text[:100]}...")
    else:
        result = processor.process_image(file_path)
        print(f"\nOCR Result for {file_path}:")
        print(f"  Confidence: {result.confidence:.1%}")
        print(f"  Text: {result.text[:200]}...")
