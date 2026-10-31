"""
Draft Workflow - Legal Document Generation (Memo/Brief)

Complete end-to-end workflow:
1. Intent extraction (Claude Haiku)
2. Multi-document hybrid retrieval
3. Re-ranking to top 10 chunks
4. Source organization
5. Claude Opus generation
6. Citation tracking and draft marking
"""

import logging
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from enum import Enum
import json

from langchain_anthropic import ChatAnthropic
from hybrid_retrieval import HybridRetriever
from reranker import RerankerPipeline, RankedResult

logger = logging.getLogger(__name__)


class DraftType(str, Enum):
    """Draft document types"""
    MEMO = "memo"
    BRIEF = "brief"


@dataclass
class DraftParams:
    """Parameters for draft generation"""
    document_type: DraftType
    focus_area: str
    question_presented: str
    audience: str
    tone: str
    source_documents: List[str]


@dataclass
class DraftResult:
    """Result of Draft workflow"""
    draft_params: DraftParams
    retrieved_chunks: List[RankedResult]
    generated_draft: str
    citations: List[Dict]
    source_manifest: Dict
    metadata: Dict = None


INTENT_EXTRACTION_PROMPT = """You are a legal research assistant extracting intent parameters for document drafting.

Given the user's draft request, extract the following in JSON format:

{
  "document_type": "memo" | "brief",
  "focus_area": "the specific legal area to focus on",
  "question_presented": "the legal question to analyze",
  "audience": "intended reader (attorney, client, judge, etc)",
  "tone": "formal | neutral | argumentative",
  "source_documents": ["list of relevant document names if mentioned"]
}

Rules:
- If document_type not specified, infer from request
- Focus area should be specific, not vague
- Question presented should be legally clear
- Default audience: "legal professional" if not specified
- Default tone: "formal"

Respond with ONLY the JSON, no explanation."""


