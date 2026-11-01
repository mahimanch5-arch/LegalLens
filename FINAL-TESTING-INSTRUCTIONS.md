## Final Frontend Testing Instructions

**Complete step-by-step guide to test LegalLens app from the browser.**

---

## ✅ **Pre-Flight Checklist (Do This First)**

### **1. Backend Running?**
```bash
# Terminal 1: Already running?
python run.py --port 5000

# Expected output:
# [*] Starting Legal Lens Backend
#     Host: 127.0.0.1
#     Port: 5000
#     Reload: False
#     Workers: 1
#
# [+] API will be available at http://127.0.0.1:5000/api
# [+] Interactive docs at http://127.0.0.1:5000/api/docs
```

✅ Check: Backend terminal shows no errors

### **2. Frontend Running?**
```bash
# Terminal 2: Already running?
cd frontend
npm start

# Expected output:
# Compiled successfully!
# You can now view frontend in the browser.
# Local: http://localhost:3000
```

✅ Check: Frontend terminal shows "Compiled successfully!"

### **3. Documents Ingested?**
```bash
# Terminal 3: Check if documents exist
cd backend/data

# Should have folder: chroma_db
# If empty, run ingestion:
# python -c "from app.ingestion.document_ingestion import ingest_documents; ingest_documents('test_documents/')"
```

✅ Check: chroma_db folder exists in backend/data

### **4. API Working?**
```bash
# In browser or new terminal:
curl -X POST http://localhost:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello?","chat_history":[]}'

# Should return: {"success": true, "data": {...}}
```

✅ Check: Get success response with data

---

## 🚀 **Start Testing (Open Browser)**

Open this URL in your browser:
```
http://localhost:3000
```

You should see:
- ✅ LegalLens logo/title
- ✅ Three tabs: Ask | Summary | Draft
- ✅ No console errors (F12 to check)

---

## 📝 **Test 1: Ask Workflow (Question & Answer)**

### **Step 1: Click "Ask" Tab**
```
You should see:
- Input field for "Question"
- Chat history area (empty initially)
- "Ask" button
```

### **Step 2: Enter a Question**
```
Question: "What are the termination rights?"
Click "Ask"
```

### **Expected Result (Wait 2-5 seconds):**
```
✅ See processing steps:
   1. Rewriting question...
   2. Searching documents...
   3. Ranking results...
   4. Generating answer...

✅ Answer appears with:
   - Full answer text
   - [1][2][3]... citation numbers in answer
   - Sources listed below with:
     * Source document name
     * Quoted text
     * Relevance score

✅ Metadata shows:
   - Response time (should be 2-5 seconds)
   - Number of chunks retrieved

✅ Chat history updated with:
   - Your question
   - Assistant's answer
```

### **What to Check:**
- [ ] Question input worked
- [ ] Answer is relevant to question
- [ ] Citations [1][2]... appear in answer
- [ ] Each citation has matching source below
- [ ] Sources are from actual documents
- [ ] No error messages shown
- [ ] No console errors (F12)

---

## 📝 **Test 2: Ask with Chat History**

### **Step 1: Ask First Question**
```
Question: "What type of agreement is this?"
Click "Ask"
```

### **Step 2: Review Answer**
```
Should show answer about document type
Chat history now shows this conversation
```

### **Step 3: Ask Follow-Up Question**
```
Question: "What about termination?"
Click "Ask"
```

### **Expected Result:**
```
✅ Question is rewritten to use context from first answer
   Example: 
   Original: "What about termination?"
   Rewritten: "What are the termination rights in this [type] agreement?"

✅ Answer is more specific than if asked alone

✅ Chat history shows both conversations

✅ All the same checks as Test 1 apply
```

### **What to Check:**
- [ ] Question rewriting visible
- [ ] Context from previous answer used
- [ ] Answer is more detailed/specific
- [ ] Chat history preserved

---

## 📝 **Test 3: Summary Workflow (Document Summarization)**

### **Step 1: Click "Summary" Tab**
```
You should see:
- Document selector dropdown
- Query field (optional)
- "Summarize" button
```

### **Step 2: Select a Document**
```
Click dropdown
Select any document (e.g., "contract_001.pdf")
Leave Query empty
Click "Summarize"
```

