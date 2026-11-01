## Frontend Testing Guide - LegalLens Workflows

**Complete instructions for testing Ask, Summary, and Draft workflows from the frontend.**

---

## 🎯 Prerequisites

### Backend Setup
```bash
# Terminal 1: Start backend API
cd backend
pip install -r requirements.txt
python app.py

# Expected output:
# * Running on http://127.0.0.1:5000
# * Workflows loaded successfully
```

### Frontend Setup
```bash
# Terminal 2: Start frontend dev server
cd frontend
npm install
npm start

# Expected output:
# Compiled successfully!
# Open http://localhost:3000 to view it in the browser
```

### Test Documents
Ensure you have test documents loaded:
```bash
# Terminal 3: Ingest test documents
cd backend
python -c "
from app.ingestion.document_ingestion import ingest_documents
ingest_documents('test_documents/')
print('✅ Test documents ingested')
"
```

---

## ✅ Test Checklist

- [ ] Backend API running on port 5000
- [ ] Frontend dev server running on port 3000
- [ ] Test documents ingested into vector store
- [ ] ANTHROPIC_API_KEY set in backend .env
- [ ] Browser console clear (no errors)
- [ ] Network tab shows successful API calls

---

## 🧪 Testing Workflow 1: ASK (Q&A)

### Test 1.1: Basic Question

**Step 1: Open Frontend**
```
Go to http://localhost:3000
Select "Ask" tab
```

**Step 2: Enter Question**
```
Question: "What are the termination rights?"
Chat History: Leave empty
Click "Ask"
```

**Expected Result:**
```
⏳ Processing steps shown:
  1. Rewriting question...
  2. Searching documents...
  3. Ranking results...
  4. Generating answer...

✅ Answer appears with:
  - Generated answer text
  - [1][2][3]... citations
  - Source documents listed below
  - Response time (2-4 seconds)
```

**What to Check:**
- [ ] All 4 processing steps complete
- [ ] Answer is relevant to question
- [ ] Citations [1][2] appear in answer
- [ ] Sources match cited chunks
- [ ] No errors in browser console

---

### Test 1.2: Question with Chat History

**Step 1: First Question**
```
Question: "What type of agreement is this?"
Click "Ask"
```

**Step 2: Follow-up Question with History**
```
Question: "What about termination?"
Chat History: Should auto-populate with previous Q&A
Click "Ask"
```

**Expected Result:**
```
✅ Rewritten question shows:
  - Original: "What about termination?"
  - Rewritten: "What are the termination terms in this [type] agreement?"
  - Confidence score: 0.85+
  - Reason: "Relevant context from chat history"

✅ Answer uses context from first question
✅ More precise answer than without history
```

**What to Check:**
- [ ] Question is rewritten (shown in UI)
- [ ] Rewrite uses previous context
- [ ] Answer is more specific than it would be alone
- [ ] Confidence score displays
- [ ] History not lost after answer

---

### Test 1.3: Empty Question

**Step 1: Send Empty Question**
```
Question: "" (leave blank)
Click "Ask"
```

**Expected Result:**
```
⚠️ Error message: "Question cannot be empty"
❌ No API call made
```

**What to Check:**
- [ ] Error message appears
- [ ] No loading indicators shown
- [ ] Network tab shows no request

---

### Test 1.4: Very Long Question

**Step 1: Long Question**
```
Question: "Considering the legal framework established in the agreement, 
          what are the specific conditions, procedures, and requirements 
          that must be met by either party to exercise their right to 
          terminate the contract, and what are the financial, legal, or 
          operational consequences of exercising such termination rights?"
Click "Ask"
```

**Expected Result:**
```
✅ Long question is rewritten to shorter form
✅ Answer quality is good
✅ Processing time similar to short question
```

**What to Check:**
- [ ] No truncation of question
- [ ] Rewrite shortens/clarifies
- [ ] Answer is comprehensive
- [ ] Performance is acceptable

---

### Test 1.5: No Relevant Results

**Step 1: Question Outside Document Scope**
```
Question: "What is the weather today?"
Click "Ask"
```

**Expected Result:**
```
✅ Answer: "This is not addressed in the provided documents."
✅ Citations: None or minimal
✅ Sources: Empty or N/A
```

**What to Check:**
- [ ] Graceful handling of out-of-scope questions
- [ ] Honest response about document limitations
- [ ] No hallucination or made-up answers

---

