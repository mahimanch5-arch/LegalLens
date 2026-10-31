"""
Re-ranker for Ask/Summary/Draft Workflows

Uses BGE Reranker Large to score and rank search results.
Reduces candidates from ~50 to top 5-10 based on relevance.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RankedResult:
    """A re-ranked search result"""
    chunk_id: str
    document_id: str
    text: str
    score: float  # BGE Reranker score (0-1)
    rank: int     # Position in ranked list (1-indexed)
    metadata: dict = None


class BGEReranker:
    """
    Re-ranker using BAAI/bge-reranker-large

    Features:
    - Cross-encoder architecture
    - Trained on legal document ranking
    - Returns normalized scores (0-1)
    - ~50ms per chunk inference
    """

    MODEL_NAME = "BAAI/bge-reranker-large"

    def __init__(self, model_name: str = MODEL_NAME):
        """
        Initialize re-ranker.

        Args:
            model_name: HuggingFace model identifier
        """
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the BGE Reranker model"""
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading reranker: {self.model_name}")
            self.model = CrossEncoder(self.model_name)
            logger.info("Reranker loaded successfully")
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        except Exception as e:
            logger.error(f"Failed to load reranker: {e}")
            raise

    def rerank(self,
               query: str,
               documents: List[str],
               chunk_ids: Optional[List[str]] = None,
               document_ids: Optional[List[str]] = None,
               metadatas: Optional[List[dict]] = None,
               top_k: int = 10) -> List[RankedResult]:
        """
        Re-rank documents by relevance to query.

        Args:
            query: Search query
            documents: List of document texts
            chunk_ids: List of chunk IDs (if None, generates sequential IDs)
            document_ids: List of document IDs
            metadatas: List of metadata dicts
            top_k: Number of top results to return

        Returns:
            List of RankedResult sorted by relevance
        """
        if not documents:
            return []

        if not self.model:
            logger.error("Model not loaded")
            return []

        # Validate inputs
        n_docs = len(documents)
        if chunk_ids is None:
            chunk_ids = [f"chunk_{i}" for i in range(n_docs)]
        if document_ids is None:
            document_ids = ["" for _ in range(n_docs)]
        if metadatas is None:
            metadatas = [{} for _ in range(n_docs)]

        assert len(chunk_ids) == n_docs, "chunk_ids length mismatch"
        assert len(document_ids) == n_docs, "document_ids length mismatch"
        assert len(metadatas) == n_docs, "metadatas length mismatch"

        try:
            # Prepare query-document pairs
            pairs = [[query, doc] for doc in documents]

            # Get relevance scores
            scores = self.model.predict(pairs)

            # Normalize scores to 0-1 range
            scores = self._normalize_scores(scores)

            # Create ranked results
            ranked = []
            for i, (chunk_id, doc_id, text, score, metadata) in enumerate(
                zip(chunk_ids, document_ids, documents, scores, metadatas)
            ):
                ranked.append(RankedResult(
                    chunk_id=chunk_id,
                    document_id=doc_id,
                    text=text,
                    score=float(score),
                    rank=i + 1,
                    metadata=metadata
                ))

            # Sort by score (descending)
            ranked.sort(key=lambda x: x.score, reverse=True)

            # Update ranks after sorting
            for i, result in enumerate(ranked, 1):
                result.rank = i

            # Return top-k
            top_results = ranked[:top_k]
            logger.info(f"Re-ranked {n_docs} documents, returned top {len(top_results)}")

            return top_results

        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            return []

    @staticmethod
    def _normalize_scores(scores) -> List[float]:
        """Normalize scores to 0-1 range"""
        import numpy as np

        scores = np.array(scores)

        # Min-max normalization
        min_score = scores.min()
        max_score = scores.max()

        if max_score == min_score:
            # All scores are the same
            return [0.5] * len(scores)

        normalized = (scores - min_score) / (max_score - min_score)
        return normalized.tolist()


class RerankerPipeline:
    """End-to-end re-ranking pipeline"""

    def __init__(self, top_k: int = 10):
        """
        Initialize pipeline.

        Args:
            top_k: Number of top results to return
        """
        self.reranker = BGEReranker()
        self.top_k = top_k

    def rerank_results(self,
                      query: str,
                      retrieved_results,  # List with .chunk_id, .document_id, .text, .metadata
                      top_k: Optional[int] = None) -> List[RankedResult]:
        """
        Re-rank retrieval results.

        Args:
            query: Search query
            retrieved_results: Results from hybrid_retrieval
            top_k: Override default top_k

        Returns:
            List of top re-ranked results
        """
        if not retrieved_results:
            return []

        top_k = top_k or self.top_k

        logger.info(f"Re-ranking {len(retrieved_results)} results")

        # Extract components
        documents = [r.text for r in retrieved_results]
        chunk_ids = [r.chunk_id for r in retrieved_results]
        document_ids = [r.document_id for r in retrieved_results]
        metadatas = [r.metadata for r in retrieved_results]

        # Re-rank
        ranked = self.reranker.rerank(
            query=query,
            documents=documents,
            chunk_ids=chunk_ids,
            document_ids=document_ids,
            metadatas=metadatas,
            top_k=top_k
        )

        return ranked


# Convenience function
def rerank_results(query: str,
                  retrieved_results,
                  top_k: int = 10) -> List[RankedResult]:
    """
    Simple function to re-rank retrieval results.

    Args:
        query: Search query
        retrieved_results: Results from hybrid_retrieval
        top_k: Number of top results

    Returns:
        List of top re-ranked results
    """
    pipeline = RerankerPipeline(top_k=top_k)
    return pipeline.rerank_results(query, retrieved_results, top_k=top_k)


if __name__ == "__main__":
    # Test
    import logging
    logging.basicConfig(level=logging.INFO)

    try:
        reranker = BGEReranker()

        # Test data
        query = "What are the termination rights?"
        documents = [
            "Section 5. Termination. Either party may terminate with 30 days notice.",
            "Section 3. Renewal. The contract automatically renews annually.",
            "Section 5A. Early Termination. Termination fees apply if terminated before 1 year.",
            "Section 2. Effective Date. This contract becomes effective on signature.",
            "Section 5B. Termination for Cause. Immediate termination allowed for material breach.",
        ]

        # Re-rank
        ranked = reranker.rerank(query, documents, top_k=3)

        print("\nRe-ranking Results:")
        print(f"Query: {query}\n")
        for result in ranked:
            print(f"Rank {result.rank}: Score {result.score:.2%}")
            print(f"  {result.text[:80]}...\n")

    except Exception as e:
        print(f"Error: {e}")
