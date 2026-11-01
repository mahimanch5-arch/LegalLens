"""
LegalLens Workflows - Ask, Summary, and Draft workflows for legal document Q&A

This module provides three main workflows:
1. Ask - Question answering with RAG
2. Summary - Document summarization
3. Draft - Legal document generation (memo/brief)

All workflows use:
- Claude Haiku for pre-retrieval processing
- BGE embeddings for semantic search
- BGE Reranker for relevance ranking
- Claude Sonnet/Opus for generation
"""

from ask_workflow import AskResult, AskWorkflow, ask
from draft_workflow import DraftResult, DraftWorkflow, draft
from hybrid_retrieval import ChromaVectorHybridRetriever, HybridRetriever, RetrievalResult
from question_rewriter import QuestionRewriter, RewriteResult
from reranker import BGEReranker, RankedResult, RerankerPipeline
from summary_workflow import SummaryResult, SummaryWorkflow, summarize

__all__ = [
    # Question Rewriting
    "QuestionRewriter",
    "RewriteResult",

    # Retrieval
    "HybridRetriever",
    "ChromaVectorHybridRetriever",
    "RetrievalResult",

    # Re-ranking
    "BGEReranker",
    "RerankerPipeline",
    "RankedResult",

    # Workflows
    "AskWorkflow",
    "AskResult",
    "ask",

    "SummaryWorkflow",
    "SummaryResult",
    "summarize",

    "DraftWorkflow",
    "DraftResult",
    "draft",
]

__version__ = "0.1.0"
__author__ = "LegalLens AI Team"
