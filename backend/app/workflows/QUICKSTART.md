## Workflows Quick Start Guide

Get the Ask/Summary/Draft workflows running in 5 minutes.

---

## 1️⃣ Installation

```bash
# Navigate to workflows directory
cd backend/app/workflows

# Install dependencies
pip install -r requirements-workflows.txt

# Verify installation
python -c "import langchain; import sentence_transformers; print('✅ Ready')"
```

---

## 2️⃣ Configuration

Create a `.env` file in the workflows directory:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
```

Get your API key from [console.anthropic.com](https://console.anthropic.com)

---

## 3️⃣ Run Tests

```bash
# Run all tests
pytest -v

# Run specific test file
pytest test_ask_workflow.py -v

# Run with coverage
pytest --cov=. --cov-report=html
```

**Expected output:**
```
test_ask_workflow.py::TestAskResult::test_ask_result_creation PASSED
test_ask_workflow.py::TestAskWorkflowExecution::test_execute_five_step_pipeline PASSED
...
========================= 90 passed in 1.23s =========================
```

---

## 4️⃣ Basic Usage

### Ask Workflow (Q&A)

```python
from workflows import ask, AskWorkflow
from hybrid_retrieval import ChromaVectorHybridRetriever

# Initialize retriever (connects to vector store)
retriever = ChromaVectorHybridRetriever()

# Simple usage
result = ask(retriever, "What are termination rights?")

print(f"Question: {result.original_question}")
print(f"Rewritten: {result.rewritten_question}")
print(f"Answer: {result.generated_answer}")
print(f"Citations: {len(result.citations)} sources cited")

# With chat history
history = [
    ("What is this agreement?", "It's a service agreement"),
    ("Who are the parties?", "ABC Corp and XYZ LLC")
]

result = ask(retriever, "What about termination?", chat_history=history)
```

### Summary Workflow (Document Understanding)

```python
from workflows import summarize

# Summarize a document
result = summarize(retriever, document_id="doc_123")

print(f"Document Type: {result.document_type}")
print(f"Summary:\n{result.structured_summary['content']}")
```

### Draft Workflow (Document Generation)

```python
from workflows import draft

# Generate a memo
result = draft(retriever, "Draft a memo analyzing termination clause")

print(f"Draft Type: {result.draft_params.document_type}")
print(f"Generated:\n{result.generated_draft}")
print(f"Sources Used: {len(result.citations)} citations")
```

---

## 5️⃣ Common Tasks

### Test a Specific Component

```bash
# Test question rewriting
pytest test_question_rewriter.py::TestGuardrails -v

# Test retrieval
pytest test_hybrid_retrieval.py::TestChromaVectorHybridRetriever::test_hybrid_search_merging -v

# Test citation extraction
pytest test_ask_workflow.py::TestCitationExtraction -v
```

### Debug a Failing Test

```bash
# Show print statements
pytest test_ask_workflow.py -v -s

# Stop on first failure
pytest test_ask_workflow.py -v -x

# Drop into debugger on failure
pytest test_ask_workflow.py -v --pdb
```

### Check Test Coverage

```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html

# View report
open htmlcov/index.html  # macOS
start htmlcov/index.html # Windows
xdg-open htmlcov/index.html # Linux
```

---

## 6️⃣ Architecture Overview

```
User Question
    ↓
[1] Question Rewriter (Claude Haiku)
    - Applies 3 strict guardrails
    - Checks chat history
    ↓
[2] Hybrid Retrieval
    - Vector search (BGE embeddings)
    - Keyword search (BM25)
    - Merges & deduplicates → ~50 results
    ↓
[3] Re-ranking (BGE Reranker)
    - Scores each chunk (0-1)
    - Sorts by relevance
    - Returns top 10
    ↓
[4] RAG Context Building
    - Formats chunks with citations [1][2]...
    - Includes source information
    ↓
[5] Generation (Claude Sonnet/Opus)
    - Answers with citations
    - Extracts sources automatically
    ↓
Answer + Citations + Sources
```

---

## 7️⃣ File Structure

```
workflows/
├── question_rewriter.py ............ Question rewriting with guardrails
├── hybrid_retrieval.py ............ Vector + keyword search
├── reranker.py .................... BGE re-ranking
├── ask_workflow.py ................ Complete Ask workflow (Q&A)
├── summary_workflow.py ............ Document summarization
├── draft_workflow.py .............. Memo/brief generation
│
├── test_question_rewriter.py ....... 20+ tests
├── test_hybrid_retrieval.py ........ 18+ tests
├── test_reranker.py ............... 22+ tests
├── test_ask_workflow.py ........... 30+ tests
│
├── __init__.py .................... Module exports
├── requirements-workflows.txt ...... Dependencies
├── TESTING-WORKFLOWS.md ........... Full testing guide
└── QUICKSTART.md .................. This file
```

---

## 🎯 Next Steps

1. **Install & Test** — `pip install -r requirements-workflows.txt && pytest -v`
2. **Run a Single Test** — `pytest test_ask_workflow.py::TestAskResult -v`
3. **Try the Ask Workflow** — Follow usage example above
4. **Review Test Coverage** — `pytest --cov=. --cov-report=html`
5. **Read TESTING-WORKFLOWS.md** — For comprehensive test documentation

---

## ❓ Troubleshooting

### ImportError: No module named 'langchain'

```bash
pip install langchain langchain-anthropic
```

### ImportError: No module named 'sentence_transformers'

```bash
pip install sentence-transformers
```

### ANTHROPIC_API_KEY not found

Create `.env` file with:
```
ANTHROPIC_API_KEY=your-key-here
```

### Tests fail with "Model not loaded"

Tests use mocks by default. To test with real models, set:
```bash
export SKIP_MOCK_TESTS=false
```

### Vector store not initialized

Most tests use mocks. For integration tests with real Chroma:
```python
from chromadb import Client
retriever = ChromaVectorHybridRetriever()
retriever.vector_store = Client().get_or_create_collection("test")
```

---

## ✅ Verification Checklist

After installation:

- [ ] `pip list` shows langchain, anthropic, sentence-transformers
- [ ] `python -c "import langchain"` works
- [ ] `python -c "from workflows import ask"` works
- [ ] `pytest -v` shows 90+ tests
- [ ] `pytest test_ask_workflow.py::TestAskResult::test_ask_result_creation PASSED`

---

## 📚 Additional Resources

- [TESTING-WORKFLOWS.md](TESTING-WORKFLOWS.md) — Complete testing guide
- [ASK-SUMMARY-DRAFT-WORKFLOWS-PLAN.md](../../../ASK-SUMMARY-DRAFT-WORKFLOWS-PLAN.md) — Architecture document
- [WORKFLOWS-IMPLEMENTATION-COMPLETE.md](../../../WORKFLOWS-IMPLEMENTATION-COMPLETE.md) — Implementation status
- [Anthropic Documentation](https://docs.anthropic.com)
- [LangChain Documentation](https://python.langchain.com)

---

**Status:** ✅ Ready to use | 90+ tests passing | Production-ready code

Happy coding! 🚀
