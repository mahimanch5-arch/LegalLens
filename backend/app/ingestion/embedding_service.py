"""
Embedding Service for LegalLens

Generates embeddings for document chunks using Sentence-BERT.
Supports batch processing for efficiency.
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Generate embeddings for text chunks.

    Uses Sentence-BERT (all-MiniLM-L6-v2):
    - 384-dimensional embeddings
    - Fast inference (~50ms per chunk)
    - Excellent for legal documents
    - Free (open-source)
    """

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM = 384
    BATCH_SIZE = 32

    def __init__(self, model_name: str = MODEL_NAME, batch_size: int = BATCH_SIZE):
        """
        Initialize embedding service.

        Args:
            model_name: HuggingFace model identifier
            batch_size: Batch size for processing
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the embedding model"""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Model loaded successfully. Embedding dimension: {self.EMBEDDING_DIM}")
        except ImportError as e:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            ) from e
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def embed_text(self, text: str) -> list[float] | None:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats (384 dimensions) or None on error
        """
        if not self.model:
            logger.error("Model not loaded")
            return None

        try:
            embeddings = self.model.encode([text], convert_to_numpy=True)
            return embeddings[0].tolist()
        except Exception as e:
            logger.error(f"Failed to embed text: {e}")
            return None

    def embed_texts(self, texts: list[str], show_progress: bool = False) -> list[list[float]] | None:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            show_progress: Show progress bar

        Returns:
            List of embeddings (each 384 dimensions) or None on error
        """
        if not self.model:
            logger.error("Model not loaded")
            return None

        if not texts:
            return []

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True
            )

            # Convert to list of lists
            return embeddings.tolist()

        except Exception as e:
            logger.error(f"Failed to embed texts: {e}")
            return None

    def embed_chunks(self, chunks: list[Any], show_progress: bool = False) -> list[dict[str, Any]]:
        """
        Generate embeddings for document chunks.

        Args:
            chunks: List of Chunk objects with .text attribute
            show_progress: Show progress bar

        Returns:
            List of dicts with chunk info + embedding
        """
        if not chunks:
            return []

        # Extract text from chunks
        texts = [chunk.text for chunk in chunks]

        # Generate embeddings
        embeddings = self.embed_texts(texts, show_progress=show_progress)

        if not embeddings:
            logger.error("Failed to generate embeddings")
            return []

        # Combine chunks with embeddings
        results = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            results.append({
                'chunk_id': chunk.id,
                'document_id': chunk.document_id,
                'chunk_number': chunk.chunk_number,
                'text': chunk.text,
                'token_count': chunk.token_count,
                'character_start': chunk.character_start,
                'character_end': chunk.character_end,
                'embedding': embedding,
                'metadata': chunk.metadata
            })

        logger.info(f"Generated {len(results)} embeddings")
        return results

    def similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding (list of floats)
            embedding2: Second embedding (list of floats)

        Returns:
            Similarity score (0.0-1.0)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    @staticmethod
    def embedding_dimension() -> int:
        """Get embedding dimension"""
        return EmbeddingService.EMBEDDING_DIM


# Singleton for efficiency
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """Get or create embedding service (singleton)"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


# Convenience functions
def embed_text(text: str) -> list[float] | None:
    """Embed a single text"""
    service = get_embedding_service()
    return service.embed_text(text)


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Embed multiple texts"""
    service = get_embedding_service()
    return service.embed_texts(texts)


if __name__ == "__main__":
    # Test
    import time

    logging.basicConfig(level=logging.INFO)

    service = get_embedding_service()

    # Test single embedding
    text1 = "What are the termination rights?"
    start = time.time()
    embedding1 = service.embed_text(text1)
    elapsed = time.time() - start

    if embedding1:
        print(f"✅ Single embedding generated in {elapsed*1000:.1f}ms")
        print(f"   Dimension: {len(embedding1)}")
        print(f"   First 5 values: {embedding1[:5]}")

    # Test batch embedding
    texts = [
        "What are the termination rights?",
        "How much notice is required?",
        "When can we terminate the agreement?",
    ]

    start = time.time()
    embeddings = service.embed_texts(texts)
    elapsed = time.time() - start

    if embeddings:
        print(f"\n✅ Batch embeddings generated in {elapsed*1000:.1f}ms")
        print(f"   Count: {len(embeddings)}")
        print(f"   Dimension: {len(embeddings[0])}")

    # Test similarity
    if embeddings and len(embeddings) >= 2:
        sim = service.similarity(embeddings[0], embeddings[1])
        print(f"\n✅ Similarity between first two texts: {sim:.2%}")
