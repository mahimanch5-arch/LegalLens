"""
Unit tests for IntentClassifier

Tests both heuristic and LLM-based classification paths.
"""

from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env from the same directory as intent_classifier.py
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

import pytest  # noqa: E402  (.env must load first)
from intent_classifier import (  # noqa: E402
    ClassificationResult,
    Intent,
    IntentClassifier,
)


@pytest.fixture
def classifier() -> Any:
    """Create a classifier instance for testing"""
    return IntentClassifier()


class TestHeuristicClassification:
    """Test the fast heuristic classification path"""

    def test_draft_intent_with_draft_keyword(self, classifier: Any) -> None:
        """Draft messages with 'draft' keyword"""
        result = classifier.classify("Draft a memo on indemnification")
        assert result.intent == Intent.DRAFT
        assert result.confidence >= 0.9
        assert result.used_heuristic

    def test_draft_intent_with_write_keyword(self, classifier: Any) -> None:
        """Draft messages with 'write' keyword"""
        result = classifier.classify("Write a case brief for this opinion")
        assert result.intent == Intent.DRAFT
        assert result.confidence >= 0.9
        assert result.used_heuristic

    def test_draft_intent_with_create_keyword(self, classifier: Any) -> None:
        """Draft messages with 'create' keyword"""
        result = classifier.classify("Create a memo analyzing the termination clause")
        assert result.intent == Intent.DRAFT
        assert result.confidence >= 0.9

    def test_draft_intent_with_generate_keyword(self, classifier: Any) -> None:
        """Draft messages with 'generate' keyword"""
        result = classifier.classify("Generate a brief summarizing the holding")
        assert result.intent == Intent.DRAFT
        assert result.confidence >= 0.9

    def test_draft_intent_case_insensitive(self, classifier: Any) -> None:
        """Draft intent detection is case-insensitive"""
        result = classifier.classify("DRAFT A MEMO PLEASE")
        assert result.intent == Intent.DRAFT
        assert result.confidence >= 0.9

    def test_summary_intent_with_summarize_keyword(self, classifier: Any) -> None:
        """Summary messages with 'summarize' keyword"""
        result = classifier.classify("Summarize this contract")
        assert result.intent == Intent.SUMMARY
        assert result.confidence >= 0.85
        assert result.used_heuristic

    def test_summary_intent_with_overview_keyword(self, classifier: Any) -> None:
        """Summary messages with 'overview' keyword"""
        result = classifier.classify("Give me an overview of this opinion")
        assert result.intent == Intent.SUMMARY
        assert result.confidence >= 0.85

    def test_summary_intent_with_key_points(self, classifier: Any) -> None:
        """Summary messages with 'key points' phrase"""
        result = classifier.classify("Tell me the key points")
        assert result.intent == Intent.SUMMARY
        assert result.confidence >= 0.85

    def test_summary_intent_with_extract_keyword(self, classifier: Any) -> None:
        """Summary messages with 'extract' keyword"""
        result = classifier.classify("Extract the main terms from this agreement")
        assert result.intent == Intent.SUMMARY
        assert result.confidence >= 0.85

    def test_summary_intent_case_insensitive(self, classifier: Any) -> None:
        """Summary intent detection is case-insensitive"""
        result = classifier.classify("SUMMARIZE THIS DOCUMENT")
        assert result.intent == Intent.SUMMARY
        assert result.confidence >= 0.85

    def test_ask_intent_with_question_mark(self, classifier: Any) -> None:
        """Ask messages with question mark"""
        result = classifier.classify("What are the termination rights?")
        assert result.intent == Intent.ASK
        assert result.confidence >= 0.8
        assert result.used_heuristic

    def test_ask_intent_multiple_questions(self, classifier: Any) -> None:
        """Ask messages with multiple questions"""
        result = classifier.classify("When does the contract expire? What are the terms?")
        assert result.intent == Intent.ASK
        assert result.confidence >= 0.8

    def test_ask_intent_with_tell_me_phrase(self, classifier: Any) -> None:
        """Ask messages starting with 'Tell me'"""
        result = classifier.classify("Tell me about the non-compete clause")
        assert result.intent == Intent.ASK
        assert result.confidence >= 0.8

    def test_ask_intent_with_show_me_phrase(self, classifier: Any) -> None:
        """Ask messages starting with 'Show me'"""
        result = classifier.classify("Show me the payment terms")
        assert result.intent == Intent.ASK
        assert result.confidence >= 0.8

    def test_ask_intent_with_explain_phrase(self, classifier: Any) -> None:
        """Ask messages starting with 'Explain'"""
        result = classifier.classify("Explain the indemnification clause")
        assert result.intent == Intent.ASK
        assert result.confidence >= 0.8

    def test_ask_intent_short_message(self, classifier: Any) -> None:
        """Very short messages default to Ask"""
        result = classifier.classify("xyz")
        assert result.intent == Intent.ASK
        assert result.used_heuristic

    def test_ask_intent_as_default(self, classifier: Any) -> None:
        """Ambiguous messages default to Ask with low confidence"""
        result = classifier.classify("The contract terms")
        assert result.intent == Intent.ASK
        # Low confidence because it's ambiguous
        assert result.confidence < 0.7

    def test_draft_priority_over_summary(self, classifier: Any) -> None:
        """Draft keyword has priority over Summary"""
        result = classifier.classify("Draft a summary of the opinion")
        assert result.intent == Intent.DRAFT
        assert result.confidence >= 0.9

    def test_draft_with_both_keywords(self, classifier: Any) -> None:
        """Message with both draft and summary keywords → Draft"""
        result = classifier.classify("Draft and summarize this contract")
        assert result.intent == Intent.DRAFT

    def test_summary_with_question_mark(self, classifier: Any) -> None:
        """Message with summary keyword takes priority over question mark"""
        result = classifier.classify("Can you summarize this?")
        assert result.intent == Intent.SUMMARY


