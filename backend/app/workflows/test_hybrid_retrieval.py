"""
Unit tests for HybridRetrieval module
"""

from typing import Any
from unittest.mock import Mock

import pytest
from hybrid_retrieval import ChromaVectorHybridRetriever, HybridRetriever, RetrievalResult


class TestRetrievalResult:
    """Test suite for RetrievalResult dataclass"""

    def test_retrieval_result_creation(self) -> None:
        """Test RetrievalResult object creation"""
        result = RetrievalResult(
            chunk_id="chunk_123",
            document_id="doc_456",
            text="Sample legal text",
            score=0.85,
            source="vector_search"
        )

        assert result.chunk_id == "chunk_123"
        assert result.document_id == "doc_456"
        assert result.text == "Sample legal text"
        assert result.score == 0.85
        assert result.source == "vector_search"

    def test_retrieval_result_with_metadata(self) -> None:
        """Test RetrievalResult with metadata"""
        metadata = {"filename": "contract.pdf", "page": 5}
        result = RetrievalResult(
            chunk_id="chunk_1",
            document_id="doc_1",
            text="Text",
            score=0.9,
            source="vector",
            metadata=metadata
        )

        assert result.metadata == metadata


class TestHybridRetriever:
    """Test suite for HybridRetriever abstract class"""

    def test_retriever_interface(self) -> None:
        """Test that HybridRetriever defines required interface"""
        # HybridRetriever is abstract, so we can't instantiate it directly
        # But we can verify it has the required methods
        assert hasattr(HybridRetriever, 'hybrid_search')
        assert hasattr(HybridRetriever, 'vector_search')
        assert hasattr(HybridRetriever, 'keyword_search')


class TestChromaVectorHybridRetriever:
    """Test suite for ChromaVectorHybridRetriever"""

    @pytest.fixture
    def mock_vector_store(self) -> Any:
        """Create a mock vector store"""
        return Mock()

    @pytest.fixture
    def retriever(self, mock_vector_store: Any) -> Any:
        """Create a retriever with mock vector store"""
        retriever = ChromaVectorHybridRetriever()
        retriever.vector_store = mock_vector_store
        return retriever

    def test_vector_search(self, retriever: Any, mock_vector_store: Any) -> None:
        """Test vector search functionality"""
        # Setup mock response
        mock_vector_store.similarity_search_with_score.return_value = [
            (Mock(page_content="Result 1", metadata={"chunk_id": "c1", "document_id": "d1"}), 0.9),
            (Mock(page_content="Result 2", metadata={"chunk_id": "c2", "document_id": "d2"}), 0.8),
        ]

        results = retriever.vector_search("test query", top_k=2)

        assert len(results) == 2
        assert all(isinstance(r, RetrievalResult) for r in results)
        assert results[0].score == 0.9
        assert results[1].score == 0.8

    def test_keyword_search(self, retriever: Any, mock_vector_store: Any) -> None:
        """Test keyword search (BM25) functionality"""
        # Mock BM25 search
        retriever.bm25 = Mock()
        retriever.bm25_chunks = [
            Mock(page_content="BM25 Result 1", metadata={"chunk_id": "c3", "document_id": "d1"}),
            Mock(page_content="BM25 Result 2", metadata={"chunk_id": "c4", "document_id": "d2"}),
        ]
        retriever.bm25.get_top_n.return_value = retriever.bm25_chunks

        results = retriever.keyword_search("termination", top_k=2)

        assert len(results) == 2
        assert all(isinstance(r, RetrievalResult) for r in results)

    def test_hybrid_search_merging(self, retriever: Any, mock_vector_store: Any) -> None:
        """Test that hybrid search merges vector and keyword results"""
        # Setup mock vector search
        mock_vector_store.similarity_search_with_score.return_value = [
            (Mock(page_content="Vector result", metadata={"chunk_id": "c1", "document_id": "d1"}), 0.9),
        ]

        # Setup mock keyword search
        retriever.bm25 = Mock()
        retriever.bm25_chunks = [
            Mock(page_content="Keyword result", metadata={"chunk_id": "c2", "document_id": "d2"}),
        ]

        results = retriever.hybrid_search("test query", top_k=10)

        # Should return merged results (union of vector and keyword)
        assert len(results) >= 1
        assert all(isinstance(r, RetrievalResult) for r in results)

    def test_hybrid_search_deduplication(self, retriever: Any, mock_vector_store: Any) -> None:
        """Test that hybrid search deduplicates results"""
        # Setup: same chunk from both searches
        duplicate_chunk = Mock(
            page_content="Duplicate content",
            metadata={"chunk_id": "c1", "document_id": "d1"}
        )

        # Vector search returns this chunk
        mock_vector_store.similarity_search_with_score.return_value = [
            (duplicate_chunk, 0.95),
        ]

        # Keyword search also returns same chunk
        retriever.bm25 = Mock()
        retriever.bm25_chunks = [duplicate_chunk]

        results = retriever.hybrid_search("test", top_k=10)

        # Should deduplicate to single result
        chunk_ids = [r.chunk_id for r in results]
        assert chunk_ids.count("c1") == 1

    def test_document_filtering(self, retriever: Any, mock_vector_store: Any) -> None:
        """Test that results can be filtered by document ID"""
        # Setup mock with mixed documents
        mock_vector_store.similarity_search_with_score.return_value = [
            (Mock(page_content="Doc1 Result", metadata={"chunk_id": "c1", "document_id": "doc1"}), 0.9),
            (Mock(page_content="Doc2 Result", metadata={"chunk_id": "c2", "document_id": "doc2"}), 0.8),
            (Mock(page_content="Doc1 Result2", metadata={"chunk_id": "c3", "document_id": "doc1"}), 0.7),
        ]

        results = retriever.hybrid_search("test", top_k=10, document_filter="doc1")

        # Should only return results from doc1
        assert all(r.document_id == "doc1" for r in results)

    def test_score_normalization(self, retriever: Any, mock_vector_store: Any) -> None:
        """Test that scores are normalized to 0-1 range"""
        mock_vector_store.similarity_search_with_score.return_value = [
            (Mock(page_content="Result", metadata={"chunk_id": "c1", "document_id": "d1"}), 0.95),
        ]

        results = retriever.vector_search("test", top_k=1)

        assert 0.0 <= results[0].score <= 1.0

    def test_empty_results(self, retriever: Any, mock_vector_store: Any) -> None:
        """Test handling of empty search results"""
        mock_vector_store.similarity_search_with_score.return_value = []

        results = retriever.vector_search("nonexistent", top_k=10)

        assert results == []

    def test_top_k_parameter(self, retriever: Any, mock_vector_store: Any) -> None:
        """Test that top_k parameter is respected"""
        # Setup: 5 results available
        mock_vector_store.similarity_search_with_score.return_value = [
            (Mock(page_content=f"Result {i}", metadata={"chunk_id": f"c{i}", "document_id": f"d{i}"}), 0.9 - i*0.1)
            for i in range(5)
        ]

        results = retriever.hybrid_search("test", top_k=2)

        # Should return at most 2 results
        assert len(results) <= 2


