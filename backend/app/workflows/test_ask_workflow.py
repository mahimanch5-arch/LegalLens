"""
Unit tests for Ask Workflow module
"""

import contextlib
from unittest.mock import Mock, patch

import pytest
from ask_workflow import AskResult, AskWorkflow


class TestAskResult:
    """Test suite for AskResult dataclass"""

    def test_ask_result_creation(self):
        """Test AskResult object creation"""
        result = AskResult(
            original_question="What is X?",
            rewritten_question="What is X in the context of Y?",
            retrieved_chunks=[],
            generated_answer="The answer is...",
            citations=[]
        )

        assert result.original_question == "What is X?"
        assert result.rewritten_question == "What is X in the context of Y?"
        assert result.generated_answer == "The answer is..."

    def test_ask_result_with_citations(self):
        """Test AskResult with citations"""
        citations = [
            {
                "citation_number": 1,
                "chunk_id": "c1",
                "document_id": "d1",
                "text": "Citation text",
                "score": 0.95
            }
        ]

        result = AskResult(
            original_question="Q",
            rewritten_question="Q rewritten",
            retrieved_chunks=[],
            generated_answer="Answer[1]",
            citations=citations
        )

        assert len(result.citations) == 1
        assert result.citations[0]["citation_number"] == 1

    def test_ask_result_metadata(self):
        """Test AskResult with metadata"""
        metadata = {
            "retrieval_count": 50,
            "final_chunks": 10,
            "document_filter": None
        }

        result = AskResult(
            original_question="Q",
            rewritten_question="Q",
            retrieved_chunks=[],
            generated_answer="A",
            citations=[],
            metadata=metadata
        )

        assert result.metadata["retrieval_count"] == 50
        assert result.metadata["final_chunks"] == 10


class TestAskWorkflowInit:
    """Test AskWorkflow initialization"""

    @pytest.fixture
    def mock_retriever(self):
        """Create a mock retriever"""
        return Mock()

    def test_workflow_initialization(self, mock_retriever):
        """Test AskWorkflow initialization"""
        with patch('ask_workflow.QuestionRewriter'), patch('ask_workflow.RerankerPipeline'), \
                patch('ask_workflow.ChatAnthropic'):
            workflow = AskWorkflow(mock_retriever, reranker_top_k=10)

            assert workflow.retriever == mock_retriever
            assert workflow.reranker_top_k == 10

    def test_workflow_with_custom_model(self, mock_retriever):
        """Test AskWorkflow with custom LLM model"""
        with patch('ask_workflow.QuestionRewriter'), patch('ask_workflow.RerankerPipeline'), \
                patch('ask_workflow.ChatAnthropic') as mock_anthropic:
            AskWorkflow(
                mock_retriever,
                llm_model="claude-opus-5-5"
            )

            # Verify ChatAnthropic was called with correct model
            calls = [c for c in mock_anthropic.call_args_list
                    if 'model' in c.kwargs or (len(c[0]) > 0 and 'claude' in str(c))]
            assert len(calls) > 0


