# Legal Lens — Frontend Implementation Plan (UI only, mock data)

**Status:** approved 2026-10-04 · P0–P7 implemented in `frontend/` · P8: unit tests done (30 passing); Playwright smoke test and axe audit still to do · scope = milestone **M2** of the BRD (§10) — the full UI, built against mock data, with no backend, orchestration or AI layer.
**Sources:** `docs/LegalLens-BRD-PRD-FRD.md` (FR / NFR / TS numbers below refer to it) · `docs/architecture/legallens-technical-flow.excalidraw` (endpoint list and SSE event types).

---

## 1. What we are building, in one paragraph

A light, calm, professional chat workspace for attorneys. It feels familiar to anyone who has used ChatGPT or Claude: a sidebar of past conversations, a centred thread, and a prompt bar at the bottom. It differs from them in one way that drives most of the design: **every answer must be verifiable in seconds**. So the layout has a third region — a **Sources panel** on the right that opens when you click a citation and shows the exact highlighted passage in the source document. Refusals ("not in your documents") look like a normal, successful answer, not an error. Drafts are permanently marked as unreviewed AI output.

## 2. Design direction

**Inspiration, and what we take from each**
| Product | What we borrow |
|---|---|
| Claude | Warm off-white canvas, generous whitespace, side panel that slides in beside the chat (our Sources panel) |
| ChatGPT | Sidebar grouped by date (Today / Yesterday / Previous 7 days / Older), hover actions on threads, compact prompt bar with chips |
| Perplexity | Numbered inline citation chips `[1]` with a source strip under each answer |
| Harvey / CoCounsel (legal AI) | Serif type for document and draft text, sober colour, explicit "AI draft" marking |
| Linear / Notion | Command palette (Ctrl/Cmd+K), crisp keyboard support, quiet UI chrome |

**Theme — light only for v1** (you asked for nothing dark). Colours are defined as CSS tokens, so a dark theme can be added later without touching components.

| Token | Value | Use |
|---|---|---|
| `--bg` | `#FAFAF8` warm off-white | App canvas |
| `--surface` | `#FFFFFF` | Cards, prompt bar, panels |
| `--sidebar` | `#F4F3EF` | Sidebar background |
| `--border` | `#E6E4DE` | Hairlines |
| `--text` | `#1C1B19` | Body text |
| `--text-muted` | `#6B6862` | Secondary text |
| `--primary` | `#1F3A5F` deep navy | Primary buttons, active states, links |
| `--primary-soft` | `#E8EEF6` | Selected thread, active chip |
| `--accent` | `#A07A2C` muted brass | Sparing: logo mark, draft badge |
| `--highlight` | `#FFF1C2` | Cited span highlight in the source viewer |
| `--success` / `--warning` / `--danger` | `#2F7D4F` / `#B7791F` / `#B42318` | Status pills, errors |

All text/background pairs checked against **WCAG 2.1 AA** (NFR-13).

**Type:** *Inter* for UI · *Source Serif 4* for answers, drafts and document text (reads like a legal document) · *JetBrains Mono* for IDs and trace details only.

**Feel:** 8 px spacing grid, 10–12 px radii, soft single-layer shadows, 150–200 ms transitions, and nothing that animates unless it carries meaning (streaming cursor, upload progress).

## 3. Technology choices

| Concern | Choice | Why |
|---|---|---|
| Framework | React 18 + Vite + TypeScript (strict) | Fixed by the BRD |
| Styling | Tailwind CSS driven by the CSS tokens above | Fast, consistent, no one-off colours |
| Accessible primitives | Radix UI (dialog, dropdown, popover, tooltip, tabs) | Keyboard and screen-reader behaviour handled correctly (NFR-13) |
| Icons | lucide-react | Clean, consistent line icons |
| Routing | React Router | `/c/:id`, `/library`, … |
| Server state | TanStack Query | Caching, refetch and polling (upload status) — same code works against the real API later |
| UI state | Zustand | Sidebar open/closed, Sources panel, composer mode |
| Markdown | react-markdown + remark-gfm | Rendering answers and drafts |
| **Mocking** | **MSW (Mock Service Worker)** | Intercepts real `fetch` calls to the real endpoint paths, including **streamed SSE** responses. When the backend is ready we turn MSW off and change nothing else. |
| Tests | Vitest + Testing Library; Playwright smoke test | |

