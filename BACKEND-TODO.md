# Legal Lens — Backend Implementation Plan (FastAPI, standalone)

**Status:** approved 2026-10-05 with the §11 defaults · **B0–B9 implemented in `backend/`** · 44 tests passing, ruff + mypy (strict) clean · deviations from this plan are listed in §12 · scope = milestone **M3** of the BRD (§10): the real API, storage, sessions, upload and parsing, the five endpoint groups, SSE and actionable errors. The orchestration and AI/RAG layers (diagram lanes 3–5, 8) are **not** built here.
**Sources:** `docs/LegalLens-BRD-PRD-FRD.md` (FR / NFR / DR / TS numbers refer to it) · `docs/architecture/legallens_flow_gen.py` (lanes 2, 6, 7) · **`frontend/src/api/types.ts` is the contract.** Where the diagram and `types.ts` disagree, `types.ts` wins, because a working consumer already depends on it.

---

## 1. What we are building, in one paragraph

A FastAPI service that the frontend can switch to by setting `VITE_USE_MOCKS=false`, with **no other frontend change**. It owns everything the diagram puts in the API and persistence lanes: sign-in and sessions, the conversation DB (SQLite), document upload, encrypted file storage, text extraction with page and character offsets, ingestion status, the chat turn streamed over SSE, citations that resolve to real spans, feedback, usage and audit. The AI layer is replaced by a **stub orchestrator** behind the exact `answer() / summarize() / draft()` interface the BRD fixes (NFR-14). The stub does real lexical search over the documents you upload and returns extractive, cited answers, so the whole product works end to end — upload a PDF, ask about it, click a citation, see the highlighted passage — before any LLM exists. When the real orchestrator is ready it replaces the stub, and nothing in the API changes.

## 2. Boundaries

| In this phase | Not in this phase (later, behind an interface that already exists) |
|---|---|
| All HTTP endpoints in §5, matching `types.ts` exactly | LangChain orchestration, intent-router LLM, query rewriting |
| SQLite conversation DB + migrations | Qdrant, embeddings, hybrid search, reranking |
| Upload validation, encrypted blob store, SHA-256 dedupe | Layout-aware parsing (Docling), OCR, layout QA gate |
| Text extraction per page with char offsets (pypdf, python-docx, txt) | Section/clause tree, section-aware chunking |
| Ingestion status machine + background worker | Celery / Redis (no Docker or Redis on this machine) |
| SSE chat turn: lifecycle, ordering, persistence, disconnect handling | Citation-verification LLM judge (claim-level NLI) |
| Stub orchestrator (keyword router, SQLite FTS5 search, extractive answers) | Real summaries / drafts written by an LLM |
| Span resolution, feedback, usage ledger, traces, audit log | Tracing backend (Langfuse / OTel exporter), CI eval gate |
| Hard delete, verified by test (FR-26, TS-6) | Postgres, deployment, rollback (M6) |

## 3. Technology choices

| Concern | Choice | Why |
|---|---|---|
| Runtime | Python 3.13, managed with **uv** (already installed) | 3.14 is on the machine, but 3.13 has wider wheel coverage |
| Framework | FastAPI + Uvicorn | Fixed by the BRD |
| Validation | Pydantic v2; **camelCase JSON** via an alias generator, snake_case in Python | `types.ts` uses camelCase (`sizeBytes`, `nextCursor`, …) |
| DB | **SQLite** (the "conversation DB" in the diagram) via SQLAlchemy 2.0 async + aiosqlite; WAL mode | Zero-ops for v1; the diagram plans a Postgres swap at M6 with no schema change |
| Migrations | Alembic | Schema is versioned from day one |
| Search (stub only) | SQLite **FTS5** (BM25) over page text | Real ranked retrieval with no extra service; replaced by Qdrant hybrid later |
| Auth | Server-side sessions in SQLite, HttpOnly cookie, argon2 password hash | FR-27: one user, email + password, server-side sessions |
| Files at rest | Fernet (AES) encrypted blobs on local disk, key from env | NFR-9 |
| Parsing | pypdf (PDF text layer), python-docx, plain text | Enough for page + char offsets (FR-4); layout/OCR come with the ingestion lane |
| SSE | sse-starlette (keep-alive pings, client-disconnect detection) | Needed to mark a stopped answer *incomplete* (NFR-7) |
| Background jobs | In-process asyncio worker reading a DB-backed `ingestion_jobs` table, behind a `JobQueue` interface | Survives restarts (jobs resume); Celery/Redis can replace it without touching routes |
| Tests / quality | pytest, pytest-asyncio, httpx `AsyncClient`, ruff, mypy (strict on `app/`) | |

