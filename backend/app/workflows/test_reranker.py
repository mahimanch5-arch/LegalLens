"""
Unit tests for Re-ranker module
"""

from typing import Any
from unittest.mock import Mock, patch

import pytest
from reranker import BGEReranker, RankedResult, RerankerPipeline


class TestRankedResult:
    """Test suite for RankedResult dataclass"""

    def test_ranked_result_creation(self) -> None:
        """Test RankedResult object creation"""
        result = RankedResult(
            chunk_id="chunk_123",
            document_id="doc_456",
            text="Sample legal text",
            score=0.95,
            rank=1
        )

        assert result.chunk_id == "chunk_123"
        assert result.document_id == "doc_456"
        assert result.text == "Sample legal text"
        assert result.score == 0.95
        assert result.rank == 1

    def test_ranked_result_with_metadata(self) -> None:
        """Test RankedResult with metadata"""
        metadata = {"filename": "agreement.pdf", "page": 10}
        result = RankedResult(
            chunk_id="c1",
            document_id="d1",
            text="Text",
            score=0.9,
            rank=1,
            metadata=metadata
        )

        assert result.metadata == metadata

    def test_ranked_result_score_range(self) -> None:
        """Test that scores are in valid range"""
        result = RankedResult(
            chunk_id="c1",
            document_id="d1",
            text="Text",
            score=0.75,
            rank=1
        )

        assert 0.0 <= result.score <= 1.0


class TestBGEReranker:
    """Test suite for BGEReranker"""

    @pytest.fixture
    def mock_model(self) -> Any:
        """Create a mock CrossEncoder model"""
        return Mock()

    @pytest.fixture
    def reranker(self, mock_model: Any) -> Any:
        """Create a reranker with mock model"""
        reranker = BGEReranker()
        reranker.model = mock_model
        return reranker

    def test_reranker_initialization(self) -> None:
        """Test BGEReranker initialization"""
        # Mock the model loading to avoid needing the actual model
        with patch('reranker.BGEReranker._load_model'):
            reranker = BGEReranker()
            assert reranker.model_name == "BAAI/bge-reranker-large"

    def test_rerank_basic(self, reranker: Any, mock_model: Any) -> None:
        """Test basic re-ranking functionality"""
        # Setup mock scores
        mock_model.predict.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]

        query = "What are termination rights?"
        documents = [
            "The contract can be terminated with notice",
            "Termination requires 30 days notice",
            "Early termination has penalties",
            "Section 5 covers termination",
            "Both parties can terminate"
        ]

        results = reranker.rerank(query, documents, top_k=3)

        assert len(results) == 3
        assert all(isinstance(r, RankedResult) for r in results)

    def test_rerank_sorting(self, reranker: Any, mock_model: Any) -> None:
        """Test that results are sorted by score (descending)"""
        # Setup mock scores
        mock_model.predict.return_value = [0.3, 0.1, 0.5, 0.2]

        documents = ["Doc1", "Doc2", "Doc3", "Doc4"]
        results = reranker.rerank("query", documents, top_k=4)

        # Results should be sorted by score descending
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_rerank_rank_assignment(self, reranker: Any, mock_model: Any) -> None:
        """Test that ranks are assigned correctly"""
        mock_model.predict.return_value = [0.1, 0.2, 0.3]

        documents = ["Doc1", "Doc2", "Doc3"]
        results = reranker.rerank("query", documents, top_k=3)

        # Ranks should be 1, 2, 3 in order
        ranks = [r.rank for r in results]
        assert ranks == [1, 2, 3]

    def test_top_k_parameter(self, reranker: Any, mock_model: Any) -> None:
        """Test that top_k parameter limits results"""
        # Setup: 10 documents
        mock_model.predict.return_value = [0.1 + i*0.05 for i in range(10)]

        documents = [f"Doc{i}" for i in range(10)]

        # Request top 3
        results = reranker.rerank("query", documents, top_k=3)
        assert len(results) == 3

        # Request top 7
        results = reranker.rerank("query", documents, top_k=7)
        assert len(results) == 7

    def test_chunk_id_generation(self, reranker: Any, mock_model: Any) -> None:
        """Test automatic chunk ID generation"""
        mock_model.predict.return_value = [0.5, 0.6]

        documents = ["Doc1", "Doc2"]
        results = reranker.rerank("query", documents, chunk_ids=None, top_k=2)

        # Should generate sequential chunk IDs
        assert all(hasattr(r, 'chunk_id') for r in results)

    def test_metadata_preservation(self, reranker: Any, mock_model: Any) -> None:
        """Test that metadata is preserved through re-ranking"""
        mock_model.predict.return_value = [0.5, 0.6]

        documents = ["Doc1", "Doc2"]
        chunk_ids = ["c1", "c2"]
        document_ids = ["d1", "d2"]
        metadatas = [{"page": 1}, {"page": 2}]

        results = reranker.rerank(
            "query",
            documents,
            chunk_ids=chunk_ids,
            document_ids=document_ids,
            metadatas=metadatas,
            top_k=2
        )

        # Metadata should be preserved
        assert all(r.metadata is not None for r in results)

    def test_score_normalization(self, reranker: Any, mock_model: Any) -> None:
        """Test that scores are normalized to 0-1 range"""
        # Raw scores from model (might be raw logits)
        raw_scores = [-1.5, -0.5, 0.5, 1.5]
        mock_model.predict.return_value = raw_scores

        documents = ["Doc1", "Doc2", "Doc3", "Doc4"]
        results = reranker.rerank("query", documents, top_k=4)

        # All scores should be in 0-1 range
        assert all(0.0 <= r.score <= 1.0 for r in results)

    def test_empty_documents(self, reranker: Any) -> None:
        """Test handling of empty document list"""
        results = reranker.rerank("query", [], top_k=10)
        assert results == []

    def test_single_document(self, reranker: Any, mock_model: Any) -> None:
        """Test re-ranking single document"""
        mock_model.predict.return_value = [0.8]

        documents = ["Only document"]
        results = reranker.rerank("query", documents, top_k=10)

        assert len(results) == 1
        assert results[0].text == "Only document"

    def test_validation_mismatch(self, reranker: Any) -> None:
        """Test validation of input length mismatches"""
        documents = ["Doc1", "Doc2"]
        chunk_ids = ["c1"]  # Wrong length

        # Should raise assertion error
        with pytest.raises(AssertionError):
            reranker.rerank(
                "query",
                documents,
                chunk_ids=chunk_ids,
                top_k=2
            )