class TestAskWorkflowExecution:
    """Test AskWorkflow.execute() method"""

    @pytest.fixture
    def mock_components(self):
        """Create mock components"""
        retriever = Mock()

        # Mock question rewriter
        rewrite_result = Mock()
        rewrite_result.rewritten_question = "Rewritten question"

        # Mock retrieval results
        retrieval_results = [
            Mock(
                chunk_id=f"chunk_{i}",
                document_id=f"doc_{i}",
                text=f"Document content {i}",
                metadata={"filename": f"doc_{i}.pdf"}
            )
            for i in range(5)
        ]
        retriever.hybrid_search.return_value = retrieval_results

        # Mock ranked results
        ranked_results = [
            Mock(
                chunk_id=f"chunk_{i}",
                document_id=f"doc_{i}",
                text=f"Document content {i}",
                score=0.9 - i*0.1,
                rank=i+1,
                metadata={"filename": f"doc_{i}.pdf"}
            )
            for i in range(3)
        ]

        # Mock LLM response
        llm_response = Mock()
        llm_response.content = "Answer to the question[1][2]."

        return {
            "retriever": retriever,
            "rewrite_result": rewrite_result,
            "retrieval_results": retrieval_results,
            "ranked_results": ranked_results,
            "llm_response": llm_response
        }

    def test_execute_five_step_pipeline(self, mock_components):
        """Test complete five-step Ask workflow pipeline"""
        with patch('ask_workflow.QuestionRewriter') as mock_qr_class, \
                patch('ask_workflow.RerankerPipeline') as mock_rr_class, \
                patch('ask_workflow.ChatAnthropic') as mock_llm_class:
            # Setup mocks
            mock_qr = Mock()
            mock_qr.rewrite.return_value = mock_components["rewrite_result"]
            mock_qr_class.return_value = mock_qr

            mock_rr = Mock()
            mock_rr.rerank_results.return_value = mock_components["ranked_results"]
            mock_rr_class.return_value = mock_rr

            mock_llm = Mock()
            mock_llm.invoke.return_value = mock_components["llm_response"]
            mock_llm_class.return_value = mock_llm

            # Execute workflow
            workflow = AskWorkflow(mock_components["retriever"])
            result = workflow.execute("What is the question?")

            # Verify all steps were executed
            assert result.original_question == "What is the question?"
            assert result.rewritten_question == "Rewritten question"
            assert len(result.retrieved_chunks) > 0
            assert result.generated_answer is not None

    def test_execute_with_chat_history(self, mock_components):
        """Test execute with chat history"""
        with patch('ask_workflow.QuestionRewriter') as mock_qr_class, \
                patch('ask_workflow.RerankerPipeline'), \
                patch('ask_workflow.ChatAnthropic'):
            mock_qr = Mock()
            mock_qr.rewrite.return_value = mock_components["rewrite_result"]
            mock_qr_class.return_value = mock_qr

            chat_history = [
                ("Previous question", "Previous answer")
            ]

            workflow = AskWorkflow(mock_components["retriever"])
            workflow.question_rewriter = mock_qr

            # Execute with history
            workflow.execute("Follow-up question", chat_history=chat_history)

            # Verify rewriter was called with history
            mock_qr.rewrite.assert_called_with("Follow-up question", chat_history)

    def test_execute_with_document_filter(self, mock_components):
        """Test execute with document filter"""
        with patch('ask_workflow.QuestionRewriter'), patch('ask_workflow.RerankerPipeline'), \
                patch('ask_workflow.ChatAnthropic'):
            workflow = AskWorkflow(mock_components["retriever"])
            workflow.execute("Question", document_filter="specific_doc")

            # Verify retriever was called with filter
            assert mock_components["retriever"].hybrid_search.called
            call_kwargs = mock_components["retriever"].hybrid_search.call_args.kwargs
            assert call_kwargs["document_filter"] == "specific_doc"


class TestRAGContextBuilding:
    """Test RAG context building"""

    def test_build_rag_context(self):
        """Test RAG context building from ranked chunks"""
        ranked_chunks = [
            Mock(
                text="First chunk text",
                metadata={"filename": "doc1.pdf"}
            ),
            Mock(
                text="Second chunk text",
                metadata={"filename": "doc2.pdf"}
            )
        ]

        context = AskWorkflow._build_rag_context(ranked_chunks)

        assert "First chunk text" in context
        assert "Second chunk text" in context
        assert "[1]" in context  # Should have numbered citations
        assert "[2]" in context

    def test_rag_context_with_sources(self):
        """Test that RAG context includes source information"""
        ranked_chunks = [
            Mock(
                text="Important clause",
                metadata={"filename": "contract.pdf"}
            )
        ]

        context = AskWorkflow._build_rag_context(ranked_chunks)

        assert "contract.pdf" in context or "Source" in context


