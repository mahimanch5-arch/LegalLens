# Document Ingestion Pipeline Strategy

**Purpose:** Automatically ingest, process, and index uploaded legal documents for retrieval and analysis.

**Scope:** Handles PDF, DOCX, and TXT files; detects scanned vs. unscanned PDFs; extracts text; chunks intelligently; generates embeddings; stores in vector database.

---

## Architecture Overview

```
User uploads document
    ↓
[Automatic Scanned Detection]
    ├─ PDF has text layer? → Unscanned
    └─ PDF empty or image-only? → Scanned
    ↓
[Unscanned Path]              [Scanned Path]
├─ PDFLoader (pypdf)          ├─ Tesseract OCR
├─ DOCX Loader                ├─ Process image pages
├─ TXT Loader                 └─ Extract text
↓                             ↓
[Text Extraction Complete]
    ↓
[Chunking - Recursive Split]
├─ Chunk size: 512 tokens
├─ Overlap: 20% (102 tokens)
├─ Preserve legal boundaries
├─ Keep clause structure intact
    ↓
[Embedding Generation]
├─ Model: Sentence-BERT (all-MiniLM-L6-v2)
├─ Local computation (no API calls)
├─ Dimension: 384
├─ Batch processing for efficiency
    ↓
[Vector Storage]
├─ Store in Chroma (local dev)
├─ Metadata: doc_id, chunk_id, page, filename, type
├─ Enable hybrid search (text + semantic)
    ↓
[Indexing Complete]
├─ Mark document as "ready"
├─ Make available for Ask/Summary/Draft
├─ Log ingestion metrics
```

---

## Phase 1: Unscanned Documents

**Input:** PDF with text layer, DOCX, or TXT file

**Process:**

1. **Load Document**
   - **PDF:** Use PyPDF2 to extract text per page
   - **DOCX:** Use python-docx to extract paragraphs
   - **TXT:** Load as-is

2. **Extract Text**
   - Preserve page numbers and section structure
   - Remove excessive whitespace
   - Keep line breaks meaningful

3. **Chunk Document**
   - Use RecursiveCharacterTextSplitter
   - Target: 512 tokens per chunk
   - Overlap: 20% (102 tokens) for context
   - Respect: paragraph boundaries, clause boundaries

4. **Generate Embeddings**
   - Model: `all-MiniLM-L6-v2` (384 dimensions)
   - Fast, accurate, free
   - Process chunks in batches
   - Cost: $0

5. **Store in Vector DB**
   - Chroma (file-based, local)
   - Store: embedding + metadata
   - Create index for fast retrieval

---

## Phase 2: Scanned Documents

**Input:** PDF with no text layer (image-based)

**Process:**

1. **Detect Scanned Document**
   - Extract text from first page with PyPDF2
   - If text < 50 characters → likely scanned
   - Mark as scanned in metadata

2. **Apply OCR**
   - Use Tesseract for image-to-text
   - Process page-by-page
   - Extract text with confidence scores
   - Flag low-confidence regions

3. **Extract Text**
   - Combine OCR results from all pages
   - Preserve page structure
   - Add OCR confidence metadata
   - Flag pages with <80% confidence

4. **Chunk Document**
   - Same chunking strategy as unscanned
   - Add OCR confidence to metadata
   - Flag chunks from low-confidence pages

5. **Generate Embeddings & Store**
   - Same as unscanned documents
   - Include OCR metadata

---

## Chunking Strategy

### Why Recursive Character Split?

- **Semantic preservation** — Respects sentence/paragraph boundaries
- **Legal documents** — Keeps clauses together
- **Context retention** — 20% overlap maintains continuity
- **Efficiency** — Fast computation, good quality

### Configuration

```python
chunk_size = 512        # tokens (not characters)
chunk_overlap = 0.2     # 20% overlap
separators = [
    "\n\n",            # Paragraph breaks (strongest)
    "\n",              # Line breaks
    ". ",              # Sentences
    " ",               # Words
    ""                 # Characters (fallback)
]
```

### Example

```
Original: "Section 5. Termination. Either party may terminate this agreement..."

Chunks:
- Chunk 1: "Section 5. Termination. Either party may terminate this agreement 
           with 30 days written notice..." (512 tokens)
- Chunk 2: "...with 30 days written notice. Termination is effective upon 
           written receipt by the other party..." (512 tokens)
```

---

## Embedding Model Selection

### Model: `all-MiniLM-L6-v2`

**Why:**
- Excellent for legal documents (trained on diverse data)
- Fast inference (~50ms per 512-token chunk)
- Small footprint (22 MB, runs on CPU)
- 384-dimensional embeddings (good quality/speed tradeoff)
- Free (open-source, no API calls)

**Alternatives (if needed later):**
- `all-mpnet-base-v2` — Slightly better quality, slower
- `bge-large-en-v1.5` — Better for legal, larger
- Claude Embeddings API — Consistent with Claude-first approach, but costs $$

---

## Vector Database Strategy

### Phase 1: Chroma (Development)

**Why:**
- File-based (no Docker needed)
- In-memory + persistent storage
- Good enough for testing
- Easy to inspect data
- Supports semantic search + hybrid

**Setup:**
```python
import chromadb

client = chromadb.Client()
collection = client.create_collection(
    name="legallens_documents",
    metadata={"hnsw:space": "cosine"}
)
```

