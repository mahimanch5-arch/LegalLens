/**
 * API contract types — the frontend's view of the OpenAPI schema (BRD §10, M0).
 * Endpoint paths and SSE event names follow docs/architecture/legallens-technical-flow.excalidraw.
 * The mock layer (src/mocks) and the real backend must both satisfy these shapes.
 */

// ---------- Documents ----------

export type DocType = 'contract' | 'opinion' | 'pleading' | 'other';
export type DocStatus = 'queued' | 'parsing' | 'indexing' | 'ready' | 'failed';

export interface LegalDocument {
  id: string;
  name: string;
  mimeType: string;
  sizeBytes: number;
  /** Unknown until parsing finishes. */
  pages: number | null;
  type: DocType;
  /** Classifier confidence 0–1 (FR-5). */
  typeConfidence: number;
  /** True when the attorney overrode the detected type. */
  typeOverridden: boolean;
  status: DocStatus;
  /** 0–100 while queued/parsing/indexing. */
  progress: number;
  /** Human-readable failure reason, naming the next action (FR-28). */
  error?: string;
  /** Pages with low OCR confidence (DR-1). */
  lowOcrPages: number[];
  uploadedAt: string;
}

export interface DocumentPage {
  documentId: string;
  page: number;
  text: string;
  ocrConfidence: number;
  lowOcr: boolean;
}

export const UPLOAD_LIMITS = {
  maxBytes: 50 * 1024 * 1024,
  maxPages: 500,
  accept: ['.pdf', '.docx', '.txt'],
  mimeTypes: [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
  ],
} as const;

// ---------- Conversations & messages ----------

/** The mode chip the user picked. `auto` lets the backend intent router decide. */
export type Mode = 'auto' | 'ask' | 'summary' | 'draft';
/** What the backend actually did. */
export type Intent = 'ask' | 'summary' | 'draft';

export type Scope = { kind: 'workspace' } | { kind: 'documents'; documentIds: string[] };

export interface ScopeUsed {
  kind: Scope['kind'];
  documentIds: string[];
  /** e.g. "Whole workspace (6 documents)" — always shown on the response (FR-9). */
  label: string;
}

export type DraftType = 'memo' | 'brief';
export type DraftTone = 'neutral' | 'persuasive' | 'formal';

export interface DraftParams {
  draftType: DraftType;
  questionPresented: string;
  audience: string;
  position: string;
  tone: DraftTone;
  sourceDocumentIds: string[];
}

export interface Conversation {
  id: string;
  title: string;
  /** Intent of the most recent assistant turn — drives the sidebar icon. */
  lastIntent: Intent | null;
  pinned: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Citation {
  /** 1-based marker number as it appears in the text, e.g. [2]. */
  n: number;
  spanId: string;
  documentId: string;
  documentName: string;
  page: number;
  charStart: number;
  charEnd: number;
  /** The exact cited text. */
  quote: string;
  /** Clause or section label, when known (FR-4). */
  section?: string;
}

export interface Excerpt {
  spanId: string;
  documentId: string;
  documentName: string;
  page: number;
  section?: string;
  text: string;
  /** Reranker score 0–1. */
  score: number;
}

export interface Refusal {
  reason: string;
  scopeLabel: string;
  suggestions: string[];
}

export type ErrorCode = 'llm_unavailable' | 'rate_limited' | 'timeout' | 'parse_failure' | 'unknown';

export interface ApiErrorBody {
  code: ErrorCode;
  message: string;
  /** Seconds until a retry is sensible (rate_limited). */
  retryAfterSec?: number;
}

export interface SummaryField {
  label: string;
  /** null → "Not addressed in this document" (FR-16). */
  value: string | null;
  /** Citation marker numbers supporting the value. */
  citations: number[];
  flag?: string;
}

export interface SummarySection {
  title: string;
  fields: SummaryField[];
}

export interface SummaryResult {
  documentId: string;
  documentName: string;
  docType: DocType;
  sections: SummarySection[];
  coverage: {
    pagesTotal: number;
    pagesCovered: number;
    skippedPages: number[];
    note?: string;
  };
}

export interface DraftMeta {
  draftType: DraftType;
  title: string;
  params: DraftParams;
  sources: { documentId: string; documentName: string }[];
}

export interface Usage {
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
  latencyMs: number;
}

export type Feedback = { rating: 'up' | 'down'; reason?: string; comment?: string };

export interface UserMessage {
  id: string;
  role: 'user';
  text: string;
  mode: Mode;
  scope: Scope;
  draftParams?: DraftParams;
  summaryDocumentId?: string;
  createdAt: string;
}

export type AssistantStatus = 'streaming' | 'complete' | 'incomplete' | 'error';

export interface AssistantMessage {
  id: string;
  role: 'assistant';
  createdAt: string;
  status: AssistantStatus;
  intent: Intent | null;
  /** Progress line shown before the first token, e.g. "Searching 6 documents…". */
  stage?: string;
  scopeUsed?: ScopeUsed;
  /** Markdown with [n] citation markers. For drafts this is the draft body. */
  answerMd: string;
  citations: Citation[];
  excerpts: Excerpt[];
  refusal?: Refusal;
  summary?: SummaryResult;
  draft?: DraftMeta;
  error?: ApiErrorBody;
  usage?: Usage;
  feedback?: Feedback;
  traceId?: string;
  modelVersion?: string;
  promptVersion?: string;
}

export type Message = UserMessage | AssistantMessage;

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface Page<T> {
  items: T[];
  nextCursor: string | null;
}

// ---------- Chat turn request & SSE events ----------

export interface SendMessageRequest {
  text: string;
  mode: Mode;
  scope: Scope;
  draftParams?: DraftParams;
  summaryDocumentId?: string;
}

/**
 * Server-sent events on POST /api/conversations/{id}/messages.
 * A stream that ends without `done` or `error` is treated as interrupted (NFR-7).
 */
export type StreamEvent =
  | { event: 'meta'; data: { userMessageId: string; messageId: string; intent: Intent; scopeUsed: ScopeUsed; traceId: string } }
  | { event: 'stage'; data: { label: string } }
  | { event: 'token'; data: { text: string } }
  | { event: 'citation'; data: Citation }
  | { event: 'excerpt'; data: Excerpt }
  | { event: 'summary'; data: SummaryResult }
  | { event: 'draft'; data: DraftMeta }
  | { event: 'refusal'; data: Refusal }
  | { event: 'usage'; data: Usage }
  | { event: 'done'; data: { modelVersion: string; promptVersion: string } }
  | { event: 'error'; data: ApiErrorBody };

// ---------- Auth ----------

export interface User {
  id: string;
  name: string;
  email: string;
  initials: string;
}

export interface WorkspaceStats {
  documents: number;
  ready: number;
  processing: number;
  failed: number;
}
