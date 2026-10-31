# LegalLens Frontend-Backend Integration Plan

**Status:** Planning phase (awaiting approval to implement)  
**Created:** 2026-10-13  
**Scope:** Connect frontend (React + Vite + MSW mocks) to backend (FastAPI + SQLite)

---

## Overview

The frontend and backend have been built in parallel against a shared API contract (`frontend/src/api/types.ts`). This plan brings them together by:

1. Starting the backend server (FastAPI on `localhost:8000`)
2. Turning off frontend mocks (`VITE_USE_MOCKS=false`)
3. Routing frontend API calls through the Vite proxy to the backend
4. Testing end-to-end flows

**Key insight:** The frontend already has the proxy configured in `vite.config.ts` and env variables are ready. We mainly need to start the backend and verify integration.

---

## Phase 1: Backend Setup

### 1.1 Prepare the backend environment
- [ ] Navigate to `backend/` directory
- [ ] Check that `.env` file exists; if not, copy from `.env.example`:
  ```bash
  cp .env.example .env
  ```
- [ ] Review `.env` settings:
  - `LL_ENV=dev` (enables `/api/dev/*` endpoints for testing)
  - `LL_USER_EMAIL=dana@whitfieldlaw.com` / `LL_USER_PASSWORD=legallens` (test user)
  - `LL_DATA_DIR=./data` (SQLite DB location)
  - Other settings can stay as defaults

### 1.2 Initialize database & seed data
- [ ] Run database migrations:
  ```bash
  uv run alembic upgrade head
  ```
  Expected: database created in `backend/data/legallens.db` (or configured `LL_DATA_DIR`)

- [ ] (Optional) Seed demo data (the 7 fixture documents from the frontend mock):
  ```bash
  uv run python -m scripts.seed_demo
  ```
  Expected: 6 documents + 4 conversations created, ready to test with

### 1.3 Verify backend is ready
- [ ] Run linting & type checks:
  ```bash
  uv run ruff check app/
  uv run mypy app/
  ```
  Expected: No errors

- [ ] Run tests:
  ```bash
  uv run pytest
  ```
  Expected: All tests pass (currently 44+ passing)

---

## Phase 2: Frontend Setup

### 2.1 Environment configuration
- [ ] Verify `frontend/.env` has:
  ```
  VITE_USE_MOCKS=false
  VITE_API_BASE_URL=
  ```
  - `VITE_USE_MOCKS=false` turns off MSW (uses real API)
  - `VITE_API_BASE_URL=` (empty) means use same-origin, routed via Vite proxy

### 2.2 Vite proxy verification
- [ ] Confirm `frontend/vite.config.ts` has:
  ```typescript
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000' },
  }
  ```
  (It should already be there. This means frontend requests to `/api/*` are proxied to the backend.)

### 2.3 Clear any stale state (optional but recommended)
- [ ] Clear browser's IndexedDB / localStorage (optional):
  - Open DevTools → Application → Storage → Clear
  - Or just use an incognito window for fresh testing

---

## Phase 3: Start Services

### 3.1 Start the backend server
- [ ] In `backend/` directory:
  ```bash
  uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```
  Expected output:
  ```
  INFO:     Uvicorn running on http://0.0.0.0:8000
  INFO:     Application startup complete
  ```
- [ ] Verify health endpoint: `curl http://localhost:8000/api/health`
  Expected: `{"status":"ok","version":"..."}`

### 3.2 Start the frontend dev server
- [ ] In `frontend/` directory:
  ```bash
  npm run dev
  ```
  Expected output:
  ```
  VITE v4.x.x  ready in x ms
  ➜  Local:   http://localhost:5173/
  ```

- [ ] Open browser to `http://localhost:5173`

---

## Phase 4: Integration Testing

### 4.1 Smoke tests (basic connectivity)
- [ ] **Login page loads**
  - Navigate to `/login`
  - Page renders without errors
  - No fetch errors in DevTools console

- [ ] **Auth flow**
  - Log in with `dana@whitfieldlaw.com` / `legallens`
  - Verify `ll_session` cookie is set (DevTools → Application → Cookies)
  - Redirects to `/` (home)
  - Verify `GET /api/auth/me` succeeds in Network tab

### 4.2 Core flows (end-to-end)

#### 4.2.1 Document library flow
- [ ] Navigate to `/library`
  - Sidebar shows "📁 Library"
  - If seeded, fixture documents appear in the table
  - If not seeded, empty state with upload zone is visible

- [ ] Upload a test file (if not seeded):
  - Drag a PDF, DOCX, or TXT file into the drop zone
  - Status pill changes: queued → parsing → indexing → ready
  - File appears in table with name, pages, type

- [ ] Verify document parsing worked:
  - Click the document row
  - Document viewer opens, shows page text
  - No "Error" status in the table

#### 4.2.2 Chat flow
- [ ] Navigate to `/` or click "New chat"
  - Sidebar shows "+ New chat" button
  - Main area shows "Ask anything about your documents"
  - Prompt bar at bottom is enabled

- [ ] Ask a question (if documents exist):
  - Type: "What are the termination rights?" (or similar)
  - Mode: "Auto" (default)
  - Scope: "Whole workspace"
  - Press Enter or click Send
  - Expected:
    - Message appears in chat as "You: ..."
    - Loading state appears
    - Answer streams token by token
    - Citations `[1]` appear inline
    - "Sources" strip appears below answer with retrieved excerpts