### Phase 2: Qdrant (Production)

**Why:** (already planned in BRD)
- Distributed vector database
- High performance at scale
- Multiple index types
- Better filtering
- Production-ready

**Migration:** Simple — both use same embedding format

---

## Scanned Document Detection

### Automatic Detection Logic

```
1. Extract first page with PyPDF2
2. Count extracted characters
3. If characters < 50:
   - Classify as "scanned"
   - Flag for OCR
4. Else:
   - Classify as "unscanned"
   - Use standard loader
```

### Confidence Scoring

For scanned documents with OCR:

```python
confidence_threshold = 0.80  # 80% minimum

If average_confidence < 80%:
  - Flag document as "low_ocr"
  - Mark affected pages
  - Show warning in UI
  - Still index, but note in metadata
```

---

## Metadata Structure

Each stored chunk contains:

```json
{
  "id": "doc_abc123~chunk_001",
  "document_id": "doc_abc123",
  "chunk_id": 1,
  "filename": "acme-msa.pdf",
  "file_type": "pdf",
  "is_scanned": false,
  "page_number": 1,
  "page_count": 42,
  "text": "Section 5. Termination...",
  "embedding": [...384 dimensions...],
  "character_start": 150,
  "character_end": 662,
  "created_at": "2026-10-23T10:30:00Z",
  "chunk_count": 15,
  "ocr_confidence": null  // Only for scanned docs
}
```

---

## Error Handling

### Document Level

| Error | Handling |
|-------|----------|
| Corrupt PDF | Reject, user notified |
| Unsupported format | Reject, user notified |
| Password-protected PDF | Reject with instructions |
| Empty document | Reject, user notified |
| File > 50MB | Reject with size limit message |
| Pages > 500 | Process anyway, but mark warning |

### Chunk Level

| Error | Handling |
|-------|----------|
| OCR confidence < 50% | Flag chunk, still store, add metadata |
| Embedding failure | Log, skip chunk, continue with others |
| Vector store unavailable | Queue for retry, mark document as "pending" |

### Recovery

- **Retry mechanism** — Automatic retry for transient failures
- **Partial ingestion** — Don't fail entire document for 1-2 bad chunks
- **Status tracking** — Mark document progress (parsing → chunking → embedding → storing)

---

## Performance Expectations

| Operation | Time | Notes |
|-----------|------|-------|
| Load PDF (10 pages) | 100ms | PyPDF2 |
| Extract text | 50ms | Per page average |
| Chunk document | 200ms | Recursive split on 10 pages |
| Embed chunks | 2-5s | Batch of 15 chunks, CPU |
| Store in Chroma | 500ms | Write to vector DB |
| **Total (10-page PDF)** | **3-6 seconds** | End-to-end unscanned |
| **Scanned (OCR add-on)** | **+5-15s** | Per page with OCR |

---

## Retrieval Strategy

### Semantic Search

```python
# User query: "What are the termination rights?"
# 1. Embed query (384 dims)
# 2. Find top-k similar chunks (cosine similarity)
# 3. Return with scores (0.0-1.0)

query = "What are the termination rights?"
query_embedding = model.encode(query)

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5
)

# Returns: [
#   {id: "doc_abc~chunk_005", distance: 0.92, text: "..."},
#   {id: "doc_abc~chunk_006", distance: 0.85, text: "..."},
#   ...
# ]
```

### Filtering

```python
# Example: Search only in contract documents
results = collection.query(
    query_embeddings=[query_embedding],
    where={"file_type": {"$eq": "pdf"}},
    where_document={"$contains": "termination"},
    n_results=5
)
```

---

## Integration with Intent Classifier

**Ask intent** → Uses semantic search to find relevant chunks  
**Summary intent** → Retrieves all chunks from single document, then summarizes  
**Draft intent** → Retrieves relevant chunks as sources for memo/brief  

---

## Future Enhancements

1. **Hybrid Search** — Combine semantic + keyword search
2. **Re-ranking** — Use cross-encoder to re-rank retrieved chunks
3. **Metadata Filtering** — Filter by document type, date, keyword
4. **Incremental Indexing** — Update embeddings without reprocessing
5. **Multi-modal** — Handle scanned documents with layout understanding (Docling)
6. **Section Awareness** — Preserve document structure (clauses, sections)
7. **Query Expansion** — Expand legal queries with synonyms
8. **Caching** — Cache frequent query embeddings

---

## Testing Strategy

### Unit Tests
- Document loading (PDF, DOCX, TXT)
- Scanned detection accuracy
- Chunking logic (boundary preservation)
- Embedding generation
- Vector store operations

### Integration Tests
- End-to-end ingestion pipeline
- Multi-file processing
- Error recovery
- Performance benchmarks

### Test Data
- Clean PDFs (unscanned)
- Scanned PDFs (image-based)
- DOCX files
- TXT files
- Edge cases (empty, corrupt, large)

---

## Success Criteria

✅ Correctly ingests PDF, DOCX, TXT  
✅ Detects scanned documents automatically  
✅ Applies OCR to scanned documents  
✅ Chunks documents intelligently  
✅ Generates embeddings for all chunks  
✅ Stores in vector DB with full metadata  
✅ Enables semantic search  
✅ Handles errors gracefully  
✅ Performance < 10s for 10-page PDF  
✅ All unit + integration tests pass  

