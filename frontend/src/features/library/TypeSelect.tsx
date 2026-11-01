import { AlertCircle, ChevronDown } from 'lucide-react';
import { useUpdateDocumentType } from '@/api/queries';
import type { DocType, LegalDocument } from '@/api/types';
import { Menu, MenuCheckItem, MenuContent, MenuLabel, MenuTrigger } from '@/components/ui/Menu';
import { Tooltip } from '@/components/ui/Tooltip';
import { cn } from '@/lib/cn';
import { DOC_TYPE_LABEL } from '@/lib/format';

const DESCRIPTIONS: Record<DocType, string> = {
  contract: 'Agreements, amendments, SOWs',
  opinion: 'Judicial opinions and orders',
  pleading: 'Complaints, answers, motions',
  other: 'Anything else — generic summary',
};

/** Shows the detected type and lets the attorney override it (FR-5). The type picks the summary template. */
export function TypeSelect({ doc }: { doc: LegalDocument }) {
  const update = useUpdateDocumentType();
  const lowConfidence = !doc.typeOverridden && doc.typeConfidence < 0.8;

  if (doc.status !== 'ready') return <span className="text-sm text-subtle">—</span>;

  return (
    <Menu>
      <Tooltip
        content={
          doc.typeOverridden
            ? 'Set manually'
            : `Detected automatically · ${Math.round(doc.typeConfidence * 100)}% confidence${lowConfidence ? ' — please check' : ''}`
        }
      >
        <MenuTrigger
          aria-label={`Document type: ${DOC_TYPE_LABEL[doc.type]}. Change type`}
          className={cn(
            'inline-flex h-7 items-center gap-1 rounded-lg border px-2 text-[13px] transition-colors hover:border-ink/25 data-[state=open]:border-primary/50',
            lowConfidence ? 'border-warning/40 bg-warning-soft/60' : 'border-transparent hover:bg-surface',
          )}
        >
          {lowConfidence && <AlertCircle className="size-3.5 text-warning" />}
          <span className="text-ink">{DOC_TYPE_LABEL[doc.type]}</span>
          {doc.typeOverridden && <span className="text-[11px] text-subtle">· edited</span>}
          <ChevronDown className="size-3.5 text-subtle" />
        </MenuTrigger>
      </Tooltip>
      <MenuContent className="w-[250px]">
        <MenuLabel>Document type</MenuLabel>
        {(Object.keys(DOC_TYPE_LABEL) as DocType[]).map((t) => (
          <MenuCheckItem key={t} checked={doc.type === t} description={DESCRIPTIONS[t]} onSelect={() => update.mutate({ id: doc.id, type: t })}>
            {DOC_TYPE_LABEL[t]}
          </MenuCheckItem>
        ))}
      </MenuContent>
    </Menu>
  );
}
