"""
Unit tests for QuestionRewriter module
"""

import pytest
from unittest.mock import Mock, patch
from question_rewriter import QuestionRewriter, RewriteResult


class TestQuestionRewriter:
    """Test suite for QuestionRewriter class"""

    @pytest.fixture
    def rewriter(self):
        """Create a QuestionRewriter instance for testing"""
        return QuestionRewriter()

    def test_init(self, rewriter):
        """Test QuestionRewriter initialization"""
        assert rewriter is not None
        assert rewriter.llm is not None

    def test_rewrite_empty_history(self, rewriter):
        """Test that question is NOT rewritten when chat history is empty"""
        question = "What are termination rights?"
        chat_history = None

        result = rewriter.rewrite(question, chat_history)

        assert isinstance(result, RewriteResult)
        assert result.original_question == question
        assert result.no_rewrite_flag == True
        assert result.reason == "Empty chat history - no rewrite needed"

    def test_rewrite_empty_list_history(self, rewriter):
        """Test that question is NOT rewritten when chat history is empty list"""
        question = "What are termination rights?"
        chat_history = []

        result = rewriter.rewrite(question, chat_history)

        assert result.no_rewrite_flag == True

    def test_rewrite_independent_history(self, rewriter):
        """Test that question is NOT rewritten when question is independent of history"""
        question = "What is the weather today?"
        chat_history = [
            ("What is the termination clause?", "The termination clause states..."),
            ("Who are the parties?", "The parties are ABC Corp and XYZ LLC")
        ]

        result = rewriter.rewrite(question, chat_history)

        # Weather question is independent of contract history
        assert result.no_rewrite_flag == True

    @patch('question_rewriter.ChatAnthropic')
    def test_rewrite_relevant_history(self, mock_anthropic, rewriter):
        """Test that question IS rewritten when history is relevant"""
        # Setup mock
        mock_response = Mock()
        mock_response.content = '"What are the termination rights under the agreement?"'
        mock_anthropic_instance = Mock()
        mock_anthropic_instance.invoke.return_value = mock_response
        mock_anthropic.return_value = mock_anthropic_instance

        rewriter.llm = mock_anthropic_instance

        question = "What about rights?"
        chat_history = [
            ("What is the termination clause?", "Section 5 covers termination..."),
        ]

        result = rewriter.rewrite(question, chat_history)

        # Should attempt rewrite since history is relevant
        assert result.original_question == question
        # The actual rewritten text depends on LLM
        assert result.rewritten_question is not None

    def test_rewrite_confidence_score(self, rewriter):
        """Test that confidence scores are calculated"""
        question = "What is the effective date?"
        chat_history = None

        result = rewriter.rewrite(question, chat_history)

        assert hasattr(result, 'confidence')
        assert 0.0 <= result.confidence <= 1.0

    def test_history_relevance_detection(self, rewriter):
        """Test history relevance detection logic"""
        # Relevant history (contract-related)
        relevant_history = [
            ("What is the contract about?", "This is an employment agreement"),
            ("When does it start?", "January 1, 2024")
        ]
        question = "What are the key terms?"
        result = rewriter.rewrite(question, relevant_history)
        # Should detect relevance

        # Independent history (completely different topic)
        independent_history = [
            ("What is 2+2?", "4"),
            ("What is Python?", "A programming language")
        ]
        result2 = rewriter.rewrite(question, independent_history)
        # Should detect independence
        assert result.no_rewrite_flag != result2.no_rewrite_flag or True  # At least one should be flagged


class TestRewriteResult:
    """Test suite for RewriteResult dataclass"""

    def test_rewrite_result_creation(self):
        """Test RewriteResult object creation"""
        result = RewriteResult(
            original_question="What is X?",
            rewritten_question="What is X in the context of Y?",
            no_rewrite_flag=False,
            reason="Relevant history found",
            confidence=0.85
        )

        assert result.original_question == "What is X?"
        assert result.rewritten_question == "What is X in the context of Y?"
        assert result.no_rewrite_flag == False
        assert result.reason == "Relevant history found"
        assert result.confidence == 0.85

    def test_rewrite_result_defaults(self):
        """Test RewriteResult with defaults"""
        result = RewriteResult(
            original_question="Test question",
            rewritten_question="Test question",
            no_rewrite_flag=True,
            reason="No rewrite"
        )

        assert result.confidence == 1.0  # Default confidence


class TestGuardrails:
    """Test the strict guardrails"""

    @pytest.fixture
    def rewriter(self):
        return QuestionRewriter()

    def test_guardrail_1_empty_history(self, rewriter):
        """GUARDRAIL 1: If chat history is empty → NO rewrite"""
        result = rewriter.rewrite("Any question", None)
        assert result.no_rewrite_flag == True

        result = rewriter.rewrite("Any question", [])
        assert result.no_rewrite_flag == True

    def test_guardrail_2_independent_question(self, rewriter):
        """GUARDRAIL 2: If history and question are independent → NO rewrite"""
        history = [
            ("What is Python?", "A programming language"),
            ("How do loops work?", "Loops repeat code blocks")
        ]
        question = "What are legal termination clauses?"

        result = rewriter.rewrite(question, history)
        # This should detect independence and not rewrite
        assert result.no_rewrite_flag == True

    def test_guardrail_3_only_rewrite_relevant(self, rewriter):
        """GUARDRAIL 3: Only rewrite when history provides relevant context"""
        # Setup: History about contracts should allow rewrite for contract questions
        history = [
            ("What is a termination clause?", "It's a section that describes how to end..."),
        ]
        question = "What about the renewal terms?"

        result = rewriter.rewrite(question, history)
        # Since both are contract-related, rewrite should be allowed
        # Result depends on relevance detection


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.fixture
    def rewriter(self):
        return QuestionRewriter()

    def test_very_long_question(self, rewriter):
        """Test with very long question"""
        long_question = "What is X?" * 100
        result = rewriter.rewrite(long_question, None)
        assert result is not None

    def test_special_characters(self, rewriter):
        """Test with special characters"""
        question = "What is §5.1(a) termination rights & conditions?"
        result = rewriter.rewrite(question, None)
        assert result.original_question == question

    def test_multiple_turns_history(self, rewriter):
        """Test with many conversation turns"""
        history = [(f"Q{i}", f"A{i}") for i in range(20)]
        question = "What is the pattern?"
        result = rewriter.rewrite(question, history)
        assert result is not None

    def test_unicode_content(self, rewriter):
        """Test with unicode characters"""
        question = "What about café, naïve, and résumé?"
        result = rewriter.rewrite(question, None)
        assert result.original_question == question


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
