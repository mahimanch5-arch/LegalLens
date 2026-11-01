import { memo } from 'react';
import type { AssistantMessage as AssistantMsg, UserMessage } from '@/api/types';
import { LogoMark } from '@/components/ui/Logo';
import { Spinner } from '@/components/ui/Spinner';
import { fullDateTime } from '@/lib/format';
import { useUi } from '@/stores/ui';
import { DraftView } from '../draft/DraftView';
import { useOpenSource } from '../sources/useOpenSource';
import { SummaryCard } from '../summary/SummaryCard';
import { Markdown } from './Markdown';
import { MessageActions } from './MessageActions';
import { MessageMeta } from './MessageMeta';
import { SourcesStrip } from './SourcesStrip';
import { ErrorCard, IncompleteNotice, RefusalCard } from './StateCards';

interface Props {
  conversationId: string;
  conversationTitle: string;
  message: AssistantMsg;
  prompt?: UserMessage;
  isLast: boolean;
  onRetry: (prompt: UserMessage) => void;
  onWiden: (prompt: UserMessage) => void;
}

export const AssistantMessage = memo(function AssistantMessage({ conversationId, conversationTitle, message, prompt, isLast, onRetry, onWiden }: Props) {
  const { openCitation } = useOpenSource(message);
  const activeCitation = useUi((s) => (s.sources?.messageId === message.id ? s.sources.citationN : undefined));

  const streaming = message.status === 'streaming';
  const hasBody = !!(message.answerMd || message.refusal || message.summary || message.draft || message.error);
  const retry = prompt ? () => onRetry(prompt) : undefined;
  const canWiden = prompt && prompt.scope.kind === 'documents' && message.intent === 'ask';

  return (
    <article className="flex gap-3.5" aria-label="Legal Lens response" aria-busy={streaming}>
      <LogoMark className="mt-0.5 size-7 shrink-0" />
      <div className="min-w-0 flex-1">
        <header className="flex h-7 items-center gap-2">
          <span className="text-sm font-semibold text-ink">Legal Lens</span>
          <time className="text-xs text-subtle" dateTime={message.createdAt} title={fullDateTime(message.createdAt)}>
            {new Date(message.createdAt).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
          </time>
        </header>

        {streaming && message.stage && (
          <div className="mt-1.5 flex items-center gap-2 text-sm" aria-hidden>
            <Spinner className="size-3.5 text-primary" />
            <span className="shimmer-text font-medium">{message.stage}</span>
          </div>
        )}

        {hasBody && (
          <div className="mt-1.5">
            {message.status === 'error' && message.error ? (
              <ErrorCard error={message.error} onRetry={isLast ? retry : undefined} />
            ) : message.refusal ? (
              <RefusalCard refusal={message.refusal} onWiden={canWiden ? () => onWiden(prompt!) : undefined} />
            ) : message.summary ? (
              <>
                {message.answerMd && <Markdown md={message.answerMd} citations={message.citations} onCite={openCitation} streaming={streaming} className="mb-3 text-[15.5px]" />}
                <SummaryCard summary={message.summary} citations={message.citations} onCite={openCitation} activeCitation={activeCitation} />
              </>
            ) : message.draft ? (
              <DraftView message={message} onCite={openCitation} activeCitation={activeCitation} />
            ) : (
              <Markdown md={message.answerMd} citations={message.citations} onCite={openCitation} activeCitation={activeCitation} streaming={streaming} />
            )}
          </div>
        )}

        {message.status === 'incomplete' && <IncompleteNotice onRetry={retry} />}

        {!message.refusal && (
          <SourcesStrip key={message.excerpts.length > 0 ? 'has' : 'none'} message={message} defaultOpen={!message.summary && !message.draft} />
        )}

        {!streaming && (
          <>
            <div className="mt-3">
              <MessageMeta message={message} userMode={prompt?.mode} />
            </div>
            {message.status !== 'error' && (
              <MessageActions
                conversationId={conversationId}
                message={message}
                question={prompt?.text}
                title={message.draft?.title ?? conversationTitle}
                onRetry={retry}
              />
            )}
          </>
        )}
      </div>
    </article>
  );
});