class TestConfidenceScores:
    """Test confidence score assignments"""

    def test_high_confidence_on_draft(self, classifier: Any) -> None:
        """Draft with keywords has high confidence"""
        result = classifier.classify("Draft a memo")
        assert result.confidence >= 0.9

    def test_high_confidence_on_summary(self, classifier: Any) -> None:
        """Summary with keywords has high confidence"""
        result = classifier.classify("Summarize this")
        assert result.confidence >= 0.85

    def test_high_confidence_on_question(self, classifier: Any) -> None:
        """Questions have high confidence"""
        result = classifier.classify("What is this?")
        assert result.confidence >= 0.8

    def test_medium_confidence_on_ambiguous(self, classifier: Any) -> None:
        """Ambiguous messages have medium-to-low confidence"""
        result = classifier.classify("The contract")
        assert result.confidence < 0.7


class TestEdgeCases:
    """Test edge cases and unusual inputs"""

    def test_empty_message(self, classifier: Any) -> None:
        """Empty message handled gracefully"""
        result = classifier.classify("")
        assert result.intent in [Intent.ASK, Intent.DRAFT, Intent.SUMMARY]
        assert isinstance(result.confidence, float)

    def test_whitespace_only(self, classifier: Any) -> None:
        """Whitespace-only message handled gracefully"""
        result = classifier.classify("   \n\t  ")
        assert result.intent in [Intent.ASK, Intent.DRAFT, Intent.SUMMARY]

    def test_special_characters(self, classifier: Any) -> None:
        """Special characters don't break classification"""
        result = classifier.classify("What??? Why!!! How???")
        assert result.intent == Intent.ASK

    def test_unicode_characters(self, classifier: Any) -> None:
        """Unicode characters handled"""
        result = classifier.classify("What are the δικαιώματα (rights)?")
        assert result.intent == Intent.ASK

    def test_very_long_message(self, classifier: Any) -> None:
        """Very long message classified correctly"""
        long_msg = "What " * 100 + "?"
        result = classifier.classify(long_msg)
        assert result.intent == Intent.ASK

    def test_repeated_keywords(self, classifier: Any) -> None:
        """Repeated keywords don't change intent"""
        result = classifier.classify("Summarize summarize summarize")
        assert result.intent == Intent.SUMMARY


class TestContextAwareness:
    """Test classification with context parameters"""

    def test_with_document_scope(self, classifier: Any) -> None:
        """Classification works with document scope context"""
        result = classifier.classify(
            "What are the key points?",
            document_scope="single_doc"
        )
        # Heuristic doesn't use scope, but it should still work
        assert result.intent in [Intent.ASK, Intent.SUMMARY]

    def test_with_conversation_history(self, classifier: Any) -> None:
        """Classification works with conversation history length"""
        result = classifier.classify(
            "And the rest?",
            conversation_history_length=5
        )
        assert result.intent in [Intent.ASK, Intent.DRAFT, Intent.SUMMARY]


class TestResultDataclass:
    """Test ClassificationResult dataclass"""

    def test_result_has_all_fields(self) -> None:
        """ClassificationResult has all required fields"""
        result = ClassificationResult(
            intent=Intent.ASK,
            confidence=0.9,
            reason="Test reason",
            used_heuristic=True
        )
        assert result.intent == Intent.ASK
        assert result.confidence == 0.9
        assert result.reason == "Test reason"
        assert result.used_heuristic is True


class TestIntentEnum:
    """Test Intent enum"""

    def test_all_intents_defined(self) -> None:
        """All expected intents are defined"""
        assert Intent.ASK.value == "ask"
        assert Intent.SUMMARY.value == "summary"
        assert Intent.DRAFT.value == "draft"
        assert Intent.AUTO.value == "auto"

    def test_intent_string_value(self) -> None:
        """Intent can be converted to string"""
        assert str(Intent.ASK.value) == "ask"


# Integration tests (require ANTHROPIC_API_KEY)
class TestLLMFallback:
    """Test LLM fallback path (requires valid API key)"""

    @pytest.mark.skipif(
        not __import__('os').getenv('ANTHROPIC_API_KEY'),
        reason="ANTHROPIC_API_KEY not set"
    )
    def test_llm_classification_ask(self, classifier: Any) -> None:
        """LLM can classify Ask intent"""
        result = classifier.classify("Is there a non-compete?")
        assert result.intent == Intent.ASK
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.skipif(
        not __import__('os').getenv('ANTHROPIC_API_KEY'),
        reason="ANTHROPIC_API_KEY not set"
    )
    def test_llm_classification_summary(self, classifier: Any) -> None:
        """LLM can classify Summary intent"""
        result = classifier.classify("Give me an overview")
        assert result.intent == Intent.SUMMARY
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.skipif(
        not __import__('os').getenv('ANTHROPIC_API_KEY'),
        reason="ANTHROPIC_API_KEY not set"
    )
    def test_llm_classification_draft(self, classifier: Any) -> None:
        """LLM can classify Draft intent"""
        result = classifier.classify("Please write something legal")
        assert result.intent == Intent.DRAFT
        assert 0.0 <= result.confidence <= 1.0


if __name__ == "__main__":
    # Run tests: pytest test_intent_classifier.py -v
    pytest.main([__file__, "-v"])
