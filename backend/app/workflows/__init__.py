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

from question_rewriter import QuestionRewriter, RewriteResult
from hybrid_retrieval import HybridRetriever, ChromaVectorHybridRetriever, RetrievalResult
from reranker import BGEReranker, RerankerPipeline, RankedResult
from ask_workflow import AskWorkflow, AskResult, ask
from summary_workflow import SummaryWorkflow, SummaryResult, summarize
from draft_workflow import DraftWorkflow, DraftResult, draft

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