**The key decision:** the UI talks to the API exactly as the architecture diagram defines it (`/api/conversations`, `/api/conversations/{id}/messages` as SSE, `/api/documents`, `/api/spans/{id}`, `/api/feedback`, `/api/auth/*`). MSW answers those calls with realistic mock data. This is milestone M0's "API contract first" idea applied from the frontend side.

## 4. Screens and layout

```
┌────────────┬───────────────────────────────────────┬──────────────────┐
│  SIDEBAR   │              CHAT THREAD              │  SOURCES PANEL   │
│ + New chat │   (max-width ~760px, centred)          │  (slides in on   │
│ 🔍 Search  │                                       │  citation click) │
│ Pinned     │   You: What are the termination…      │  Acme MSA · p.14 │
│ Today      │   Legal Lens: Either party may… [1][2] │  ┌────────────┐ │
│ Yesterday  │   Sources: [1] Acme MSA p.14  [2] …   │  │ …highlight…│ │
│ Prev 7 days│   👍 👎  Copy  Searched: Workspace     │  └────────────┘ │
│ ────────── │                                       │  Excerpts list   │
│ 📁 Library │ ┌───────────────────────────────────┐ │                  │
│ 6 docs ●   │ │ Ask anything about your documents…│ │                  │
│ 👤 Dana    │ │ [Auto|Ask|Summary|Draft] [Scope▾] ⏎│ │                  │
└────────────┴─┴───────────────────────────────────┴─┴──────────────────┘
```

| Route | Screen |
|---|---|
| `/login` | Sign-in (email + password, mocked) — FR-27 |
| `/` | New chat: greeting, suggested prompts per mode, "upload your first documents" state when the library is empty |
| `/c/:conversationId` | Conversation thread |
| `/library` | Document library (table + upload drop zone) |
| `/library/:documentId` | Document viewer (full page) |
| `/settings` | Profile, data-handling statement (NFR-10), delete workspace (FR-26) |

**Responsive:** ≥1280 px three columns · 768–1279 px Sources panel overlays the chat · <768 px sidebar becomes a drawer and Sources a full-screen sheet.

## 5. Feature checklist (the nuanced parts)

### 5.1 Sidebar
- [ ] "New chat" button (calls `POST /api/conversations`, the NCC endpoint)
- [ ] Search conversations (Ctrl/Cmd+K opens a command palette: search threads, jump to library, new chat)
- [ ] Threads grouped Pinned / Today / Yesterday / Previous 7 days / Older; title + relative time
- [ ] Hover menu per thread: rename (inline edit), pin/unpin, delete (with confirm)
- [ ] Mode icon on each thread (Ask / Summary / Draft) so drafts are easy to find again
- [ ] Footer: Library link with document count and an index-health dot (all ready / some processing / some failed)
- [ ] User menu: settings, sign out
- [ ] Collapsible to an icon rail; state remembered per browser

### 5.2 Prompt bar (composer)
- [ ] Auto-growing textarea; **Enter** sends, **Shift+Enter** new line (ChatGPT/Claude convention)
- [ ] Mode chips: **Auto · Ask · Summary · Draft** (Auto = backend intent router decides) — FR-8
- [ ] Scope picker: Whole workspace / Selected documents (multi-select with search) / Current document; defaults to workspace — FR-8, FR-9
- [ ] Draft mode opens a **parameters drawer**: draft type (memo / case brief), question presented, audience, position to argue, tone, source documents (required) — FR-18, FR-19
- [ ] Summary mode asks which document (single select); shows its detected type
- [ ] Attach button → upload from the composer (goes to the library, appears in scope when ready)
- [ ] Send turns into **Stop** while streaming
- [ ] Disabled with an explanation when no documents are ready yet
- [ ] Footer line: "Legal Lens answers only from your documents. It is a work-product aid, not legal advice." — TS-5

### 5.3 Chat thread and messages
- [ ] Streaming render token-by-token with a soft cursor; auto-scroll that stops when the user scrolls up, plus a "jump to latest" button — FR-10
- [ ] Inline citation chips `[1]` — hover shows a preview card (document, page, quoted snippet); click opens the Sources panel at that span — FR-11, FR-13
- [ ] **Sources strip** under each answer: the retrieved excerpts, visible without any click — FR-12
- [ ] Response meta row: "Searched: Whole workspace (6 documents)" · detected intent in Auto mode ("Answered as Ask") — FR-9
- [ ] Actions: copy, export Markdown, retry, thumbs up / down — FR-24, FR-25
- [ ] Thumbs-down opens a small reason picker (wrong citation · not supported by source · missed something · other + free text) — FR-25
- [ ] **Refusal card** — a calm, neutral (not red) card: "This isn't answered in your documents," the scope searched, and suggestions (widen scope, upload more, rephrase) — FR-14, TS-3
- [ ] **Interrupted stream** marked "Incomplete — the response was interrupted," with Retry — NFR-7
- [ ] **Actionable error cards**, each naming a next step: AI service unavailable (excerpts still shown — NFR-6), rate limited (with retry countdown), timeout, parse failure — FR-28

