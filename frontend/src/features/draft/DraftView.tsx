import { FileText, ShieldAlert } from 'lucide-react';
import type { AssistantMessage, Citation } from '@/api/types';
import { Pill } from '@/components/ui/Pill';
import { docTitle } from '@/lib/format';
import { Markdown } from '../chat/Markdown';

/** Persistent, non-dismissable marking (FR-23). */
export function DraftBanner() {
  return (
    <div className="flex items-start gap-2.5 border-b border-accent/25 bg-accent-soft px-5 py-2.5 text-[13px] leading-5 text-ink">
      <ShieldAlert className="mt-px size-4 shrink-0 text-accent" />
      <p>
        <span className="font-semibold tracking-wide text-accent">UNREVIEWED AI DRAFT</span>
        <span className="text-muted"> — attorney review required before any use. Every factual statement is cited; verify each one against its source.</span>
      </p>
    </div>
  );
}

interface Props {
  message: AssistantMessage;
  onCite: (c: Citation) => void;
  activeCitation?: number;
}

export function DraftView({ message, onCite, activeCitation }: Props) {
  const draft = message.draft!;
  const streaming = message.status === 'streaming';
  const p = draft.params;

  return (
    <article className="overflow-hidden rounded-xl border border-border bg-surface shadow-soft" aria-label={draft.title}>
      <DraftBanner />
      <div className="flex flex-wrap items-center gap-2 border-b border-border px-5 py-2.5 text-xs text-muted">
        <Pill tone="accent">{draft.draftType === 'memo' ? 'Legal memo' : 'Case brief'}</Pill>
        {p.audience && <span>For: <span className="text-ink">{p.audience}</span></span>}
        <span aria-hidden>·</span>
        <span>Tone: <span className="capitalize text-ink">{p.tone}</span></span>
        {p.position && (
          <>
            <span aria-hidden>·</span>
            <span className="min-w-0 truncate">Position: <span className="text-ink">{p.position}</span></span>
          </>
        )}
      </div>

      <div className="px-5 py-5 sm:px-8 sm:py-7">
        {message.answerMd ? (
          <Markdown md={message.answerMd} citations={message.citations} onCite={onCite} activeCitation={activeCitation} streaming={streaming} />
        ) : (
          <div className="space-y-3" aria-hidden>
            <div className="skeleton h-6 w-2/3" />
            <div className="skeleton h-4 w-full" />
            <div className="skeleton h-4 w-5/6" />
          </div>
        )}
      </div>

      {!streaming && draft.sources.length > 0 && (
        <footer className="border-t border-border bg-bg/60 px-5 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.06em] text-subtle">Source manifest</p>
          <ul className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-muted">
            {draft.sources.map((s) => (
              <li key={s.documentId} className="flex items-center gap-1.5">
                <FileText className="size-3.5 text-subtle" />
                {docTitle(s.documentName)}
              </li>
            ))}
          </ul>
        </footer>
      )}
      <div className="border-t border-accent/25 bg-accent-soft/60 px-5 py-1.5 text-center text-[11px] font-medium uppercase tracking-[0.08em] text-accent">
        Unreviewed AI draft · not legal advice
      </div>
    </article>
  );
}
