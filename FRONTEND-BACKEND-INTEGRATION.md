## Frontend-Backend Integration Guide

**Complete integration instructions for connecting React/Vue frontend to workflow APIs.**

---

## 🔌 API Endpoints

### Base URL
```
http://localhost:5000/api
```

---

## 📝 Ask Workflow API

### Endpoint: POST `/ask`

**Request:**
```javascript
POST http://localhost:5000/api/ask
Content-Type: application/json

{
  "question": "What are the termination rights?",
  "chat_history": [
    {
      "user": "What type of agreement?",
      "assistant": "This is an employment agreement..."
    }
  ],
  "document_filter": null  // Optional: filter to single document
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "original_question": "What are the termination rights?",
    "rewritten_question": "What are the termination rights in this agreement?",
    "generated_answer": "According to [1] the agreement, termination can occur [2]...",
    "citations": [
      {
        "number": 1,
        "text": "Section 5. Termination...",
        "document_id": "doc_123",
        "chunk_id": "chunk_456",
        "score": 0.95
      },
      {
        "number": 2,
        "text": "Either party may terminate with 30 days notice...",
        "document_id": "doc_123",
        "chunk_id": "chunk_457",
        "score": 0.92
      }
    ],
    "metadata": {
      "retrieval_count": 50,
      "final_chunks": 10,
      "processing_time_ms": 3500
    }
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Question cannot be empty",
  "code": "INVALID_INPUT"
}
```

### Frontend Implementation (React)

```javascript
import { useState } from 'react';

export function AskWorkflow() {
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAsk = async () => {
    if (!question.trim()) {
      setError('Question cannot be empty');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:5000/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          chat_history: chatHistory,
          document_filter: null
        })
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error);
      }

      setAnswer(data.data);
      
      // Add to chat history
      setChatHistory([
        ...chatHistory,
        {
          user: question,
          assistant: data.data.generated_answer
        }
      ]);

      setQuestion(''); // Clear input
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ask-workflow">
      <h1>Ask - Question & Answers</h1>
      
      {/* Chat History */}
      <div className="chat-history">
        {chatHistory.map((turn, i) => (
          <div key={i}>
            <div className="user-message">👤 {turn.user}</div>
            <div className="assistant-message">🤖 {turn.assistant}</div>
          </div>
        ))}
      </div>

      {/* Question Input */}
      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask your question..."
        disabled={loading}
      />

      <button onClick={handleAsk} disabled={loading}>
        {loading ? 'Processing...' : 'Ask'}
      </button>

      {/* Error */}
      {error && <div className="error">{error}</div>}

      {/* Answer */}
      {answer && (
        <div className="answer">
          <h3>Answer</h3>
          <p>{answer.generated_answer}</p>
          
          <h4>Sources</h4>
          {answer.citations.map((citation) => (
            <div key={citation.number} className="citation">
              <strong>[{citation.number}]</strong>
              <p>{citation.text}</p>
              <small>
                From: {citation.document_id} 
                (Score: {(citation.score * 100).toFixed(1)}%)
              </small>
            </div>
          ))}

          <div className="metadata">
            <p>Retrieved: {answer.metadata.retrieval_count} chunks</p>
            <p>Final: {answer.metadata.final_chunks} chunks</p>
            <p>Time: {answer.metadata.processing_time_ms}ms</p>
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## 📊 Summary Workflow API

### Endpoint: POST `/summarize`

**Request:**
```javascript
POST http://localhost:5000/api/summarize
Content-Type: application/json