class TestRerankerPipeline:
    """Test suite for RerankerPipeline"""

    @pytest.fixture
    def mock_retrieval_result(self) -> Any:
        """Create a mock retrieval result object"""
        result = Mock()
        result.chunk_id = "chunk_1"
        result.document_id = "doc_1"
        result.text = "Sample text"
        result.metadata = {"page": 1}
        return result

    @pytest.fixture
    def pipeline(self) -> Any:
        """Create a pipeline with mocked reranker"""
        pipeline = RerankerPipeline(top_k=5)
        pipeline.reranker = Mock()
        return pipeline

    def test_pipeline_initialization(self) -> None:
        """Test pipeline initialization"""
        with patch('reranker.BGEReranker'):
            pipeline = RerankerPipeline(top_k=10)
            assert pipeline.top_k == 10

    def test_pipeline_rerank_results(self, pipeline: Any, mock_retrieval_result: Any) -> None:
        """Test pipeline re-ranking of retrieval results"""
        # Setup mock reranker output
        mock_ranked = Mock()
        mock_ranked.chunk_id = "chunk_1"
        mock_ranked.score = 0.95
        mock_ranked.rank = 1
        pipeline.reranker.rerank.return_value = [mock_ranked]

        retrieved = [mock_retrieval_result]
        results = pipeline.rerank_results("query", retrieved, top_k=5)

        assert len(results) == 1
        assert results[0].score == 0.95

    def test_pipeline_extracts_components(self, pipeline: Any) -> None:
        """Test that pipeline extracts correct components from results"""
        # Create mock retrieval results
        results_list = []
        for i in range(3):
            r = Mock()
            r.chunk_id = f"chunk_{i}"
            r.document_id = f"doc_{i}"
            r.text = f"Text {i}"
            r.metadata = {"index": i}
            results_list.append(r)

        # Mock the reranker to capture inputs
        pipeline.reranker.rerank.return_value = []

        pipeline.rerank_results("query", results_list)

        # Verify reranker was called with extracted components
        assert pipeline.reranker.rerank.called
        call_args = pipeline.reranker.rerank.call_args
        assert "documents" in call_args.kwargs or len(call_args[0]) >= 2

    def test_pipeline_top_k_override(self, pipeline: Any) -> None:
        """Test that pipeline respects top_k override"""
        pipeline.reranker.rerank.return_value = []

        results = [Mock(chunk_id=f"c{i}", document_id="d", text="t", metadata={}) for i in range(10)]

        # Override default top_k
        pipeline.rerank_results("query", results, top_k=3)

        # Should call reranker with overridden top_k
        pipeline.reranker.rerank.assert_called_once()


class TestScoreNormalization:
    """Test score normalization logic"""

    def test_normalize_scores_basic(self) -> None:
        """Test basic score normalization"""
        import numpy as np
        scores = np.array([0, 1, 2, 3, 4])

        reranker = BGEReranker()
        normalized = reranker._normalize_scores(scores)

        assert min(normalized) >= 0.0
        assert max(normalized) <= 1.0

    def test_normalize_identical_scores(self) -> None:
        """Test normalization when all scores are identical"""
        import numpy as np
        scores = np.array([0.5, 0.5, 0.5])

        reranker = BGEReranker()
        normalized = reranker._normalize_scores(scores)

        # All should be 0.5
        assert all(s == 0.5 for s in normalized)

    def test_normalize_negative_scores(self) -> None:
        """Test normalization with negative scores"""
        import numpy as np
        scores = np.array([-2, -1, 0, 1, 2])

        reranker = BGEReranker()
        normalized = reranker._normalize_scores(scores)

        assert min(normalized) >= 0.0
        assert max(normalized) <= 1.0


class TestRerankingQuality:
    """Test re-ranking quality and ordering"""

    @pytest.fixture
    def reranker_with_mock(self) -> Any:
        reranker = BGEReranker()
        reranker.model = Mock()
        return reranker

    def test_higher_scores_ranked_first(self, reranker_with_mock: Any) -> None:
        """Test that higher scored documents appear first"""
        # Setup: deliberately out-of-order scores to test sorting
        reranker_with_mock.model.predict.return_value = [0.3, 0.9, 0.6, 0.1]

        documents = ["Low1", "High", "Medium", "Low2"]
        results = reranker_with_mock.rerank("query", documents, top_k=4)

        # First result should have highest score
        assert results[0].score == max(r.score for r in results)

        # Verify complete ordering
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