## 🎯 Testing Workflow 2: SUMMARY (Summarization)

### Test 2.1: Summarize Contract

**Step 1: Open Summary Tab**
```
Go to http://localhost:3000
Select "Summary" tab
```

**Step 2: Select Document and Summarize**
```
Document: Select a contract document
Click "Summarize"
```

**Expected Result:**
```
✅ Processing steps shown:
  1. Analyzing document type...
  2. Detecting complexity...
  3. Selecting summary template...
  4. Generating summary...

✅ Structured Summary appears with fields:
  - Document Type: "Contract"
  - Parties: Names extracted
  - Effective Date: Date extracted
  - Key Terms: Top terms listed
  - Obligations: Summarized obligations
  - Termination: Termination clause summary
  - Renewal: Renewal terms summary

✅ Metadata shown:
  - Complexity: "simple" | "moderate" | "complex"
  - Chunks Used: "8 of 50 retrieved"
  - Response Time: 3-6 seconds
```

**What to Check:**
- [ ] All processing steps complete
- [ ] All expected fields populated
- [ ] Document type correctly identified
- [ ] Summary is accurate and concise
- [ ] No missing information
- [ ] Formatting is clean and readable

---

### Test 2.2: Summarize Court Opinion

**Step 1: Select Opinion Document**
```
Document: Select a court opinion
Click "Summarize"
```

**Expected Result:**
```
✅ Different template applied with fields:
  - Court: Court name
  - Parties: Case parties
  - Issue: Legal issue
  - Facts: Relevant facts
  - Holding: Court's holding
  - Reasoning: Legal reasoning
  - Disposition: Final disposition

✅ Template matches document type (opinion)
```

**What to Check:**
- [ ] Correct template for opinion
- [ ] Legal reasoning clearly explained
- [ ] Holding is highlighted
- [ ] Citation information preserved

---

### Test 2.3: Complexity-Based Model Selection

**Step 1: Simple Document (< 50 pages)**
```
Document: Short agreement (5-10 pages)
Click "Summarize"
Check: Response time
```

**Step 2: Complex Document (> 50 pages)**
```
Document: Long contract (100+ pages)
Click "Summarize"
Check: Response time
```

**Expected Result:**
```
✅ Simple doc (Sonnet model):
  - Faster response (~3-4 seconds)
  - Quality: Good for straightforward docs

✅ Complex doc (Opus model):
  - Slower response (~5-8 seconds)
  - Quality: Higher detail for complex docs

✅ Metadata shows which model used
```

**What to Check:**
- [ ] Model selection visible in metadata
- [ ] Response times match expectations
- [ ] Quality difference is perceivable
- [ ] Complexity detection is accurate

---

### Test 2.4: Filtered Summary (Single Document)

**Step 1: With Document Filter**
```
Document: Select specific contract
Query: "Analyze only termination terms"
Click "Summarize"
```

**Expected Result:**
```
✅ Summary focuses on specified area
✅ Other sections not included
✅ More targeted output
```

**What to Check:**
- [ ] Summary is focused
- [ ] Other sections omitted
- [ ] Query respected in output

---

## 📝 Testing Workflow 3: DRAFT (Document Generation)

### Test 3.1: Draft a Memo

**Step 1: Open Draft Tab**
```
Go to http://localhost:3000
Select "Draft" tab
```

**Step 2: Request Memo**
```
Request: "Draft a memo analyzing the termination clause"
Click "Draft"
```

**Expected Result:**
```
✅ Processing steps shown:
  1. Extracting intent...
  2. Searching relevant documents...
  3. Ranking most relevant chunks...
  4. Organizing sources...
  5. Generating memo...

✅ Structured Memo appears with fields:
  - TO: [Audience]
  - FROM: [Author]
  - DATE: [Current date]
  - RE: [Subject - Termination Clause Analysis]
  
  1. QUESTION PRESENTED
  2. SHORT ANSWER
  3. FACTS
  4. ANALYSIS
     A. Termination Rights
     B. Notice Requirements
     C. Penalties
  5. CONCLUSION

✅ Metadata shown:
  - Draft Type: "memo"
  - Question Presented: "What are..."
  - Audience: "legal professional"
  - Tone: "formal"
  - Sources Used: "8 citations"
  - Warning: "UNREVIEWED AI DRAFT - ATTORNEY REVIEW REQUIRED"
```

