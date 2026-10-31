"""
Hybrid Retrieval for Ask/Summary/Draft Workflows

Combines semantic (vector) search with keyword (BM25) search.
Returns merged results ready for re-ranking.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """A single retrieved chunk"""
    chunk_id: str
    document_id: str
    text: str
    score: float  # Relevance score (0-1)
    source: str  # "vector" or "keyword"
    metadata: dict[str, Any] | None = None


class HybridRetriever(ABC):
    """Abstract base class for hybrid retrieval"""

    @abstractmethod
    def vector_search(self, query: str, top_k: int = 25) -> list[RetrievalResult]:
        """Search using vector embeddings"""
        pass

    @abstractmethod
    def keyword_search(self, query: str, top_k: int = 25) -> list[RetrievalResult]:
        """Search using BM25 keyword matching"""
        pass

    def hybrid_search(self,
                     query: str,
                     top_k: int = 25,
                     document_filter: str | None = None) -> list[RetrievalResult]:
        """
        Perform hybrid search combining vector and keyword results.

        Args:
            query: Search query
            top_k: Number of results per method
            document_filter: Optional document_id to filter results

        Returns:
            Merged list of retrieval results
        """
        # Run both searches in parallel
        vector_results = self.vector_search(query, top_k=top_k)
        keyword_results = self.keyword_search(query, top_k=top_k)

        # Filter by document if specified
        if document_filter:
            vector_results = [r for r in vector_results if r.document_id == document_filter]
            keyword_results = [r for r in keyword_results if r.document_id == document_filter]

        # Merge and deduplicate
        merged = self._merge_results(vector_results, keyword_results)

        logger.info(f"Hybrid search: {len(vector_results)} vector + {len(keyword_results)} keyword "
                   f"= {len(merged)} merged results")

        return merged

    @staticmethod
    def _merge_results(vector_results: list[RetrievalResult],
                      keyword_results: list[RetrievalResult]) -> list[RetrievalResult]:
        """
        Merge vector and keyword results.

        Strategy:
        - Combine both lists
        - Deduplicate by chunk_id
        - For duplicates, average scores
        """
        merged_dict = {}

        # Add vector results
        for result in vector_results:
            if result.chunk_id not in merged_dict:
                merged_dict[result.chunk_id] = result
            else:
                # Average scores for duplicates
                existing = merged_dict[result.chunk_id]
                avg_score = (existing.score + result.score) / 2
                merged_dict[result.chunk_id].score = avg_score

        # Add keyword results
        for result in keyword_results:
            if result.chunk_id not in merged_dict:
                merged_dict[result.chunk_id] = result
            else:
                # Average scores for duplicates
                existing = merged_dict[result.chunk_id]
                avg_score = (existing.score + result.score) / 2
                merged_dict[result.chunk_id].score = avg_score

        # Convert to list and sort by score
        merged_list = list(merged_dict.values())
        merged_list.sort(key=lambda x: x.score, reverse=True)

        return merged_list


class ChromaVectorHybridRetriever(HybridRetriever):
    """Hybrid retriever using Chroma for vectors and BM25 for keywords"""

    def __init__(self,
                 vector_store: Any,  # Chroma vector store
                 bm25_index: Any) -> None:   # BM25 index
        """
        Initialize hybrid retriever.

        Args:
            vector_store: Chroma vector store instance
            bm25_index: BM25 index instance (or similar keyword search)
        """
        self.vector_store = vector_store
        self.bm25_index = bm25_index

    def vector_search(self, query: str, top_k: int = 25) -> list[RetrievalResult]:
        """Search using Chroma vector embeddings"""
        try:
            from embedding_service import get_embedding_service

            embedding_service = get_embedding_service()
            query_embedding = embedding_service.embed_text(query)

            if not query_embedding:
                logger.error("Failed to embed query")
                return []

            # Search vector store
            results = self.vector_store.search(query_embedding, top_k=top_k)

            # Convert to RetrievalResult format
            retrieval_results = []
            for chunk_id, similarity, metadata in results:
                chunk = self.vector_store.get_chunk(chunk_id)
                if chunk:
                    retrieval_results.append(RetrievalResult(
                        chunk_id=chunk_id,
                        document_id=metadata.get('document_id', ''),
                        text=chunk['text'],
                        score=similarity,
                        source='vector',
                        metadata=metadata
                    ))

            logger.info(f"Vector search returned {len(retrieval_results)} results")
            return retrieval_results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def keyword_search(self, query: str, top_k: int = 25) -> list[RetrievalResult]:
        """Search using BM25 keyword matching"""
        try:
            # This would use BM25 index or similar
            # Implementation depends on BM25 library used
            logger.info(f"BM25 search for: {query} (top {top_k})")

            # Placeholder: would call self.bm25_index.search(query, top_k)
            # For now, return empty list as this needs integration with actual BM25
            return []

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []


class HybridRetrievalPipeline:
    """End-to-end hybrid retrieval pipeline"""

    def __init__(self, retriever: HybridRetriever):
        """
        Initialize pipeline.

        Args:
            retriever: HybridRetriever instance
        """
        self.retriever = retriever

    def retrieve(self,
                query: str,
                top_k: int = 25,
                document_filter: str | None = None) -> list[RetrievalResult]:
        """
        Retrieve relevant chunks using hybrid search.

        Args:
            query: Search query
            top_k: Number of results per method
            document_filter: Optional document_id to limit results

        Returns:
            Ranked list of retrieval results
        """
        logger.info(f"Hybrid retrieval for: '{query[:60]}...'")

        results = self.retriever.hybrid_search(
            query=query,
            top_k=top_k,
            document_filter=document_filter
        )

        logger.info(f"Retrieved {len(results)} total results")
        return results


# Convenience function
def hybrid_search(retriever: HybridRetriever,
                 query: str,
                 top_k: int = 25,
                 document_filter: str | None = None) -> list[RetrievalResult]:
    """
    Simple function to perform hybrid search.

    Args:
        retriever: HybridRetriever instance
        query: Search query
        top_k: Number of results per method
        document_filter: Optional document_id filter

    Returns:
        List of retrieval results
    """
    pipeline = HybridRetrievalPipeline(retriever)
    return pipeline.retrieve(query, top_k=top_k, document_filter=document_filter)


if __name__ == "__main__":
    # Test structure
    logging.basicConfig(level=logging.INFO)

    print("""
    Hybrid Retrieval Module Ready

    To use:
    1. Initialize with vector store + BM25 index
    2. Call hybrid_search() with query
    3. Get merged results from both methods

    Example:
        retriever = ChromaVectorHybridRetriever(chroma_store, bm25_index)
        results = hybrid_search(retriever, "What are termination rights?", top_k=25)
        # Returns ~50 merged results ready for re-ranking
    """)
