import { ChevronDown, FileText, Library, Layers } from 'lucide-react';
import { useState } from 'react';
import type { LegalDocument, Scope } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/Popover';
import { cn } from '@/lib/cn';
import { docTitle } from '@/lib/format';
import { DocumentChecklist } from './DocumentChecklist';

const triggerCls =
  'inline-flex h-8 max-w-[220px] items-center gap-1.5 rounded-lg px-2 text-[13px] font-medium text-muted transition-colors hover:bg-ink/[0.05] hover:text-ink data-[state=open]:bg-ink/[0.05] data-[state=open]:text-ink [&_svg]:size-3.5';

/** Ask scope: whole workspace, or a chosen subset (FR-8, FR-9). */
export function ScopePicker({ scope, onChange, documents }: { scope: Scope; onChange: (s: Scope) => void; documents: LegalDocument[] }) {
  const [open, setOpen] = useState(false);
  const ready = documents.filter((d) => d.status === 'ready');
  const ids = scope.kind === 'documents' ? scope.documentIds.filter((id) => ready.some((d) => d.id === id)) : [];
  const [draft, setDraft] = useState<string[]>(ids);

  const label =
    scope.kind === 'workspace' || ids.length === 0
      ? 'Whole workspace'
      : ids.length === 1
        ? docTitle(ready.find((d) => d.id === ids[0])?.name ?? 'Document')
        : `${ids.length} documents`;

  return (
    <Popover
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (o) setDraft(ids);
      }}
    >
      <PopoverTrigger className={triggerCls} aria-label={`Search scope: ${label}`}>
        {scope.kind === 'workspace' || ids.length === 0 ? <Library /> : ids.length === 1 ? <FileText /> : <Layers />}
        <span className="truncate">{label}</span>
        <ChevronDown className="shrink-0 opacity-60" />
      </PopoverTrigger>
      <PopoverContent className="w-[340px] p-2" align="start" side="top">
        <p className="px-2 pb-1 pt-1 text-xs font-semibold uppercase tracking-[0.06em] text-subtle">Search in</p>
        <button
          type="button"
          onClick={() => {
            onChange({ kind: 'workspace' });
            setOpen(false);
          }}
          className={cn('flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-left hover:bg-ink/[0.04]', scope.kind === 'workspace' && 'bg-primary-soft hover:bg-primary-soft')}
        >
          <Library className="size-4 text-primary" />
          <span className="flex-1">
            <span className="block text-sm font-medium text-ink">Whole workspace</span>
            <span className="block text-xs text-muted">All {ready.length} ready documents</span>
          </span>
        </button>
        <div className="my-2 h-px bg-border" />
        <p className="px-2 pb-2 text-xs font-semibold uppercase tracking-[0.06em] text-subtle">Or choose documents</p>
        <div className="px-1">
          <DocumentChecklist documents={documents} selected={draft} onChange={setDraft} maxHeight={220} />
        </div>
        <div className="mt-2 flex items-center justify-between border-t border-border px-1 pt-2">
          <span className="text-xs text-muted">{draft.length} selected</span>
          <Button
            size="sm"
            variant="primary"
            disabled={draft.length === 0}
            onClick={() => {
              onChange({ kind: 'documents', documentIds: draft });
              setOpen(false);
            }}
          >
            Search {draft.length === 1 ? 'this document' : 'these documents'}
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}

/** Summary target: exactly one document. */
export function SummaryDocPicker({ value, onChange, documents }: { value: string | null; onChange: (id: string) => void; documents: LegalDocument[] }) {
  const [open, setOpen] = useState(false);
  const doc = documents.find((d) => d.id === value && d.status === 'ready');
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger className={cn(triggerCls, !doc && 'text-primary')} aria-label={doc ? `Document to summarise: ${docTitle(doc.name)}` : 'Choose a document to summarise'}>
        <FileText />
        <span className="truncate">{doc ? docTitle(doc.name) : 'Choose document'}</span>
        <ChevronDown className="shrink-0 opacity-60" />
      </PopoverTrigger>
      <PopoverContent className="w-[340px] p-2" align="start" side="top">
        <p className="px-2 pb-2 pt-1 text-xs font-semibold uppercase tracking-[0.06em] text-subtle">Summarise one document</p>
        <div className="px-1">
          <DocumentChecklist
            single
            documents={documents}
            selected={doc ? [doc.id] : []}
            onChange={(ids) => {
              onChange(ids[0]);
              setOpen(false);
            }}
          />
        </div>
        <p className="mt-1 border-t border-border px-2 pt-2 text-xs leading-5 text-muted">The summary template follows the document’s type. Change a type in the Library if it’s wrong.</p>
      </PopoverContent>
    </Popover>
  );
}
