import { AlertTriangle, CheckCircle2, ChevronDown, FileSearch } from 'lucide-react';
import { useState } from 'react';
import type { Citation, SummaryResult } from '@/api/types';
import { Pill } from '@/components/ui/Pill';
import { cn } from '@/lib/cn';
import { DOC_TYPE_LABEL, docTitle } from '@/lib/format';
import { CitationChip } from '../chat/CitationChip';

interface Props {
  summary: SummaryResult;
  citations: Citation[];
  onCite: (c: Citation) => void;
  activeCitation?: number;
}

/** Template-driven summary (BRD §9): every populated field cited, gaps stated, never inferred (FR-15, FR-16). */
export function SummaryCard({ summary, citations, onCite, activeCitation }: Props) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const all = summary.sections.flatMap((s) => s.fields);
  const filled = all.filter((f) => f.value).length;
  const flags = all.filter((f) => f.flag).length;

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-soft">
      <header className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-border bg-bg/60 px-4 py-3">
        <FileSearch className="size-[18px] text-primary" />
        <h3 className="min-w-0 flex-1 truncate font-medium text-ink">{docTitle(summary.documentName)}</h3>
        <Pill tone="primary">{DOC_TYPE_LABEL[summary.docType]} template</Pill>
        <Pill>
          {filled}/{all.length} fields addressed
        </Pill>
        {flags > 0 && (
          <Pill tone="warning" icon={<AlertTriangle />}>
            {flags} flagged
          </Pill>
        )}
      </header>

      <div className="divide-y divide-border">
        {summary.sections.map((s) => {
          const isCollapsed = collapsed[s.title];
          return (
            <section key={s.title}>
              <button
                className="flex w-full items-center gap-2 px-4 py-2.5 text-left hover:bg-bg/60"
                onClick={() => setCollapsed({ ...collapsed, [s.title]: !isCollapsed })}
                aria-expanded={!isCollapsed}
              >
                <ChevronDown className={cn('size-4 text-subtle transition-transform', isCollapsed && '-rotate-90')} />
                <span className="text-[13px] font-semibold uppercase tracking-[0.06em] text-muted">{s.title}</span>
              </button>
              {!isCollapsed && (
                <dl className="px-4 pb-3">
                  {s.fields.map((f) => (
                    <div key={f.label} className="grid gap-x-6 gap-y-0.5 py-2 sm:grid-cols-[180px_1fr]">
                      <dt className="pt-0.5 text-[13px] font-medium text-muted">{f.label}</dt>
                      <dd className="font-serif text-[15.5px] leading-relaxed text-ink">
                        {f.value ? (
                          <>
                            {f.value}
                            {f.citations.map((n) => {
                              const c = citations.find((x) => x.n === n);
                              return c ? <CitationChip key={n} citation={c} onOpen={onCite} active={activeCitation === n} /> : null;
                            })}
                            {f.flag && (
                              <span className="mt-1.5 flex items-center gap-1.5 font-sans text-xs font-medium text-warning">
                                <AlertTriangle className="size-3.5" /> {f.flag}
                              </span>
                            )}
                          </>
                        ) : (
                          <span className="font-sans text-sm italic text-subtle">Not addressed in this document</span>
                        )}
                      </dd>
                    </div>
                  ))}
                </dl>
              )}
            </section>
          );
        })}
      </div>

      <CoverageLedger coverage={summary.coverage} />
    </div>
  );
}

/** States exactly what was read, so nothing is silently truncated (FR-17). */
function CoverageLedger({ coverage }: { coverage: SummaryResult['coverage'] }) {
  const full = coverage.pagesCovered === coverage.pagesTotal && coverage.skippedPages.length === 0;
  const pct = coverage.pagesTotal ? Math.round((coverage.pagesCovered / coverage.pagesTotal) * 100) : 0;
  return (
    <footer className="flex items-start gap-2.5 border-t border-border bg-bg/60 px-4 py-3 text-[13px]">
      {full ? <CheckCircle2 className="mt-px size-4 shrink-0 text-success" /> : <AlertTriangle className="mt-px size-4 shrink-0 text-warning" />}
      <div className="min-w-0 flex-1">
        <p className="text-ink">
          <span className="font-medium">Coverage:</span> {coverage.pagesCovered} of {coverage.pagesTotal} pages read
          {full && ' — the whole document'}.
        </p>
        {coverage.note && <p className="mt-0.5 text-muted">{coverage.note}</p>}
        <div className="mt-2 h-1.5 w-full max-w-[240px] overflow-hidden rounded-full bg-border" aria-hidden>
          <div className={cn('h-full rounded-full', full ? 'bg-success' : 'bg-warning')} style={{ width: `${pct}%` }} />
        </div>
      </div>
    </footer>
  );
}
