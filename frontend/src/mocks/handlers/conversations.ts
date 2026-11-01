import { http, HttpResponse, delay } from 'msw';
import type {
  AssistantMessage,
  Conversation,
  ConversationDetail,
  Feedback,
  SendMessageRequest,
  StreamEvent,
  UserMessage,
} from '@/api/types';
import { db, save, tickDocuments, uid } from '../db';
import { planResponse, titleFrom, type ResponsePlan } from '../engine';
import { scenario } from '../scenario';
import { requireAuth } from './auth';

const PAGE_SIZE = 30;

const notFound = () => HttpResponse.json({ code: 'unknown', message: 'Conversation not found.' }, { status: 404 });
const findConv = (id: string) => db.state.conversations.find((c) => c.id === id);

function toSummary(c: ConversationDetail): Conversation {
  return { id: c.id, title: c.title, lastIntent: c.lastIntent, pinned: c.pinned, createdAt: c.createdAt, updatedAt: c.updatedAt };
}

const frame = (e: StreamEvent) => `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`;

/** Splits markdown into word-sized tokens, keeping whitespace attached. */
const tokenize = (md: string) => md.match(/\S+\s*|\s+/g) ?? [];

export const conversationHandlers = [
  http.get('/api/conversations', async ({ request }) => {
    const denied = requireAuth();
    if (denied) return denied;
    await delay(200);
    const cursor = Number(new URL(request.url).searchParams.get('cursor') ?? 0);
    const sorted = [...db.state.conversations].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
    const items = sorted.slice(cursor, cursor + PAGE_SIZE).map(toSummary);
    const next = cursor + PAGE_SIZE < sorted.length ? String(cursor + PAGE_SIZE) : null;
    return HttpResponse.json({ items, nextCursor: next });
  }),

  // "NCC" — new conversation.
  http.post('/api/conversations', async () => {
    const denied = requireAuth();
    if (denied) return denied;
    await delay(120);
    const now = new Date().toISOString();
    const conv: ConversationDetail = { id: uid('conv'), title: 'New conversation', lastIntent: null, pinned: false, createdAt: now, updatedAt: now, messages: [] };
    db.state.conversations.unshift(conv);
    save();
    return HttpResponse.json(toSummary(conv), { status: 201 });
  }),

  http.get('/api/conversations/:id', async ({ params }) => {
    await delay(220);
    const conv = findConv(params.id as string);
    return conv ? HttpResponse.json(conv) : notFound();
  }),

  http.get('/api/conversations/:id/messages', async ({ params }) => {
    const conv = findConv(params.id as string);
    return conv ? HttpResponse.json({ items: conv.messages, nextCursor: null }) : notFound();
  }),

  http.patch('/api/conversations/:id', async ({ params, request }) => {
    const conv = findConv(params.id as string);
    if (!conv) return notFound();
    const body = (await request.json()) as Partial<Pick<Conversation, 'title' | 'pinned'>>;
    if (typeof body.title === 'string' && body.title.trim()) conv.title = body.title.trim().slice(0, 120);
    if (typeof body.pinned === 'boolean') conv.pinned = body.pinned;
    save();
    return HttpResponse.json(toSummary(conv));
  }),

  http.delete('/api/conversations/:id', async ({ params }) => {
    await delay(200);
    db.state.conversations = db.state.conversations.filter((c) => c.id !== params.id);
    save();
    return new HttpResponse(null, { status: 204 });
  }),

  http.post('/api/feedback', async ({ request }) => {
    const body = (await request.json()) as { conversationId: string; messageId: string } & Feedback;
    const conv = findConv(body.conversationId);
    const msg = conv?.messages.find((m) => m.id === body.messageId) as AssistantMessage | undefined;
    const feedback: Feedback = { rating: body.rating, reason: body.reason, comment: body.comment };
    if (msg) msg.feedback = feedback;
    db.state.feedback.push({ conversationId: body.conversationId, messageId: body.messageId, feedback, at: new Date().toISOString() });
    save();
    await delay(150);
    return new HttpResponse(null, { status: 204 });
  }),

  // Chat turn — streamed over SSE (FR-10).
  http.post('/api/conversations/:id/messages', async ({ params, request }) => {
    const denied = requireAuth();
    if (denied) return denied;
    const conv = findConv(params.id as string);
    if (!conv) return notFound();
    const req = (await request.json()) as SendMessageRequest;
    tickDocuments();

    const forced = scenario.consumeReply();
    if (forced === 'rate_limited') {
      return HttpResponse.json(
        { code: 'rate_limited', message: 'You have sent several requests in a short time. Please wait a moment before trying again.', retryAfterSec: 20 },
        { status: 429 },
      );
    }

    let plan: ResponsePlan = planResponse(req, db.state.documents);
    if (forced === 'refusal') {
      plan = { ...plan, answerMd: '', citations: [], excerpts: [], summary: undefined, draft: undefined, refusal: { reason: "I couldn't find anything in your documents that answers this question, so I won't guess.", scopeLabel: plan.scopeUsed.label, suggestions: ['Widen the scope to the whole workspace.', 'Upload the document that covers this topic.'] } };
    }

    const now = new Date().toISOString();
    const userMsg: UserMessage = { id: uid('msg'), role: 'user', text: req.text, mode: req.mode, scope: req.scope, draftParams: req.draftParams, summaryDocumentId: req.summaryDocumentId, createdAt: now };
    const assistant: AssistantMessage = { id: uid('msg'), role: 'assistant', createdAt: now, status: 'streaming', intent: plan.intent, scopeUsed: plan.scopeUsed, answerMd: '', citations: [], excerpts: [], traceId: uid('trace') };
    const isFirst = conv.messages.length === 0;
    conv.messages.push(userMsg, assistant);
    conv.updatedAt = now;
    conv.lastIntent = plan.intent;
    if (isFirst) {
      const summaryDoc = db.state.documents.find((d) => d.id === plan.summary?.documentId);
      conv.title = plan.draft
        ? plan.draft.title.replace(/^(Memorandum|Case brief) — /, plan.draft.draftType === 'memo' ? 'Memo: ' : 'Brief: ')
        : titleFrom(req.text, plan.intent, summaryDoc?.name);
    }
    save();

    const tokenDelay = scenario.tokenDelayMs();
    let cancelled = false;
    const encoder = new TextEncoder();

    const finish = (status: AssistantMessage['status']) => {
      assistant.status = status;
      save();
    };

    const stream = new ReadableStream<Uint8Array>({
      async start(controller) {
        const send = (e: StreamEvent) => {
          if (cancelled) return;
          controller.enqueue(encoder.encode(frame(e)));
        };
        try {
          send({ event: 'meta', data: { userMessageId: userMsg.id, messageId: assistant.id, intent: plan.intent, scopeUsed: plan.scopeUsed, traceId: assistant.traceId! } });

          for (const label of plan.stages) {
            send({ event: 'stage', data: { label } });
            await delay(Math.round(tokenDelay * 14 + 120));
            if (cancelled) return;
          }

          if (forced === 'timeout') {
            await delay(1500);
            assistant.error = { code: 'timeout', message: 'The answer took too long to generate and was stopped. This is usually temporary.' };
            send({ event: 'error', data: assistant.error });
            finish('error');
            controller.close();
            return;
          }

          // Retrieval results arrive before generation, so excerpts render first (FR-12).
          for (const ex of plan.excerpts) {
            send({ event: 'excerpt', data: ex });
            assistant.excerpts.push(ex);
          }

          if (forced === 'llm_unavailable') {
            await delay(600);
            assistant.error = { code: 'llm_unavailable', message: 'The AI model provider did not respond. Your documents were searched and the matching excerpts are shown, but no answer was written.' };
            send({ event: 'error', data: assistant.error });
            finish('error');
            controller.close();
            return;
          }

          if (plan.refusal) {
            assistant.refusal = plan.refusal;
            send({ event: 'refusal', data: plan.refusal });
          }
          if (plan.summary) {
            for (const c of plan.citations) {
              send({ event: 'citation', data: c });
              assistant.citations.push(c);
            }
            assistant.summary = plan.summary;
            send({ event: 'summary', data: plan.summary });
          }
          if (plan.draft) {
            assistant.draft = plan.draft;
            send({ event: 'draft', data: plan.draft });
          }

          const tokens = tokenize(plan.answerMd);
          const cutAt = forced === 'interrupted' ? Math.floor(tokens.length * 0.4) : Infinity;
          const emitted = new Set(assistant.citations.map((c) => c.n));
          for (let i = 0; i < tokens.length; i++) {
            if (cancelled) return;
            if (i >= cutAt) {
              finish('incomplete');
              controller.close(); // no `done` → the client marks it incomplete (NFR-7)
              return;
            }
            const tok = tokens[i];
            for (const m of tok.matchAll(/\[(\d+)\]/g)) {
              const n = Number(m[1]);
              const c = plan.citations.find((x) => x.n === n);
              if (c && !emitted.has(n)) {
                emitted.add(n);
                assistant.citations.push(c);
                send({ event: 'citation', data: c });
              }
            }
            assistant.answerMd += tok;
            send({ event: 'token', data: { text: tok } });
            await delay(tokenDelay + (tok.endsWith('\n') ? tokenDelay * 3 : 0));
          }

          assistant.usage = plan.usage;
          assistant.modelVersion = 'mock-model-2026-09';
          assistant.promptVersion = `${plan.intent}-v1.3`;
          send({ event: 'usage', data: plan.usage });
          send({ event: 'done', data: { modelVersion: assistant.modelVersion, promptVersion: assistant.promptVersion } });
          finish('complete');
          controller.close();
        } catch {
          finish('incomplete');
        }
      },
      cancel() {
        // Client pressed Stop or navigated away: persist what was produced, marked incomplete.
        cancelled = true;
        finish('incomplete');
      },
    });

    return new HttpResponse(stream, {
      headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' },
    });
  }),
];
