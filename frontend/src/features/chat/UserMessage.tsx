import { FileText, Layers, PenLine, ScrollText } from 'lucide-react';
import { memo } from 'react';
import { useDocuments } from '@/api/queries';
import type { UserMessage as UserMsg } from '@/api/types';
import { docTitle, fullDateTime } from '@/lib/format';

export const UserMessage = memo(function UserMessage({ message }: { message: UserMsg }) {
  const { data: docs } = useDocuments();
  const nameOf = (id: string) => docTitle(docs?.find((d) => d.id === id)?.name ?? 'Deleted document');

  const chips: { icon: JSX.Element; label: string }[] = [];
  if (message.mode === 'summary') chips.push({ icon: <ScrollText />, label: 'Summary' });
  if (message.mode === 'ask') chips.push({ icon: <FileText />, label: 'Ask' });
  if (message.mode === 'draft' && message.draftParams) {
    const n = message.draftParams.sourceDocumentIds.length;
    chips.push({ icon: <PenLine />, label: `${message.draftParams.draftType === 'memo' ? 'Memo' : 'Case brief'} · ${n} source${n === 1 ? '' : 's'}` });
  } else if (message.scope.kind === 'documents') {
    const ids = message.scope.documentIds;
    chips.push({ icon: <Layers />, label: ids.length === 1 ? nameOf(ids[0]) : `${ids.length} documents` });
  }

  return (
    <div className="flex flex-col items-end" title={fullDateTime(message.createdAt)}>
      <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-bubble px-4 py-2.5 text-[15px] leading-relaxed text-ink">
        {message.text}
      </div>
      {chips.length > 0 && (
        <div className="mt-1.5 flex flex-wrap justify-end gap-1.5">
          {chips.map((c) => (
            <span key={c.label} className="inline-flex max-w-[260px] items-center gap-1 rounded-full border border-border bg-surface px-2 py-0.5 text-[11.5px] text-muted [&_svg]:size-3">
              {c.icon}
              <span className="truncate">{c.label}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
});
