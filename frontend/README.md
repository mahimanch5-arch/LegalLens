# Legal Lens — Frontend

React + Vite + TypeScript UI for Legal Lens (BRD milestone **M2**). It runs fully on mock data: [MSW](https://mswjs.io) intercepts every `/api/*` call in the browser and answers with realistic, *grounded* responses, including token-by-token SSE streaming.

## Run it

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Sign in with any email and a password of 4+ characters. Use the password `wrong` to see the error state.

| Script | What it does |
|---|---|
| `npm run dev` | Dev server with mocks |
| `npm run build` | Typecheck + production build |
| `npm test` | Unit tests (engine grounding, SSE parser, citations, upload validation) |
| `npm run lint` | ESLint |

## Mock data

- **7 fictional documents**: contracts, two opinions, a complaint, a low-OCR scanned exhibit, and one failed upload. Every party, court and case in them is invented.
- **9 seeded conversations** covering a cited answer, a refusal, contract and opinion summaries, a memo, a case brief, an interrupted answer and an AI-unavailable error.
- Data is saved to `localStorage`, so it survives a reload.
- **"Mock data" pill (top right)**:
  - Force the next reply to be a refusal, AI outage, rate limit, timeout or interrupted stream.
  - Change the stream speed.
  - Make the next upload fail.
  - Reset or empty the workspace.

The test in `src/mocks/engine.test.ts` checks that every citation the mock emits resolves to its exact span in the page text. This mirrors the BRD's 100% citation-precision gate.

## Switching to the real backend

Copy `.env.example` to `.env.local` and set:

```
VITE_USE_MOCKS=false
VITE_API_BASE_URL=http://localhost:8000
```

The UI talks only through `src/api/` (`client.ts`, `sse.ts`, `queries.ts`). The backend must satisfy the shapes in `src/api/types.ts`, which follow the endpoints and SSE events in `docs/architecture/legallens-technical-flow.excalidraw`.

## Structure

```
src/
  api/          contract types, fetch client, SSE parser, TanStack Query hooks
  mocks/        MSW handlers, in-browser DB, mock response engine, fixtures
  stores/       Zustand: UI (sidebar, sources panel), composer, toasts
  components/ui buttons, dialogs, menus, tooltips, pills…
  features/
    chat/       thread, streaming, messages, citations, refusal/error states
    composer/   prompt bar, mode chips, scope picker, draft settings
    sources/    citation & excerpt viewer with span highlighting
    summary/    template-driven summary card + coverage ledger
    draft/      draft view, review banner, Markdown export
    library/    upload, status, type override, delete, document reader
    sidebar/    conversation list, command palette
    settings/   data-handling statement, workspace delete
    dev/        mock scenario switcher (dev only)
```