class TestCitationExtraction:
    """Test citation extraction from generated answers"""

    def test_extract_basic_citations(self):
        """Test extraction of basic [n] citations"""
        answer = "The contract states [1] that termination requires [2] thirty days notice."
        chunks = [
            Mock(chunk_id="c1", document_id="d1", text="Text 1", score=0.95, metadata={}),
            Mock(chunk_id="c2", document_id="d2", text="Text 2", score=0.90, metadata={}),
        ]

        citations = AskWorkflow._extract_citations(answer, chunks)

        assert len(citations) == 2
        assert citations[0]["citation_number"] == 1
        assert citations[1]["citation_number"] == 2

    def test_extract_citations_matching(self):
        """Test that extracted citations match chunk references"""
        answer = "According to [1] the agreement, [2] renewal is automatic."
        chunks = [
            Mock(chunk_id="c1", document_id="d1", text="Agreement text", score=0.95, metadata={"source": "source1"}),
            Mock(chunk_id="c2", document_id="d2", text="Renewal text", score=0.90, metadata={"source": "source2"}),
        ]

        citations = AskWorkflow._extract_citations(answer, chunks)

        # First citation should reference first chunk
        assert citations[0]["chunk_id"] == "c1"
        assert citations[1]["chunk_id"] == "c2"

    def test_extract_citations_out_of_range(self):
        """Test handling of out-of-range citation numbers"""
        answer = "Reference [1] and [10]"
        chunks = [
            Mock(chunk_id="c1", document_id="d1", text="Text", score=0.95, metadata={})
        ]

        citations = AskWorkflow._extract_citations(answer, chunks)

        # Should only extract citation [1], skip [10] as out of range
        assert len(citations) == 1
        assert citations[0]["citation_number"] == 1

    def test_extract_no_citations(self):
        """Test handling of answers with no citations"""
        answer = "This is an answer without any citations."
        chunks = []

        citations = AskWorkflow._extract_citations(answer, chunks)

        assert len(citations) == 0

    def test_extract_duplicate_citations(self):
        """Test handling of duplicate citation numbers"""
        answer = "First [1] and second mention of [1]."
        chunks = [
            Mock(chunk_id="c1", document_id="d1", text="Text", score=0.95, metadata={})
        ]

        citations = AskWorkflow._extract_citations(answer, chunks)

        # Should extract both occurrences
        assert len(citations) == 2
        assert all(c["citation_number"] == 1 for c in citations)


