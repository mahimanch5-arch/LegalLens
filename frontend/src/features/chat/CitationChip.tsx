import { FileText } from 'lucide-react';
import type { Citation } from '@/api/types';
import { Tooltip } from '@/components/ui/Tooltip';
import { cn } from '@/lib/cn';
import { docTitle } from '@/lib/format';

interface Props {
  citation: Citation;
  active?: boolean;
  onOpen: (c: Citation) => void;
}

export function CitationChip({ citation, active, onOpen }: Props) {
  const label = `Source ${citation.n}: ${docTitle(citation.documentName)}, page ${citation.page}${citation.section ? `, ${citation.section}` : ''}`;
  return (
    <Tooltip
      side="top"
      className="block max-w-[340px] bg-surface p-0 text-ink ring-1 ring-border"
      content={
        <span className="block p-3 text-left">
          <span className="flex items-center gap-1.5 text-xs font-semibold text-ink">
            <FileText className="size-3.5 shrink-0 text-primary" />
            <span className="truncate">{docTitle(citation.documentName)}</span>
          </span>
          <span className="mt-0.5 block text-[11px] font-medium text-muted">
            Page {citation.page}
            {citation.section && ` · ${citation.section}`}
          </span>
          <span className="mt-2 line-clamp-4 block border-l-2 border-highlight pl-2 font-serif text-[13px] font-normal leading-5 text-ink">
            {citation.quote}
          </span>
          <span className="mt-2 block text-[11px] font-normal text-subtle">Click to open the source</span>
        </span>
      }
    >
      <button
        type="button"
        onClick={() => onOpen(citation)}
        aria-label={label}
        className={cn(
          'mx-[1px] inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-[5px] px-1 align-[2px] font-sans text-[11px] font-semibold leading-none transition-colors',
          active ? 'bg-primary text-white' : 'bg-primary-soft text-primary hover:bg-primary hover:text-white',
        )}
      >
        {citation.n}
      </button>
    </Tooltip>
  );
}
