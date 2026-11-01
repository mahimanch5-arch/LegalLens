import { ChevronDown, FileText } from 'lucide-react';
import { useState } from 'react';
import type { AssistantMessage } from '@/api/types';
import { cn } from '@/lib/cn';
import { docTitle } from '@/lib/format';
import { useUi } from '@/stores/ui';
import { useOpenSource } from '../sources/useOpenSource';

/**
 * Retrieved excerpts shown under the answer without any click (FR-12). For summaries and
 * drafts, where every field already carries chips, it starts collapsed.
 */
export function SourcesStrip({ message, defaultOpen = true }: { message: AssistantMessage; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const { openExcerpt } = useOpenSource(message);
  const activeSpan = useUi((s) => (s.sources?.messageId === message.id && s.sources.highlight ? s.sources.citationN : undefined));
  const items = message.excerpts;
  if (items.length === 0) return null;

  const docCount = new Set(items.map((e) => e.documentId)).size;
  const nFor = (spanId: string) => message.citations.find((c) => c.spanId === spanId)?.n;

  return (
    <section className="mt-4" aria-label="Sources">
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="group flex items-center gap-1.5 text-xs font-semibold uppercase tracking-[0.06em] text-muted hover:text-ink"
      >
        Sources
        <span className="font-medium normal-case tracking-normal text-subtle">
          · {items.length} passage{items.length === 1 ? '' : 's'} from {docCount} document{docCount === 1 ? '' : 's'}
        </span>
        <ChevronDown className={cn('size-3.5 transition-transform', !open && '-rotate-90')} />
      </button>
      {open && (
        <ol className="mt-2.5 grid gap-2 sm:grid-cols-2">
          {items.map((e) => {
            const n = nFor(e.spanId);
            return (
              <li key={e.spanId}>
                <button
                  onClick={() => openExcerpt(e)}
                  className={cn(
                    'group flex h-full w-full flex-col rounded-xl border bg-surface p-3 text-left transition-all hover:border-primary/40 hover:shadow-soft',
                    n !== undefined && activeSpan === n ? 'border-primary/60 ring-1 ring-primary/30' : 'border-border',
                  )}
                >
                  <span className="flex w-full items-center gap-2 text-xs">
                    {n !== undefined ? (
                      <span className="flex h-[18px] min-w-[18px] items-center justify-center rounded-[5px] bg-primary-soft px-1 text-[11px] font-semibold text-primary">
                        {n}
                      </span>
                    ) : (
                      <FileText className="size-3.5 text-subtle" />
                    )}
                    <span className="min-w-0 flex-1 truncate font-medium text-ink">{docTitle(e.documentName)}</span>
                    <span className="shrink-0 text-subtle">
                      p.{e.page}
                      {e.section && ` · ${e.section}`}
                    </span>
                  </span>
                  <span className="mt-1.5 line-clamp-3 font-serif text-[13.5px] leading-5 text-muted group-hover:text-ink">{e.text}</span>
                </button>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