## 4. Cross-cutting rules (apply to every endpoint)

- [x] **JSON shape** — camelCase keys, ISO-8601 UTC timestamps (`2026-10-05T14:03:00Z`), IDs with a readable prefix (`doc_`, `conv_`, `msg_`, `trace_`, `usr_`), `null` rather than omitted where `types.ts` says `T | null`, omitted where it says `field?`.
- [x] **Pagination** — every list returns `Page<T>` = `{ items, nextCursor }`; opaque cursor; `limit` default 30, max 100.
- [x] **Error envelope** — every non-2xx response is `ApiErrorBody` = `{ code, message, retryAfterSec? }`, with a message that names the next action (FR-28). Mapping:

  | HTTP | `code` | When |
  |---|---|---|
  | 401 | `unknown` | not signed in / bad credentials |
  | 404 | `unknown` | conversation, document, page or span not found |
  | 409 | `unknown` | e.g. summarising a document that is not `ready` |
  | 413 / 422 | `unknown` | body too large / validation failure (message lists the field) |
  | 429 | `rate_limited` | with `retryAfterSec` and a `Retry-After` header |
  | 503 | `llm_unavailable` | orchestrator unavailable before the stream starts |
  | 504 | `timeout` | turn exceeded its budget before the stream starts |
  | 500 | `unknown` | anything else; never leaks a stack trace or document text |

  (See decision 4 in §11 about adding more specific codes.)
- [x] **Middleware chain** (diagram lane 2): request-id (`X-Request-ID` in and out) → session auth → rate limit → Pydantic validation → route → error envelope → audit write.
- [x] **No document content in logs** (DR-5): log IDs, sizes, timings and status codes only; a test enforces it on the upload and chat paths.
- [x] **CORS** — allow the Vite origin with credentials when configured; same-origin through the Vite proxy is the default (decision 5).

## 5. API contract

Every request and response model below already exists as a TypeScript type in `frontend/src/api/types.ts`; the backend's Pydantic models mirror them one-for-one. Auth is required everywhere except `/api/auth/login` and `/api/health`.

### 5.1 Auth (FR-27)

| Method & path | Request | Response |
|---|---|---|
| `POST /api/auth/login` | `{ email, password }` | `200 User` + `Set-Cookie: ll_session` (HttpOnly, SameSite=Lax, Secure outside dev) · `401` "That email and password combination is incorrect." |
| `POST /api/auth/logout` | — | `204`, session row deleted, cookie cleared |
| `GET /api/auth/me` | — | `200 User` · `401` |

`User` = `{ id, name, email, initials }`. The single user is seeded from env (`LL_USER_EMAIL`, `LL_USER_PASSWORD`, `LL_USER_NAME`). Sessions slide on activity; idle timeout 12 h, absolute 7 d. Login is rate limited (5 per minute) to slow password guessing.

### 5.2 Conversations — sidebar and NCC

| Method & path | Request | Response |
|---|---|---|
| `GET /api/conversations?cursor=&limit=` | — | `Page<Conversation>`, newest `updatedAt` first |
| `POST /api/conversations` **(NCC)** | — | `201 Conversation` with title "New conversation", `lastIntent: null` |
| `GET /api/conversations/{id}` | — | `ConversationDetail` = `Conversation` + `messages: Message[]` (oldest first) |
| `GET /api/conversations/{id}/messages?cursor=` | — | `Page<Message>` |
| `PATCH /api/conversations/{id}` | `{ title?, pinned? }` | `Conversation`; title trimmed, 1–120 chars |
| `DELETE /api/conversations/{id}` | — | `204`; messages, citations, excerpts and feedback cascade |

`Conversation` = `{ id, title, lastIntent, pinned, createdAt, updatedAt }`. `Message` is the `UserMessage | AssistantMessage` union discriminated by `role`; the assistant message carries everything the UI renders after a reload: `status, intent, scopeUsed, answerMd, citations[], excerpts[], refusal?, summary?, draft?, error?, usage?, feedback?, traceId, modelVersion, promptVersion`.

