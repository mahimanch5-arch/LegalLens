import { AlertTriangle, ArrowLeft, ChevronLeft, ChevronRight, FileQuestion, MessageSquareText, ScrollText } from 'lucide-react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useDocuments } from '@/api/queries';
import { Button, IconButton } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { Pill } from '@/components/ui/Pill';
import { cn } from '@/lib/cn';
import { DOC_TYPE_LABEL, docTitle, formatBytes, shortDate } from '@/lib/format';
import { askAbout, summarise } from '@/lib/startChat';
import { DocumentPageView } from '../sources/DocumentPageView';

/** Full-page reader for one document, reachable from the Library and from "Open" in the Sources panel. */
export function DocumentPage() {
  const { documentId = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const { data: docs, isLoading } = useDocuments();
  const doc = docs?.find((d) => d.id === documentId);
  const total = doc?.pages ?? 1;
  const page = Math.min(Math.max(1, Number(params.get('page')) || 1), total);
  const go = (p: number) => setParams({ page: String(p) }, { replace: true });

  if (isLoading) return <div className="flex-1" aria-busy />;
  if (!doc || doc.status !== 'ready') {
    return (
      <div className="flex flex-1 items-center justify-center">
        <EmptyState icon={<FileQuestion />} title={doc ? 'This document isn’t ready yet' : 'Document not found'} action={<Link to="/library" className="text-sm font-medium text-primary hover:underline">Back to Library</Link>}>
          {doc ? 'It can be opened once processing finishes.' : 'It may have been deleted.'}
        </EmptyState>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1">
      <nav aria-label="Pages" className="hidden w-[132px] shrink-0 overflow-y-auto border-r border-border px-3 py-4 md:block">
        <ol className="space-y-1">
          {Array.from({ length: total }, (_, i) => i + 1).map((n) => (
            <li key={n}>
              <button
                onClick={() => go(n)}
                aria-current={n === page ? 'page' : undefined}
                className={cn(
                  'flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-xs tabular-nums transition-colors',
                  n === page ? 'bg-primary-soft font-semibold text-primary' : 'text-muted hover:bg-ink/[0.04] hover:text-ink',
                )}
              >
                Page {n}
                {doc.lowOcrPages.includes(n) && <AlertTriangle className="size-3 text-warning" aria-label="Low OCR confidence" />}
              </button>
            </li>
          ))}
        </ol>
      </nav>

      <div className="min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[820px] px-4 py-5 sm:px-8">
          <Link to="/library" className="inline-flex items-center gap-1 text-[13px] text-muted hover:text-ink">
            <ArrowLeft className="size-3.5" /> Library
          </Link>
          <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="font-serif text-2xl font-semibold leading-snug text-ink">{docTitle(doc.name)}</h2>
              <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-muted">
                <Pill tone="primary">{DOC_TYPE_LABEL[doc.type]}</Pill>
                <span>{doc.pages} pages</span>
                <span>·</span>
                <span>{formatBytes(doc.sizeBytes)}</span>
                <span>·</span>
                <span>Uploaded {shortDate(doc.uploadedAt)}</span>
              </div>
            </div>
            <div className="flex gap-2">
              <Button icon={<ScrollText className="size-4" />} onClick={() => summarise(navigate, doc.id)}>
                Summarise
              </Button>
              <Button variant="primary" icon={<MessageSquareText className="size-4" />} onClick={() => askAbout(navigate, doc.id)}>
                Ask about this
              </Button>
            </div>
          </div>

          <div className="mt-5 flex items-center justify-between">
            <IconButton label="Previous page" disabled={page <= 1} onClick={() => go(page - 1)}>
              <ChevronLeft />
            </IconButton>
            <span className="text-sm tabular-nums text-muted">
              Page {page} of {total}
            </span>
            <IconButton label="Next page" disabled={page >= total} onClick={() => go(page + 1)}>
              <ChevronRight />
            </IconButton>
          </div>
          <DocumentPageView documentId={doc.id} page={page} totalPages={total} className="mt-3" />
        </div>
      </div>
    </div>
  );
}
