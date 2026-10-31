import { ArrowDown, MessageSquareOff } from 'lucide-react';
import { useCallback, useEffect, useRef } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { ApiError } from '@/api/client';
import { useConversation } from '@/api/queries';
import type { Message, SendMessageRequest, UserMessage as UserMsg } from '@/api/types';
import { EmptyState } from '@/components/ui/EmptyState';
import { useAutoScroll } from '@/hooks/useAutoScroll';
import { useComposer } from '@/stores/composer';
import { useUi } from '@/stores/ui';
import { Composer } from '../composer/Composer';
import { AssistantMessage } from './AssistantMessage';
import { sendMessage, stopStreaming, useStreaming } from './stream';
import { UserMessage } from './UserMessage';

export function ChatPage() {
  const { conversationId = '' } = useParams();
  const qc = useQueryClient();
  const { data: conv, isLoading, error } = useConversation(conversationId);
  const streaming = useStreaming((s) => !!s.active[conversationId]);
  const scroller = useRef<HTMLDivElement>(null);
  const closeSources = useUi((s) => s.closeSources);

  const messages = conv?.messages ?? [];
  const last = messages[messages.length - 1];
  const contentKey = last ? `${messages.length}:${last.role === 'assistant' ? last.answerMd.length + last.excerpts.length + (last.stage ?? '') : ''}` : 0;
  const { atBottom, scrollToBottom } = useAutoScroll(scroller, contentKey);

  // Entering a conversation: start at the bottom, close any stale source, and carry the last scope forward.
  const initialised = useRef<string | null>(null);
  useEffect(() => {
    if (!conv || initialised.current === conv.id) return;
    initialised.current = conv.id;
    closeSources();
    requestAnimationFrame(() => scrollToBottom(false));
    const lastUser = [...conv.messages].reverse().find((m): m is UserMsg => m.role === 'user');
    if (lastUser) {
      const { setScope, setMode, setSummaryDocument } = useComposer.getState();
      setScope(lastUser.scope);
      setMode(lastUser.mode === 'ask' ? 'ask' : 'auto');
      if (lastUser.summaryDocumentId) setSummaryDocument(lastUser.summaryDocumentId);
    }
  }, [conv, closeSources, scrollToBottom]);

  const send = useCallback(
    (req: SendMessageRequest) => {
      void sendMessage(qc, conversationId, req);
      requestAnimationFrame(() => scrollToBottom());
    },
    [qc, conversationId, scrollToBottom],
  );

  const retry = useCallback((p: UserMsg) => send({ text: p.text, mode: p.mode, scope: p.scope, draftParams: p.draftParams, summaryDocumentId: p.summaryDocumentId }), [send]);
  const widen = useCallback((p: UserMsg) => {
    useComposer.getState().setScope({ kind: 'workspace' });
    send({ text: p.text, mode: p.mode, scope: { kind: 'workspace' } });
  }, [send]);

  if (error) {
    const missing = error instanceof ApiError && error.status === 404;
    return (
      <div className="flex flex-1 items-center justify-center">
        <EmptyState
          icon={<MessageSquareOff />}
          title={missing ? 'Conversation not found' : 'This conversation could not be loaded'}
          action={<Link to="/" className="text-sm font-medium text-primary hover:underline">Start a new conversation</Link>}
        >
          {missing ? 'It may have been deleted.' : 'Check your connection and reload the page.'}
        </EmptyState>
      </div>
    );
  }

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      <div ref={scroller} className="min-h-0 flex-1 overflow-y-auto" role="log" aria-label="Conversation" aria-live="off">
        <div className="mx-auto w-full max-w-[780px] px-4 pb-10 pt-6 sm:px-6">
          {isLoading ? <ThreadSkeleton /> : <Thread messages={messages} conversationId={conversationId} title={conv?.title ?? ''} onRetry={retry} onWiden={widen} />}
        </div>
      </div>

      {!atBottom && (
        <button
          onClick={() => scrollToBottom()}
          className="absolute bottom-[150px] left-1/2 z-10 flex -translate-x-1/2 animate-fade-in items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 text-xs font-medium text-muted shadow-pop hover:text-ink"
        >
          <ArrowDown className="size-3.5" /> Jump to latest
        </button>
      )}

      <div className="bg-gradient-to-t from-bg via-bg to-bg/0 px-4 pb-3 pt-2 sm:px-6">
        <div className="mx-auto max-w-[780px]">
          <Composer onSubmit={send} streaming={streaming} onStop={() => stopStreaming(conversationId)} autoFocus />
        </div>
      </div>
    </div>
  );
}

function Thread({ messages, conversationId, title, onRetry, onWiden }: { messages: Message[]; conversationId: string; title: string; onRetry: (p: UserMsg) => void; onWiden: (p: UserMsg) => void }) {
  if (messages.length === 0) return <p className="py-10 text-center text-sm text-subtle">Send a message to begin.</p>;
  return (
    <div className="space-y-8">
      {messages.map((m, i) => {
        if (m.role === 'user') return <UserMessage key={m.id} message={m} />;
        const prev = messages[i - 1];
        return (
          <AssistantMessage
            key={m.id}
            conversationId={conversationId}
            conversationTitle={title}
            message={m}
            prompt={prev?.role === 'user' ? prev : undefined}
            isLast={i === messages.length - 1}
            onRetry={onRetry}
            onWiden={onWiden}
          />
        );
      })}
    </div>
  );
}

function ThreadSkeleton() {
  return (
    <div className="space-y-8" aria-label="Loading conversation" aria-busy>
      <div className="flex justify-end">
        <div className="skeleton h-11 w-2/3 rounded-2xl" />
      </div>
      <div className="flex gap-3.5">
        <div className="skeleton size-7 shrink-0 rounded-lg" />
        <div className="flex-1 space-y-2.5">
          <div className="skeleton h-4 w-24" />
          <div className="skeleton h-4 w-full" />
          <div className="skeleton h-4 w-11/12" />
          <div className="skeleton h-4 w-3/5" />
        </div>
      </div>
    </div>
  );
}
