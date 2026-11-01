# Ask/Summary/Draft Workflows - Complete Implementation Plan

**Date:** 2026-10-23  
**Status:** Planning Phase (Awaiting Approval)  
**Scope:** Three complete Q&A workflows with question rewriting, hybrid search, and re-ranking

---

## 🎯 Part 1: Embedding & Re-ranking Model Selection

### Challenge
- Need **open-source** models (not OpenAI)
- Must work well with **semantic search** (Ask)
- Must work well with **re-ranking** (all three workflows)
- Focus on **quality** (not latency or cost)
- Ideal for **legal documents**

### Recommended Solution

#### **EMBEDDING MODEL: BAAI/BGE-Large-En-v1.5** ⭐

**Why BGE?**
- Specifically designed for retrieval tasks
- Excellent for legal domain (trained on diverse data)
- 1024-dimensional embeddings (better quality than 384/768)
- Strong performance on dense retrieval benchmarks
- Perfect match for re-ranking (both from BAAI)

**Specifications:**
- Model: `BAAI/bge-large-en-v1.5`
- Dimensions: 1024
- Size: 1.3 GB
- Inference Time: ~100ms per 512-token chunk
- Best For: High-quality retrieval from legal documents

**Installation:**
```bash
pip install sentence-transformers
```

**Usage:**
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('BAAI/bge-large-en-v1.5')
embeddings = model.encode(texts, normalize_embeddings=True)
```

---

#### **RE-RANKING MODEL: BAAI/BGE-Reranker-Large** ⭐

**Why BGE Reranker?**
- Specifically designed to rank search results
- Perfect companion to BGE embeddings
- Trained on millions of query-document pairs
- Excellent for legal document ranking
- Returns relevance scores (0-1)

**Specifications:**
- Model: `BAAI/bge-reranker-large`
- Type: Cross-encoder (takes query + document as input)
- Size: 1.1 GB
- Inference Time: ~50ms per chunk
- Best For: Re-ranking top-k results

**Installation:**
```bash
pip install sentence-transformers
```

**Usage:**
```python
from sentence_transformers import CrossEncoder

model = CrossEncoder('BAAI/bge-reranker-large')
scores = model.predict([[query, document1], [query, document2]])
```

---

### Alternative Options (if needed)

| Use Case | Model | Dimensions | Size | Notes |
|----------|-------|-----------|------|-------|
| **Faster Embedding** | `BAAI/bge-base-en-v1.5` | 768 | 440 MB | 20% faster, slightly lower quality |
| **Faster Re-ranking** | `BAAI/bge-reranker-base` | — | 370 MB | 30% faster, good quality |
| **General Purpose** | `sentence-transformers/all-mpnet-base-v2` | 768 | 420 MB | Good all-around, not specialized |
| **Semantic Ranking** | `cross-encoders/ms-marco-MiniLM-L-12-v2` | — | 270 MB | Lightweight re-ranker |
| **Multi-lingual** | `cross-encoders/mmarco-MiniLMv2-L12-H384-v1` | — | 270 MB | If multi-language needed |

---

## 🎯 Part 2: Three Workflow Architectures

### WORKFLOW 1: ASK (Question Answering)

```
User Question
    ↓
[PRE-RETRIEVAL: Question Rewriting]
├─ Input: Question + Chat History
├─ Model: Claude Haiku 4.5
├─ Guard Rails:
│  ├─ If chat_history is empty → Skip rewrite
│  ├─ If chat_history and question independent → Skip rewrite
│  └─ Otherwise → Rewrite for context
├─ Output: Original or Rewritten Question
    ↓
[RETRIEVAL: Hybrid Search]
├─ Vector Search:
│  ├─ Embed question (BGE embeddings)
│  ├─ Search vector DB (Chroma/Qdrant)
│  └─ Get top 20-25 chunks
├─ Keyword Search:
│  ├─ BM25 search on document text
│  └─ Get top 20-25 chunks
├─ Merge Results:
│  └─ Combine + deduplicate
    ↓
[RE-RANKING]
├─ Input: Question + 40-50 candidate chunks
├─ Model: BGE Reranker Large
├─ Process:
│  ├─ Score each chunk (0-1)
│  ├─ Sort by relevance
│  └─ Keep top 5-10 chunks
├─ Output: Top 5-10 ranked chunks with scores
    ↓
[AUGMENTATION]
├─ Create RAG context from top chunks
├─ Include citations and sources
├─ Build prompt with context
    ↓
[GENERATION: LLM Response]
├─ Model: Claude Sonnet 5.5 ⭐
├─ Input: Question + Context + Chat History
├─ Output: Cited answer with sources
    ↓
[POST-PROCESSING]
├─ Extract citations
├─ Build sources strip
├─ Format response for UI
    ↓
User sees: Answer with citations + sources
```

**Components:**
- Pre-retrieval: Question rewriting (Haiku)
- Retrieval: Hybrid (vector + BM25)
- Re-ranking: BGE Reranker
- Generation: Claude Sonnet 5.5

**Flow Metrics:**
- Pre-retrieval time: ~300ms (Haiku)
- Vector search: ~100ms
- Keyword search: ~50ms
- Re-ranking: ~500ms (10 chunks × 50ms)
- LLM generation: 1-3s (Sonnet)
- **Total: ~2-4 seconds**

---

### WORKFLOW 2: SUMMARY (Document Summarization)

```
User Request: "Summarize this document"
    ↓
