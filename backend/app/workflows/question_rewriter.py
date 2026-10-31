"""
Question Rewriter for Ask Workflow

Uses Claude Haiku to rewrite user questions with chat history context.
Includes strict guardrails to avoid unnecessary rewrites.
"""

import logging
from dataclasses import dataclass

from langchain_anthropic import ChatAnthropic

logger = logging.getLogger(__name__)


@dataclass
class RewriteResult:
    """Result of question rewriting"""
    original_question: str
    rewritten_question: str
    was_rewritten: bool
    reason: str


QUESTION_REWRITE_SYSTEM_PROMPT = """You are a question clarification expert for a legal document Q&A system.

Your task: Given a user's question and chat history, decide whether to rewrite
the question for better retrieval or keep it as-is.

STRICT GUARDRAILS - MUST FOLLOW:

1. If chat_history is EMPTY → NEVER rewrite. Output the question UNCHANGED.
   Example: chat_history = [], question = "What are termination rights?"
   → Output: "What are termination rights?" (no change)

2. If chat_history and question are TOTALLY INDEPENDENT OR MUTUALLY EXCLUSIVE
   → NEVER rewrite. They don't relate to each other.
   Example: chat_history = "We discussed contract law", question = "What is the capital of France?"
   → Output: "What is the capital of France?" (no change - independent)

3. Only rewrite if chat_history provides RELEVANT context that improves understanding:
   - The question references something from chat history
   - Rewriting clarifies ambiguous pronouns or references
   - The chat history directly relates to the question

REWRITING RULES:
- Keep the legal intent intact
- Add context from chat history ONLY where it clarifies
- Make the question self-contained (no pronouns referencing chat)
- Preserve the original structure and length where possible
- Do NOT change the legal focus of the question

OUTPUT FORMAT:
- If rewriting: Output ONLY the rewritten question (no explanation, no markers)
- If NOT rewriting: Output ONLY the original question UNCHANGED (no explanation)

EXAMPLES:

Example 1 (Rewrite):
Chat History: "We discussed the Acme MSA earlier"
Question: "What about the renewal clause?"
→ Output: "What is the renewal clause in the Acme MSA?"
(Reason: Clarifies ambiguous reference)

Example 2 (No Rewrite - Empty):
Chat History: []
Question: "What are termination rights?"
→ Output: "What are termination rights?"
(Reason: No context to add)

Example 3 (No Rewrite - Independent):
Chat History: "We looked at contract law"
Question: "What is the capital of France?"
→ Output: "What is the capital of France?"
(Reason: Totally independent topics)

Example 4 (Rewrite):
Chat History: "We're looking at the payment terms in the contract"
Question: "What happens if there's a delay?"
→ Output: "What happens if there's a delay in payment in the contract?"
(Reason: Clarifies ambiguous reference)

Example 5 (No Rewrite - Already Clear):
Chat History: "We discussed the Acme MSA"
Question: "What are the termination rights in the Acme MSA?"
→ Output: "What are the termination rights in the Acme MSA?"
(Reason: Question already clear and specific)

Remember: ONLY output the question (rewritten or unchanged). No explanation. No markers."""


class QuestionRewriter:
    """Rewrite questions using chat history with strict guardrails"""

    def __init__(self, model: str = "claude-haiku-4-5"):
        """
        Initialize question rewriter.

        Args:
            model: Claude model to use (Haiku recommended for speed)
        """
        self.model = model
        self.client = ChatAnthropic(model=model, temperature=0.2)

    def rewrite(self,
                question: str,
                chat_history: list[tuple[str, str]] | None = None) -> RewriteResult:
        """
        Rewrite a question using chat history as context.

        Args:
            question: The user's question
            chat_history: List of (user_message, assistant_response) tuples

        Returns:
            RewriteResult with original, rewritten, and metadata
        """
        # Apply guardrail: Empty chat history
        if not chat_history:
            logger.info("No chat history - skipping rewrite")
            return RewriteResult(
                original_question=question,
                rewritten_question=question,
                was_rewritten=False,
                reason="No chat history"
            )

        # Format chat history for the prompt
        chat_text = self._format_chat_history(chat_history)

        # Call Claude Haiku
        try:
            response = self.client.invoke([
                {
                    "role": "system",
                    "content": QUESTION_REWRITE_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": f"""Chat History:
{chat_text}

Question: {question}"""
                }
            ])

            rewritten = response.content.strip()

            # Determine if rewrite happened
            was_rewritten = rewritten != question

            if was_rewritten:
                logger.info(f"Question rewritten: '{question}' → '{rewritten}'")
                reason = "Context added from chat history"
            else:
                logger.info("Question unchanged (guardrail applied)")
                reason = "Guardrail: chat history independent or empty"

            return RewriteResult(
                original_question=question,
                rewritten_question=rewritten,
                was_rewritten=was_rewritten,
                reason=reason
            )

        except Exception as e:
            logger.error(f"Error rewriting question: {e}")
            # Fall back to original question
            return RewriteResult(
                original_question=question,
                rewritten_question=question,
                was_rewritten=False,
                reason=f"Error during rewrite: {str(e)}"
            )

    @staticmethod
    def _format_chat_history(chat_history: list[tuple[str, str]]) -> str:
        """Format chat history for inclusion in prompt"""
        if not chat_history:
            return "[Empty]"

        formatted = []
        for i, (user_msg, assistant_msg) in enumerate(chat_history, 1):
            formatted.append(f"Turn {i}:")
            formatted.append(f"User: {user_msg}")
            formatted.append(f"Assistant: {assistant_msg}")

        return "\n".join(formatted)


# Convenience function
def rewrite_question(question: str,
                    chat_history: list[tuple[str, str]] | None = None) -> str:
    """
    Simple function to rewrite a question.

    Args:
        question: The question to potentially rewrite
        chat_history: Chat history for context

    Returns:
        Original or rewritten question
    """
    rewriter = QuestionRewriter()
    result = rewriter.rewrite(question, chat_history)
    return result.rewritten_question


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)

    rewriter = QuestionRewriter()

    # Test 1: Empty chat history
    print("\nTest 1: Empty chat history")
    result = rewriter.rewrite("What are termination rights?", chat_history=[])
    print(f"Original: {result.original_question}")
    print(f"Rewritten: {result.rewritten_question}")
    print(f"Changed: {result.was_rewritten}")

    # Test 2: With relevant chat history
    print("\nTest 2: Relevant chat history")
    chat = [
        ("Tell me about the Acme MSA", "The Acme Master Services Agreement is a 42-page document covering...")
    ]
    result = rewriter.rewrite("What about the renewal clause?", chat_history=chat)
    print(f"Original: {result.original_question}")
    print(f"Rewritten: {result.rewritten_question}")
    print(f"Changed: {result.was_rewritten}")

    # Test 3: Independent chat history
    print("\nTest 3: Independent chat history")
    chat = [
        ("Tell me about contract law", "Contract law is the body of law...")
    ]
    result = rewriter.rewrite("What is the capital of France?", chat_history=chat)
    print(f"Original: {result.original_question}")
    print(f"Rewritten: {result.rewritten_question}")
    print(f"Changed: {result.was_rewritten}")
