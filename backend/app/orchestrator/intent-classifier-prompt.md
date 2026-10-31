# Intent Classification Strategy for LegalLens

**Purpose:** Automatically classify user queries into one of three intents: **Ask**, **Summary**, or **Draft**.

**Model:** Claude Haiku 4.5 (optimized for fast, accurate classification without overthinking)

---

## Intent Definitions

### 1. **Ask** (Information Retrieval & Q&A)
**Goal:** Answer a specific question by retrieving and synthesizing relevant information from documents.

**Characteristics:**
- User asks a direct question (starts with "What", "How", "When", "Where", "Who", "Why", "Can", "Will", "Is")
- Seeks facts, explanations, or clarifications
- Expects a conversational, cited answer with specific excerpts
- Examples:
  - "What are the termination rights in this agreement?"
  - "When does the contract expire?"
  - "How much notice must be given?"
  - "Are there non-compete clauses?"

**Heuristics:**
- Contains question marks or interrogative words
- Length: typically short (1-3 sentences)
- Intent is to *find and cite* specific information

---

### 2. **Summary** (Document Summarization & Structure Extraction)
**Goal:** Extract key information from a *single document* in a structured format.

**Characteristics:**
- User explicitly asks to "summarize" or wants a structured overview
- Applies to one document at a time
- Returns a template (Contract Summary / Opinion Summary / Pleading Summary) with standardized fields
- Examples:
  - "Summarize this contract"
  - "What are the key terms?"
  - "Give me an overview of this opinion"
  - "Extract the main points from this document"

**Heuristics:**
- Contains words: "summarize", "summary", "overview", "extract", "key points", "key terms", "main points", "structure"
- User mentions a specific document or implies one
- Scope is almost always single-document
- Expects structured output, not prose

---

### 3. **Draft** (Document Generation & Writing)
**Goal:** Generate new legal documents (memos, briefs) by synthesizing information from source documents.

**Characteristics:**
- User asks to "draft", "write", "create", or "generate" a new document
- Produces a memo or case brief with a formal structure
- Requires draft parameters: type (memo/brief), question presented, audience, position, tone, source documents
- Examples:
  - "Draft a memo analyzing the termination clause"
  - "Write a case brief for the Smith v. Jones opinion"
  - "Create a memo on indemnification provisions"
  - "Prepare a brief summarizing the holding"

**Heuristics:**
- Contains words: "draft", "write", "create", "generate", "prepare", "memo", "brief", "memorandum"
- Requests original content creation, not retrieval or summarization
- Implies formal structure and synthesis

---

### 4. **Auto** (Router Decision)
**Goal:** When the user doesn't explicitly specify an intent, infer it from context.

**How Auto works:**
1. If none of the above keywords match, use these fallback rules:
   - **→ Ask** if: question mark + no draft/summary keywords
   - **→ Summary** if: query mentions a single document + asks about its content
   - **→ Draft** if: query requests creation, generation, or writing
   - **→ Ask** (default) if: ambiguous or unclear

---

## Classification Rules (Priority Order)

Execute these checks in order; return as soon as one matches:

| Rule # | Condition | Intent | Confidence |
|--------|-----------|--------|------------|
| 1 | Message contains "draft", "write", "create", "generate", "prepare", "brief", "memo" (case-insensitive) | **Draft** | High |
| 2 | Message contains "summarize", "summary", "overview", "extract", "key points", "key terms" (case-insensitive) | **Summary** | High |
| 3 | Message ends with "?" AND no draft/summary keywords | **Ask** | High |
| 4 | Message is very short (< 20 chars) AND no draft/summary keywords | **Ask** | Medium |
| 5 | Conversation history shows user just uploaded a document → suggest **Summary** | **Summary** | Medium |
| 6 | Default if no rules match | **Ask** | Low |

---

## Examples

### Example 1: Clear Ask
**User:** "What are the termination rights in the Acme MSA?"
- Contains "?"
- No draft/summary keywords
- **Classification:** Ask (Rule 3)
- **Confidence:** High

