import { AlertTriangle, CloudOff, Clock, FileWarning, RefreshCw, SearchX, ServerCrash } from 'lucide-react';
import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import type { ApiErrorBody, Refusal } from '@/api/types';
import { Button } from '@/components/ui/Button';

/**
 * "Not in your documents" is a first-class, successful outcome (TS-3), so it is calm and
 * neutral — never red, never styled like an error.
 */
export function RefusalCard({ refusal, onWiden }: { refusal: Refusal; onWiden?: () => void }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4 shadow-soft">
      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary">
          <SearchX className="size-[18px]" />
        </span>
        <div className="min-w-0">
          <p className="font-medium text-ink">Not answerable from your documents</p>
          <p className="mt-1 font-serif text-[15.5px] leading-relaxed text-ink">{refusal.reason}</p>
          <p className="mt-2 text-[13px] text-muted">
            Searched: <span className="font-medium text-ink">{refusal.scopeLabel}</span>
          </p>
          {refusal.suggestions.length > 0 && (
            <div className="mt-3 border-t border-border pt-3">
              <p className="text-xs font-semibold uppercase tracking-[0.06em] text-subtle">You could</p>
              <ul className="mt-1.5 space-y-1 text-sm text-muted">
                {refusal.suggestions.map((s) => (
                  <li key={s} className="flex gap-2">
                    <span className="mt-2 size-1 shrink-0 rounded-full bg-subtle" />
                    {s}
                  </li>
                ))}
              </ul>
              <div className="mt-3 flex flex-wrap gap-2">
                {onWiden && (
                  <Button size="sm" variant="secondary" onClick={onWiden}>
                    Search whole workspace
                  </Button>
                )}
                <Link to="/library" className="inline-flex h-8 items-center rounded-lg px-2.5 text-[13px] font-medium text-primary hover:bg-primary-soft">
                  Go to Library
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const ERROR_COPY: Record<ApiErrorBody['code'], { title: string; icon: ReactNode; next: string }> = {
  llm_unavailable: { title: 'AI service unavailable', icon: <CloudOff />, next: 'Try again in a minute. The excerpts below are still available to read.' },
  rate_limited: { title: 'Too many requests', icon: <Clock />, next: 'Wait a moment, then retry.' },
  timeout: { title: 'The response timed out', icon: <Clock />, next: 'Retry, or narrow the scope to fewer documents for a faster answer.' },
  parse_failure: { title: "A document couldn't be read", icon: <FileWarning />, next: 'Check the document in the Library and re-upload it.' },
  unknown: { title: 'Something went wrong', icon: <ServerCrash />, next: 'Try again. If it keeps happening, reload the page.' },
};

/** Actionable error state, always naming a next step (FR-28). */
export function ErrorCard({ error, onRetry }: { error: ApiErrorBody; onRetry?: () => void }) {
  const copy = ERROR_COPY[error.code] ?? ERROR_COPY.unknown;
  const [wait, setWait] = useState(error.retryAfterSec ?? 0);
  useEffect(() => {
    if (wait <= 0) return;
    const t = window.setTimeout(() => setWait((w) => w - 1), 1000);
    return () => window.clearTimeout(t);
  }, [wait]);

  return (
    <div role="alert" className="rounded-xl border border-danger/25 bg-danger-soft/60 p-4">
      <div className="flex items-start gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-danger-soft text-danger [&_svg]:size-[18px]">{copy.icon}</span>
        <div className="min-w-0 flex-1">
          <p className="font-medium text-ink">{copy.title}</p>
          <p className="mt-0.5 text-sm leading-6 text-muted">{error.message}</p>
          <p className="mt-1 text-sm text-ink">{copy.next}</p>
          {onRetry && (
            <Button size="sm" className="mt-3" icon={<RefreshCw className="size-3.5" />} onClick={onRetry} disabled={wait > 0}>
              {wait > 0 ? `Retry in ${wait}s` : 'Retry'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

/** An interrupted stream is never presented as complete (NFR-7). */
export function IncompleteNotice({ onRetry }: { onRetry?: () => void }) {
  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-warning/30 bg-warning-soft px-3 py-2 text-sm">
      <AlertTriangle className="size-4 shrink-0 text-warning" />
      <span className="flex-1 text-ink">
        <span className="font-medium">Incomplete.</span> This response was interrupted before it finished — don’t rely on it as a full answer.
      </span>
      {onRetry && (
        <button onClick={onRetry} className="inline-flex items-center gap-1 text-[13px] font-medium text-primary hover:underline">
          <RefreshCw className="size-3.5" /> Regenerate
        </button>
      )}
    </div>
  );
}
