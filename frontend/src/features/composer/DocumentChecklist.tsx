import { Check, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import type { LegalDocument } from '@/api/types';
import { Pill } from '@/components/ui/Pill';
import { cn } from '@/lib/cn';
import { DOC_TYPE_LABEL, docTitle, STATUS_LABEL } from '@/lib/format';

interface Props {
  documents: LegalDocument[];
  selected: string[];
  onChange: (ids: string[]) => void;
  single?: boolean;
  /** Highlights documents of this type as the expected choice (e.g. opinions for a brief). */
  preferType?: LegalDocument['type'];
  maxHeight?: number;
}

/** Searchable document list used by the scope picker and the draft drawer. Only ready documents are selectable (FR-7). */
export function DocumentChecklist({ documents, selected, onChange, single, preferType, maxHeight = 260 }: Props) {
  const [q, setQ] = useState('');
  const list = useMemo(() => {
    const term = q.trim().toLowerCase();
    return documents
      .filter((d) => !term || d.name.toLowerCase().includes(term))
      .sort((a, b) => Number(b.status === 'ready') - Number(a.status === 'ready'));
  }, [documents, q]);

  const toggle = (id: string) => {
    if (single) return onChange([id]);
    onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  };

  return (
    <div>
      {documents.length > 5 && (
        <div className="relative mb-2">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-subtle" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Filter documents"
            aria-label="Filter documents"
            className="h-8 w-full rounded-lg border border-border bg-bg pl-8 pr-2 text-sm placeholder:text-subtle focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/15"
          />
        </div>
      )}
      <ul role={single ? 'radiogroup' : 'group'} className="-mx-1 overflow-y-auto" style={{ maxHeight }}>
        {list.map((d) => {
          const ready = d.status === 'ready';
          const on = selected.includes(d.id);
          return (
            <li key={d.id}>
              <button
                type="button"
                role={single ? 'radio' : 'checkbox'}
                aria-checked={on}
                disabled={!ready}
                onClick={() => toggle(d.id)}
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left text-sm transition-colors',
                  ready ? 'hover:bg-ink/[0.04]' : 'cursor-not-allowed opacity-50',
                )}
              >
                <span
                  className={cn(
                    'flex size-4 shrink-0 items-center justify-center border transition-colors',
                    single ? 'rounded-full' : 'rounded',
                    on ? 'border-primary bg-primary text-white' : 'border-ink/25 bg-surface',
                  )}
                >
                  {on && (single ? <span className="size-1.5 rounded-full bg-white" /> : <Check className="size-3" strokeWidth={3} />)}
                </span>
                <span className="min-w-0 flex-1 truncate text-ink">{docTitle(d.name)}</span>
                {ready ? (
                  <Pill tone={preferType && d.type === preferType ? 'primary' : 'neutral'} className="h-5 text-[11px]">
                    {DOC_TYPE_LABEL[d.type]}
                  </Pill>
                ) : (
                  <span className="text-[11px] text-subtle">{STATUS_LABEL[d.status]}</span>
                )}
              </button>
            </li>
          );
        })}
        {list.length === 0 && <li className="px-2 py-3 text-center text-sm text-subtle">No documents match.</li>}
      </ul>
    </div>
  );
}
