## Quick Test Reference Card

**Print this and keep it handy while testing!**

---

## 🚀 Quick Start (5 minutes)

```bash
# Terminal 1: Backend
cd backend
pip install -r requirements.txt
python app.py

# Terminal 2: Frontend
cd frontend
npm install
npm start

# Terminal 3: Ingest Documents
cd backend
python -c "from app.ingestion.document_ingestion import ingest_documents; \
           ingest_documents('test_documents/')"

# Result: All running ✅
# Backend: http://localhost:5000
# Frontend: http://localhost:3000
```

---

## 📋 Test Scenarios (Copy-Paste Ready)

### Ask Workflow Tests

**Test 1: Basic Question**
```
Question: "What are the termination rights?"
Chat History: Empty
Expected: Answer with [1][2]... citations in 2-4 seconds
```

**Test 2: With History**
```
Q1: "What type of agreement?"
Q2: "What about termination?" (with history)
Expected: Q2 shows rewritten version with context
```

**Test 3: Long Question**
```
Question: "Considering the legal framework established in the agreement, 
           what are the specific conditions, procedures, and requirements 
           that must be met by either party to exercise their right to 
           terminate the contract?"
Expected: Question shortened and rewritten, answer still good
```

**Test 4: No Relevant Results**
```
Question: "What is the weather today?"
Expected: "This is not addressed in the provided documents."
```

### Summary Workflow Tests

**Test 5: Contract Summary**
```
Document: Select any contract
Expected: Summary with parties, dates, key terms, obligations, termination, renewal
```

**Test 6: Opinion Summary**
```
Document: Select any court opinion
Expected: Different template with court, parties, issue, facts, holding, reasoning
```

**Test 7: Complexity Detection**
```
Simple doc (< 50 pages): Response time ~3-4s (Sonnet model)
Complex doc (> 50 pages): Response time ~5-8s (Opus model)
Expected: Faster for simple, more detailed for complex
```

### Draft Workflow Tests

**Test 8: Draft Memo**
```
Request: "Draft a memo analyzing the termination clause"
Expected: Memo format with TO/FROM/DATE/RE, sections 1-5, [1][2]... citations
```

**Test 9: Draft Brief**
```
Request: "Draft a brief for motion to dismiss on termination grounds"
Expected: Brief format with case, posture, facts, issue, holding, reasoning, disposition
```

**Test 10: Intent Extraction**
```
Request: "Write something about provisions"
Expected: Reasonable defaults for missing parameters
```

---

## 🔍 What to Check

### After Each Test

- [ ] No errors in browser console (F12)
- [ ] No 404/500 errors in Network tab
- [ ] Answer/summary/draft content looks good
- [ ] Citations [1][2]... present and valid
- [ ] Response time shown
- [ ] No UI freezing during processing
- [ ] Can submit next request

### Response Time Checklist

```
Ask:     ⏱️ 2-4 seconds ✅
Summary: ⏱️ 4-6 seconds ✅
Draft:   ⏱️ 5-8 seconds ✅
> 10s:   ❌ Investigate slow backend
```

### Error Checklist

```
Backend not running?      → python app.py
No documents?             → Ingest test_documents/
Wrong API key?            → Check backend .env
CORS error?               → Check Flask CORS config
Network error?            → Check http://localhost:5000
```

---

## 🐛 Common Quick Fixes

| Issue | Command |
|-------|---------|
| Backend crashes | `python app.py` |
| No docs found | `python -c "from app.ingestion.document_ingestion import ingest_documents; ingest_documents('test_documents/')"` |
| API key error | Check backend `.env` has `ANTHROPIC_API_KEY=sk-ant-...` |
| CORS error | Ensure backend CORS config includes `http://localhost:3000` |
| Slow response | Check vector store isn't corrupted, try fewer documents |
| Can't connect to backend | Ensure port 5000 is free, check firewall |

---

## 📱 Device Testing Checklist

```
📱 Mobile (375x667):
   [ ] Can type in input field
   [ ] Buttons are clickable
   [ ] No horizontal scroll
   [ ] Text is readable
   [ ] Results stack vertically

💻 Tablet (768x1024):
   [ ] Layout adapts properly
   [ ] All content visible
   [ ] Touch targets large enough
   [ ] Responsive grid works

🖥️ Desktop (1920x1080):
   [ ] Full layout visible
   [ ] Nothing cramped
   [ ] Nice spacing
```

---

## ♿ Accessibility Quick Test

```
🎹 Keyboard Only:
   [ ] Tab through all buttons
   [ ] Can submit forms with Enter
   [ ] Focus visible everywhere
   [ ] Can read all text

🔊 Screen Reader:
   [ ] All buttons have labels
   [ ] Form fields labeled
   [ ] Errors announced
   [ ] Links make sense
```

---

## ✅ Final Checklist (Before "Ready for Production")