[PRE-RETRIEVAL: Query Clarification]
├─ Input: "Summarize this document" + Chat History
├─ Model: Claude Haiku 4.5
├─ Task: Check if more context needed
├─ Output: Clarified or expanded query
    ↓
[RETRIEVAL: Hybrid Search]
├─ Vector Search:
│  ├─ Embed question
│  ├─ Search for document chunks
│  └─ Get top 20-25 chunks from document
├─ Keyword Search:
│  ├─ BM25 on document text
│  └─ Get top 20-25 chunks
├─ Filter:
│  └─ Only chunks from same document
    ↓
[RE-RANKING]
├─ Input: Query + document chunks
├─ Model: BGE Reranker Large
├─ Output: Top 5-10 most important chunks
    ↓
[AUGMENTATION]
├─ Create document context from chunks
├─ Build structured prompt for summary
    ↓
[GENERATION: LLM Summary]
├─ Model: Claude Opus 5.5 OR Sonnet 5.5 (complexity-dependent)
├─ Template: Contract/Opinion/Pleading summary
├─ Output: Structured summary with fields
    ↓
User sees: Formatted summary (Contract Summary / Opinion Summary / Pleading Summary)
```

**Components:**
- Pre-retrieval: Query clarification (Haiku)
- Retrieval: Hybrid (limited to single document)
- Re-ranking: BGE Reranker
- Generation: Opus (complex docs) or Sonnet (simpler docs)

**Model Decision Logic:**
- Use **Opus** if: Document > 50 pages OR complexity > medium
- Use **Sonnet** if: Document < 50 pages AND straightforward content

---

### WORKFLOW 3: DRAFT (Document Generation - Memo/Brief)

```
User Request: "Draft a memo analyzing the termination clause"
    ↓
[PRE-RETRIEVAL: Intent Extraction]
├─ Input: Draft request + Chat History
├─ Model: Claude Haiku 4.5
├─ Task: Extract memo parameters
│  ├─ Document type (memo/brief)
│  ├─ Focus area
│  ├─ Question presented
│  ├─ Audience
│  └─ Tone
├─ Output: Structured draft parameters
    ↓
[RETRIEVAL: Hybrid Search]
├─ Vector Search:
│  ├─ Embed extracted intent/focus area
│  ├─ Search across all source documents
│  └─ Get top 20-25 relevant chunks
├─ Keyword Search:
│  ├─ BM25 on focus keywords
│  └─ Get top 20-25 chunks
├─ Merge:
│  └─ Combine all candidate chunks
    ↓
[RE-RANKING]
├─ Input: Focus area + candidate chunks
├─ Model: BGE Reranker Large
├─ Output: Top 10 most relevant source chunks
    ↓
[AUGMENTATION]
├─ Create citation context
├─ Organize sources by relevance
├─ Build prompt with structure
├─ Include draft template (memo/brief)
    ↓
[GENERATION: LLM Draft]
├─ Model: Claude Opus 5.5 ⭐⭐ (most capable)
├─ Input: Focus area + sources + structure template
├─ Output: Full memo/brief with citations
    ↓
[POST-PROCESSING]
├─ Add "UNREVIEWED DRAFT" banner
├─ Extract all citations
├─ Build source manifest
├─ Format for UI
    ↓
User sees: Complete draft with warnings + sources
```

**Components:**
- Pre-retrieval: Intent extraction (Haiku)
- Retrieval: Hybrid (across all documents)
- Re-ranking: BGE Reranker
- Generation: Claude Opus 5.5 (highest capability needed)

**Flow Metrics:**
- Pre-retrieval: ~300ms (Haiku)
- Retrieval: ~150ms
- Re-ranking: ~500ms (10 chunks)
- LLM generation: 2-5s (Opus, more complex)
- **Total: ~3-6 seconds**

---

## 🎯 Part 3: System Prompt Design

### ASK: Question Rewriting System Prompt

```
You are a question clarification expert for a legal document Q&A system.

Your task: Given a user's question and chat history, decide whether to rewrite 
the question for better retrieval or keep it as-is.

STRICT GUARDRAILS:
1. If chat_history is empty → NEVER rewrite. Output the question unchanged.
2. If chat_history and question are TOTALLY INDEPENDENT OR MUTUALLY EXCLUSIVE 
   → NEVER rewrite. They don't relate to each other.
3. Only rewrite if:
   - Chat history provides RELEVANT context that improves understanding
   - The question references something from chat history
   - Rewriting clarifies ambiguous pronouns or references

REWRITING RULES:
- Keep the legal intent intact
- Add context from chat history only where it clarifies
- Make the question self-contained (no pronouns referencing chat)
- Preserve the original structure and length
- Do NOT change the legal focus of the question

OUTPUT FORMAT:
If rewriting: Output ONLY the rewritten question (no explanation)
If not rewriting: Output ONLY the original question unchanged