### Example 2: Clear Summary
**User:** "Summarize the key terms of this contract"
- Contains "summarize" + "key terms"
- **Classification:** Summary (Rule 2)
- **Confidence:** High

### Example 3: Clear Draft
**User:** "Draft a memo analyzing the indemnification clause"
- Contains "draft" + "memo"
- **Classification:** Draft (Rule 1)
- **Confidence:** High

### Example 4: Ambiguous
**User:** "Tell me about the pricing terms"
- No "?" (but implied question)
- No draft/summary keywords
- Contains request for information
- **Classification:** Ask (Rule 6 - default)
- **Confidence:** Medium

### Example 5: Multi-word Query
**User:** "Create a case brief summarizing the holding"
- Contains "create" (draft keyword) AND "summarizing" (summary keyword)
- **Priority:** Draft > Summary
- **Classification:** Draft (Rule 1 takes precedence)
- **Confidence:** High

---

## Context Awareness (Optional Enhancements)

When available, these factors can refine classification:

1. **Document scope:** If documents are selected/scoped:
   - Single document + ambiguous query → prefer **Summary**
   - Multiple documents + ambiguous query → prefer **Ask**

2. **Conversation history:**
   - Previous turn was an upload → next ambiguous query → prefer **Summary**
   - Previous answers were "Ask" results → next "this too" → continue **Ask**

3. **Model confidence:**
   - If confidence < 50%, return **Auto** and let backend router decide
   - If confidence ≥ 50%, return the classified intent

---

## LLM Prompt (for fallback: when rules are inconclusive)

When heuristic rules are inconclusive (e.g., multi-intent mixed keywords, edge cases), call Claude Haiku with this system prompt:

```
You are an intent classifier for a legal document Q&A system. Classify the user's 
query into ONE of: Ask (answer a question), Summary (summarize a document), or Draft 
(write a new legal document).

Ask: Direct question seeking factual retrieval or explanation from documents.
Summary: Request to extract key information from a single document in structured format.
Draft: Request to generate new legal content (memo, brief) from source documents.

Respond with ONLY the intent name: Ask, Summary, or Draft.
```

**Input to the model:**
```json
{
  "user_message": "...",
  "conversation_history_length": N,
  "document_scope": "workspace|documents|single_doc"
}
```

**Expected output:**
```json
{
  "intent": "Ask|Summary|Draft",
  "confidence": 0.95
}
```

---

## Implementation Notes

1. **Order matters:** Always check Draft before Summary before Ask (because "draft a summary" should be Draft, not Summary)

2. **Case insensitivity:** All keyword checks are case-insensitive

3. **Whitespace tolerance:** Trim and normalize whitespace

4. **Scope context:** When available, pass document scope to refine the classification

5. **Fallback to LLM:** If heuristics are inconclusive, use Claude Haiku for final classification

6. **No overthinking:** Haiku is fast and sufficient for this task — don't use a larger model

---

## Testing Scenarios

### Happy Path
- ✓ "What is the termination clause?" → Ask
- ✓ "Summarize this contract" → Summary
- ✓ "Draft a memo on indemnification" → Draft

### Edge Cases
- ✓ "Tell me the key points" → Summary (has "key points")
- ✓ "Create a brief" → Draft (has "brief")
- ✓ "Is there a non-compete?" → Ask (has "?")
- ✓ "xyz" → Ask (default; too short and no indicators)

### Ambiguous/Multi-intent
- ✓ "Draft a summary of the opinion" → Draft (Draft > Summary)
- ✓ "Summarize and create a memo" → Draft (Draft > Summary)
- ✓ "What is a good case brief?" → Ask (question, but not asking to draft)

---

## Future Enhancements

1. **Machine learning:** Train a small classifier on real user queries
2. **Intent confidence scores:** Return confidence with each classification
3. **Multi-intent support:** Some queries might legitimately be Ask + Draft
4. **Conversation context:** Track conversation flow to refine classifications
5. **User intent feedback loop:** Log misclassifications and retrain

