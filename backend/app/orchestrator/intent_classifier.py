"""
Intent Classifier for LegalLens Orchestrator

Classifies user queries into one of four intents:
- Ask: Question answering / information retrieval
- Summary: Document summarization
- Draft: Legal document generation (memo/brief)
- Auto: Let the backend router decide

Uses fast heuristic rules first, falls back to Claude Haiku for edge cases.
"""

import os
import re
from dataclasses import dataclass
from enum import StrEnum

# Load environment variables from .env file (handle different working directories)
from pathlib import Path

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

# Try to find and load .env file
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Fallback: try current directory
    load_dotenv()


class Intent(StrEnum):
    """Legal Lens intent types"""
    ASK = "ask"
    SUMMARY = "summary"
    DRAFT = "draft"
    AUTO = "auto"


@dataclass
class ClassificationResult:
    """Result of intent classification"""
    intent: Intent
    confidence: float
    reason: str
    used_heuristic: bool


class IntentClassifier:
    """
    Classify user messages into Ask, Summary, Draft, or Auto intent.

    Uses a two-stage approach:
    1. Fast heuristic rules (pattern matching, keywords)
    2. Claude Haiku fallback for inconclusive cases
    """

    # Keywords for each intent (case-insensitive)
    # Imperative verbs that indicate draft intent
    DRAFT_VERBS = {
        "draft", "write", "create", "generate", "prepare",
        "compose", "pen", "develop", "build"
    }

    # Nouns that indicate draft intent (only meaningful with a draft verb)
    DRAFT_NOUNS = {"memo", "memorandum", "brief", "outline"}

    SUMMARY_KEYWORDS = {
        "summarize", "summary", "overview", "extract",
        "key points", "key terms", "main points", "outline",
        "structure", "breakdown"
    }

    ASK_MARKERS = {"?", "what", "how", "when", "where", "who", "why", "can", "will", "is"}

    def __init__(self) -> None:
        """Initialize the intent classifier with Claude Haiku"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Please set it in .env or environment."
            )

        model_name = os.getenv("INTENT_CLASSIFIER_MODEL", "claude-haiku-4-5")
        temperature = float(os.getenv("INTENT_CLASSIFIER_TEMPERATURE", "0.2"))

        self.llm = ChatAnthropic(
            api_key=api_key,
            model=model_name,
            temperature=temperature,
        )

        self.confidence_threshold = float(
            os.getenv("INTENT_CLASSIFIER_CONFIDENCE_THRESHOLD", "0.7")
        )
        self.debug = os.getenv("INTENT_CLASSIFIER_DEBUG", "false").lower() == "true"

    def classify(
        self,
        message: str,
        document_scope: str | None = None,
        conversation_history_length: int = 0
    ) -> ClassificationResult:
        """
        Classify a user message into an intent.

        Args:
            message: The user's message
            document_scope: "workspace", "documents", "single_doc", or None
            conversation_history_length: Number of previous messages in conversation

        Returns:
            ClassificationResult with intent, confidence, and reason
        """
        # Try heuristic classification first (fast path)
        heuristic_result = self._classify_heuristic(message)

        if self.debug:
            print(f"[DEBUG] Heuristic result: {heuristic_result}")

        # If heuristic confidence is high enough, return it
        if heuristic_result.confidence >= self.confidence_threshold:
            return heuristic_result

        # Otherwise, use Claude Haiku for classification
        if self.debug:
            print(f"[DEBUG] Heuristic confidence {heuristic_result.confidence:.2f} < threshold {self.confidence_threshold}. Falling back to LLM.")

        llm_result = self._classify_llm(
            message,
            document_scope=document_scope,
            conversation_history_length=conversation_history_length
        )

        if self.debug:
            print(f"[DEBUG] LLM result: {llm_result}")

        return llm_result

    def _classify_heuristic(self, message: str) -> ClassificationResult:
        """
        Fast heuristic-based classification.

        Rules (in order of precedence):
        1. Draft keywords → Draft (high confidence)
        2. Summary keywords → Summary (high confidence)
        3. Question mark + no draft/summary → Ask (high confidence)
        4. Short message + no keywords → Ask (medium confidence)
        5. Default → Ask (low confidence)
        """
        normalized = message.lower().strip()

        # Rule 1: Draft verbs (highest priority)
        # Must contain an imperative verb like "draft", "write", "create"
        # (not just nouns like "brief" or "memo")
        if self._contains_keywords(normalized, self.DRAFT_VERBS):
            return ClassificationResult(
                intent=Intent.DRAFT,
                confidence=0.95,
                reason="Contains draft keywords (draft, write, create, etc.)",
                used_heuristic=True
            )

        # Rule 2: Summary keywords
        if self._contains_keywords(normalized, self.SUMMARY_KEYWORDS):
            return ClassificationResult(
                intent=Intent.SUMMARY,
                confidence=0.90,
                reason="Contains summary keywords (summarize, overview, extract, etc.)",
                used_heuristic=True
            )

        # Rule 3: Question mark (strong indicator of Ask)
        if "?" in normalized:
            return ClassificationResult(
                intent=Intent.ASK,
                confidence=0.85,
                reason="Message contains question mark",
                used_heuristic=True
            )

        # Rule 4: Very short message (likely Ask, but less certain)
        if len(normalized) < 20:
            return ClassificationResult(
                intent=Intent.ASK,
                confidence=0.60,
                reason="Very short message (likely a question)",
                used_heuristic=True
            )

        # Rule 5: Check for question-like patterns without question mark
        # (e.g., "Tell me about...", "Show me...", "What about...")
        if any(normalized.startswith(word) for word in ["tell me", "show me", "explain", "describe", "give me"]):
            return ClassificationResult(
                intent=Intent.ASK,
                confidence=0.80,
                reason="Starts with information-seeking phrase",
                used_heuristic=True
            )

        # Default: Ask (low confidence - needs LLM refinement)
        return ClassificationResult(
            intent=Intent.ASK,
            confidence=0.50,
            reason="No strong intent signals; defaulting to Ask",
            used_heuristic=True
        )

    def _classify_llm(
        self,
        message: str,
        document_scope: str | None = None,
        conversation_history_length: int = 0
    ) -> ClassificationResult:
        """
        Classify using Claude Haiku LLM.

        Used as a fallback when heuristics are inconclusive.
        """
        system_prompt = SystemMessage(
            content="""You are an intent classifier for a legal document Q&A system.
