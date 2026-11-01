/**
 * In-browser mock database behind the MSW handlers. Persisted to localStorage so a demo
 * survives a reload; "Reset demo data" in the dev panel restores the seed.
 */
import type {
  AssistantMessage,
  ConversationDetail,
  DocType,
  DraftParams,
  Feedback,
  LegalDocument,
  Mode,
  Scope,
  SendMessageRequest,
  UserMessage,
} from '@/api/types';
import { DOC_IDS, seedDocuments } from './fixtures/documents';
import { planResponse, titleFrom } from './engine';

const KEY = 'legallens.mockdb.v1';

interface Processing {
  startedAt: number;
  /** Total time to reach `ready`, in ms. */
  durationMs: number;
  failAt?: 'parsing' | 'indexing';
  failMessage?: string;
  finalPages: number;
}

interface DbState {
  signedIn: boolean;
  documents: LegalDocument[];
  processing: Record<string, Processing>;
  conversations: ConversationDetail[];
  feedback: { messageId: string; conversationId: string; feedback: Feedback; at: string }[];
}

let seq = Date.now() % 100000;
export const uid = (prefix: string) => `${prefix}_${(seq++).toString(36)}${Math.random().toString(36).slice(2, 6)}`;

const ago = (days: number, minutes = 0) => new Date(Date.now() - days * 86_400_000 - minutes * 60_000).toISOString();

// ---------- seed ----------

interface SeedTurn {
  text: string;
  mode: Mode;
  scope: Scope;
  draftParams?: DraftParams;
  summaryDocumentId?: string;
  /** Post-process the assistant message to show a non-happy state. */
  outcome?: 'incomplete' | 'llm_unavailable';
}

interface SeedConversation {
  daysAgo: number;
  pinned?: boolean;
  turns: SeedTurn[];
}

const ws: Scope = { kind: 'workspace' };
const only = (...ids: string[]): Scope => ({ kind: 'documents', documentIds: ids });

const SEED: SeedConversation[] = [
  {
    daysAgo: 0,
    pinned: true,
    turns: [
      { text: 'What are the termination rights under the Acme MSA?', mode: 'ask', scope: only(DOC_IDS.acme) },
      { text: 'What about assignment on a change of control?', mode: 'ask', scope: only(DOC_IDS.acme) },
    ],
  },
  { daysAgo: 0, turns: [{ text: 'Does an email count as written notice of breach?', mode: 'auto', scope: ws }] },
  { daysAgo: 1, turns: [{ text: 'Summarize Smith v. Jones Holdings', mode: 'summary', scope: only(DOC_IDS.smith), summaryDocumentId: DOC_IDS.smith }] },
  { daysAgo: 3, turns: [{ text: 'Summarize the Acme–Northwind MSA', mode: 'summary', scope: only(DOC_IDS.acme), summaryDocumentId: DOC_IDS.acme }] },
  {
    daysAgo: 4,
    turns: [
      {
        text: 'Draft a memo: can Acme terminate the MSA for breach using email notice alone?',
        mode: 'draft',
        scope: only(DOC_IDS.acme, DOC_IDS.smith),
        draftParams: {
          draftType: 'memo',
          questionPresented: 'Can Acme terminate the Northwind MSA for breach by giving notice by email alone?',
          audience: 'Supervising partner',
          position: "Acme's email notice of breach was effective",
          tone: 'neutral',
          sourceDocumentIds: [DOC_IDS.acme, DOC_IDS.smith],
        },
      },
    ],
  },
  { daysAgo: 5, turns: [{ text: 'Are there any non-compete restrictions on our employees?', mode: 'ask', scope: ws }] },
  { daysAgo: 9, turns: [{ text: 'Compare the liability caps across our agreements', mode: 'ask', scope: ws, outcome: 'incomplete' }] },
  { daysAgo: 12, turns: [{ text: 'When was Reyes terminated, and when did she first complain?', mode: 'ask', scope: only(DOC_IDS.reyes), outcome: 'llm_unavailable' }] },
  {
    daysAgo: 20,
    turns: [
      {
        text: 'Brief Bayview v. Delmar',
        mode: 'draft',
        scope: only(DOC_IDS.bayview),
        draftParams: { draftType: 'brief', questionPresented: 'Does a negotiated liability cap protect a carrier from its own gross negligence?', audience: 'Litigation team', position: '', tone: 'neutral', sourceDocumentIds: [DOC_IDS.bayview] },
      },
    ],
  },
];

export function buildAssistant(req: SendMessageRequest, docs: LegalDocument[], createdAt: string): AssistantMessage {
  const plan = planResponse(req, docs);
  return {
    id: uid('msg'),
    role: 'assistant',
    createdAt,
    status: 'complete',
    intent: plan.intent,
    scopeUsed: plan.scopeUsed,
    answerMd: plan.answerMd,
    citations: plan.citations,
    excerpts: plan.excerpts,
    refusal: plan.refusal,
    summary: plan.summary,
    draft: plan.draft,
    usage: plan.usage,
    traceId: uid('trace'),
    modelVersion: 'mock-model-2026-09',
    promptVersion: `${plan.intent}-v1.3`,
  };
}

