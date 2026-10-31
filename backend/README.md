# Legal Lens — Backend (FastAPI)

Milestone **M3** of the BRD: real sign-in, document upload and parsing, the conversation DB (SQLite), the chat turn streamed over SSE, citations that resolve to real text, feedback, usage, traces and audit. The plan and its status live in [`../BACKEND-TODO.md`](../BACKEND-TODO.md).

The AI layer is **not** here. A **stub orchestrator** sits behind the `answer()` / `summarize()` / `draft()` interface ([`app/orchestrator/interface.py`](app/orchestrator/interface.py)). It searches the documents you upload with SQLite full-text search and answers *extractively*: it quotes the most relevant sentences and cites each one. So upload → ask → click a citation works end to end today. The LangChain orchestrator will replace the stub without any API change.

## Run it

Requires [uv](https://docs.astral.sh/uv/). Python 3.13 is picked automatically.

```bash
cd backend
uv sync                                   # install
cp .env.example .env                      # optional: every setting has a dev default
uv run python -m scripts.seed_demo        # optional: the 7 demo documents + 4 sample conversations
uv run uvicorn app.main:app --reload --port 8000
```

- Swagger UI: <http://localhost:8000/api/docs>
- Sign in: `dana@whitfieldlaw.com` / `legallens` (set by `LL_USER_EMAIL` / `LL_USER_PASSWORD`)
- Data (SQLite DB, encrypted files, dev encryption key) goes to `./data`. Delete that folder to start over, or run `seed_demo --reset`.

Migrations run automatically at startup. To run them by hand: `uv run alembic upgrade head`.

## Connect the frontend

The frontend keeps working against its mocks until you switch it over. When you're ready to integrate:

1. In `frontend/.env`: `VITE_USE_MOCKS=false` and leave `VITE_API_BASE_URL` empty.
2. In `frontend/vite.config.ts`, add a dev proxy so the session cookie stays same-origin:
   ```ts
   server: { port: 5173, proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: false } } },
   ```
3. Start both: `uvicorn` as above, and `npm run dev` in `frontend/`.

To serve the frontend from a different origin instead, set `LL_CORS_ORIGINS=["http://localhost:5173"]` and `VITE_API_BASE_URL=http://localhost:8000`.

**Seeing every UI state against the real backend.** The frontend's ScenarioSwitcher drives the mock only. Its backend twin is `PUT /api/dev/scenario` (dev and test only):

```bash
# next answer fails with "AI provider unavailable" (excerpts still shown); also: refusal, rate_limited, timeout, interrupted
curl -b cookies.txt -X PUT localhost:8000/api/dev/scenario -H 'Content-Type: application/json' -d '{"nextReply":"llm_unavailable"}'
# next upload fails at parsing; streaming speed fast | normal | slow
curl -b cookies.txt -X PUT localhost:8000/api/dev/scenario -H 'Content-Type: application/json' -d '{"nextUploadFails":true,"speed":"slow"}'
```

## API at a glance

The contract mirrors `frontend/src/api/types.ts` (camelCase JSON). The exported schema is in [`docs/api/openapi.json`](../docs/api/openapi.json); regenerate it with `uv run python -m scripts.export_openapi`.

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/login` · `POST /api/auth/logout` · `GET /api/auth/me` |
| Conversations | `GET/POST /api/conversations` (POST = new chat) · `GET/PATCH/DELETE /api/conversations/{id}` · `GET /api/conversations/{id}/messages` |
| Chat turn (SSE) | `POST /api/conversations/{id}/messages` · explicit modes: `POST /api/ask`, `/api/summarize`, `/api/draft` |
| Documents | `GET/POST/DELETE /api/documents` · `GET/PATCH/DELETE /api/documents/{id}` · `…/{id}/status` · `…/{id}/pages/{n}` · `…/{id}/file` |
| Trust & ops | `GET /api/spans/{spanId}` · `POST /api/feedback` · `GET /api/traces/{traceId}` · `GET /api/usage` · `GET /api/health`, `/api/health/ready` |

**Stream order:** `meta` → `stage`… → `excerpt`… → `refusal`? → (`citation`… `summary`)? → `draft`? → (`token` | `citation`)… → `usage` → `done` | `error`. Each citation arrives before the first token that carries its `[n]` marker. A stream with no terminal event is an interrupted answer. Stop and disconnect are saved as `incomplete`, with the partial text kept.

**Errors** are always `{ code, message, retryAfterSec? }`. Errors found before the stream opens (404, 422, 429) come back as plain JSON, not SSE.

## How it fits together

```
app/
  main.py            app factory; lifespan runs migrations, seeds the user, starts the ingestion worker
  api/routes/        thin HTTP layer: auth, conversations (+ chat turn, feedback), modes, documents, ops, dev
  services/          chat_turn (turn lifecycle + citation guard), conversations, documents (upload, hard delete),
                     spans, auth, audit, ops (traces, usage), scenario (dev switches)
  ingestion/         validate → encrypted blob store → in-process job queue → parsers (pypdf, python-docx, txt)
                     → classifier → FTS5 page index
  orchestrator/      interface.py (the only door to the AI layer) · stub/ (router, retrieval, summary templates, drafts)
  db/                SQLAlchemy models, async engine, Alembic runner
  schemas/           Pydantic models mirroring types.ts; SSE event types
```

Notes on what to expect:

- **Ingestion** runs on asyncio tasks in the API process (3 at a time), reading the `ingestion_jobs` table, so unfinished jobs resume after a restart. Celery + Redis can replace it behind the `JobQueue` protocol.
- **Scans:** PDFs are read from their text layer. Pages with almost no text are flagged `lowOcr`, shown in the viewer, and left out of search. A PDF with no readable page fails with a message suggesting OCR. Layout-aware parsing and OCR come with the AI layer's ingestion lane.
- **Encryption:** uploaded files are encrypted at rest (Fernet). Extracted page text sits in plain SQLite for now (SQLCipher is planned for M6).
- **Citation guard:** every citation is checked against stored page text before it is streamed or saved. One that doesn't match exactly is dropped.
- **Hard delete** removes the file, pages, search rows, chunk metadata and jobs. A tombstone stays in the audit log. Old answers keep their quoted text, but their spans stop resolving.
- **Demo documents** from `seed_demo` have page text but no original file, so `GET …/file` returns 404 for them.

## Develop

```bash
uv run pytest            # 44 tests: endpoints, SSE order, scenarios, disconnect, deletion, no-content-in-logs, contract
uv run ruff check . && uv run ruff format --check .
uv run mypy              # strict, on app/
```

`tests/test_contract.py` checks every response against the interfaces in `frontend/src/api/types.ts`. It also runs recorded streams through the frontend's own SSE parser using `vite-node`. It skips itself if `frontend/` or Node isn't available.
