import * as Tabs from '@radix-ui/react-tabs';
import { ChevronLeft, ChevronRight, ExternalLink, FileText, X } from 'lucide-react';
import { useEffect, useRef, type PointerEvent as ReactPointerEvent } from 'react';
import { Link } from 'react-router-dom';
import { useDocuments } from '@/api/queries';
import type { Citation } from '@/api/types';
import { IconButton } from '@/components/ui/Button';
import { cn } from '@/lib/cn';
import { docTitle } from '@/lib/format';
import { useUi } from '@/stores/ui';
import { DocumentPageView } from './DocumentPageView';

const tabCls =
  'relative h-10 px-1 text-[13px] font-medium text-muted transition-colors hover:text-ink data-[state=active]:text-ink data-[state=active]:after:absolute data-[state=active]:after:inset-x-0 data-[state=active]:after:-bottom-px data-[state=active]:after:h-0.5 data-[state=active]:after:rounded-full data-[state=active]:after:bg-primary';

/** Right-hand panel: the cited passage in its page, and all sources for the answer (FR-12, FR-13). */
export function SourcesPanel() {
  const { sources, sourcesTab, setSourcesTab, setSourcesPage, closeSources, openSources, sourcesWidth, setSourcesWidth } = useUi();
  const { data: docs } = useDocuments();
  const panelRef = useRef<HTMLElement>(null);

  // Move focus into the panel when it opens so keyboard and screen-reader users land on the source.
  const key = sources ? `${sources.documentId}:${sources.page}:${sources.citationN ?? ''}` : '';
  useEffect(() => {
    if (key) panelRef.current?.focus({ preventScroll: true });
  }, [key]);

  useEffect(() => {
    if (!sources) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !document.querySelector('[role="dialog"]')) closeSources();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [sources, closeSources]);

  if (!sources) return null;

  const doc = docs?.find((d) => d.id === sources.documentId);
  const total = doc?.pages ?? null;
  const citation = sources.citations.find((c) => c.n === sources.citationN);

  const showCitation = (c: Citation) =>
    openSources({ ...sources, documentId: c.documentId, documentName: c.documentName, page: c.page, highlight: { start: c.charStart, end: c.charEnd }, citationN: c.n });

  const startResize = (e: ReactPointerEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startW = sourcesWidth;
    const move = (ev: PointerEvent) => setSourcesWidth(startW + (startX - ev.clientX));
    const up = () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
      document.body.style.cursor = '';
    };
    document.body.style.cursor = 'col-resize';
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  };

  const list = [...sources.citations].sort((a, b) => a.n - b.n);

  return (
    <>
      {/* Below xl the panel overlays the chat. */}
      <div className="fixed inset-0 z-40 animate-fade-in bg-ink/20 xl:hidden" onClick={closeSources} aria-hidden />
      <aside
        ref={panelRef}
        tabIndex={-1}
        aria-label="Sources"
        style={{ ['--w' as string]: `${sourcesWidth}px` }}
        className="fixed inset-y-0 right-0 z-50 flex w-full max-w-full animate-slide-in-right flex-col border-l border-border bg-bg shadow-pop focus:outline-none sm:w-[min(var(--w),92vw)] xl:static xl:z-auto xl:w-[var(--w)] xl:shadow-none"
      >
        <div
          onPointerDown={startResize}
          className="group absolute inset-y-0 -left-1 z-10 hidden w-2 cursor-col-resize xl:block"
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize sources panel"
        >
          <div className="mx-auto h-full w-px bg-transparent transition-colors group-hover:bg-primary/40" />
        </div>

        <header className="flex items-center gap-2 border-b border-border bg-surface px-4 py-2.5">
          <FileText className="size-4 shrink-0 text-primary" />
          <h2 className="min-w-0 flex-1 truncate text-sm font-semibold text-ink" title={sources.documentName}>
            {docTitle(sources.documentName)}
          </h2>
          <Link
            to={`/library/${sources.documentId}?page=${sources.page}`}
            className="inline-flex h-8 items-center gap-1 rounded-lg px-2 text-xs font-medium text-muted hover:bg-ink/[0.05] hover:text-ink"
          >
            <ExternalLink className="size-3.5" /> Open
          </Link>
          <IconButton label="Close sources" shortcut="Esc" onClick={closeSources} size="sm">
            <X />
          </IconButton>
        </header>

        <Tabs.Root value={sourcesTab} onValueChange={(v) => setSourcesTab(v as 'passage' | 'all')} className="flex min-h-0 flex-1 flex-col">
          <Tabs.List className="flex gap-5 border-b border-border bg-surface px-4" aria-label="Source views">
            <Tabs.Trigger value="passage" className={tabCls}>
              {citation ? 'Cited passage' : 'Page'}
            </Tabs.Trigger>
            <Tabs.Trigger value="all" className={tabCls}>
              All sources <span className="ml-0.5 text-subtle">{list.length}</span>
            </Tabs.Trigger>
          </Tabs.List>

          <Tabs.Content value="passage" className="flex min-h-0 flex-1 flex-col focus:outline-none">
            <div className="flex items-center gap-2 border-b border-border px-4 py-2">
              {citation ? (
                <span className="flex min-w-0 flex-1 items-center gap-2 text-xs text-muted">
                  <span className="flex h-[18px] min-w-[18px] items-center justify-center rounded-[5px] bg-primary px-1 text-[11px] font-semibold text-white">{citation.n}</span>
                  <span className="truncate">
                    Page {citation.page}
                    {citation.section && ` · ${citation.section}`}
                  </span>
                </span>
              ) : (
                <span className="flex-1 text-xs text-muted">Page {sources.page}</span>
              )}
              <div className="flex items-center gap-0.5">
                <IconButton size="sm" label="Previous page" disabled={sources.page <= 1} onClick={() => setSourcesPage(sources.page - 1)}>
                  <ChevronLeft />
                </IconButton>
                <span className="min-w-[64px] text-center text-xs tabular-nums text-muted">
                  {sources.page} / {total ?? '–'}
                </span>
                <IconButton size="sm" label="Next page" disabled={!!total && sources.page >= total} onClick={() => setSourcesPage(sources.page + 1)}>
                  <ChevronRight />
                </IconButton>
              </div>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-4">
              <DocumentPageView documentId={sources.documentId} page={sources.page} totalPages={total} highlight={sources.highlight} />
              <p className="sr-only" aria-live="polite">
                Showing page {sources.page} of {docTitle(sources.documentName)}
                {citation ? `, with source ${citation.n} highlighted` : ''}.
              </p>
            </div>
          </Tabs.Content>

          <Tabs.Content value="all" className="min-h-0 flex-1 overflow-y-auto p-3 focus:outline-none">
            <ol className="space-y-2">
              {list.map((c) => (
                <li key={c.n}>
                  <button
                    onClick={() => showCitation(c)}
                    className={cn(
                      'w-full rounded-xl border bg-surface p-3 text-left transition-colors hover:border-primary/40',
                      c.n === sources.citationN ? 'border-primary/50 ring-1 ring-primary/25' : 'border-border',
                    )}
                  >
                    <span className="flex items-center gap-2 text-xs">
                      <span className="flex h-[18px] min-w-[18px] items-center justify-center rounded-[5px] bg-primary-soft px-1 text-[11px] font-semibold text-primary">{c.n}</span>
                      <span className="min-w-0 flex-1 truncate font-medium text-ink">{docTitle(c.documentName)}</span>
                      <span className="shrink-0 text-subtle">
                        p.{c.page}
                        {c.section && ` · ${c.section}`}
                      </span>
                    </span>
                    <span className="mt-1.5 block border-l-2 border-highlight pl-2.5 font-serif text-[13.5px] leading-5 text-ink">{c.quote}</span>
                  </button>
                </li>
              ))}
              {list.length === 0 && <li className="py-8 text-center text-sm text-subtle">No citations for this response.</li>}
            </ol>
          </Tabs.Content>
        </Tabs.Root>
      </aside>
    </>
  );
}
