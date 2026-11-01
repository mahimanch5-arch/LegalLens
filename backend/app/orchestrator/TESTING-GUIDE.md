# Intent Classifier - Complete Testing Guide

## Prerequisites

### 1. Get API Key
Get your Anthropic API key from: https://console.anthropic.com/

### 2. Install Dependencies
```bash
cd backend
pip install langchain langchain-anthropic python-dotenv pytest
```

### 3. Add API Key to .env
Edit `backend/app/orchestrator/.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-v0-your-actual-key-here
INTENT_CLASSIFIER_MODEL=claude-haiku-4-5
INTENT_CLASSIFIER_CONFIDENCE_THRESHOLD=0.7
INTENT_CLASSIFIER_TEMPERATURE=0.2
INTENT_CLASSIFIER_DEBUG=false
```

---

## Test Suite Overview

### Phase 1: Heuristic Classification (No API calls needed)
Fast, rule-based intent classification. Tests keyword matching and priority rules.

### Phase 2: LLM Fallback (Requires API key)
Claude Haiku classification for edge cases when heuristics are inconclusive.

### Phase 3: Unit Tests (Requires API key for some tests)
40+ comprehensive tests with pytest.

---

## Running Tests

### Option A: Interactive Mode (Best for Understanding)

```bash
cd backend/app/orchestrator
python test_classifier_cli.py
```

**Try these examples:**

```
Input:  What are the termination rights?
Output: Intent: ASK, Confidence: 85%, Method: Heuristic
Reason: Message contains question mark

Input:  Summarize this contract
Output: Intent: SUMMARY, Confidence: 90%, Method: Heuristic
Reason: Contains summary keywords

Input:  Draft a memo on indemnification
Output: Intent: DRAFT, Confidence: 95%, Method: Heuristic
Reason: Contains draft keywords (draft, write, create, etc.)

Input:  Tell me about the key points
Output: Intent: SUMMARY, Confidence: 90%, Method: Heuristic
Reason: Contains summary keywords

Input:  Create a brief summarizing the holding
Output: Intent: DRAFT, Confidence: 95%, Method: Heuristic
Reason: Contains draft keywords (draft, write, create, etc.)

Input:  xyz
Output: Intent: ASK, Confidence: 60%, Method: Heuristic
Reason: Very short message (likely a question)

Input:  quit
Output: (exits the program)
```

### Option B: Batch Test Mode (Quick Results)

```bash
python test_classifier_cli.py --batch
```

**Expected output:**
```
🤖 LegalLens Intent Classifier - Batch Test Mode
======================================================================

✅ [PASS] What are the termination rights?       → ask        (expected: ask)
✅ [PASS] When does the contract expire?         → ask        (expected: ask)
✅ [PASS] How much notice must be given?         → ask        (expected: ask)
✅ [PASS] Are there non-compete clauses?         → ask        (expected: ask)
✅ [PASS] Can you explain the indemnification?   → ask        (expected: ask)
✅ [PASS] Tell me about the payment terms        → ask        (expected: ask)
✅ [PASS] Summarize this contract                → summary    (expected: summary)
✅ [PASS] Give me an overview of this opinion    → summary    (expected: summary)
✅ [PASS] What are the key points?               → summary    (expected: summary)
✅ [PASS] Extract the main terms                 → summary    (expected: summary)
✅ [PASS] Summarize and extract key information  → summary    (expected: summary)
✅ [PASS] Draft a memo on indemnification        → draft      (expected: draft)
✅ [PASS] Write a case brief for this opinion    → draft      (expected: draft)
✅ [PASS] Create a memo analyzing termination    → draft      (expected: draft)
✅ [PASS] Generate a brief summarizing holding   → draft      (expected: draft)
✅ [PASS] Prepare a memorandum on pricing        → draft      (expected: draft)
✅ [PASS] xyz                                    → ask        (expected: ask)
✅ [PASS] draft a summary                        → draft      (expected: draft)
✅ [PASS] What is a good case brief?             → ask        (expected: ask)

======================================================================
Results: 20 passed, 0 failed out of 20 tests
🎉 All tests passed!
======================================================================
```

### Option C: Single Classification

```bash
python test_classifier_cli.py "Your test message here"
```

**Example:**
```bash
python test_classifier_cli.py "What are the termination rights?"

======================================================================
Message: What are the termination rights?
----------------------------------------------------------------------
Intent:        ASK
Confidence:    85.0%
Method:        Heuristic
Reason:        Message contains question mark
======================================================================
```

### Option D: Unit Tests with pytest

```bash
# Run all tests
pytest test_intent_classifier.py -v

# Run with coverage
pytest test_intent_classifier.py --cov=intent_classifier -v

# Run specific test class
pytest test_intent_classifier.py::TestHeuristicClassification -v
```

**Expected output:**
```
test_intent_classifier.py::TestHeuristicClassification::test_draft_intent_with_draft_keyword PASSED
test_intent_classifier.py::TestHeuristicClassification::test_draft_intent_with_write_keyword PASSED
test_intent_classifier.py::TestHeuristicClassification::test_summary_intent_with_summarize_keyword PASSED
test_intent_classifier.py::TestHeuristicClassification::test_ask_intent_with_question_mark PASSED
...
===================== 40 passed in 0.45s =====================
```