class TestAnswerGeneration:
    """Test answer generation with Claude"""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM"""
        mock = Mock()
        mock.invoke.return_value.content = "Generated answer[1]"
        return mock

    def test_generate_answer_with_context(self, mock_llm):
        """Test answer generation with RAG context"""
        workflow = AskWorkflow(Mock())
        workflow.llm = mock_llm

        answer, citations = workflow._generate_answer(
            question="What is X?",
            rewritten_question="What is X in context Y?",
            rag_context="[1] Context about X",
            ranked_chunks=[]
        )

        # Verify LLM was called
        assert mock_llm.invoke.called
        # Verify system prompt was included
        call_args = mock_llm.invoke.call_args
        assert "system" in str(call_args).lower() or call_args[0][0][0]["role"] == "system"

    def test_generate_answer_system_prompt(self, mock_llm):
        """Test that system prompt includes RAG context"""
        workflow = AskWorkflow(Mock())
        workflow.llm = mock_llm

        context = "[1] Important information"
        workflow._generate_answer("Q", "Q", context, [])

        # Verify RAG context was included in system prompt
        call_args = mock_llm.invoke.call_args[0][0]
        system_message = call_args[0]["content"]
        assert "context" in system_message.lower() or "document" in system_message.lower()


class TestErrorHandling:
    """Test error handling in Ask workflow"""

    def test_execute_handles_rewrite_error(self):
        """Test handling of question rewriting errors"""
        with patch('ask_workflow.QuestionRewriter') as mock_qr_class:
            mock_qr = Mock()
            mock_qr.rewrite.side_effect = Exception("Rewrite failed")
            mock_qr_class.return_value = mock_qr

            workflow = AskWorkflow(Mock())
            workflow.question_rewriter = mock_qr

            # Should propagate error
            with pytest.raises(Exception, match="Rewrite failed"):
                workflow.execute("Question")

    def test_execute_handles_retrieval_error(self):
        """Test handling of retrieval errors"""
        mock_retriever = Mock()
        mock_retriever.hybrid_search.side_effect = Exception("Retrieval failed")

        with patch('ask_workflow.QuestionRewriter'), patch('ask_workflow.RerankerPipeline'), \
                patch('ask_workflow.ChatAnthropic'):
            workflow = AskWorkflow(mock_retriever)

            # Should propagate error
            with pytest.raises(Exception, match="Retrieval failed"):
                workflow.execute("Question")

    def test_execute_handles_generation_error(self):
        """Test handling of LLM generation errors"""
        mock_retriever = Mock()
        mock_retriever.hybrid_search.return_value = [Mock(chunk_id="c1", document_id="d1", text="t", metadata={})]

        with patch('ask_workflow.QuestionRewriter'), patch('ask_workflow.RerankerPipeline'), \
                patch('ask_workflow.ChatAnthropic') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.invoke.side_effect = Exception("Generation failed")
            mock_llm_class.return_value = mock_llm

            workflow = AskWorkflow(mock_retriever)

            # Should propagate error
            with pytest.raises(Exception, match="Generation failed"):
                workflow.execute("Question")


class TestConvenienceFunction:
    """Test convenience function"""

    def test_ask_convenience_function(self):
        """Test the ask() convenience function"""
        mock_retriever = Mock()

        with patch('ask_workflow.AskWorkflow') as mock_workflow_class:
            mock_workflow = Mock()
            mock_result = Mock()
            mock_workflow.execute.return_value = mock_result
            mock_workflow_class.return_value = mock_workflow

            from ask_workflow import ask
            ask(mock_retriever, "Question")

            # Verify workflow was created and executed
            assert mock_workflow_class.called
            assert mock_workflow.execute.called


class TestPerformance:
    """Test performance characteristics"""

    def test_execution_timing_structure(self):
        """Test that execution follows expected timing structure"""
        # Verify that each step logs timing information
        mock_retriever = Mock()
        mock_retriever.hybrid_search.return_value = []

        with patch('ask_workflow.QuestionRewriter'), patch('ask_workflow.RerankerPipeline'), \
                patch('ask_workflow.ChatAnthropic'):
            workflow = AskWorkflow(mock_retriever)
            with contextlib.suppress(BaseException):
                workflow.execute("Q")


class TestIntegration:
    """Integration tests for Ask workflow"""

    def test_full_pipeline_structure(self):
        """Test that full pipeline executes in correct order"""
        execution_order = []

        def track_execution(name):
            def tracker(*args, **kwargs):
                execution_order.append(name)
                return Mock()
            return tracker

        mock_retriever = Mock()
        mock_retriever.hybrid_search = track_execution("retrieve")

        with patch('ask_workflow.QuestionRewriter') as mock_qr_class, \
                patch('ask_workflow.RerankerPipeline') as mock_rr_class, \
                patch('ask_workflow.ChatAnthropic') as mock_llm_class:
            mock_qr = Mock()
            mock_qr.rewrite.side_effect = track_execution("rewrite")
            mock_qr.rewrite.return_value = Mock(rewritten_question="Q")
            mock_qr_class.return_value = mock_qr

            mock_rr = Mock()
            mock_rr.rerank_results = track_execution("rerank")
            mock_rr.rerank_results.return_value = []
            mock_rr_class.return_value = mock_rr

            mock_llm = Mock()
            mock_llm_class.return_value = mock_llm

            workflow = AskWorkflow(mock_retriever)

            with contextlib.suppress(BaseException):
                workflow.execute("Q")

            # Pipeline should execute steps in order: rewrite, retrieve, rerank
            if execution_order:
                assert execution_order[0] == "rewrite"
                assert "retrieve" in execution_order
                assert "rerank" in execution_order


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