### 5.4 Summary result
- [ ] Structured card that follows the template for the document type (contract / opinion / pleading — BRD §9)
- [ ] Each field shows its value plus citation chips; empty fields say *"Not addressed in this document"* in muted italics — FR-16
- [ ] Off-market terms flagged with a warning pill
- [ ] **Coverage ledger**: "Covered pages 1–212 of 212" or "3 pages could not be read (OCR)" — FR-17
- [ ] Collapse/expand sections; copy / export Markdown

### 5.5 Draft result
- [ ] Persistent **"UNREVIEWED AI DRAFT — attorney review required"** banner, which cannot be dismissed — FR-23
- [ ] Serif, document-like rendering in conventional structure (Memo: Question Presented → Short Answer → Statement of Facts → Discussion → Conclusion; Brief: Posture → Facts → Issue → Holding → Reasoning → Disposition) — FR-18
- [ ] Citations on every factual assertion; source manifest at the end — FR-20
- [ ] Export Markdown and copy to clipboard, both carrying the draft marking — FR-24
- [ ] "Open in side panel" for a wider reading view

### 5.6 Sources panel (citation and excerpt viewer)
- [ ] Opens beside the chat on citation click; resizable; closes with Esc
- [ ] Tabs: **Cited passage** (document page text, scrolled to and highlighting the exact span) · **All excerpts** for that answer
- [ ] Page navigation, "open full document" link
- [ ] Low-OCR-confidence warning on affected pages — DR-1
- [ ] Keyboard navigable; the highlighted span is announced to screen readers — NFR-13
- [ ] (Mock: page text rendered as text. Real PDF page images via pdf.js come later with the backend.)

### 5.7 Document library
- [ ] Drag-and-drop zone + file picker, multiple files at once; accepts PDF, DOCX, TXT — FR-1
- [ ] Client-side rejection over 50 MB, naming the limit and the actual size; page limit (500) reported back by the mock — FR-2
- [ ] Per-file status pills that progress live: queued → parsing → indexing → ready / failed; one failure never blocks the others — FR-3
- [ ] Table: name, type, pages, status, uploaded date; sortable and filterable (type, status, search) — FR-6
- [ ] Type shown as a pill with an override dropdown (contract / opinion / pleading / other) — FR-5
- [ ] Row actions: open, ask about this document (starts a chat scoped to it), summarise, delete
- [ ] Delete confirmation that states exactly what is removed (file, text, index) — FR-26
- [ ] Empty state with a short explanation of what Legal Lens does with uploads

### 5.8 Auth, settings, global
- [ ] Sign-in page (mock: any email + password works; a "wrong password" path for the error state) — FR-27
- [ ] Settings: profile, data-handling statement (zero-retention, encryption — NFR-9/10), delete entire workspace with typed confirmation
- [ ] Toasts for background events (upload finished, document failed)
- [ ] Skeleton loaders (no layout shift), focus rings everywhere, skip-to-content link
- [ ] Keyboard shortcuts sheet (`?`): new chat, search, toggle sidebar, focus composer, close panel

## 6. Mock data and the mock API

**Fixtures** (realistic, all fictional or public-domain-style):
- 7 documents: *Acme–Northwind Master Services Agreement* (contract, 42 pp, ready) · *Helix SaaS Subscription Agreement* (contract, ready) · *Smith v. Jones* opinion (ready) · *Harbor Freight Co. v. Delmar* opinion (ready) · *Complaint — Reyes v. Coastal Logistics* (pleading, ready) · a scanned exhibit (ready with low-OCR warning on 3 pages) · one *failed* file (password-protected PDF)
- 8 conversations covering every message kind: cited Ask answer, refusal, contract summary, opinion summary, memo draft, case-brief draft, an interrupted answer, an error
- Page text for the cited pages, so highlighting works for real

**MSW handlers:** one per endpoint in the architecture diagram. The chat endpoint streams SSE events `token · citation · excerpt · refusal · usage · done · error` with realistic timing (~400 ms to first token, ~25 ms per token). Uploads move through statuses on a timer.

