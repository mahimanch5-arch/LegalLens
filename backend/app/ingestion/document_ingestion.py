"""
Document Ingestion Pipeline Orchestrator

Coordinates the entire ingestion process:
1. Load document (PDF/DOCX/TXT)
2. Detect if scanned
3. Apply OCR if needed
4. Chunk document
5. Generate embeddings
6. Store in vector database
"""

from typing import Optional, Dict
import logging
import time
from dataclasses import dataclass

from document_loader import DocumentLoader, LoadedDocument
from ocr_processor import get_ocr_processor
from chunking import DocumentChunker, Chunk
from embedding_service import get_embedding_service
from vector_store import get_vector_store, VectorStore

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of document ingestion"""
    success: bool
    document_id: str
    filename: str
    chunks_created: int
    total_tokens: int
    embeddings_generated: int
    is_scanned: bool
    ocr_quality: Optional[float]  # Average OCR confidence if scanned
    low_ocr_pages: list  # Pages with low OCR confidence
    elapsed_time: float
    error_message: Optional[str] = None


class DocumentIngestionPipeline:
    """
    End-to-end document ingestion pipeline.

    Handles:
    - Document loading (PDF, DOCX, TXT)
    - Scanned document detection
    - OCR for scanned documents
    - Text chunking
    - Embedding generation
    - Vector storage
    """

    def __init__(self,
                 vector_store_type: str = "chroma",
                 chunk_size_tokens: int = 512,
                 chunk_overlap_percent: float = 0.20,
                 **kwargs):
        """
        Initialize ingestion pipeline.

        Args:
            vector_store_type: "chroma" or "qdrant"
            chunk_size_tokens: Chunk size in tokens
            chunk_overlap_percent: Overlap between chunks
            **kwargs: Additional arguments for vector store
        """
        self.vector_store = get_vector_store(vector_store_type, **kwargs)
        self.chunker = DocumentChunker(chunk_size_tokens, chunk_overlap_percent)
        self.embedding_service = get_embedding_service()
        self.ocr_processor = get_ocr_processor()

    def ingest(self, file_path: str, document_id: str) -> IngestionResult:
        """
        Ingest a document through the full pipeline.

        Args:
            file_path: Path to document file
            document_id: Unique identifier for the document

        Returns:
            IngestionResult with success status and metrics
        """
        start_time = time.time()
        result = IngestionResult(
            success=False,
            document_id=document_id,
            filename="",
            chunks_created=0,
            total_tokens=0,
            embeddings_generated=0,
            is_scanned=False,
            ocr_quality=None,
            low_ocr_pages=[],
            elapsed_time=0
        )

        try:
            # Step 1: Load document
            logger.info(f"Loading document: {file_path}")
            loaded_doc = DocumentLoader.load(file_path)
            result.filename = loaded_doc.filename
            result.is_scanned = loaded_doc.is_scanned

            # Step 2: Apply OCR if scanned
            if loaded_doc.is_scanned:
                logger.info("Document is scanned, applying OCR...")
                ocr_results = self.ocr_processor.process_scanned_pdf(file_path)

                if ocr_results:
                    # Combine OCR results
                    ocr_texts = [r.text for r in ocr_results]
                    loaded_doc.text = "\n\n".join(ocr_texts)

                    # Calculate OCR quality metrics
                    ocr_confidences = [r.confidence for r in ocr_results]
                    result.ocr_quality = sum(ocr_confidences) / len(ocr_confidences)
                    result.low_ocr_pages = [r.page_num for r in ocr_results if r.confidence < 0.80]

                    logger.info(f"OCR complete: {result.ocr_quality:.1%} average confidence")

            # Step 3: Chunk document
            logger.info("Chunking document...")
            chunks = self.chunker.chunk_document(
                document_id=document_id,
                text=loaded_doc.text,
                metadata={
                    'filename': loaded_doc.filename,
                    'file_type': loaded_doc.file_type,
                    'is_scanned': loaded_doc.is_scanned,
                    'page_count': loaded_doc.page_count
                }
            )

            if not chunks:
                raise Exception("No chunks created from document")

            result.chunks_created = len(chunks)
            result.total_tokens = sum(c.token_count for c in chunks)
            logger.info(f"Created {len(chunks)} chunks ({result.total_tokens} tokens total)")

            # Step 4: Generate embeddings
            logger.info("Generating embeddings...")
            embedded_chunks = self.embedding_service.embed_chunks(chunks, show_progress=True)

            if not embedded_chunks:
                raise Exception("Failed to generate embeddings")

            result.embeddings_generated = len(embedded_chunks)
            logger.info(f"Generated {len(embedded_chunks)} embeddings")

            # Step 5: Store in vector database
            logger.info("Storing embeddings in vector database...")
            success = self.vector_store.add_embeddings(embedded_chunks)

            if not success:
                raise Exception("Failed to store embeddings in vector database")

            result.success = True
            logger.info("✅ Document ingestion complete!")

        except Exception as e:
            logger.error(f"❌ Ingestion failed: {e}")
            result.error_message = str(e)

        finally:
            result.elapsed_time = time.time() - start_time

        return result

    def delete_document(self, document_id: str) -> bool:
        """
        Delete all chunks for a document from vector database.

        Args:
            document_id: Document ID to delete

        Returns:
            True if successful
        """
        logger.info(f"Deleting document {document_id} from vector store...")
        return self.vector_store.delete_document(document_id)

    def search_documents(self, query: str, top_k: int = 5) -> list:
        """
        Search documents using semantic search.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            List of results with chunk_id, similarity, text
        """
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)

        if not query_embedding:
            logger.error("Failed to embed query")
            return []

        # Search vector store
        results = self.vector_store.search(query_embedding, top_k=top_k)

        # Enrich results
        enriched = []
        for chunk_id, similarity, metadata in results:
            chunk = self.vector_store.get_chunk(chunk_id)
            if chunk:
                enriched.append({
                    'chunk_id': chunk_id,
                    'similarity': similarity,
                    'text': chunk['text'],
                    'metadata': metadata,
                    'document_id': metadata.get('document_id')
                })

        return enriched


def ingest_document(file_path: str, document_id: str) -> IngestionResult:
    """
    Simple function to ingest a document.

    Args:
        file_path: Path to document
        document_id: Unique document ID

    Returns:
        IngestionResult
    """
    pipeline = DocumentIngestionPipeline()
    return pipeline.ingest(file_path, document_id)


def search_documents(query: str, top_k: int = 5) -> list:
    """
    Search ingested documents.

    Args:
        query: Search query
        top_k: Number of results

    Returns:
        List of matching chunks
    """
    pipeline = DocumentIngestionPipeline()
    return pipeline.search_documents(query, top_k=top_k)


if __name__ == "__main__":
    # Test
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python document_ingestion.py <file_path> [document_id]")
        sys.exit(1)

    file_path = sys.argv[1]
    document_id = sys.argv[2] if len(sys.argv) > 2 else "test_doc"

    pipeline = DocumentIngestionPipeline()
    result = pipeline.ingest(file_path, document_id)

    print(f"\n{'='*70}")
    print(f"Ingestion Result")
    print(f"{'='*70}")
    print(f"Success:             {result.success}")
    print(f"Document ID:         {result.document_id}")
    print(f"Filename:            {result.filename}")
    print(f"Is Scanned:          {result.is_scanned}")
    print(f"Chunks Created:      {result.chunks_created}")
    print(f"Total Tokens:        {result.total_tokens}")
    print(f"Embeddings:          {result.embeddings_generated}")
    print(f"Time Elapsed:        {result.elapsed_time:.2f}s")

    if result.is_scanned and result.ocr_quality:
        print(f"OCR Quality:         {result.ocr_quality:.1%}")
        if result.low_ocr_pages:
            print(f"Low OCR Pages:       {result.low_ocr_pages}")

    if result.error_message:
        print(f"Error:               {result.error_message}")

    print(f"{'='*70}")