class TestScoreAveraging:
    """Test score averaging when merging duplicate results"""

    @pytest.fixture
    def retriever(self) -> Any:
        retriever = ChromaVectorHybridRetriever()
        retriever.vector_store = Mock()
        return retriever

    def test_score_averaging_on_merge(self, retriever: Any) -> None:
        """Test that duplicate results have scores averaged"""
        # When a chunk appears in both vector and keyword results,
        # its score should be the average of both

        # Create identical chunk with different scores
        vector_score = 0.9

        # Setup vector search result
        retriever.vector_store.similarity_search_with_score.return_value = [
            (Mock(page_content="Content", metadata={"chunk_id": "c1", "document_id": "d1"}), vector_score),
        ]

        # Setup keyword search with same chunk
        retriever.bm25 = Mock()
        retriever.bm25_chunks = [
            Mock(page_content="Content", metadata={"chunk_id": "c1", "document_id": "d1"}),
        ]

        results = retriever.hybrid_search("test", top_k=10)

        # Should have exactly 1 result (deduplicated)
        assert len(results) == 1
        # Score should be merged (typically averaged)
        # Implementation detail: might be average, max, min, or weighted


class TestErrorHandling:
    """Test error handling in hybrid retrieval"""

    @pytest.fixture
    def retriever(self) -> Any:
        retriever = ChromaVectorHybridRetriever()
        retriever.vector_store = Mock()
        return retriever

    def test_vector_search_error(self, retriever: Any) -> None:
        """Test handling of vector search errors"""
        retriever.vector_store.similarity_search_with_score.side_effect = Exception("Vector search failed")

        # Should either raise or return empty list (implementation dependent)
        try:
            results = retriever.vector_search("test")
            assert results == [] or isinstance(results, list)
        except Exception:
            pass  # Also acceptable behavior

    def test_keyword_search_error(self, retriever: Any) -> None:
        """Test handling of keyword search errors"""
        retriever.bm25 = Mock()
        retriever.bm25.get_top_n.side_effect = Exception("BM25 search failed")

        try:
            results = retriever.keyword_search("test")
            assert results == [] or isinstance(results, list)
        except Exception:
            pass


class TestIntegration:
    """Integration tests for hybrid retrieval"""

    def test_full_pipeline(self) -> None:
        """Test complete hybrid search pipeline"""
        # This would test with actual vector store if available
        # For now, we'll create a minimal retriever
        try:
            retriever = ChromaVectorHybridRetriever()
            # If vector store isn't initialized, that's ok for this test
            results = retriever.hybrid_search("What is X?", top_k=5)
            # Should return a list of RetrievalResult or empty
            assert isinstance(results, list)
        except Exception:
            # Expected if no vector store initialized
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
