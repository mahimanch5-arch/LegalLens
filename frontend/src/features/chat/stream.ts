import type { QueryClient } from '@tanstack/react-query';
import { create } from 'zustand';
import { ApiError } from '@/api/client';
import { qk } from '@/api/queries';
import { streamPost } from '@/api/sse';
import type { AssistantMessage, ConversationDetail, SendMessageRequest, StreamEvent, UserMessage } from '@/api/types';

interface StreamingState {
  /** conversationId → controller for the in-flight turn. */
  active: Record<string, AbortController>;
  /** Last completion, for the screen-reader announcement. */
  announcement: string;
  start: (conversationId: string, ac: AbortController) => void;
  end: (conversationId: string, announcement: string) => void;
}

export const useStreaming = create<StreamingState>((set, get) => ({
  active: {},
  announcement: '',
  start: (id, ac) => set({ active: { ...get().active, [id]: ac }, announcement: 'Legal Lens is responding.' }),
  end: (id, announcement) => {
    const active = { ...get().active };
    delete active[id];
    set({ active, announcement });
  },
}));

export function stopStreaming(conversationId: string) {
  useStreaming.getState().active[conversationId]?.abort();
}

let tmp = 0;

/**
 * Sends one chat turn and folds the SSE stream into the conversation cache, so every view
 * (thread, sidebar, sources panel) renders from one source of truth.
 */
export async function sendMessage(qc: QueryClient, conversationId: string, req: SendMessageRequest): Promise<void> {
  const key = qk.conversation(conversationId);
  const now = new Date().toISOString();
  const user: UserMessage = { id: `tmp_u_${++tmp}`, role: 'user', createdAt: now, ...req };
  let assistantId = `tmp_a_${tmp}`;
  const assistant: AssistantMessage = {
    id: assistantId,
    role: 'assistant',
    createdAt: now,
    status: 'streaming',
    intent: req.mode === 'auto' ? null : req.mode,
    stage: 'Starting…',
    answerMd: '',
    citations: [],
    excerpts: [],
  };

  qc.setQueryData<ConversationDetail>(key, (old) => (old ? { ...old, messages: [...old.messages, user, assistant] } : old));

  const update = (fn: (m: AssistantMessage) => AssistantMessage) =>
    qc.setQueryData<ConversationDetail>(key, (old) =>
      old
        ? { ...old, messages: old.messages.map((m) => (m.id === assistantId && m.role === 'assistant' ? fn(m) : m)) }
        : old,
    );

  const onEvent = (e: StreamEvent) => {
    switch (e.event) {
      case 'meta': {
        const { userMessageId, messageId, intent, scopeUsed, traceId } = e.data;
        const oldUser = user.id;
        qc.setQueryData<ConversationDetail>(key, (old) =>
          old
            ? {
                ...old,
                lastIntent: intent,
                messages: old.messages.map((m) => {
                  if (m.id === oldUser) return { ...m, id: userMessageId };
                  if (m.id === assistantId && m.role === 'assistant') return { ...m, id: messageId, intent, scopeUsed, traceId };
                  return m;
                }),
              }
            : old,
        );
        user.id = userMessageId;
        assistantId = messageId;
        break;
      }
      case 'stage':
        update((m) => ({ ...m, stage: e.data.label }));
        break;
      case 'token':
        update((m) => ({ ...m, stage: undefined, answerMd: m.answerMd + e.data.text }));
        break;
      case 'citation':
        update((m) => (m.citations.some((c) => c.n === e.data.n) ? m : { ...m, citations: [...m.citations, e.data] }));
        break;
      case 'excerpt':
        update((m) => ({ ...m, excerpts: [...m.excerpts, e.data] }));
        break;
      case 'summary':
        update((m) => ({ ...m, stage: undefined, summary: e.data }));
        break;
      case 'draft':
        update((m) => ({ ...m, draft: e.data }));
        break;
      case 'refusal':
        update((m) => ({ ...m, stage: undefined, refusal: e.data }));
        break;
      case 'usage':
        update((m) => ({ ...m, usage: e.data }));
        break;
      case 'done':
        update((m) => ({ ...m, status: 'complete', stage: undefined, ...e.data }));
        break;
      case 'error':
        update((m) => ({ ...m, status: 'error', stage: undefined, error: e.data }));
        break;
    }
  };

  const ac = new AbortController();
  useStreaming.getState().start(conversationId, ac);
  let announcement = 'Response complete.';

  try {
    const { terminated } = await streamPost(`/api/conversations/${conversationId}/messages`, req, onEvent, ac.signal);
    if (!terminated) {
      update((m) => ({ ...m, status: 'incomplete', stage: undefined }));
      announcement = 'The response was interrupted.';
    }
  } catch (err) {
    if (ac.signal.aborted) {
      update((m) => ({ ...m, status: 'incomplete', stage: undefined }));
      announcement = 'Response stopped.';
    } else if (err instanceof ApiError) {
      update((m) => ({ ...m, status: 'error', stage: undefined, error: { code: err.code, message: err.message, retryAfterSec: err.retryAfterSec } }));
      announcement = 'The response failed.';
    } else {
      update((m) => ({
        ...m,
        status: 'error',
        stage: undefined,
        error: { code: 'unknown', message: "Couldn't reach Legal Lens. Check your connection, then try again." },
      }));
      announcement = 'The response failed.';
    }
  } finally {
    useStreaming.getState().end(conversationId, announcement);
    void qc.invalidateQueries({ queryKey: qk.conversations });
  }
}