{
  "document_id": "doc_123",
  "query": null  // Optional: summarize specific aspect
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "document_type": "contract",
    "document_id": "doc_123",
    "structured_summary": {
      "type": "contract",
      "model_used": "claude-sonnet-5-5",
      "fields": {
        "Parties": "ABC Corp and XYZ LLC",
        "Effective Date": "January 1, 2024",
        "Key Terms": "Service agreement with 2-year term",
        "Obligations": "ABC: Provide services; XYZ: Pay monthly fees",
        "Termination": "Either party with 30 days notice",
        "Renewal": "Automatic annual renewal unless terminated"
      },
      "content": "Full summary text..."
    },
    "metadata": {
      "complexity": "moderate",
      "chunks_used": 8,
      "retrieval_count": 50,
      "processing_time_ms": 4200
    }
  }
}
```

### Frontend Implementation (React)

```javascript
export function SummaryWorkflow() {
  const [documents, setDocuments] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch available documents
  useEffect(() => {
    fetch('http://localhost:5000/api/documents')
      .then(r => r.json())
      .then(data => setDocuments(data.documents))
      .catch(err => setError(err.message));
  }, []);

  const handleSummarize = async () => {
    if (!selectedDoc) {
      setError('Please select a document');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:5000/api/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: selectedDoc,
          query: null
        })
      });

      const data = await response.json();
      if (!data.success) throw new Error(data.error);

      setSummary(data.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="summary-workflow">
      <h1>Summarize - Document Understanding</h1>

      {/* Document Selection */}
      <select 
        value={selectedDoc || ''} 
        onChange={(e) => setSelectedDoc(e.target.value)}
        disabled={loading}
      >
        <option value="">Select document...</option>
        {documents.map(doc => (
          <option key={doc.id} value={doc.id}>
            {doc.name}
          </option>
        ))}
      </select>

      <button onClick={handleSummarize} disabled={loading || !selectedDoc}>
        {loading ? 'Summarizing...' : 'Summarize'}
      </button>

      {error && <div className="error">{error}</div>}

      {summary && (
        <div className="summary">
          <h2>{summary.document_type.toUpperCase()} Summary</h2>
          
          <div className="complexity-badge">
            Complexity: <strong>{summary.metadata.complexity}</strong>
          </div>

          <div className="fields">
            {Object.entries(summary.structured_summary.fields).map(
              ([field, value]) => (
                <div key={field} className="field">
                  <strong>{field}:</strong>
                  <p>{value}</p>
                </div>
              )
            )}
          </div>

          <div className="metadata">
            <p>Model: {summary.structured_summary.model_used}</p>
            <p>Chunks Used: {summary.metadata.chunks_used}</p>
            <p>Time: {summary.metadata.processing_time_ms}ms</p>
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## 📝 Draft Workflow API

### Endpoint: POST `/draft`

**Request:**
```javascript
POST http://localhost:5000/api/draft
Content-Type: application/json

{
  "request": "Draft a memo analyzing the termination clause"
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "draft_params": {
      "document_type": "memo",
      "focus_area": "termination clause",
      "question_presented": "What are the termination rights and procedures?",
      "audience": "legal professional",
      "tone": "formal",
      "source_documents": []
    },
    "generated_draft": "MEMORANDUM\n\nTO: Attorney\nFROM: LegalLens AI\n...",
    "citations": [
      {
        "number": 1,
        "chunk_id": "chunk_123",
        "document_id": "doc_456",
        "text": "Section 5. Termination..."
      }
    ],
    "source_manifest": {
      "doc_456": [
        {
          "chunk_id": "chunk_123",
          "rank": 1,
          "score": 0.95
        }
      ]
    },
    "metadata": {
      "retrieval_count": 45,
      "final_chunks": 10,
      "citation_count": 8,
      "warning": "UNREVIEWED AI DRAFT - ATTORNEY REVIEW REQUIRED",
      "processing_time_ms": 5800
    }
  }
}
```

### Frontend Implementation (React)

```javascript
export function DraftWorkflow() {
  const [request, setRequest] = useState('');
  const [draft, setDraft] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleDraft = async () => {
    if (!request.trim()) {
      setError('Please enter a draft request');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:5000/api/draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request })
      });

      const data = await response.json();
      if (!data.success) throw new Error(data.error);

      setDraft(data.data);
      setRequest('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="draft-workflow">
      <h1>Draft - Document Generation</h1>

      {/* Warning Banner */}
      {draft && (
        <div className="warning-banner">
          ⚠️ {draft.metadata.warning}
        </div>
      )}

      {/* Request Input */}
      <textarea
        value={request}
        onChange={(e) => setRequest(e.target.value)}
        placeholder="What would you like to draft? (e.g., 'Draft a memo analyzing termination clause')"
        disabled={loading}
        rows={4}
      />

      <button onClick={handleDraft} disabled={loading || !request.trim()}>
        {loading ? 'Generating...' : 'Draft'}
      </button>

      {error && <div className="error">{error}</div>}

      {draft && (
        <div className="draft-result">
          {/* Intent Parameters */}
          <div className="parameters">
            <h3>Document Parameters</h3>
            <p><strong>Type:</strong> {draft.draft_params.document_type}</p>
            <p><strong>Audience:</strong> {draft.draft_params.audience}</p>
            <p><strong>Tone:</strong> {draft.draft_params.tone}</p>
            <p><strong>Focus:</strong> {draft.draft_params.focus_area}</p>
          </div>

          {/* Generated Draft */}
          <div className="generated-draft">
            <h3>Generated Draft</h3>
            <div className="draft-content">
              {draft.generated_draft}
            </div>
          </div>

          {/* Citations */}
          <div className="citations">
            <h3>Sources ({draft.citations.length})</h3>
            {draft.citations.map((cite) => (
              <div key={cite.number} className="citation">
                <strong>[{cite.number}]</strong>
                <p>{cite.text}</p>
                <small>From: {cite.document_id}</small>
              </div>
            ))}
          </div>

          {/* Metadata */}
          <div className="metadata">
            <p>Retrieved: {draft.metadata.retrieval_count}</p>
            <p>Final: {draft.metadata.final_chunks}</p>
            <p>Time: {draft.metadata.processing_time_ms}ms</p>
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## 🔗 Common Integration Patterns

### Error Handling with Retry

```javascript
async function callWorkflowAPI(endpoint, body, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(`http://localhost:5000/api${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error);
      }

      return data.data;
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      // Wait before retry
      await new Promise(r => setTimeout(r, 1000 * (i + 1)));
    }
  }
}
```

### Progress Tracking

```javascript
function* askWorkflowSteps(question, chatHistory) {
  yield { step: 1, status: 'Rewriting question...' };
  
  yield { step: 2, status: 'Searching documents...' };
  
  yield { step: 3, status: 'Ranking results...' };
  
  yield { step: 4, status: 'Generating answer...' };
  
  const response = await fetch('http://localhost:5000/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, chat_history: chatHistory })
  });

  yield { step: 5, status: 'Complete', data: await response.json() };
}
```

### Streaming Results (if backend supports)

```javascript
async function streamAsk(question) {
  const response = await fetch('http://localhost:5000/api/ask/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        yield data;
      }
    }
  }
}
```

### Request Cancellation

```javascript
export function useAskWorkflow() {
  const abortControllerRef = useRef(null);

  const ask = async (question, chatHistory) => {
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('http://localhost:5000/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, chat_history: chatHistory }),
        signal: abortControllerRef.current.signal
      });

      return await response.json();
    } catch (error) {
      if (error.name === 'AbortError') {
        return { error: 'Request cancelled' };
      }
      throw error;
    }
  };

  const cancel = () => {
    abortControllerRef.current?.abort();
  };

  return { ask, cancel };
}
```

---

## 📱 API Response Formats

### Success Response Format

```json
{
  "success": true,
  "data": {
    // Workflow-specific data
  }
}
```

### Error Response Format

```json
{
  "success": false,
  "error": "Human-readable error message",
  "code": "ERROR_CODE",
  "details": {
    // Optional: Additional error context
  }
}
```

### Common Error Codes

```
INVALID_INPUT       - Request validation failed
NO_DOCUMENTS        - No documents in vector store
API_KEY_INVALID     - Anthropic API key invalid
API_TIMEOUT         - Request exceeded timeout
CONNECTION_ERROR    - Cannot connect to service
INTERNAL_ERROR      - Server error
```

---

## 🔐 Security Considerations

### CORS Configuration

Add to backend `app.py`:

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})
```

### Rate Limiting

```javascript
// Frontend: Implement cooldown
const [cooldownUntil, setCooldownUntil] = useState(0);

const canAsk = Date.now() > cooldownUntil;

const handleAsk = async () => {
  if (!canAsk) return;
  
  // ... ask logic ...
  
  setCooldownUntil(Date.now() + 2000); // 2s cooldown
};
```

### API Key Management

Never expose API key in frontend. Keep it server-side only:

```javascript
// ❌ WRONG: Never do this
const answer = await fetch('...?api_key=sk-ant-...');

// ✅ RIGHT: Backend handles auth
const answer = await fetch('http://localhost:5000/api/ask', {
  method: 'POST',
  body: JSON.stringify({ question })
  // Backend uses ANTHROPIC_API_KEY from .env
});
```

---

## 🧪 Testing the Integration

### Manual API Testing with cURL

```bash
# Test Ask
curl -X POST http://localhost:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are termination rights?",
    "chat_history": [],
    "document_filter": null
  }'

# Test Summary
curl -X POST http://localhost:5000/api/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_123",
    "query": null
  }'

# Test Draft
curl -X POST http://localhost:5000/api/draft \
  -H "Content-Type: application/json" \
  -d '{
    "request": "Draft a memo about termination"
  }'
```

### JavaScript Testing

```javascript
// In browser console
fetch('http://localhost:5000/api/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: 'What are the parties?',
    chat_history: []
  })
})
.then(r => r.json())
.then(data => console.log(data))
.catch(e => console.error(e));
```

---

## 📊 Expected Response Times

| Workflow | Step | Time |
|----------|------|------|
| Ask | Rewrite | 300ms |
| Ask | Retrieve | 150ms |
| Ask | Rerank | 500ms |
| Ask | Generate | 1-3s |
| Ask | **Total** | **2-4s** |
| Summary | Full pipeline | 4-6s |
| Draft | Full pipeline | 5-8s |

---

## 🚀 Deployment Checklist

- [ ] Backend running on production URL
- [ ] CORS configured properly
- [ ] API keys stored securely
- [ ] Error handling implemented
- [ ] Loading states shown
- [ ] Timeouts configured
- [ ] Rate limiting implemented
- [ ] Logging enabled
- [ ] Monitoring configured
- [ ] Documentation updated

---

**Integration complete and ready for testing!** ✅