### **Expected Result (Wait 4-8 seconds):**
```
✅ Processing steps shown:
   1. Analyzing document type...
   2. Detecting complexity...
   3. Selecting summary template...
   4. Generating summary...

✅ Structured summary appears with fields:
   - Document Type: "Contract" or "Opinion" or "Pleading"
   - Parties: Names of parties extracted
   - Effective Date: Date extracted
   - Key Terms: Main terms listed
   - Obligations: Summarized obligations
   - Termination: How contract can end
   - Renewal: Renewal terms

✅ Metadata shows:
   - Complexity level: "simple" | "moderate" | "complex"
   - Chunks used (e.g., "8 of 50 retrieved")
   - Response time

✅ All fields populated with relevant content
```

### **What to Check:**
- [ ] Document selector works
- [ ] Summary generated successfully
- [ ] All expected fields present
- [ ] Content is accurate and relevant
- [ ] Document type correctly identified
- [ ] No error messages
- [ ] Response time reasonable (< 10s)

---

## 📝 **Test 4: Draft Workflow (Document Generation)**

### **Step 1: Click "Draft" Tab**
```
You should see:
- Text input for "What would you like to draft?"
- "Draft" button
```

### **Step 2: Enter Draft Request**
```
Request: "Draft a memo analyzing the termination clause"
Click "Draft"
```

### **Expected Result (Wait 5-10 seconds):**
```
✅ Processing steps shown:
   1. Extracting intent...
   2. Searching relevant documents...
   3. Ranking most relevant chunks...
   4. Organizing sources...
   5. Generating memo...

✅ Draft parameters shown:
   - Document Type: "memo" or "brief"
   - Audience: "legal professional" or other
   - Tone: "formal" or other
   - Focus Area: What's being analyzed

✅ Generated draft appears with:
   - Proper memo structure:
     * TO: [Audience]
     * FROM: [Author]
     * DATE: [Date]
     * RE: [Subject]
     * QUESTION PRESENTED
     * SHORT ANSWER
     * FACTS
     * ANALYSIS (with sub-sections)
     * CONCLUSION
   
   - [1][2][3]... citation numbers throughout

✅ Sources section shows:
   - List of all cited documents
   - Source relevance scores

✅ Warning banner at top:
   "UNREVIEWED AI DRAFT - ATTORNEY REVIEW REQUIRED"

✅ Metadata shows:
   - Number of citations used
   - Response time
```

### **What to Check:**
- [ ] Request input worked
- [ ] Draft generated successfully
- [ ] Proper memo/brief structure
- [ ] Citations present and numbered
- [ ] Sources listed and relevant
- [ ] Warning banner visible
- [ ] Content is professional
- [ ] No hallucinations (made-up facts)
- [ ] Response time reasonable

---

## 🔄 **Test 5: Cross-Workflow Consistency**

### **Step 1: Ask a Question**
```
Question: "What is the payment schedule?"
Note the answer and sources
```

### **Step 2: Summarize Same Document**
```
Go to Summary tab
Select same document
Note the summary mentions payment schedule
```

### **Step 3: Draft About Payment**
```
Go to Draft tab
Request: "Draft a memo about the payment schedule"
Note the sources overlap with Ask and Summary
```

### **Expected Result:**
```
✅ All three workflows show consistent information
✅ No contradictions between workflows
✅ Similar documents cited across all three
✅ Complementary information (Ask detailed, Summary structured, Draft comprehensive)
```

### **What to Check:**
- [ ] No contradictions between workflows
- [ ] Sources are consistent
- [ ] All three workflows reference same documents
- [ ] Information is coherent across workflows

---

## ❌ **Test 6: Error Handling**

