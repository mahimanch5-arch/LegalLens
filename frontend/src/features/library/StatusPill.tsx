import { CheckCircle2, Clock, XCircle } from 'lucide-react';
import type { LegalDocument } from '@/api/types';
import { Pill } from '@/components/ui/Pill';
import { Spinner } from '@/components/ui/Spinner';
import { STATUS_LABEL } from '@/lib/format';

/** Per-file ingestion status, live while processing (FR-3). */
export function StatusPill({ doc }: { doc: LegalDocument }) {
  switch (doc.status) {
    case 'ready':
      return <Pill tone="success" icon={<CheckCircle2 />}>Ready</Pill>;
    case 'failed':
      return <Pill tone="danger" icon={<XCircle />}>Failed</Pill>;
    case 'queued':
      return <Pill icon={<Clock />}>Queued</Pill>;
    default:
      return (
        <span className="inline-flex flex-col gap-1" aria-label={`${STATUS_LABEL[doc.status]}, ${doc.progress}%`}>
          <Pill tone="primary" icon={<Spinner className="size-3" />}>
            {STATUS_LABEL[doc.status]} {doc.progress}%
          </Pill>
          <span className="h-1 w-[92px] overflow-hidden rounded-full bg-primary-soft" aria-hidden>
            <span className="block h-full rounded-full bg-primary transition-[width] duration-700" style={{ width: `${doc.status === 'parsing' ? doc.progress / 2 : 50 + doc.progress / 2}%` }} />
          </span>
        </span>
      );
  }
}
