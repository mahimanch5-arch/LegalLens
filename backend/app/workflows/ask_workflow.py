"""
Ask Workflow - Question Answering with RAG

Complete end-to-end workflow:
1. Question rewriting with chat history
2. Hybrid retrieval (vector + BM25)
3. Re-ranking (BGE Reranker)
4. RAG augmentation
5. Claude Sonnet generation with citations
"""

import logging
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from langchain_anthropic import ChatAnthropic

from question_rewriter import QuestionRewriter, RewriteResult
from hybrid_retrieval import HybridRetriever, RetrievalResult
from reranker import RerankerPipeline, RankedResult

logger = logging.getLogger(__name__)


@dataclass
class AskResult:
    """Result of Ask workflow"""
    original_question: str
    rewritten_question: str
    retrieved_chunks: List[RankedResult]
    generated_answer: str
    citations: List[Dict]  # {text, chunk_id, source}
    metadata: Dict = None


ASK_GENERATION_SYSTEM_PROMPT = """You are an expert legal analyst assistant helping attorneys research documents.

Your task: Answer the user's question by citing relevant passages from provided documents.

INSTRUCTIONS:
1. Answer comprehensively using ONLY the provided document excerpts
2. Cite every factual assertion with [n] markers
3. Be precise and legal in your language
4. If information is not in the documents, state clearly: "This is not addressed in the provided documents"
5. For each citation, reference both the document and the specific passage
6. Structure your answer clearly with proper legal terminology

CITATION FORMAT:
- Use [1], [2], [3] etc. for each citation
- Place citations immediately after the relevant sentence
- Include the source: "According to [document name], [quoted text]"

DOCUMENT EXCERPTS:
{document_context}

Remember: Only use information from the provided excerpts. Do not use external knowledge."""


class AskWorkflow:
    """Complete Ask workflow orchestrator"""

    def __init__(self,
                 retriever: HybridRetriever,
                 reranker_top_k: int = 10,
                 llm_model: str = "claude-sonnet-5-5"):
        """
        Initialize Ask workflow.

        Args:
            retriever: HybridRetriever instance
            reranker_top_k: Number of chunks to keep after re-ranking
            llm_model: Claude model for generation (default: Sonnet)
        """
        self.question_rewriter = QuestionRewriter()
        self.retriever = retriever
        self.reranker = RerankerPipeline(top_k=reranker_top_k)
        self.llm = ChatAnthropic(model=llm_model, temperature=0.2)
        self.reranker_top_k = reranker_top_k

    def execute(self,
               question: str,
               chat_history: Optional[List[Tuple[str, str]]] = None,
               document_filter: Optional[str] = None) -> AskResult:
        """
        Execute complete Ask workflow.

        Args:
            question: User's question
            chat_history: Previous conversation turns
            document_filter: Optional document_id to limit search

        Returns:
            AskResult with answer and citations
        """
        logger.info(f"Starting Ask workflow: '{question[:60]}...'")

        try:
            # Step 1: Rewrite question with chat history
            logger.info("Step 1: Rewriting question with context...")
            rewrite_result = self.question_rewriter.rewrite(question, chat_history)
            rewritten_question = rewrite_result.rewritten_question
            logger.info(f"  Rewritten: '{rewritten_question[:60]}...'")

            # Step 2: Hybrid retrieval
            logger.info("Step 2: Hybrid retrieval (vector + keyword)...")
            retrieved = self.retriever.hybrid_search(
                query=rewritten_question,
                top_k=25,
                document_filter=document_filter
            )
            logger.info(f"  Retrieved {len(retrieved)} candidates")

            # Step 3: Re-ranking
            logger.info("Step 3: Re-ranking with BGE Reranker...")
            ranked = self.reranker.rerank_results(
                query=rewritten_question,
                retrieved_results=retrieved,
                top_k=self.reranker_top_k
            )
            logger.info(f"  Re-ranked to top {len(ranked)} chunks")

            # Step 4: RAG augmentation
            logger.info("Step 4: Building RAG context...")
            rag_context = self._build_rag_context(ranked)

            # Step 5: Generate answer with Claude Sonnet
            logger.info("Step 5: Generating answer with Claude Sonnet...")
            answer, citations = self._generate_answer(
                question=question,
                rewritten_question=rewritten_question,
                rag_context=rag_context,
                ranked_chunks=ranked
            )
            logger.info(f"  Generated answer with {len(citations)} citations")

            return AskResult(
                original_question=question,
                rewritten_question=rewritten_question,
                retrieved_chunks=ranked,
                generated_answer=answer,
                citations=citations,
                metadata={
                    'retrieval_count': len(retrieved),
                    'final_chunks': len(ranked),
                    'document_filter': document_filter
                }
            )

        except Exception as e:
            logger.error(f"Ask workflow failed: {e}")
            raise

    @staticmethod
    def _build_rag_context(ranked_chunks: List[RankedResult]) -> str:
        """Build RAG context from ranked chunks"""
        context = []
        for i, chunk in enumerate(ranked_chunks, 1):
            context.append(f"[{i}] {chunk.text}")
            if chunk.metadata and 'filename' in chunk.metadata:
                context.append(f"    Source: {chunk.metadata['filename']}")

        return "\n\n".join(context)

    def _generate_answer(self,
                        question: str,
                        rewritten_question: str,
                        rag_context: str,
                        ranked_chunks: List[RankedResult]) -> Tuple[str, List[Dict]]:
        """Generate answer using Claude Sonnet with RAG context"""

        # Build system prompt
        system_prompt = ASK_GENERATION_SYSTEM_PROMPT.format(
            document_context=rag_context
        )

        # Build user message
        user_message = f"""Answer this question using ONLY the provided document excerpts:

Question: {question}"""

        try:
            # Call Claude Sonnet
            response = self.llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ])

            answer = response.content

            # Extract citations from answer
            citations = self._extract_citations(answer, ranked_chunks)

            return answer, citations

        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            raise

    @staticmethod
    def _extract_citations(answer: str, chunks: List[RankedResult]) -> List[Dict]:
        """Extract citations from generated answer"""
        import re

        citations = []

        # Find all [n] patterns in answer
        citation_pattern = r'\[(\d+)\]'
        matches = re.finditer(citation_pattern, answer)

        for match in matches:
            citation_num = int(match.group(1))

            # Get corresponding chunk (1-indexed)
            if citation_num <= len(chunks):
                chunk = chunks[citation_num - 1]
                citations.append({
                    'citation_number': citation_num,
                    'chunk_id': chunk.chunk_id,
                    'document_id': chunk.document_id,
                    'text': chunk.text[:200],  # First 200 chars
                    'score': chunk.score,
                    'metadata': chunk.metadata
                })

        return citations


# Convenience function
def ask(retriever: HybridRetriever,
        question: str,
        chat_history: Optional[List[Tuple[str, str]]] = None,
        document_filter: Optional[str] = None) -> AskResult:
    """
    Simple function to run Ask workflow.

    Args:
        retriever: HybridRetriever instance
        question: User's question
        chat_history: Previous turns
        document_filter: Optional document limit

    Returns:
        AskResult with answer and citations
    """
    workflow = AskWorkflow(retriever)
    return workflow.execute(question, chat_history, document_filter)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("""
    Ask Workflow Ready

    To use:
    1. Initialize with HybridRetriever
    2. Call ask() or AskWorkflow().execute()
    3. Get result with answer and citations

    Example:
        workflow = AskWorkflow(retriever)
        result = workflow.execute("What are termination rights?")
        print(result.generated_answer)
        print(f"Citations: {result.citations}")
    """)