Classify the user's query into ONE of: ask, summary, or draft.

Definitions:
- ask: Direct question seeking factual information or explanation from documents
- summary: Request to extract key information from a single document in structured format
- draft: Request to generate new legal content (memo, brief) from source documents

Respond with ONLY the word: ask, summary, or draft (lowercase, no explanation)."""
        )

        # Prepare context for the LLM
        context = f"Message: {message}"
        if document_scope:
            context += f"\nDocument scope: {document_scope}"
        if conversation_history_length > 0:
            context += f"\nPrevious messages in conversation: {conversation_history_length}"

        user_message = HumanMessage(content=context)

        try:
            response = self.llm.invoke([system_prompt, user_message])
            intent_text = response.content.strip().lower()

            # Parse the response
            if intent_text in ["ask", "summary", "draft"]:
                intent = Intent(intent_text)
                confidence = 0.75  # LLM classifications are moderately confident
                reason = f"LLM classification: {intent_text}"
            else:
                # Fallback if LLM returns unexpected format
                intent = Intent.ASK
                confidence = 0.50
                reason = f"LLM returned unexpected response: {intent_text}; defaulting to ask"

            return ClassificationResult(
                intent=intent,
                confidence=confidence,
                reason=reason,
                used_heuristic=False
            )

        except Exception as e:
            print(f"[ERROR] LLM classification failed: {e}")
            # Fall back to heuristic as emergency measure
            return ClassificationResult(
                intent=Intent.ASK,
                confidence=0.40,
                reason=f"LLM classification failed ({str(e)}); falling back to ask",
                used_heuristic=True
            )

    @staticmethod
    def _contains_keywords(text: str, keywords: set[str]) -> bool:
        """Check if text contains any of the given keywords (handles multi-word phrases)."""
        for keyword in keywords:
            # Use word boundaries for single words, simple substring for phrases
            if " " in keyword:
                # Multi-word phrase: substring match
                if keyword in text:
                    return True
            else:
                # Single word: word boundary match
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, text):
                    return True
        return False


# Convenience function for testing
def classify_intent(
    message: str,
    document_scope: str | None = None,
    conversation_history_length: int = 0
) -> ClassificationResult:
    """Classify a message into an intent (singleton pattern)."""
    classifier = IntentClassifier()
    return classifier.classify(message, document_scope, conversation_history_length)


if __name__ == "__main__":
    # Simple test when run directly
    classifier = IntentClassifier()

    test_messages = [
        "What are the termination rights?",
        "Summarize this contract",
        "Draft a memo on indemnification",
        "Tell me the key points",
        "Create a case brief",
        "xyz"
    ]

    print("Intent Classification Test\n" + "="*50)
    for msg in test_messages:
        result = classifier.classify(msg)
        print(f"Message: {msg}")
        print(f"Intent: {result.intent.value}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Reason: {result.reason}")
        print()