### 5.3 Chat turn — `POST /api/conversations/{id}/messages` (SSE, FR-10)

**Request** — `SendMessageRequest`:
```json
{ "text": "What are the termination rights?", "mode": "auto",
  "scope": { "kind": "documents", "documentIds": ["doc_acme_msa"] },
  "draftParams": null, "summaryDocumentId": null }
```

**Validated before the stream opens** (plain JSON error, not SSE): conversation exists · text 1–8 000 chars · valid mode, scope and draft params · rate limit. *No ready documents in scope*, *no draft sources* and *a brief without an opinion* are answered in-stream as **refusals** instead (see §12).

**Response** — `Content-Type: text/event-stream`, frames `event: <name>\ndata: <json>\n\n`, keep-alive comment every 15 s. Order:

| # | Event | Payload | Notes |
|---|---|---|---|
| 1 | `meta` | `{ userMessageId, messageId, intent, scopeUsed, traceId }` | always first; both message rows already written |
| 2 | `stage` × n | `{ label }` | "Searching 6 documents…", "Writing the answer…" |
| 3 | `excerpt` × n | `Excerpt` | retrieval results, sent **before** generation so excerpts show even if generation fails (FR-12, NFR-6) |
| 4 | `refusal` | `Refusal` | instead of tokens, when support is insufficient (FR-14) |
| 5 | `citation` × n + `summary` | `Citation`, `SummaryResult` | summary turns |
| 5 | `draft` | `DraftMeta` | draft turns; the body then streams as tokens |
| 6 | `token` × n / `citation` | `{ text }` / `Citation` | each citation is sent the first time its `[n]` marker appears |
| 7 | `usage` | `Usage` | tokens, cost, latency |
| 8 | `done` **or** `error` | `{ modelVersion, promptVersion }` / `ApiErrorBody` | exactly one terminal event |

