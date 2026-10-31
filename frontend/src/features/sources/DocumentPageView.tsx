import { AlertTriangle, FileX } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { useDocumentPage } from '@/api/queries';
import { cn } from '@/lib/cn';

interface Props {
  documentId: string;
  page: number;
  totalPages?: number | null;
  highlight?: { start: number; end: number };
  className?: string;
}

/**
 * One page of extracted text with the cited character span highlighted and scrolled into
 * view (FR-13). With the real backend this gains the rendered page image underneath.
 */
export function DocumentPageView({ documentId, page, totalPages, highlight, className }: Props) {
  const { data, isLoading, isError } = useDocumentPage(documentId, page);
  const markRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (data && highlight) markRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [data, highlight]);

  if (isLoading) {
    return (
      <div className={cn('rounded-lg border border-border bg-surface p-6 shadow-soft', className)} aria-busy aria-label="Loading page">
        <div className="space-y-2.5">
          {[100, 92, 97, 60, 0, 95, 88, 99, 40].map((w, i) => (w ? <div key={i} className="skeleton h-3.5" style={{ width: `${w}%` }} /> : <div key={i} className="h-3" />))}
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className={cn('flex flex-col items-center rounded-lg border border-border bg-surface px-6 py-12 text-center', className)}>
        <FileX className="size-6 text-subtle" />
        <p className="mt-2 text-sm font-medium text-ink">This page isn’t available</p>
        <p className="mt-1 text-[13px] text-muted">The document may have been deleted or is still processing.</p>
      </div>
    );
  }

  const text = data.text;
  const hl = highlight && highlight.end <= text.length ? highlight : undefined;

  return (
    <div className={className}>
      {data.lowOcr && (
        <div className="mb-3 flex items-start gap-2 rounded-lg border border-warning/30 bg-warning-soft px-3 py-2 text-[13px] text-ink">
          <AlertTriangle className="mt-px size-4 shrink-0 text-warning" />
          <span>
            <span className="font-medium">Low OCR confidence ({Math.round(data.ocrConfidence * 100)}%).</span> This page was scanned and the text may contain recognition errors. Check the original before relying on it.
          </span>
        </div>
      )}
      <div
        role="region"
        aria-label={`Page ${page}${totalPages ? ` of ${totalPages}` : ''}`}
        className="relative rounded-lg border border-border bg-surface px-6 pb-8 pt-6 shadow-soft sm:px-8"
      >
        <div className="source-text whitespace-pre-wrap font-serif text-[14.5px] leading-[1.75] text-ink">
          {hl ? (
            <>
              {text.slice(0, hl.start)}
              <mark ref={markRef} tabIndex={-1}>
                <span className="sr-only">Cited passage: </span>
                {text.slice(hl.start, hl.end)}
                <span className="sr-only"> (end of cited passage)</span>
              </mark>
              {text.slice(hl.end)}
            </>
          ) : (
            text
          )}
        </div>
        <div className="absolute bottom-2.5 left-0 right-0 text-center text-[11px] text-subtle">
          — {page}
          {totalPages ? ` of ${totalPages}` : ''} —
        </div>
      </div>
    </div>
  );
}
