# Legal Lens — Ideas

**Status:** collected thoughts, before the BRD
**Date:** 2026-09-30
**Next step:** BRD (functional and non-functional specs) → then technical architecture

**Tags used in this file**

- **[DECIDED]** — settled; carry into the BRD.
- **[SUGGESTION]** — proposed, needs a yes/no.
- **[OPEN]** — question still to answer.
- **[DEFERRED]** — technical detail intentionally left for the architecture phase.

---

## 1. What Legal Lens is

Legal Lens is an AI application, a chatbot, built for lawyers and attorneys. An attorney can upload a legal document and then work with it through a prompt bar.

---

## 2. Core features — [DECIDED]

1. **Ask** — ask legal questions, including questions about an uploaded document.
2. **Summary** — summarize a legal document.
3. **Draft** — draft a legal case document or a legal memo.

---

## 3. Jurisdiction — [DECIDED]

- **v1: United States only.**
- **Later:** add more countries.

**[SUGGESTION]** Because more countries are planned, treat jurisdiction as a setting rather than hard-coding US assumptions. Citation style, summary and draft formats, disclaimers and data rules would each be chosen per jurisdiction, with only the US available in v1. Adding a country later then means adding a new jurisdiction configuration instead of reworking the app.

---

## 4. Build plan — three phases — [DECIDED]

### Phase 1 — Frontend

- Takes input from lawyers.
- Document upload.
- A search bar / prompt bar for asking questions, including questions about an uploaded document.
- Access to all three features: Ask, Summary, Draft.
- Built with HTML, CSS and a JavaScript framework. No preference between Angular and React.

**[SUGGESTION]** Use React. It has a large ecosystem for chat-style interfaces and for streaming responses.

### Phase 2 — Backend

- Python + FastAPI.
- **uv** for package management and dependency management.

### Phase 3 — AI layer

- A **RAG** (retrieval-augmented generation) application for now.
- Later: extend or upgrade it to a **multi-agent** system.

**[DEFERRED]** Vector database, embedding model, type of RAG and other technical details. These will be decided when building the technical architecture.

---

## 5. Suggestions to consider

- **[SUGGESTION] Define the API contract early.** Since the frontend is built first, agree on the backend endpoints (for example `/ask`, `/summarize`, `/draft`) up front and have FastAPI return sample responses. The frontend can then be built and tested without waiting for the backend or AI layer.
- **[SUGGESTION] Keep the AI layer behind a small interface.** Expose something like `ask()`, `summarize()` and `draft()` to the backend. The later move from RAG to multi-agent then stays inside the AI layer and doesn't affect the frontend or the API.
- **[SUGGESTION] Cite sources in every answer.** Answers should point back to the document and page they came from, and say "not found in your documents" rather than guess. Made-up legal citations are a serious professional risk for attorneys.
- **[SUGGESTION] Treat client documents as confidential.** Plan for encryption, deletion on request, and an LLM provider that does not keep or train on the data.

---

## 6. Open questions — [OPEN]

1. **Ask scope:** should Ask answer only from uploaded documents, or also general legal questions without a document?
2. **Draft types:** is "legal case" a case brief, a complaint/pleading, or both? Which draft types are in v1?
3. **Users:** solo attorneys only at first, or law firms with multiple users and roles?
4. **Document formats:** PDF only, or also Word and scanned documents?
5. **LLM hosting:** is a hosted LLM API acceptable for confidential client documents, or is a self-hosted model required?

---

## 7. Next step — BRD

The BRD should cover:

- Purpose, scope and out-of-scope items
- Users and user journeys
- Functional requirements for Ask, Summary and Draft
- Non-functional requirements: performance, security, privacy, availability, scalability
- Jurisdiction (US in v1, more countries later)
- Assumptions, risks and open questions
- Phased delivery plan