**What to Check:**
- [ ] All processing steps complete
- [ ] Memo follows standard format
- [ ] Analysis section comprehensive
- [ ] Citations present and relevant
- [ ] Warning banner visible
- [ ] Professional tone maintained
- [ ] No hallucinations

---

### Test 3.2: Draft a Brief

**Step 1: Request Brief**
```
Request: "Draft a brief for motion to dismiss on termination grounds"
Click "Draft"
```

**Expected Result:**
```
✅ Brief template applied with fields:
  - Case: [Citation]
  - Court: [Court name]
  - POSTURE: [Procedural status]
  - FACTS: [Case facts]
  - ISSUE: [Legal issue]
  - HOLDING: [Court holding]
  - REASONING: [Legal reasoning]
  - DISPOSITION: [Outcome]

✅ Different format from memo
✅ More case-focused structure
✅ Legal citations included
```

**What to Check:**
- [ ] Correct template for brief
- [ ] Proper legal structure
- [ ] Citations accurate
- [ ] Arguments well-organized

---

### Test 3.3: Intent Extraction Verification

**Step 1: Ambiguous Request**
```
Request: "Write something about provisions"
Click "Draft"
```

**Expected Result:**
```
✅ Intent extracted:
  - Document Type: "memo" (inferred)
  - Focus Area: Detected from context
  - Question Presented: Generated from request
  - Audience: "legal professional" (default)
  - Tone: "formal" (default)

✅ Reasonable defaults applied
✅ User can edit if needed
```

**What to Check:**
- [ ] Reasonable interpretation
- [ ] Defaults are sensible
- [ ] Can override if needed

---

### Test 3.4: Citation Accuracy

**Step 1: Check Citations**
```
In generated draft, hover over [1], [2], [3]...
```

**Expected Result:**
```
✅ Citation popup shows:
  - Source document name
  - Quoted text (first 100 chars)
  - Page/chunk reference
  - Relevance score

✅ Citations link to actual sources
✅ No broken links
✅ All [n] have corresponding sources
```

**What to Check:**
- [ ] Every citation is valid
- [ ] Sources are accurate
- [ ] Text matches original document
- [ ] Links work

---

## 🔄 Workflow Interaction Tests

### Test 4.1: Ask → Summary → Draft Chain

**Step 1: Ask Question**
```
Ask: "What are the termination terms?"
Save answer
```

**Step 2: Summarize Document**
```
Summarize: Same document
Compare with Ask answer
```

**Step 3: Draft Memo**
```
Draft: "Memo analyzing termination"
Compare with both previous outputs
```

**Expected Result:**
```
✅ All three consistent
✅ Summary more structured than Ask
✅ Memo more detailed than Summary
✅ Different purposes, same facts
```

**What to Check:**
- [ ] No contradictions between workflows
- [ ] Each adds value in different way
- [ ] Sources consistent across all three

---

### Test 4.2: Chat History Across Workflows

**Step 1: Ask with History**
```
Q1: "What type of agreement?"
Q2: "What about termination?"
Q3: "How does it end?" (uses history)
```

**Step 2: Start New Ask (Fresh)**
```
Q4: "New question without history"
Check: Answer is less specific
```

**Expected Result:**
```
✅ History used in Q3 improves specificity
✅ Q4 without history is more generic
✅ Clear demonstration of history value
```

**What to Check:**
- [ ] History improves answer quality
- [ ] Can clear history if needed
- [ ] Fresh start works correctly

---

## 🐛 Error Testing

### Test 5.1: API Timeout

**Step 1: Trigger Long-Running Question**
```
Question: Very complex question
Wait > 30 seconds
```

**Expected Result:**
```
⚠️ Timeout error displayed
💡 Suggestion: "Try a simpler question or fewer documents"
🔄 Ability to retry or cancel
```

**What to Check:**
- [ ] Error message is clear
- [ ] Suggestions are helpful
- [ ] Can retry or go back

---

### Test 5.2: Missing Document

**Step 1: No Documents Ingested**
```
Try to Ask/Summarize/Draft
Expected: Error or empty results
```

**Expected Result:**
```
⚠️ Error: "No documents available"
💡 Suggestion: "Ingest documents first"
🔗 Link to ingestion interface
```

**What to Check:**
- [ ] Clear error message
- [ ] Guidance on next steps
- [ ] No app crash

---

### Test 5.3: API Connection Error

