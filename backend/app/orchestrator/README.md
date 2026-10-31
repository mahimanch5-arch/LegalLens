# LegalLens Intent Classifier Orchestrator

Intent classification module for LegalLens — automatically routes user queries to the appropriate response type.

## Overview

The intent classifier identifies what the user is asking for and routes it to the appropriate handler:

- **Ask** — Answer a specific question with cited information
- **Summary** — Extract structured information from a single document
- **Draft** — Generate new legal documents (memo, brief)
- **Auto** — Let the backend router decide (fallback)

## Architecture

```
User Message
    ↓
    ├─→ [Heuristic Rules] (fast, rule-based)
    │   └─→ High confidence? → Return intent
    │
    └─→ [Claude Haiku LLM] (accurate, when heuristics inconclusive)
        └─→ Return intent + confidence
```

**Design philosophy:** Fast heuristics first, fallback to Claude Haiku for edge cases.

## Installation

### Dependencies

```bash
# Install LangChain and Claude SDK
pip install langchain langchain-anthropic python-dotenv

# or add to requirements.txt:
langchain>=0.1.0
langchain-anthropic>=0.0.1
python-dotenv>=1.0
```

### API Key Setup

1. Get your Anthropic API key from [console.anthropic.com](https://console.anthropic.com)
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Add your API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-v0-...your-key...
   ```

## Quick Start

### Interactive Testing

```bash
# Start interactive classification mode
python test_classifier_cli.py

# Single classification
python test_classifier_cli.py "What are the termination rights?"

# Batch test all examples
python test_classifier_cli.py --batch

# Enable debug logging
python test_classifier_cli.py --debug
```

### In Code

```python
from intent_classifier import IntentClassifier

classifier = IntentClassifier()

# Classify a message
result = classifier.classify("Draft a memo on indemnification")

print(f"Intent: {result.intent.value}")           # → "draft"
print(f"Confidence: {result.confidence:.1%}")    # → "95.0%"
print(f"Reason: {result.reason}")                # → "Contains draft keywords..."
print(f"Used heuristic: {result.used_heuristic}") # → True
```

### With Context

```python
# Provide document scope and conversation history for refinement
result = classifier.classify(
    message="What are the key terms?",
    document_scope="single_doc",  # "workspace", "documents", or "single_doc"
    conversation_history_length=3
)
```

## Classification Rules

### Heuristic Rules (Fast Path)

Executed in order; first match wins:

| Priority | Condition | Intent | Confidence |
|----------|-----------|--------|------------|
| 1 | Contains: draft, write, create, generate, memo, brief | **Draft** | 95% |
| 2 | Contains: summarize, summary, overview, extract, key points | **Summary** | 90% |
| 3 | Contains: "?" | **Ask** | 85% |
| 4 | Starts with: tell me, show me, explain, describe | **Ask** | 80% |
| 5 | Message < 20 chars | **Ask** | 60% |
| 6 | Default | **Ask** | 50% |

### LLM Fallback (Claude Haiku)

When heuristic confidence < threshold (default: 70%), the classifier falls back to Claude Haiku for accurate classification.

**Example edge cases:**
- "Create a brief" → Heuristic says "summary" (brief keyword), but should be "draft" (create keyword) → Needs LLM refinement
- Ambiguous multi-intent phrases
- Context-dependent queries

## Testing

### Unit Tests

```bash
# Run all tests
pytest test_intent_classifier.py -v

# Run specific test class
pytest test_intent_classifier.py::TestHeuristicClassification -v

# Run with coverage
pytest test_intent_classifier.py --cov=intent_classifier
```

### Test Coverage

- ✅ **Heuristic classification:** All intent types, keyword matching, case-insensitivity, priorities
- ✅ **Confidence scores:** Correct ranges for each intent
- ✅ **Edge cases:** Empty messages, unicode, very long text
- ✅ **Context awareness:** Document scope, conversation history
- ✅ **LLM fallback:** (requires API key) Haiku classification for inconclusive cases

### Running Tests with API Key

Tests requiring the API key are skipped if `ANTHROPIC_API_KEY` is not set. To run full test suite:

```bash
# Set API key
export ANTHROPIC_API_KEY=sk-ant-v0-...

# Run all tests including LLM tests
pytest test_intent_classifier.py -v
```

## Configuration

Edit `.env` or `.env.example`:

```bash
# API Configuration
ANTHROPIC_API_KEY=sk-ant-v0-...

# Model Configuration
INTENT_CLASSIFIER_MODEL=claude-haiku-4-5  # Fast, cost-effective
INTENT_CLASSIFIER_TEMPERATURE=0.2         # Low randomness (0.0-2.0)
INTENT_CLASSIFIER_CONFIDENCE_THRESHOLD=0.7  # Fallback to LLM below this

# Debug
INTENT_CLASSIFIER_DEBUG=false             # Set to true for verbose logging
```

## Files

```
backend/app/orchestrator/
├── intent_classifier.py              # Main module (standalone, no dependencies on backend)
├── test_intent_classifier.py         # Unit tests (pytest)
├── test_classifier_cli.py            # Interactive & batch testing CLI
├── intent-classifier-prompt.md       # Classification strategy & examples
├── .env.example                      # Environment template
├── .env                              # Your API key (NEVER commit)
└── README.md                         # This file
```

## Integration with Backend (Later)

When ready to integrate with the main API:

1. Move `intent_classifier.py` to the main orchestrator interface
2. Instantiate classifier in the router:
   ```python
   from app.orchestrator.intent_classifier import IntentClassifier, Intent
   
   classifier = IntentClassifier()
   result = classifier.classify(user_message)
   
   if result.intent == Intent.DRAFT:
       return await orchestrator.draft(context)
   elif result.intent == Intent.SUMMARY:
       return await orchestrator.summarize(context)
   else:  # ASK or AUTO
       return await orchestrator.answer(context)
   ```

3. Update the turn service to use classified intent

## Performance

- **Heuristic classification:** < 5ms (local keyword matching)
- **LLM classification:** ~200-500ms (Claude Haiku API call)
- **Fallback rate:** ~20-30% (well-written queries match heuristics ~70-80% of the time)

## Cost

- **API cost:** ~$0.0001 per LLM classification (Claude Haiku at $1/$5 per 1M tokens)
- **Monthly estimate** (1M classifications): ~$100 (heuristics are free)

## Troubleshooting

### "ANTHROPIC_API_KEY not set" Error

```bash
# Set your API key
export ANTHROPIC_API_KEY=sk-ant-v0-...

# Or in .env file
echo "ANTHROPIC_API_KEY=sk-ant-v0-..." >> .env
```

### LLM Classification Failing

```python
# Check debug output
import os
os.environ["INTENT_CLASSIFIER_DEBUG"] = "true"

classifier = IntentClassifier()
result = classifier.classify("your message")
```

### Wrong Classifications

1. Run batch tests to see patterns:
   ```bash
   python test_classifier_cli.py --batch
   ```

2. Lower confidence threshold to use LLM more often:
   ```bash
   INTENT_CLASSIFIER_CONFIDENCE_THRESHOLD=0.5  # Use LLM more liberally
   ```

3. Add specific keywords to heuristic rules (edit `intent_classifier.py`)

## Examples

### Ask Intent
```
"What are the termination rights?"
→ Intent: ask (confidence: 85%)
→ Reason: Message contains question mark

"Tell me about the payment terms"
→ Intent: ask (confidence: 80%)
→ Reason: Starts with information-seeking phrase
```

### Summary Intent
```
"Summarize this contract"
→ Intent: summary (confidence: 90%)
→ Reason: Contains summary keywords

"Give me an overview of this opinion"
→ Intent: summary (confidence: 85%)
→ Reason: Contains overview keyword
```

### Draft Intent
```
"Draft a memo on indemnification"
→ Intent: draft (confidence: 95%)
→ Reason: Contains draft keywords

"Write a case brief for this opinion"
→ Intent: draft (confidence: 95%)
→ Reason: Contains write, brief keywords
```

### Edge Cases
```
"Draft a summary of the opinion"
→ Intent: draft (confidence: 95%)
→ Reason: Draft takes priority over summary

"Create a brief"
→ Intent: draft (confidence: 95%)
→ Reason: Contains draft keywords

"xyz"
→ Intent: ask (confidence: 60%)
→ Reason: Very short message (likely a question)
```

## Future Enhancements

1. **Machine learning:** Train a classifier on production queries for higher accuracy
2. **Confidence feedback loop:** Track misclassifications and adjust thresholds
3. **Multi-intent support:** Some queries might be "ask + summary" or "summary + draft"
4. **Conversation context:** Use message history to refine classification
5. **User intent feedback:** Let users correct classifications to improve the model

## Questions?

See `intent-classifier-prompt.md` for the full classification strategy and reasoning.