EXAMPLES:
Chat History: "We discussed the Acme MSA earlier"
Question: "What about the renewal clause?"
→ Output: "What is the renewal clause in the Acme MSA?"

Chat History: [empty]
Question: "What are termination rights?"
→ Output: "What are termination rights?" (unchanged - no context)

Chat History: "We looked at contract law"
Question: "What is the capital of France?"
→ Output: "What is the capital of France?" (unchanged - independent)
```

### SUMMARY: Clarification System Prompt

```
You are a document summarization assistant.

Your task: Given a summary request and chat history, clarify what aspects 
of the document should be summarized.

If chat history indicates:
- Previous conversation about the same document → clarify which sections
- Questions about specific areas → focus summary on those areas
- Already discussed topics → avoid redundancy

If chat history is empty or unrelated:
- Provide full document summary

Keep clarifications brief and actionable.
```

### DRAFT: Intent Extraction System Prompt

```
You are a legal document drafting assistant.

Your task: Extract the structured parameters from a draft request.

Extract and return as JSON:
{
  "document_type": "memo" | "brief",
  "focus_area": "specific area to focus on",
  "question_presented": "the legal question",
  "audience": "intended reader",
  "tone": "formal|neutral|argumentative",
  "source_documents": ["list of relevant source docs from context"]
}

Guidelines:
- If document_type not specified, infer from request
- Focus area should be specific (not vague)
- Question presented should be legally clear
- Tone should match legal practice
- Always set document_type and focus_area (required)
```

---

## 📊 Model Selection Summary

### For All Three Workflows:

| Component | Model | Type | Purpose |
|-----------|-------|------|---------|
| **Question/Intent Processing** | Claude Haiku 4.5 | LLM | Fast, cheap, excellent for text processing |
| **Embedding** | BAAI/bge-large-en-v1.5 | Embedding | 1024-dim, retrieval-optimized, legal-domain ready |
| **Retrieval** | Vector DB + BM25 | Hybrid | Semantic + keyword search |
| **Re-ranking** | BAAI/bge-reranker-large | Cross-encoder | Relevance scoring, legal document expert |
| **Ask Generation** | Claude Sonnet 5.5 | LLM | Fast, capable, cost-effective |
| **Summary Generation** | Opus/Sonnet 5.5 | LLM | Complexity-dependent selection |
| **Draft Generation** | Claude Opus 5.5 | LLM | Most capable, best for complex synthesis |

---

## ✅ Approval Checklist

Before implementation, confirm:

- [ ] Embedding model: BAAI/bge-large-en-v1.5 ✅
- [ ] Re-ranking model: BAAI/bge-reranker-large ✅
- [ ] Ask workflow architecture ✅
- [ ] Summary workflow architecture ✅
- [ ] Draft workflow architecture ✅
- [ ] System prompts for pre-retrieval ✅
- [ ] Model assignments (Haiku/Sonnet/Opus) ✅
- [ ] Hybrid search approach (vector + BM25 + re-rank) ✅

---

## 🚀 Implementation Plan (If Approved)

**Phase 1: Question Rewriting Module**
1. Create `question_rewriter.py` (Haiku + system prompt)
2. Implement guardrails logic
3. Test with chat history edge cases

**Phase 2: Hybrid Retrieval Module**
1. Create `hybrid_retrieval.py`
2. Implement vector search (BGE embeddings)
3. Implement BM25 keyword search
4. Merge and deduplicate results

**Phase 3: Re-ranking Module**
1. Create `reranker.py` (BGE Reranker)
2. Implement scoring and sorting
3. Return top-k ranked chunks

**Phase 4: Ask Workflow**
1. Integrate all components
2. Add Sonnet LLM generation
3. Format response with citations

**Phase 5: Summary Workflow**
1. Implement complexity detection
2. Select Opus or Sonnet
3. Apply summary templates

**Phase 6: Draft Workflow**
1. Intent extraction with Haiku
2. Multi-document retrieval
3. Opus generation with templates

**Phase 7: Testing & Optimization**
1. Unit tests for each module
2. Integration tests for workflows
3. Quality assessment

---

## 📝 Questions for Clarification

Before I start, please confirm:

1. **BGE Model Sizes** — Use large (1.3GB) or smaller base versions?
2. **Re-ranking Top-K** — Keep at 5-10, or adjust per workflow?
3. **BM25 Implementation** — Use existing library or build custom?
4. **Vector DB** — Stick with Chroma from ingestion pipeline?
5. **Sonnet vs Opus for Summary** — Agree with complexity-based selection?
6. **Chat History Limit** — How many previous turns to include?
7. **Response Format** — Should all include citations/sources?

---

## ✨ Key Features

✅ Open-source models (no OpenAI dependency)  
✅ Legal domain optimized  
✅ Hybrid search (semantic + keyword)  
✅ Smart re-ranking  
✅ Question rewriting with guardrails  
✅ Three complete workflows  
✅ Flexible model selection (Haiku/Sonnet/Opus)  
✅ No budget/latency constraints  
✅ Production-ready architecture  

**Ready to implement? Awaiting your approval! 🚀**

