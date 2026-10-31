import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDocuments } from '@/api/queries';
import type { DocStatus } from '@/api/types';
import { docTitle } from '@/lib/format';
import { askAbout } from '@/lib/startChat';
import { toast } from '@/stores/toast';

/** Announces background ingestion outcomes wherever the user is in the app. */
export function useDocumentStatusToasts() {
  const { data: docs } = useDocuments();
  const prev = useRef<Map<string, DocStatus> | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!docs) return;
    const before = prev.current;
    prev.current = new Map(docs.map((d) => [d.id, d.status]));
    if (!before) return; // first load: nothing has "changed"
    for (const d of docs) {
      const was = before.get(d.id);
      if (!was || was === d.status || was === 'ready' || was === 'failed') continue;
      if (d.status === 'ready') {
        toast({
          title: `${docTitle(d.name)} is ready`,
          description: `${d.pages ?? '?'} pages indexed and searchable.`,
          tone: 'success',
          action: { label: 'Ask about it', onClick: () => askAbout(navigate, d.id) },
        });
      } else if (d.status === 'failed') {
        toast({ title: `${docTitle(d.name)} couldn’t be processed`, description: d.error, tone: 'danger', durationMs: 9000 });
      }
    }
  }, [docs, navigate]);
}