class DraftWorkflow:
    """Complete Draft workflow orchestrator"""

    def __init__(self, retriever: HybridRetriever, reranker_top_k: int = 10):
        """
        Initialize Draft workflow.

        Args:
            retriever: HybridRetriever instance
            reranker_top_k: Number of chunks to keep after re-ranking
        """
        self.intent_extractor = ChatAnthropic(model="claude-haiku-4-5", temperature=0.2)
        self.retriever = retriever
        self.reranker = RerankerPipeline(top_k=reranker_top_k)
        self.llm = ChatAnthropic(model="claude-opus-5-5", temperature=0.3)  # Opus for generation

    def execute(self, draft_request: str) -> DraftResult:
        """
        Execute complete Draft workflow.

        Args:
            draft_request: User's draft request (e.g., "Draft a memo analyzing termination clause")

        Returns:
            DraftResult with generated draft and sources
        """
        logger.info(f"Starting Draft workflow: '{draft_request[:60]}...'")

        try:
            # Step 1: Extract intent using Haiku
            logger.info("Step 1: Extracting intent parameters...")
            params = self._extract_intent(draft_request)
            logger.info(f"  Document type: {params.document_type}, Focus: {params.focus_area}")

            # Step 2: Multi-document retrieval
            logger.info("Step 2: Multi-document hybrid retrieval...")
            retrieved = self.retriever.hybrid_search(
                query=params.focus_area,
                top_k=25
            )
            logger.info(f"  Retrieved {len(retrieved)} chunks from all documents")

            # Step 3: Re-ranking
            logger.info("Step 3: Re-ranking chunks...")
            ranked = self.reranker.rerank_results(
                query=params.focus_area,
                retrieved_results=retrieved,
                top_k=10
            )

            # Step 4: Source organization
            logger.info("Step 4: Organizing sources...")
            source_manifest = self._organize_sources(ranked)

            # Step 5: Generate draft using Opus
            logger.info("Step 5: Generating draft with Claude Opus...")
            draft_text = self._generate_draft(params, ranked)

            # Step 6: Extract citations
            logger.info("Step 6: Extracting citations...")
            citations = self._extract_citations(draft_text, ranked)

            return DraftResult(
                draft_params=params,
                retrieved_chunks=ranked,
                generated_draft=draft_text,
                citations=citations,
                source_manifest=source_manifest,
                metadata={
                    'retrieval_count': len(retrieved),
                    'final_chunks': len(ranked),
                    'citation_count': len(citations),
                    'warning': "UNREVIEWED AI DRAFT - ATTORNEY REVIEW REQUIRED"
                }
            )

        except Exception as e:
            logger.error(f"Draft workflow failed: {e}")
            raise

    def _extract_intent(self, draft_request: str) -> DraftParams:
        """Extract intent parameters using Claude Haiku"""

        try:
            response = self.intent_extractor.invoke([
                {"role": "system", "content": INTENT_EXTRACTION_PROMPT},
                {"role": "user", "content": draft_request}
            ])

            # Parse JSON response
            import json
            intent_data = json.loads(response.content)

            return DraftParams(
                document_type=DraftType(intent_data.get("document_type", "memo")),
                focus_area=intent_data.get("focus_area", draft_request),
                question_presented=intent_data.get("question_presented", ""),
                audience=intent_data.get("audience", "legal professional"),
                tone=intent_data.get("tone", "formal"),
                source_documents=intent_data.get("source_documents", [])
            )

        except Exception as e:
            logger.error(f"Intent extraction failed: {e}")
            # Return default params
            return DraftParams(
                document_type=DraftType.MEMO,
                focus_area=draft_request,
                question_presented="",
                audience="legal professional",
                tone="formal",
                source_documents=[]
            )

    def _organize_sources(self, chunks: List[RankedResult]) -> Dict:
        """Organize sources by document"""

        sources = {}
        for chunk in chunks:
            doc_id = chunk.document_id
            if doc_id not in sources:
                sources[doc_id] = []

            sources[doc_id].append({
                'chunk_id': chunk.chunk_id,
                'rank': chunk.rank,
                'score': chunk.score,
                'text': chunk.text[:200]  # First 200 chars
            })

        return sources

    def _generate_draft(self, params: DraftParams, chunks: List[RankedResult]) -> str:
        """Generate draft using Claude Opus"""

        # Build context from chunks
        context = "\n\n".join([f"[{i}] {c.text}" for i, c in enumerate(chunks, 1)])

        # Get template
        template = self._get_draft_template(params.document_type)

        # TODO: Call Opus to fill template with citations
        logger.info(f"Generating {params.document_type} with Opus (audience: {params.audience})")

        # Placeholder
        return f"""[UNREVIEWED AI DRAFT - ATTORNEY REVIEW REQUIRED]

TYPE: {params.document_type.value.upper()}
QUESTION PRESENTED: {params.question_presented}
AUDIENCE: {params.audience}
TONE: {params.tone}

Draft content would be generated here using the provided sources...

[Source count: {len(chunks)} citations]"""

    @staticmethod
    def _get_draft_template(draft_type: DraftType) -> str:
        """Get template for draft type"""

        if draft_type == DraftType.MEMO:
            return """MEMORANDUM

TO:        [Audience]
FROM:      [Author]
DATE:      [Date]
RE:        [Subject - Question Presented]

1. QUESTION PRESENTED

2. SHORT ANSWER

3. FACTS

4. ANALYSIS
   A. [First Issue]
   B. [Second Issue]

5. CONCLUSION"""

        else:  # BRIEF
            return """CASE BRIEF

Case:      [Citation]
Court:     [Court Name]
Year:      [Year]

POSTURE
[Current procedural posture]

FACTS
[Key facts]

ISSUE
[Legal issue presented]

HOLDING
[Court's holding]

REASONING
[Court's reasoning]

DISPOSITION
[Final disposition]"""

    @staticmethod
    def _extract_citations(draft_text: str, chunks: List[RankedResult]) -> List[Dict]:
        """Extract citations from generated draft"""
        import re

        citations = []
        citation_pattern = r'\[(\d+)\]'

        for match in re.finditer(citation_pattern, draft_text):
            citation_num = int(match.group(1))
            if citation_num <= len(chunks):
                chunk = chunks[citation_num - 1]
                citations.append({
                    'number': citation_num,
                    'chunk_id': chunk.chunk_id,
                    'document_id': chunk.document_id,
                    'text': chunk.text[:150]
                })

        return citations


def draft(retriever: HybridRetriever, draft_request: str) -> DraftResult:
    """
    Simple function to generate a draft.

    Args:
        retriever: HybridRetriever instance
        draft_request: User's draft request

    Returns:
        DraftResult with generated draft and sources
    """
    workflow = DraftWorkflow(retriever)
    return workflow.execute(draft_request)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Draft Workflow Template - Ready to build")