**Turn lifecycle** (the hard part of this phase):
- [x] Resolve intent: `mode != auto` → that intent; `auto` → `orchestrator.route()` (stub: keyword router, same rules as the mock).
- [x] Resolve scope (FR-8, FR-9): workspace → all *ready* docs; documents → the ready subset; build `scopeUsed.label` ("Whole workspace (6 documents)", or the document's name).
- [x] Write the user message and an assistant row with `status: streaming` in one transaction, then emit `meta`.
- [x] Accumulate everything streamed into the assistant row; flush on terminal event.
- [x] **Citation guard** (FR-21 contract, enforced at the API boundary even though the real verifier lives in the AI layer): every `Citation` must resolve to stored page text, and `quote` must equal the text at `charStart..charEnd`; anything else is dropped, never streamed.
- [x] Terminal states: `done` → `complete` · `error` event → `error` with the body stored · **client disconnect / Stop** → `incomplete`, with the partial text kept (NFR-7) · server exception → `error` event with `unknown`, then `incomplete`.
- [x] First turn sets the conversation title (draft → "Memo: …", summary → "Summary: <doc>", ask → first ~60 chars); every turn updates `lastIntent` and `updatedAt`.
- [x] Turn budget: 120 s overall → `timeout` error event.
- [x] Write the usage transaction, trace and audit row (DR-4) for every turn, including refused and failed ones.

### 5.4 Explicit mode endpoints (diagram "MODE ENDPOINTS")

`POST /api/ask` · `POST /api/summarize` · `POST /api/draft` — body `SendMessageRequest` + `conversationId`; identical SSE stream with the intent fixed and the router skipped. Thin wrappers over the same turn service; the current frontend does not call them.

### 5.5 Documents (FR-1 to FR-7, FR-26)

| Method & path | Request | Response |
|---|---|---|
| `POST /api/documents` | multipart, field `files` repeated | `201 { created: LegalDocument[], rejected: { name, reason }[] }` |
| `GET /api/documents?cursor=` | — | `Page<LegalDocument>`, newest first |
| `GET /api/documents/{id}` | — | `LegalDocument` |
| `GET /api/documents/{id}/status` | — | `{ status, progress, error? }` |
| `GET /api/documents/{id}/pages/{n}` | — | `DocumentPage` = `{ documentId, page, text, ocrConfidence, lowOcr }`; `404` unless ready and `1 ≤ n ≤ pages` |
| `GET /api/documents/{id}/file` | — | original bytes, decrypted, `Content-Disposition: inline` (for pdf.js later) |
| `PATCH /api/documents/{id}` | `{ type }` | `LegalDocument` with `typeOverridden: true` (FR-5) |
| `DELETE /api/documents/{id}` | — | `204`, hard delete (§7) |
| `DELETE /api/documents` | — | `204`, whole workspace: all documents **and** all conversations (matches the mock and the Settings copy) |

`LegalDocument` = `{ id, name, mimeType, sizeBytes, pages, type, typeConfidence, typeOverridden, status, progress, error?, lowOcrPages, uploadedAt }`.

**Upload rules** — one bad file never rejects the batch (FR-3):
- [x] Extension and **magic bytes** must agree: `.pdf` (`%PDF`), `.docx` (zip with `word/document.xml`), `.txt` (valid UTF-8 or Latin-1).
- [x] Over 50 MB → rejected with the actual size ("File is 61.3 MB; the limit is 50 MB.") — FR-2. Streamed to disk in chunks, never held whole in memory.
- [x] Over 500 pages → accepted, then **failed** during parsing with the count ("This document has 612 pages; the limit is 500. Split it…") — pages are unknown until parsed, as in the mock.
- [x] Duplicate (same SHA-256 already in the library) → rejected, naming the existing document.
- [x] Workspace already holds 50 documents (NFR-4) → rejected, naming the limit.
- [x] Accepted file → encrypted blob written, `documents` row `queued`, ingestion job enqueued.

### 5.6 Spans, feedback, traces, usage, health

| Method & path | Request | Response |
|---|---|---|
| `GET /api/spans/{spanId}` | — | `{ spanId, documentId, documentName, page, charStart, charEnd, text }` |
| `POST /api/feedback` | `{ conversationId, messageId, rating: up\|down, reason?, comment? }` | `204`; upserts one row per message, linked to its `traceId` (FR-25) |
| `GET /api/traces/{traceId}` | — | `{ traceId, messageId, intent, stages: [{ name, startedAt, latencyMs, costUsd, detail }], retrieval: { query, candidates: [{ spanId, score }] }, modelVersion, promptVersion }` (NFR-11, NFR-12) |
| `GET /api/usage?from=&to=` | — | `{ totals: { turns, inputTokens, outputTokens, costUsd }, byIntent: {…}, byDay: [...] }` |
| `GET /api/health` | — | `{ status: "ok", version }` (no auth) |
| `GET /api/health/ready` | — | DB reachable, migrations current, worker alive |

**Span ID format** stays as the frontend mock already uses it: `{documentId}~p{page}~{charStart}-{charEnd}`. It is self-describing, so a span resolves by slicing stored page text — no lookup table, and it can never point at text that does not exist.

### 5.7 Dev-only (registered only when `LL_ENV=dev`)

- [x] `GET / PUT /api/dev/scenario` — `{ nextReply: normal|refusal|llm_unavailable|rate_limited|timeout|interrupted, sticky, speed: fast|normal|slow, nextUploadFails }`, the same switches as the frontend's ScenarioSwitcher, so every error and refusal card can be exercised against the real backend.
- [x] `POST /api/dev/reset` — wipe and reseed.

## 6. Database schema (SQLite, Alembic-managed)

| Table | Key columns | Purpose |
|---|---|---|
| `users` | id, email (unique), name, password_hash, created_at | single user in v1 |
| `sessions` | id (hashed token), user_id, created_at, last_seen_at, expires_at | server-side sessions |
| `documents` | id, name, mime_type, size_bytes, sha256 (unique), blob_path, pages, type, type_confidence, type_overridden, status, progress, error, uploaded_at, ready_at, parse_engine, parse_version | library |
| `document_pages` | document_id, page_no, text, ocr_confidence, low_ocr, char_count | page text + offsets: what makes a citation clickable (FR-4, FR-13) |
| `document_pages_fts` | FTS5 virtual table over page text | stub retrieval only; dropped when Qdrant arrives |
| `ingestion_jobs` | id, document_id, state, attempts, last_error, queued_at, started_at, finished_at | resumable worker queue (FR-3) |
| `conversations` | id, user_id, title, last_intent, pinned, created_at, updated_at | sidebar |
| `messages` | id, conversation_id, role, seq, created_at · user: text, mode, scope_json, draft_params_json, summary_document_id · assistant: status, intent, stage, scope_used_json, answer_md, refusal_json, summary_json, draft_json, error_json, trace_id, model_version, prompt_version | thread |
| `message_citations` | message_id, n, span_id, document_id, page, char_start, char_end, quote, section | citation rows → span refs |
| `message_excerpts` | message_id, rank, span_id, document_id, page, section, text, score | retrieved excerpts |
| `feedback` | message_id (unique), conversation_id, trace_id, rating, reason, comment, created_at | FR-25 |
| `usage_transactions` | id, message_id, trace_id, intent, input_tokens, output_tokens, cost_usd, latency_ms, created_at | $ ledger (NFR-8) |
| `traces` | trace_id, message_id, stages_json, retrieval_json, created_at | NFR-11 |
| `audit_log` | id, at, user_id, action, entity, entity_id, request_id, detail_json | DR-4; deletes leave a tombstone here only |
| `chunk_meta` | chunk_id, document_id, page, char_start, char_end, qdrant_point_id, index_version | created now, **filled by the AI layer later**, so deletion already covers it |

`summary_json` / `draft_json` store the structured objects whole; citations and excerpts get their own rows because they are queried (span checks, deletion, eval).

## 7. Ingestion and deletion

**Worker** — in-process asyncio task, up to 3 concurrent jobs (NFR-5), picks `queued` jobs from `ingestion_jobs`, resumes unfinished jobs on startup, retries twice with backoff on unexpected errors.

- [x] `queued` → **`parsing`** (progress = pages done / pages total): decrypt blob → extract text per page.
  - PDF: pypdf text layer per page. Password-protected → failed: "This PDF is password-protected. Remove the password, then upload it again." Corrupt → failed: "The file couldn't be read — it may be damaged. Re-export it… and upload again."
  - Pages with almost no text layer (< 40 chars) are marked `low_ocr` with confidence 0 — the page is flagged "could not be read" in the UI, because OCR is deferred (decision 1).
  - DOCX: paragraphs in order; pages split on explicit page breaks, otherwise every ~3 000 characters.
  - TXT: form-feed characters, otherwise every ~3 000 characters.
  - Over 500 pages → failed with the count.
- [x] → **`indexing`**: classify the type (filename + first-page keywords → contract / opinion / pleading / other with a confidence), insert pages into FTS5.
- [x] → **`ready`**: only now does the document enter any search (FR-7).
- [x] Every transition is written to the DB, so `GET /api/documents` polling (the frontend polls every 900 ms while anything is in flight) shows live progress.

**Hard delete** (FR-26, TS-6) — one transaction plus file removal: blob file → page rows → FTS rows → `chunk_meta` rows → `ingestion_jobs` → document row; tombstone in `audit_log`. Citations in old conversations stay readable as text, but their span no longer resolves (`404` "Source passage not found"). **A test proves it**: after delete, the file is gone from disk, no row anywhere references the ID, FTS search for a unique phrase from the file returns nothing, and its spans return `404`.

## 8. The orchestrator boundary and the stub

```python
class Orchestrator(Protocol):              # app/orchestrator/interface.py — the only door (NFR-14)
    async def route(self, req: TurnContext) -> Intent: ...
    def answer(self, req: TurnContext) -> AsyncIterator[OrchestratorEvent]: ...
    def summarize(self, req: TurnContext) -> AsyncIterator[OrchestratorEvent]: ...
    def draft(self, req: TurnContext) -> AsyncIterator[OrchestratorEvent]: ...
```

`TurnContext` carries the text, intent, resolved scope (ready document IDs), draft params, summary document, the last 8 turns of history, and the trace ID. `OrchestratorEvent` is a typed union matching the SSE events (`stage, excerpt, citation, token, refusal, summary, draft, usage, done, error`), so the API layer only translates and persists — it holds no retrieval or prompt logic. The implementation is chosen by `LL_ORCHESTRATOR=stub|remote`.

**Stub orchestrator** — deterministic, no network, clearly labelled `modelVersion: "stub-extractive-0.1"`:
- [x] **Router** — the same keyword rules as `frontend/src/mocks/engine.ts`.
- [x] **Ask** — FTS5 BM25 over pages in scope → top 5 sentences become excerpts and citations → the answer is those sentences joined, each followed by its `[n]` marker. Below a score threshold → **refusal** naming the scope, with suggestions (widen scope, upload, rephrase).
- [x] **Summary** — the §9 templates (contract / opinion / pleading / other); each field is filled only when a keyword search inside the document finds a supporting sentence, cited; otherwise `null` → "Not addressed in this document" (FR-16). Coverage = pages read vs. pages flagged low-OCR (FR-17).
- [x] **Draft** — memo (Question Presented → Short Answer → Statement of Facts → Discussion → Conclusion) or case brief, filled with cited sentences from the source documents only; returns `DraftMeta`.
- [x] Token streaming at a configurable speed; plausible `Usage` figures; honours the dev scenario switches.

Every citation the stub produces passes the API's citation guard, so the frontend sees the same guarantee the real verification gate will provide.

## 9. Folder structure

```
backend/
  pyproject.toml · uv.lock · .env.example · alembic.ini · README.md
  alembic/versions/
  app/
    main.py                 app factory, lifespan (migrate, seed user, start worker)
    core/                   config.py · errors.py · ids.py · logging.py · security.py (argon2, sessions)
                            crypto.py (Fernet) · ratelimit.py · middleware.py
    db/                     base.py · session.py · models/{users,documents,conversations,messages,ops}.py
    schemas/                common.py (CamelModel, Page, ApiErrorBody) · auth.py · documents.py
                            conversations.py · messages.py · stream.py · feedback.py · traces.py · usage.py
    api/
      deps.py               current_user, db session, rate-limit dependencies
      routes/               auth · conversations · chat · modes · documents · spans · feedback
                            traces · usage · health · dev
    services/               conversations · chat_turn · documents · spans · feedback · usage · audit · scope
    ingestion/              queue.py (JobQueue + InProcessQueue) · worker.py · validate.py · blob_store.py
                            classify.py · search_index.py (FTS5) · parsers/{pdf,docx,txt}.py
    orchestrator/           interface.py · factory.py
      stub/                 router.py · retrieval.py · ask.py · summarize.py · templates.py · draft.py · scenario.py
    sse.py                  frame encoding, keep-alive
  scripts/                  seed_demo.py · export_openapi.py
  tests/                    conftest.py · fixtures/ (small PDF, DOCX, TXT, password-protected PDF, blank scanned page)
                            test_auth · test_documents · test_ingestion · test_conversations · test_chat_stream
                            test_summary_draft · test_spans · test_feedback_usage · test_delete · test_contract
```

## 10. Build order (each phase ends with something you can run)

| Phase | Deliverable | Done when |
|---|---|---|
| **B0** Scaffold | uv project, app factory, config, logging, error envelope, request-id, `/api/health`, ruff + mypy + pytest | `uvicorn` starts; `/api/health` returns ok; lint and type check clean |
| **B1** Data layer | SQLAlchemy models, Alembic initial migration, all Pydantic schemas mirroring `types.ts`, `export_openapi.py` → `docs/api/openapi.json` | `alembic upgrade head` builds the DB; OpenAPI exported |
| **B2** Auth | login, logout, me, session dependency, login rate limit, seeded user | Protected routes return 401 without a cookie, 200 with one |
| **B3** Documents | upload + validation, encrypted blobs, dedupe, job queue + worker, parsers, classifier, FTS index, status, pages, file, patch, delete, workspace delete, spans | Upload a PDF, a DOCX, a TXT and a password-protected PDF: three reach `ready`, one fails with its message; pages and spans resolve |
| **B4** Conversations | list / create (NCC) / get / messages / patch / delete, feedback | Sidebar operations work through Swagger UI |
| **B5** Orchestrator + Ask | interface, factory, stub router, FTS retrieval, extractive Ask, refusal | `orchestrator.answer()` returns cited events for an uploaded document |
| **B6** Chat turn SSE | turn service, event ordering, persistence, citation guard, disconnect → incomplete, timeout, rate limit, pre-stream errors, titles, usage, trace, audit | `curl -N` streams a full cited answer; stopping mid-stream leaves an `incomplete` message |
| **B7** Summary + Draft | type templates, coverage ledger, memo and brief structure, mode endpoints | A contract summary and a memo stream end to end |
| **B8** Ops endpoints + dev | traces, usage ledger, dev scenario and reset, seed script (the frontend's 7 fixture documents as real TXT files, so the demo looks like the mock) | Every scenario-switcher state reproducible against the backend |
| **B9** Tests + hardening | endpoint tests, SSE ordering test, deletion test (TS-6), no-content-in-logs test, **contract test** (§10.1), README with run and integration steps | `uv run pytest` green; contract test green |

### 10.1 Contract test — how we know the frontend will just work
- [x] Golden JSON for every response type, checked key by key against the fields in `types.ts` (camelCase, nullability, enum values).
- [x] A recorded SSE stream for each turn kind (ask, refusal, summary, draft, error, interrupted) is fed through the frontend's own `parseSseChunk` (`frontend/src/api/sse.ts`) in a small vitest run, so the real parser is the judge, not a Python imitation of it.
- [x] Optional: generate TS types from `openapi.json` with `openapi-typescript` and type-check them against `types.ts` — catches drift whenever either side changes.

### 10.2 Integration later (not part of this phase — listed so nothing surprises us)
In `frontend/`: set `VITE_USE_MOCKS=false` and add a Vite dev proxy `/api → http://localhost:8000` (one block in `vite.config.ts`). Nothing else changes. The backend README will carry the exact steps.

## 11. Decisions — my recommended default is first; I will proceed with it unless you say otherwise

1. **Ingestion depth now** — light real parsing (pypdf / python-docx / txt, low-text pages flagged, no OCR, no embeddings) **(recommended)**, versus adding Tesseract OCR now (needs a system install on Windows). Layout parsing, OCR and Qdrant arrive with the ingestion and AI lanes.
2. **Job queue** — in-process asyncio worker over a DB job table **(recommended: no Docker or Redis on this machine)**, versus Celery + Redis as drawn in the diagram. The `JobQueue` interface makes the swap a one-file change.
3. **Stub answers** — lexical search over *real uploaded text*, producing extractive cited answers **(recommended: genuinely end to end)**, versus replaying the frontend mock's canned answers (looks nicer, but only for the 7 fixture documents).
4. **Error codes** — keep the frontend's exact `ErrorCode` union and use `unknown` for 401 / 404 / 409 / 422 **(recommended for zero frontend change)**, versus adding `unauthorized`, `not_found`, `conflict`, `validation_error` (one-line `types.ts` change at integration).
5. **Frontend connection** — Vite dev proxy, so cookies are same-origin **(recommended)**, versus CORS with credentials to a separate origin.
6. **Encryption scope** — encrypt the uploaded files at rest now; leave extracted text in plain SQLite and note SQLCipher for M6 **(recommended)**, versus encrypting page text too (it complicates FTS).
7. **Location** — a `backend/` folder beside `frontend/` in this repo **(recommended)**.

## 12. As built — where the implementation differs from this plan

1. **"Nothing to search" is a refusal, not a 409/422.** The mock and the UI treat "no ready documents in scope", "no draft sources" and "a case brief with no opinion among the sources" as refusal cards, so the backend streams a `refusal` for these (TS-3) instead of rejecting the request before the stream.
2. **Fully scanned PDFs fail with an actionable message** ("No readable text was found … run OCR in Acrobat"). Pages with almost no text are flagged `lowOcr` (confidence 0), shown in the viewer, and kept out of search. That is how the open question in BRD §16 (4) is answered until OCR exists.
3. **Stub usage reports `costUsd: 0`.** Token counts are estimates and no model is called. Real cost arrives with the AI layer.
4. **Fewer files than §9 sketched.** The ORM lives in `app/db/models.py` and the API models in `app/schemas/models.py`, each a single module mirroring `types.ts` section by section. The stub is split into `text`, `retrieval`, `templates` and `orchestrator` modules.
5. **The size-limit message uses the configured limit**, e.g. "File is 61.3 MB; the limit is 50 MB."
6. **`/api/dev/reset` empties the workspace but does not reseed.** Run `uv run python -m scripts.seed_demo` for the demo data: the frontend mock's 7 documents (exported once into `backend/scripts/seed_data/fixtures.json`) and 4 conversations generated through the stub.
7. **The contract test needs no frontend change.** The script that runs the frontend's real `parseSseChunk` lives in `backend/tests/contract/` and is executed with the frontend's own `vite-node`.
8. **The exported OpenAPI** is at `docs/api/openapi.json` (20 paths, dev routes excluded).

Verified beyond the test suite: a live uvicorn server streamed a full answer, and a `curl` cut off mid-answer left the message `incomplete` with its partial text. The server log contained no document text and no errors.