```
FUNCTIONALITY
  [ ] Ask works with question + history
  [ ] Summary works with document selection
  [ ] Draft works with natural language request
  [ ] All citations [1][2]... valid

PERFORMANCE
  [ ] Ask < 5 seconds
  [ ] Summary < 8 seconds
  [ ] Draft < 10 seconds
  [ ] UI responsive during loading

ERRORS
  [ ] Empty input shows error
  [ ] Backend down shows friendly message
  [ ] API key error is clear
  [ ] Timeout message helpful

ACCESSIBILITY
  [ ] Keyboard navigation works
  [ ] Screen reader compatible
  [ ] Mobile responsive
  [ ] Text contrast sufficient

VISUAL
  [ ] Dark mode looks good (if present)
  [ ] Fonts readable
  [ ] Colors not just informative
  [ ] Professional appearance

POLISH
  [ ] Loading spinners smooth
  [ ] Buttons have hover states
  [ ] No console errors
  [ ] Chat history preserved

RESULT
  [ ] ✅ READY FOR PRODUCTION
```

---

## 📊 Test Results Sheet

Copy and fill out:

```
Date: ___________
Tester: ___________

Ask Workflow
  Basic Q&A:        [ ] Pass  [ ] Fail
  With History:     [ ] Pass  [ ] Fail
  Long Question:    [ ] Pass  [ ] Fail
  No Results:       [ ] Pass  [ ] Fail

Summary Workflow
  Contract:         [ ] Pass  [ ] Fail
  Opinion:          [ ] Pass  [ ] Fail
  Complexity:       [ ] Pass  [ ] Fail

Draft Workflow
  Memo:             [ ] Pass  [ ] Fail
  Brief:            [ ] Pass  [ ] Fail
  Intent:           [ ] Pass  [ ] Fail

Performance
  Ask < 5s:         [ ] Pass  [ ] Fail
  Summary < 8s:     [ ] Pass  [ ] Fail
  Draft < 10s:      [ ] Pass  [ ] Fail

Accessibility
  Keyboard Nav:     [ ] Pass  [ ] Fail
  Screen Reader:    [ ] Pass  [ ] Fail
  Mobile:           [ ] Pass  [ ] Fail

Overall: [ ] Ready  [ ] Needs Work
```

---

## 🧪 API Test Commands (Copy-Paste)

### Ask
```bash
curl -X POST http://localhost:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What are termination rights?","chat_history":[]}'
```

### Summary
```bash
curl -X POST http://localhost:5000/api/summarize \
  -H "Content-Type: application/json" \
  -d '{"document_id":"doc_123","query":null}'
```

### Draft
```bash
curl -X POST http://localhost:5000/api/draft \
  -H "Content-Type: application/json" \
  -d '{"request":"Draft a memo about termination"}'
```

---

## 🎯 Expected API Responses

### Ask: Success
```json
{
  "success": true,
  "data": {
    "original_question": "What are the termination rights?",
    "rewritten_question": "What are the termination rights...",
    "generated_answer": "According to [1]...",
    "citations": [...]
  }
}
```

### Any Workflow: Error
```json
{
  "success": false,
  "error": "No documents available",
  "code": "NO_DOCUMENTS"
}
```

---

## 🚦 Traffic Light Status

### 🟢 GREEN - Ready to Test
```
✅ Backend running
✅ Frontend running  
✅ Documents ingested
✅ No console errors
```

### 🟡 YELLOW - Needs Attention
```
⚠️ Slow responses (> 10s)
⚠️ Occasional errors
⚠️ Console warnings
⚠️ API timeout once
```

### 🔴 RED - Stop and Fix
```
❌ Backend crashing
❌ API key invalid
❌ No documents found
❌ Consistent timeouts
❌ CORS blocked
```

---

## 💡 Pro Tips

1. **Keep terminal windows visible** — See backend output while testing
2. **Use Browser DevTools** (F12) → Network tab to see API calls
3. **Check console** (F12 → Console) for JavaScript errors
4. **Try simple questions first** — "What is X?" before complex questions
5. **Test with different document types** — Contracts, opinions, pleadings
6. **Refresh after changing documents** — Clear old cache
7. **Keep notes on failures** — Makes debugging easier
8. **Test on multiple devices** — Phone, tablet, desktop
9. **Check at different times** — Catch timing-related issues
10. **Read error messages carefully** — They're usually helpful

---

## 📞 Quick Troubleshooting

**"Cannot connect to backend"**
→ Check backend running: `python app.py`

**"No documents available"**
→ Ingest documents: `python -c "from app.ingestion.document_ingestion import ingest_documents; ingest_documents('test_documents/')"`

**"Invalid API key"**
→ Check `.env`: `ANTHROPIC_API_KEY=sk-ant-xxxxx`

**"Very slow responses"**
→ Reduce document count or check vector store

**"CORS error in console"**
→ Check backend CORS config for `localhost:3000`

---

## 📝 Typical Test Session (30 minutes)

```
⏱️ 0-5 min:   Setup (backend, frontend, docs)
⏱️ 5-15 min:  Ask workflow tests (5 scenarios)
⏱️ 15-20 min: Summary workflow tests (3 scenarios)
⏱️ 20-27 min: Draft workflow tests (3 scenarios)
⏱️ 27-29 min: Document test results
⏱️ 29-30 min: Final checklist

✅ If all green → Ready!
❌ If any red → Fix and retest
```

---

**Keep this handy!** Print it out and check off as you test. 🚀