**Step 1: Stop Backend Server**
```
Terminal 1: Stop Flask app (Ctrl+C)
Frontend: Click "Ask"
```

**Expected Result:**
```
⚠️ Error: "Cannot connect to backend"
💡 Suggestion: "Ensure backend is running on port 5000"
🔄 Auto-retry or manual refresh
```

**What to Check:**
- [ ] Graceful error handling
- [ ] Clear error message
- [ ] Helpful troubleshooting steps

---

### Test 5.4: Invalid API Key

**Step 1: Use Wrong API Key**
```
Backend .env: ANTHROPIC_API_KEY=sk-wrong
Try to Ask
```

**Expected Result:**
```
⚠️ Error: "Invalid API key"
💡 Suggestion: "Check your Anthropic API key"
📖 Link to documentation
```

**What to Check:**
- [ ] Clear error about auth
- [ ] User can fix easily
- [ ] No sensitive info exposed

---

## 📊 Performance Testing

### Test 6.1: Response Times

**Step 1: Measure Ask Workflow**
```
Question: "What are the key terms?"
Document: Single 20-page contract
Note: Total time
```

**Expected Result:**
```
⏱️ Typical times:
  - Rewrite: ~300ms
  - Retrieve: ~150ms
  - Rerank: ~500ms
  - Generate: ~1-3s
  - Total: 2-4 seconds

✅ Within acceptable range
```

**What to Check:**
- [ ] Total time < 10 seconds
- [ ] Each step visible in UI
- [ ] Progress indicators helpful

---

### Test 6.2: Multiple Documents Performance

**Step 1: With 1 Document**
```
Time Ask with 1 document
```

**Step 2: With 10 Documents**
```
Time Ask with 10 documents
```

**Expected Result:**
```
✅ Performance scales reasonably
✅ 10 docs ~ 5-7 seconds (not 40s)
✅ Retrieval+reranking optimized
```

**What to Check:**
- [ ] Performance acceptable
- [ ] No app freeze
- [ ] Progress shown continuously

---

### Test 6.3: UI Responsiveness

**During Processing:**
```
Click buttons while "Generating..."
Try to change question
Scroll page
```

**Expected Result:**
```
✅ UI remains responsive
✅ Can cancel if needed
✅ No "Not Responding" errors
✅ Smooth progress updates
```

**What to Check:**
- [ ] No UI freezing
- [ ] Cancel button works
- [ ] Progress updates smooth

---

## 📸 Visual Testing

### Test 7.1: Mobile Responsiveness

**Step 1: Desktop (1920x1080)**
```
Test Ask/Summary/Draft
Check layout
```

**Step 2: Tablet (768x1024)**
```
Resize browser
Test workflows
```

**Step 3: Mobile (375x667)**
```
Mobile view
Test touch interactions
```

**Expected Result:**
```
✅ All workflows work on all sizes
✅ Text readable
✅ Buttons clickable
✅ No horizontal scroll on mobile
✅ Tables/lists stack on mobile
```

**What to Check:**
- [ ] Layout adapts well
- [ ] Touch targets large enough
- [ ] No content cut off
- [ ] Mobile-first approach

---

### Test 7.2: Dark Mode (if supported)

**Step 1: Enable Dark Mode**
```
Settings: Toggle dark mode
```

**Expected Result:**
```
✅ All text readable in dark mode
✅ Contrast is sufficient
✅ No images look weird
✅ Citations stand out
```

**What to Check:**
- [ ] Color contrast WCAG AA
- [ ] No eye strain
- [ ] Professional appearance

---

## ♿ Accessibility Testing

### Test 8.1: Keyboard Navigation

**Step 1: Tab Through Interface**
```
Use Tab key to navigate
Don't use mouse
Complete full workflow
```

**Expected Result:**
```
✅ Focus visible on all buttons
✅ Tab order logical
✅ Can reach all functionality
✅ Enter key triggers actions
```

**What to Check:**
- [ ] Tab stops on all interactive elements
- [ ] Focus indicator visible
- [ ] Keyboard shortcuts work

---

### Test 8.2: Screen Reader

**Step 1: Enable Screen Reader**
```
Windows: Narrator (Windows+Enter)
Mac: VoiceOver (Cmd+F5)
Linux: ORCA
```

**Step 2: Navigate Ask Workflow**
```
Let screen reader read page
Listen to button labels
Verify semantic HTML
```

