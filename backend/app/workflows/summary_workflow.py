"""
Summary Workflow - Document Summarization

Complete end-to-end workflow:
1. Query clarification with chat history (Claude Haiku)
2. Hybrid retrieval limited to single document
3. Re-ranking to top 5-10 chunks
4. Template selection (Contract/Opinion/Pleading)
5. Claude Opus/Sonnet generation (complexity-dependent)
"""

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from hybrid_retrieval import HybridRetriever
from langchain_anthropic import ChatAnthropic
from question_rewriter import QuestionRewriter
from reranker import RankedResult, RerankerPipeline

logger = logging.getLogger(__name__)


class DocumentType(StrEnum):
    """Legal document types"""
    CONTRACT = "contract"
    OPINION = "opinion"
    PLEADING = "pleading"
    OTHER = "other"


@dataclass
class SummaryResult:
    """Result of Summary workflow"""
    document_type: DocumentType
    document_id: str
    original_query: str
    retrieved_chunks: list[RankedResult]
    structured_summary: dict[str, Any]
    metadata: dict[str, Any] | None = None


class SummaryWorkflow:
    """Complete Summary workflow orchestrator"""

    def __init__(self,
                 retriever: HybridRetriever,
                 reranker_top_k: int = 10,
                 complexity_page_threshold: int = 50):
        """
        Initialize Summary workflow.

        Args:
            retriever: HybridRetriever instance
            reranker_top_k: Number of chunks to keep after re-ranking
            complexity_page_threshold: Pages threshold for Opus vs Sonnet
        """
        self.question_rewriter = QuestionRewriter()
        self.retriever = retriever
        self.reranker = RerankerPipeline(top_k=reranker_top_k)
        self.complexity_threshold = complexity_page_threshold

        # Will be set based on complexity
        self.llm = None

    def execute(self,
               document_id: str,
               query: str | None = None,
               chat_history: list[tuple[str, str]] | None = None) -> SummaryResult:
        """
        Execute complete Summary workflow.

        Args:
            document_id: Document to summarize
            query: Optional summarization query (if None, summarize entire document)
            chat_history: Previous conversation turns

        Returns:
            SummaryResult with structured summary
        """
        logger.info(f"Starting Summary workflow for document: {document_id}")

        try:
            # Step 1: Query clarification (optional)
            if query:
                logger.info("Step 1: Query clarification...")
                query = self._clarify_query(query, chat_history)
            else:
                query = "Provide a comprehensive summary of this document"

            # Step 2: Retrieve document chunks
            logger.info("Step 2: Hybrid retrieval (limited to document)...")
            retrieved = self.retriever.hybrid_search(
                query=query,
                top_k=25,
                document_filter=document_id
            )
            logger.info(f"  Retrieved {len(retrieved)} chunks from document")

            # Step 3: Re-ranking
            logger.info("Step 3: Re-ranking chunks...")
            ranked = self.reranker.rerank_results(
                query=query,
                retrieved_results=retrieved,
                top_k=10
            )

            # Step 4: Detect document type and complexity
            doc_type, complexity = self._detect_complexity(ranked)
            logger.info(f"  Document type: {doc_type}, Complexity: {complexity}")

            # Step 5: Generate summary
            logger.info("Step 5: Generating summary...")
            summary = self._generate_summary(doc_type, ranked, complexity)

            return SummaryResult(
                document_type=doc_type,
                document_id=document_id,
                original_query=query,
                retrieved_chunks=ranked,
                structured_summary=summary,
                metadata={
                    'complexity': complexity,
                    'chunks_used': len(ranked),
                    'retrieval_count': len(retrieved)
                }
            )

        except Exception as e:
            logger.error(f"Summary workflow failed: {e}")
            raise

    def _clarify_query(self,
                      query: str,
                      chat_history: list[tuple[str, str]] | None) -> str:
        """Clarify summarization query using Haiku"""
        result = self.question_rewriter.rewrite(query, chat_history)
        return str(result.rewritten_question)

    def _detect_complexity(self, chunks: list[RankedResult]) -> tuple[DocumentType, str]:
        """
        Detect document type and complexity.

        Returns:
            (DocumentType, complexity_level: "simple" | "moderate" | "complex")
        """
        # Combine chunk texts to analyze
        full_text = " ".join([c.text for c in chunks[:5]])

        # Simple keyword matching for document type
        contract_keywords = ["agreement", "terms", "obligations", "party", "consideration"]
        opinion_keywords = ["court", "holding", "reasoned", "precedent", "affirm"]
        pleading_keywords = ["complaint", "defendant", "plaintiff", "cause of action"]

        def count_keywords(text: str, keywords: list[str]) -> int:
            return sum(text.lower().count(kw) for kw in keywords)

        contract_score = count_keywords(full_text, contract_keywords)
        opinion_score = count_keywords(full_text, opinion_keywords)
        pleading_score = count_keywords(full_text, pleading_keywords)

        if contract_score > opinion_score and contract_score > pleading_score:
            doc_type = DocumentType.CONTRACT
        elif opinion_score > pleading_score:
            doc_type = DocumentType.OPINION
        elif pleading_score > 0:
            doc_type = DocumentType.PLEADING
        else:
            doc_type = DocumentType.OTHER

        # Complexity based on chunk count and depth
        if len(chunks) > self.complexity_threshold:
            complexity = "complex"
        elif len(chunks) > 5:
            complexity = "moderate"
        else:
            complexity = "simple"

        return doc_type, complexity

    def _generate_summary(self,
                         doc_type: DocumentType,
                         chunks: list[RankedResult],
                         complexity: str) -> dict[str, Any]:
        """Generate structured summary based on document type"""

        # Select model based on complexity
        model = "claude-opus-5-5" if complexity == "complex" else "claude-sonnet-5-5"

        self.llm = ChatAnthropic(model=model, temperature=0.2)

        # Get template for document type
        template = self._get_summary_template(doc_type)

        # TODO: Build RAG context and generate summary
        # This is a placeholder implementation
        logger.info(f"Generating {doc_type} summary using {model}")

        # Return structure (actual content would be filled by LLM)
        return {
            "type": doc_type.value,
            "model_used": model,
            "fields": template,
            "content": "Summary content would go here..."
        }

    @staticmethod
    def _get_summary_template(doc_type: DocumentType) -> dict[str, Any]:
        """Get summary template for document type"""

        templates = {
            DocumentType.CONTRACT: {
                "Parties": None,
                "Effective Date": None,
                "Key Terms": None,
                "Obligations": None,
                "Termination": None,
                "Renewal": None
            },
            DocumentType.OPINION: {
                "Court": None,
                "Parties": None,
                "Issue": None,
                "Facts": None,
                "Holding": None,
                "Reasoning": None,
                "Disposition": None
            },
            DocumentType.PLEADING: {
                "Plaintiff": None,
                "Defendant": None,
                "Causes of Action": None,
                "Facts Alleged": None,
                "Relief Sought": None
            },
            DocumentType.OTHER: {
                "Title": None,
                "Summary": None,
                "Key Points": None
            }
        }

        return templates.get(doc_type, templates[DocumentType.OTHER])


def summarize(retriever: HybridRetriever,
             document_id: str,
             query: str | None = None) -> SummaryResult:
    """
    Simple function to summarize a document.

    Args:
        retriever: HybridRetriever instance
        document_id: Document to summarize
        query: Optional summarization query

    Returns:
        SummaryResult with structured summary
    """
    workflow = SummaryWorkflow(retriever)
    return workflow.execute(document_id, query)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Summary Workflow Template - Ready to build")