**Dev scenario switcher** (development builds only; small floating panel): force the next reply to be *normal / refusal / LLM unavailable / rate limited / timeout / interrupted*, toggle an empty library, change stream speed. This lets you and any reviewer see every state without editing code.

## 7. Folder structure (skeleton to create after approval)

```
frontend/
  index.html · package.json · vite.config.ts · tailwind.config.ts · tsconfig.json
  public/mockServiceWorker.js
  src/
    main.tsx · App.tsx · routes.tsx
    styles/        tokens.css · globals.css
    api/           client.ts · sse.ts (POST + stream parser) · types.ts (API contract types) · queries.ts
    mocks/         browser.ts · handlers/{conversations,messages,documents,spans,feedback,auth}.ts
                   fixtures/{documents,conversations,pages,users}.ts · scenario.ts
    stores/        ui.ts · composer.ts
    components/ui/ Button · IconButton · Chip · Pill · Tooltip · Dialog · Dropdown · Popover
                   Tabs · Toast · Skeleton · Kbd · EmptyState
    features/
      auth/        LoginPage
      layout/      AppShell · TopBar · ResizablePanel
      sidebar/     Sidebar · ConversationList · ConversationItem · SidebarFooter · CommandPalette
      composer/    Composer · ModeChips · ScopePicker · DraftParamsDrawer · SummaryDocPicker
      chat/        ChatPage · NewChatPage · MessageList · UserMessage · AssistantMessage
                   StreamingText · CitationChip · CitationPreview · SourcesStrip · MessageMeta
                   MessageActions · FeedbackPopover · RefusalCard · ErrorCard · IncompleteNotice
      summary/     SummaryCard · SummaryField · CoverageLedger
      draft/       DraftView · DraftBanner · SourceManifest · exportMarkdown.ts
      sources/     SourcesPanel · DocumentPageView · SpanHighlight · ExcerptList
      library/     LibraryPage · UploadDropzone · DocumentTable · StatusPill · TypeSelect · DeleteDialog
      settings/    SettingsPage
      dev/         ScenarioSwitcher
    hooks/         useStreamingMessage · useAutoScroll · useHotkeys · useUploadQueue
    lib/           format.ts · dates.ts · cn.ts
```

## 8. Build order (each phase ends with something you can click through)

| Phase | Deliverable | Done when |
|---|---|---|
| **P0** Setup | Vite + TS + Tailwind + tokens + fonts + Radix + MSW wired; lint/format | App boots with the empty shell; MSW logs intercepted calls |
| **P1** Shell | AppShell, Sidebar (static list), routes, login page | Navigate between all screens |
| **P2** Library | Upload, live status, table, type override, delete | Upload 5 files, one fails, others reach *ready* |
| **P3** Chat core | Composer, mode chips, scope picker, SSE streaming, stop, auto-scroll | A question streams a full answer from the mock |
| **P4** Trust UI | Citation chips + preview, sources strip, **Sources panel with highlight**, refusal, error, incomplete states | Click `[1]` → panel opens with the passage highlighted |
| **P5** Summary & Draft | Summary card + coverage; draft params drawer, draft view, banner, export | Summary and memo flows complete end to end |
| **P6** Sidebar depth | Grouping, rename/pin/delete, command palette, feedback popover, toasts | All thread actions work |
| **P7** Polish | Responsive layouts, keyboard shortcuts, a11y pass (axe), empty/loading states, scenario switcher | No axe violations; usable at 375 px wide |
| **P8** Tests | Unit tests for SSE parser, citation mapping, export; Playwright smoke (login → upload → ask → click citation) | `npm test` and the smoke test pass |

## 9. Deliberately not in this phase
Real backend calls · real PDF rendering (pdf.js) · real authentication · dark theme · `.docx` export (deferred by the BRD) · multiple users or roles.

## 10. Decisions I need from you
1. **Mocking approach:** MSW against the real endpoint paths (recommended, zero rework later) — or simpler in-app fake functions?
2. **Styling:** Tailwind + Radix (recommended) — or plain CSS Modules?
3. **Send key:** Enter to send, Shift+Enter for a new line (recommended, matches ChatGPT/Claude) — or Cmd/Ctrl+Enter as in the architecture diagram?
4. **Palette:** deep navy + warm off-white + a little brass, as above — happy with that, or would you prefer something else (e.g. a teal or plain neutral palette)?