**Expected Result:**
```
✅ All buttons labeled clearly
✅ Form fields have labels
✅ Errors announced
✅ Status messages readable
✅ No important info is visual-only
```

**What to Check:**
- [ ] Form labels present
- [ ] Buttons have accessible names
- [ ] ARIA labels where needed
- [ ] Semantic HTML used

---

## 📋 Comprehensive Test Scenario

**Complete workflow from start to finish:**

```
1. ✅ Start clean (refresh page)
2. ✅ Verify no errors in console
3. ✅ Ask: "What are the parties?"
4. ✅ Review answer and citations
5. ✅ Ask: "What is the term?" (with history)
6. ✅ Verify question rewritten
7. ✅ Summarize same document
8. ✅ Draft memo about key terms
9. ✅ Check all citations valid
10. ✅ Test error handling (bad input)
11. ✅ Test mobile responsiveness
12. ✅ Verify keyboard navigation
13. ✅ Check dark mode
14. ✅ Test accessibility
15. ✅ Review all network calls successful
```

**If all 15 pass: ✅ PRODUCTION READY** 🎉

---

## 🐛 Common Issues & Fixes

### Issue: "Cannot connect to backend"

**Cause:** Backend not running or wrong port  
**Fix:**
```bash
# Terminal 1
cd backend
python app.py
# Should show: Running on http://127.0.0.1:5000
```

### Issue: "No documents available"

**Cause:** No documents ingested  
**Fix:**
```bash
# Terminal 3
python -c "
from app.ingestion.document_ingestion import ingest_documents
ingest_documents('test_documents/')
"
```

### Issue: API key error in answers

**Cause:** ANTHROPIC_API_KEY not set  
**Fix:**
```bash
# Backend .env file
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
```

### Issue: Slow response times

**Cause:** 
- Vector store not optimized
- Too many documents to search
- Reranker model not loaded

**Fix:**
```bash
# Use fewer documents for testing
# Or run reranker on GPU if available
```

### Issue: Citations don't match content

**Cause:** Retrieval/ranking issue  
**Fix:**
```bash
# Check that documents were ingested correctly
# Verify chunks are reasonable size
# Check embedding model loaded
```

---

## ✅ Final Checklist Before Going Live

- [ ] All 3 workflows (Ask, Summary, Draft) work
- [ ] Citations are accurate
- [ ] Response times acceptable (< 10s)
- [ ] Error messages clear and helpful
- [ ] Mobile responsive on all sizes
- [ ] Keyboard navigation works
- [ ] Screen reader compatible
- [ ] No console errors
- [ ] No network errors
- [ ] Performance acceptable with many docs
- [ ] Chat history works correctly
- [ ] Document filtering works
- [ ] Dark mode (if present) looks good
- [ ] All buttons have tooltips
- [ ] Loading states show progress
- [ ] Cancel functionality works
- [ ] Can recover from errors
- [ ] Privacy/security considerations met
- [ ] Documentation complete
- [ ] Test results documented

---

## 📊 Test Report Template

Use this to document your testing:

```markdown
# Frontend Test Report

**Date:** 2026-10-23
**Tester:** [Name]
**Environment:** 
- Frontend: localhost:3000
- Backend: localhost:5000
- Browser: Chrome 120

## Test Results

### Ask Workflow
- [ ] Basic question: ✅ PASS
- [ ] With history: ✅ PASS
- [ ] Long question: ✅ PASS
- [ ] No results: ✅ PASS

### Summary Workflow
- [ ] Contract summary: ✅ PASS
- [ ] Opinion summary: ✅ PASS
- [ ] Complexity detection: ✅ PASS

### Draft Workflow
- [ ] Draft memo: ✅ PASS
- [ ] Draft brief: ✅ PASS
- [ ] Citations: ✅ PASS

### Error Handling
- [ ] Invalid input: ✅ PASS
- [ ] Connection error: ✅ PASS
- [ ] Timeout: ✅ PASS

### Performance
- [ ] Ask < 5s: ✅ PASS
- [ ] Summary < 8s: ✅ PASS
- [ ] Draft < 10s: ✅ PASS

### Accessibility
- [ ] Keyboard nav: ✅ PASS
- [ ] Screen reader: ✅ PASS
- [ ] Mobile responsive: ✅ PASS

## Issues Found
[List any bugs or issues discovered]

## Overall Result
✅ READY FOR PRODUCTION
```

---

**Happy testing! 🚀**