#### 4.2.3 Citation & sources panel
- [ ] In the chat answer, click a citation chip `[1]`
  - Expected: "Sources" panel slides in on the right
  - Shows the document name and page number
  - Shows the exact highlighted passage
  - Can scroll to see full excerpt

- [ ] Click another citation
  - Panel updates to show that citation's passage

#### 4.2.4 Summary & Draft (if ready)
- [ ] Change mode to "Summary"
  - Scope picker shows "Select document"
  - Choose a document from the dropdown
  - Send
  - Expected: Structured summary card with fields (Key Parties, Effective Date, etc.)

- [ ] Change mode to "Draft"
  - Draft params drawer opens (type, question, audience, etc.)
  - Fill and send
  - Expected: Memo/brief formatted with UNREVIEWED DRAFT banner

#### 4.2.5 Refusal case (optional but good to verify)
- [ ] Ask a question with no ready documents, or outside scope
  - Expected: Refusal card ("This isn't answered in your documents") instead of error

#### 4.2.6 Error handling (optional)
- [ ] Stop a streaming answer mid-way (click "Stop" button)
  - Expected: Answer marked "Incomplete — the response was interrupted"
  - Text that came in is preserved

---

## Phase 5: Debugging & Validation

### 5.1 Network inspection
- [ ] Open DevTools → Network tab
- [ ] Perform an action (login, upload, ask)
- [ ] Verify:
  - Requests go to `http://localhost:5173/api/*` (same-origin, via proxy)
  - Responses are from backend (check response headers, status codes)
  - No CORS errors (since it's same-origin through proxy)
  - Cookies are sent with requests (see `ll_session` in Request headers)

### 5.2 Backend logs
- [ ] In backend terminal, verify logs show:
  - `POST /api/conversations` when a new chat is created
  - `POST /api/documents` when files are uploaded
  - `POST /api/conversations/{id}/messages` with SSE stream for chat turns
  - No 500 errors or stack traces (only 200s, 201s, 204s, 4xx for bad input)

### 5.3 Frontend console
- [ ] In browser console (DevTools → Console):
  - No red errors
  - No "404 /api/*" messages
  - MSW should not be active (no "MSW: [POST /api/...]" messages)
  - If MSW messages appear, `VITE_USE_MOCKS` is still `true`

---

## Phase 6: Rollback (if needed)

### 6.1 Quick rollback to mocks
If the backend integration breaks and you need to revert:

- [ ] Stop the backend server (Ctrl+C)
- [ ] In `frontend/.env`, change:
  ```
  VITE_USE_MOCKS=true
  ```
- [ ] Frontend will auto-reload (Vite HMR) and use MSW again
- [ ] Mocks are fully functional, so the app still works for development

---

## Phase 7: Cleanup & Handoff

### 7.1 Document findings
- [ ] Record any integration issues in this file (§12 below)
- [ ] Note any API contract mismatches (would be caught by the contract test in backend)

### 7.2 Update CI/documentation
- [ ] Update backend `README.md` with the exact commands to start (B0.3):
  ```bash
  uv run uvicorn app.main:app --reload --port 8000
  ```
- [ ] Update frontend `README.md` with integration steps:
  - Ensure `VITE_USE_MOCKS=false`
  - Ensure backend runs on `:8000`
  - `npm run dev` starts the dev server with proxy

### 7.3 Next steps
- [ ] Run the contract test to verify full TS↔Python contract:
  ```bash
  cd backend && uv run pytest tests/contract/
  ```
- [ ] Once integration is solid, consider CI setup (GitHub Actions to run both servers and smoke tests)

---

## Questions & Decisions

**Before we start, clarify:**

1. **Demo data**: Should I seed the 7 fixture documents? (Recommended for testing; they were in the frontend mock.)
2. **Test scope**: Just connectivity, or full end-to-end with all flows (Ask, Summary, Draft, upload, delete)?
3. **Database cleanup**: Should we start with a fresh database, or preserve any existing data?
4. **Performance**: Any concerns about the stub orchestrator's speed (currently ~22ms per token), or is that fine for dev?

---

## Known Blockers / Edge Cases

**None anticipated**, but watching for:
- [ ] CORS issues (shouldn't happen with Vite proxy; if CORS errors appear, check `LL_CORS_ORIGINS` in backend `.env`)
- [ ] Cookie handling (backend sets `ll_session` HttpOnly; should work same-origin)
- [ ] SSE streaming (Vite proxy should pass through `Transfer-Encoding: chunked` correctly)
- [ ] File upload handling (multipart/form-data through proxy)

---

## Checklist for "Ready to Integrate"

- [x] Vite proxy configured (`vite.config.ts`)
- [x] Frontend env variables ready (`.env`)
- [x] Backend env template exists (`.env.example`)
- [x] API contract defined and shared (`frontend/src/api/types.ts`)
- [x] Backend has tests (44+ passing)
- [x] Frontend has MSW guards to switch off

**Status: Ready to implement once you approve.**

---

## Section 12: Integration Log

*To be filled in during Phase 4-5 as we discover issues.*

### Issues found:
(none yet)

### Contract mismatches:
(none expected, but the contract test will verify)

### Decisions made:
(to record during implementation)