function seedConversations(docs: LegalDocument[]): ConversationDetail[] {
  return SEED.map((c, ci) => {
    const messages: ConversationDetail['messages'] = [];
    let title = '';
    let lastIntent: ConversationDetail['lastIntent'] = null;
    c.turns.forEach((t, ti) => {
      const at = ago(c.daysAgo, (c.turns.length - ti) * 3 + ci * 37);
      const user: UserMessage = { id: uid('msg'), role: 'user', text: t.text, mode: t.mode, scope: t.scope, draftParams: t.draftParams, summaryDocumentId: t.summaryDocumentId, createdAt: at };
      const a = buildAssistant(t, docs, at);
      if (t.outcome === 'incomplete') {
        a.status = 'incomplete';
        a.answerMd = a.answerMd.slice(0, Math.floor(a.answerMd.length * 0.45));
        const used = new Set([...a.answerMd.matchAll(/\[(\d+)\]/g)].map((m) => Number(m[1])));
        a.citations = a.citations.filter((x) => used.has(x.n));
        a.usage = undefined;
      }
      if (t.outcome === 'llm_unavailable') {
        a.status = 'error';
        a.answerMd = '';
        a.citations = [];
        a.usage = undefined;
        a.error = { code: 'llm_unavailable', message: 'The AI model provider did not respond. Your documents were searched and the matching excerpts are shown, but no answer was written.' };
      }
      messages.push(user, a);
      lastIntent = a.intent;
      if (ti === 0) {
        const doc = docs.find((d) => d.id === (a.summary?.documentId ?? ''));
        title = a.draft ? a.draft.title.replace(/^(Memorandum|Case brief) — /, a.draft.draftType === 'memo' ? 'Memo: ' : 'Brief: ') : titleFrom(t.text, a.intent ?? 'ask', doc?.name);
      }
    });
    const last = messages[messages.length - 1].createdAt;
    return { id: uid('conv'), title, lastIntent, pinned: !!c.pinned, createdAt: messages[0].createdAt, updatedAt: last, messages };
  });
}

function seedState(): DbState {
  const documents = structuredClone(seedDocuments);
  return { signedIn: false, documents, processing: {}, conversations: seedConversations(documents), feedback: [] };
}

// ---------- persistence ----------

function load(): DbState {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw) as DbState;
  } catch {
    // Storage unavailable or corrupt: fall back to the seed.
  }
  return seedState();
}

let state: DbState = load();

export function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    // Quota or privacy mode — the demo still works in memory.
  }
}

export const db = {
  get state() {
    return state;
  },
  reset(options: { keepSession?: boolean; emptyLibrary?: boolean } = {}) {
    const signedIn = state.signedIn;
    state = seedState();
    if (options.keepSession) state.signedIn = signedIn;
    if (options.emptyLibrary) {
      state.documents = [];
      state.conversations = [];
    }
    save();
  },
};

// ---------- document processing simulation ----------

export function classify(name: string): { type: DocType; confidence: number } {
  const n = name.toLowerCase();
  if (/\bv\.?\s|opinion|court|appeal/.test(n)) return { type: 'opinion', confidence: 0.9 };
  if (/complaint|petition|motion|answer|pleading/.test(n)) return { type: 'pleading', confidence: 0.88 };
  if (/agreement|contract|nda|amendment|lease|msa|terms|addendum|sow/.test(n)) return { type: 'contract', confidence: 0.92 };
  return { type: 'other', confidence: 0.55 };
}

export function startProcessing(doc: LegalDocument, opts: { forceFail?: boolean }) {
  const estPages = Math.max(1, Math.round(doc.sizeBytes / 45_000));
  const p: Processing = { startedAt: Date.now(), durationMs: 6000 + Math.min(estPages, 200) * 40, finalPages: estPages };
  const lower = doc.name.toLowerCase();
  if (estPages > 500) {
    p.failAt = 'parsing';
    p.failMessage = `This document has ${estPages} pages; the limit is 500. Split it into smaller files and upload them separately.`;
  } else if (opts.forceFail || /protected|encrypted/.test(lower)) {
    p.failAt = 'parsing';
    p.failMessage = 'This PDF is password-protected. Remove the password, then upload it again.';
  } else if (/corrupt|damaged/.test(lower)) {
    p.failAt = 'parsing';
    p.failMessage = "The file couldn't be read — it may be damaged. Re-export it from the original application and upload again.";
  }
  state.processing[doc.id] = p;
}

/** Derives each in-flight document's status from elapsed time, so progress survives a reload. */
export function tickDocuments() {
  const now = Date.now();
  let changed = false;
  for (const doc of state.documents) {
    const p = state.processing[doc.id];
    if (!p) continue;
    const t = (now - p.startedAt) / p.durationMs;
    let status: LegalDocument['status'];
    let progress: number;
    if (t < 0.12) { status = 'queued'; progress = 0; }
    else if (t < 0.55) { status = 'parsing'; progress = Math.round(((t - 0.12) / 0.43) * 100); }
    else if (t < 1) { status = 'indexing'; progress = Math.round(((t - 0.55) / 0.45) * 100); }
    else { status = 'ready'; progress = 100; }

    const failPoint = p.failAt === 'parsing' ? 0.35 : 0.8;
    if (p.failAt && t >= failPoint) {
      doc.status = 'failed';
      doc.progress = 0;
      doc.error = p.failMessage;
      delete state.processing[doc.id];
      changed = true;
      continue;
    }
    if (status === 'indexing' || status === 'ready') doc.pages = p.finalPages;
    if (status === 'ready') delete state.processing[doc.id];
    if (doc.status !== status || doc.progress !== progress) changed = true;
    doc.status = status;
    doc.progress = progress;
  }
  if (changed) save();
}