### **Error Test 1: Empty Question**
```
Question: (leave empty)
Click "Ask"
```
Expected: Error message appears (don't submit)

### **Error Test 2: Backend Down**
```
Stop backend (Ctrl+C in backend terminal)
Try to Ask a question
```
Expected: Friendly error message like "Cannot connect to backend"

### **Error Test 3: Invalid Input**
```
Question: (very long, 10,000+ characters)
Click "Ask"
```
Expected: Either handles gracefully or shows error

### **What to Check:**
- [ ] Error messages are clear and helpful
- [ ] No "500 Internal Server Error" shown
- [ ] UI doesn't freeze or crash
- [ ] Can recover from errors

---

## 📊 **Test 7: Performance Testing**

### **Single Document**
```
Summary of 20-page contract
Time: Should be 4-6 seconds
Note the time
```

### **Multiple Documents**
```
Ask question that searches across all documents
Time: Should be 3-5 seconds
Compare to single document time
```

### **Expected Result:**
```
✅ All requests complete within 10 seconds
✅ No "timeout" errors
✅ UI remains responsive during processing
✅ Progress indicators show activity
```

### **What to Check:**
- [ ] All responses < 10 seconds
- [ ] No timeout errors
- [ ] UI doesn't freeze
- [ ] Loading spinners show activity

---

## 📱 **Test 8: Mobile Responsiveness**

### **Step 1: Open DevTools**
```
Press F12 in browser
Click device icon (or Ctrl+Shift+M)
Select mobile view (iPhone or similar)
```

### **Step 2: Test Each Workflow**
```
Test Ask on mobile
Test Summary on mobile  
Test Draft on mobile
```

### **Expected Result:**
```
✅ Ask workflow
   - Input field readable
   - Chat history scrolls vertically
   - Answer readable with proper line breaks
   - Citations clickable
   - Sources stack vertically

✅ Summary workflow
   - Document dropdown works
   - Summary fields stack vertically
   - Text is readable (not too small)
   - Fields don't overflow

✅ Draft workflow
   - Input field large enough to type
   - Draft text readable
   - Sources list scrollable
   - All content visible without horizontal scroll

✅ Overall
   - No horizontal scrolling
   - Touch targets (buttons) are large
   - Text is readable (minimum 14px)
   - Images scale properly
```

### **What to Check:**
- [ ] No horizontal scrolling on mobile
- [ ] Buttons/inputs are touch-friendly
- [ ] Text is readable
- [ ] All features work on mobile
- [ ] Layout adapts to screen size

---

## 🎯 **Test 9: Visual Check**

### **Step 1: Ask Workflow Visual**
```
Check:
- [ ] Colors are consistent
- [ ] Text is aligned properly
- [ ] Citations [1][2]... stand out
- [ ] Sources are clearly formatted
- [ ] No overlapping elements
- [ ] Professional appearance
```

### **Step 2: Summary Workflow Visual**
```
Check:
- [ ] Fields are clearly labeled
- [ ] Data is well-formatted
- [ ] Document type indicator visible
- [ ] Complexity level shown
- [ ] Professional appearance
```

### **Step 3: Draft Workflow Visual**
```
Check:
- [ ] Draft text is readable
- [ ] Warning banner is prominent
- [ ] Memo structure is clear
- [ ] Sources are organized
- [ ] Professional appearance
```

---

## 🔍 **Test 10: Console & Network Checks**

### **Step 1: Open DevTools**
```
Press F12 in browser
Go to Console tab
```

### **Step 2: Ask a Question**
```
Question: "What are the parties?"
Click Ask
Watch Console
```

### **Expected Result:**
```
✅ Console shows NO red errors
✅ Console shows NO red "Failed to fetch" messages
✅ Network tab (F12 → Network) shows:
   - POST request to /api/ask
   - Status: 200 (success)
   - Response contains data
```

### **What to Check:**
- [ ] No red console errors
- [ ] No network 404/500 errors
- [ ] Successful API calls (status 200)
- [ ] Response data looks valid

---

## ✅ **Final Verification Checklist**

Print this out and check off as you test:

```
SETUP
  [ ] Backend running on :5000
  [ ] Frontend running on :3000
  [ ] Documents ingested
  [ ] No console errors
  [ ] Browser DevTools clean

ASK WORKFLOW
  [ ] Basic question works
  [ ] Answer is relevant
  [ ] Citations [1][2]... present
  [ ] Sources are valid
  [ ] Chat history works
  [ ] Response time 2-5 seconds
  [ ] No errors

SUMMARY WORKFLOW
  [ ] Document selector works
  [ ] Summary generates
  [ ] All fields populated
  [ ] Document type correct
  [ ] Complexity detected
  [ ] Response time 4-8 seconds
  [ ] No errors

DRAFT WORKFLOW
  [ ] Draft request understood
  [ ] Draft generated
  [ ] Proper structure
  [ ] Citations present
  [ ] Warning banner shown
  [ ] Sources listed
  [ ] Response time 5-10 seconds
  [ ] No errors

CONSISTENCY
  [ ] No contradictions across workflows
  [ ] Sources consistent
  [ ] Information coherent

ERROR HANDLING
  [ ] Empty input shows error
  [ ] Backend down shows message
  [ ] Invalid input handled
  [ ] Can recover from errors

PERFORMANCE
  [ ] All requests < 10 seconds
  [ ] UI responsive
  [ ] No freezing
  [ ] Progress shown

MOBILE
  [ ] Ask works on mobile
  [ ] Summary works on mobile
  [ ] Draft works on mobile
  [ ] No horizontal scroll
  [ ] Readable on phone

VISUAL
  [ ] Professional appearance
  [ ] Colors consistent
  [ ] Text aligned
  [ ] No overlapping

NETWORK
  [ ] No red console errors
  [ ] API calls successful (200)
  [ ] Response data valid

RESULT: ✅ ALL CHECKS PASSED - READY FOR PRODUCTION
```

---

## 🎉 **Success Criteria**

**You're ready to go live if:**

✅ All 10 tests pass  
✅ No console errors  
✅ Performance acceptable  
✅ Mobile responsive  
✅ Error handling works  
✅ Cross-workflow consistency  
✅ Professional appearance  

---

## 📝 **Test Report Template**

Save this as `TEST_REPORT.txt`:

```
LEGALLENS FRONTEND TEST REPORT

Date: 2026-10-24
Tester: [Your Name]
Browser: [Chrome/Firefox/Safari/Edge]
OS: [Windows/Mac/Linux]

BACKEND
  Status: [Running/Error]
  Port: 5000
  Errors: [None/List]

FRONTEND  
  Status: [Running/Error]
  Port: 3000
  Errors: [None/List]

DOCUMENTS
  Count: [Number]
  Sample: [Doc names]

ASK WORKFLOW
  Test 1 (Basic): [PASS/FAIL]
  Test 2 (History): [PASS/FAIL]
  Test 3 (Edge case): [PASS/FAIL]
  Overall: [PASS/FAIL]

SUMMARY WORKFLOW
  Test 1 (Contract): [PASS/FAIL]
  Test 2 (Opinion): [PASS/FAIL]
  Test 3 (Complexity): [PASS/FAIL]
  Overall: [PASS/FAIL]

DRAFT WORKFLOW
  Test 1 (Memo): [PASS/FAIL]
  Test 2 (Brief): [PASS/FAIL]
  Test 3 (Intent): [PASS/FAIL]
  Overall: [PASS/FAIL]

PERFORMANCE
  Ask time: [X seconds]
  Summary time: [X seconds]
  Draft time: [X seconds]

ISSUES FOUND
  1. [Issue description]
  2. [Issue description]

OVERALL RESULT: [READY / NEEDS FIXES]

Notes:
[Any additional observations]
```

---

## 🚀 **Quick Reference Commands**

```bash
# Terminal 1: Backend
cd backend
python run.py --port 5000

# Terminal 2: Frontend  
cd frontend
npm start

# Browser
http://localhost:3000

# Test API
curl -X POST http://localhost:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Test?","chat_history":[]}'

# Stop everything
Ctrl+C in each terminal
```

---

## 📞 **Troubleshooting**

| Issue | Solution |
|-------|----------|
| Backend won't start | Use different port: `python run.py --port 5000` |
| Frontend shows blank | Check DevTools console (F12) for errors |
| API calls failing | Check backend is running: http://localhost:5000/api/docs |
| Slow responses | Reduce document count or check CPU/RAM |
| Citations don't match | Check vector store is initialized properly |
| Mobile looks broken | Browser zoom at 100%, try different device |

---

**You're all set! Follow these instructions and report your findings.** 🎉

Happy testing! 🚀