### Option E: Debug Mode (Verbose Logging)

```bash
python test_classifier_cli.py --debug --batch
```

Shows internal decision-making:
```
[DEBUG] Heuristic result: ClassificationResult(intent=<Intent.DRAFT: 'draft'>, confidence=0.95, reason='Contains draft keywords (draft, write, create, etc.)', used_heuristic=True)
[DEBUG] Heuristic confidence 0.95 >= threshold 0.7. Returning heuristic result.
```

---

## Test Scenarios

### Scenario 1: Happy Path (High Confidence)
```
Messages that should be classified with HIGH confidence (≥85%)
Expected: All heuristic, fast classification

• "What are the termination rights?" → Ask (85%)
• "Summarize this contract" → Summary (90%)
• "Draft a memo" → Draft (95%)
```

### Scenario 2: Edge Cases (Lower Confidence)
```
Messages that might need LLM refinement (confidence 50-70%)
Expected: Some heuristic, some LLM fallback

• "Tell me more" → Ask (60% heuristic → LLM refines)
• "The key points?" → Summary/Ask (ambiguous)
• "Create something legal" → Draft (70% heuristic)
```

### Scenario 3: Fallback to LLM
```
When heuristic confidence < 70%, use Claude Haiku
Expected: Accurate classification via API

• Ambiguous multi-intent queries
• Unusual phrasings
• Context-dependent requests
```

---

## What to Verify

### ✅ Heuristic Path Tests
- [ ] Draft keywords detected (draft, write, create, generate, memo, brief)
- [ ] Summary keywords detected (summarize, overview, extract, key points)
- [ ] Question mark triggers Ask intent
- [ ] Confidence scores are correct (95% draft, 90% summary, 85% ask)
- [ ] Keyword priority is correct (Draft > Summary > Ask)
- [ ] Case-insensitive matching works
- [ ] Edge cases return appropriate intent

### ✅ LLM Path Tests (Requires API key)
- [ ] Inconclusive messages fall back to LLM
- [ ] Claude Haiku returns correct intent
- [ ] Confidence score is ~75% for LLM results
- [ ] Response time is reasonable (~200-500ms)

### ✅ Error Handling
- [ ] Missing API key handled gracefully
- [ ] Invalid environment variables handled
- [ ] Malformed input doesn't crash
- [ ] Network errors logged properly

---

## Performance Metrics

### Expected Results

| Metric | Target | Actual |
|--------|--------|--------|
| Heuristic latency | <5ms | ? |
| LLM latency | 200-500ms | ? |
| Heuristic accuracy | >95% | ? |
| LLM fallback rate | 20-30% | ? |
| API cost per call | ~$0.0001 | ? |

---

## Troubleshooting

### Issue: "ANTHROPIC_API_KEY not set"
**Solution:**
```bash
# Option 1: Set in .env
echo "ANTHROPIC_API_KEY=sk-ant-v0-your-key" >> .env

# Option 2: Set in environment
$env:ANTHROPIC_API_KEY="sk-ant-v0-your-key"
```

### Issue: "ModuleNotFoundError: No module named 'langchain'"
**Solution:**
```bash
pip install langchain langchain-anthropic python-dotenv
```

### Issue: Tests hang or timeout
**Solution:**
```bash
# Check API key validity
# Check internet connection
# Run with debug mode to see what's happening
python test_classifier_cli.py --debug
```

### Issue: Wrong classifications
**Solution:**
1. Run batch tests to identify pattern
2. Check if it's a heuristic or LLM issue
3. Adjust keywords in `intent_classifier.py` if needed
4. Adjust confidence threshold if needed

---

## Success Criteria

✅ **All tests pass** — 40+ unit tests, 20 batch tests  
✅ **Heuristic path works** — Fast, accurate, no API calls needed  
✅ **LLM fallback works** — Handles edge cases correctly  
✅ **No errors** — Graceful error handling  
✅ **Performance acceptable** — Heuristic <5ms, LLM <500ms  

---

## Next Steps After Testing

Once all tests pass:

1. **Confirm results** — Tell me the test output
2. **Adjust if needed** — Add keywords, change thresholds
3. **Integrate with backend** — Wire into API router
4. **Build full orchestrator** — Implement answer, summarize, draft methods

---

## Quick Command Reference

```bash
# Interactive testing (try different messages)
python test_classifier_cli.py

# Batch testing (see all 20 test cases)
python test_classifier_cli.py --batch

# Single message
python test_classifier_cli.py "Your message here"

# Unit tests with pytest
pytest test_intent_classifier.py -v

# Debug mode
python test_classifier_cli.py --debug

# Debug batch mode
python test_classifier_cli.py --debug --batch
```

---

## Questions?

See `intent-classifier-prompt.md` for the classification strategy.  
See `README.md` for detailed documentation.
