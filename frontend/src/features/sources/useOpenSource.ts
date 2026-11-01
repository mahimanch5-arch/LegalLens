import { useCallback } from 'react';
import type { AssistantMessage, Citation, Excerpt } from '@/api/types';
import { useUi } from '@/stores/ui';

/** Opens the Sources panel at a citation or excerpt of the given answer (FR-13). */
export function useOpenSource(message: AssistantMessage) {
  const openSources = useUi((s) => s.openSources);
  const { citations, excerpts, id } = message;

  const openCitation = useCallback(
    (c: Citation) =>
      openSources({
        documentId: c.documentId,
        documentName: c.documentName,
        page: c.page,
        highlight: { start: c.charStart, end: c.charEnd },
        citationN: c.n,
        citations,
        excerpts,
        messageId: id,
      }),
    [openSources, citations, excerpts, id],
  );

  const openExcerpt = useCallback(
    (e: Excerpt) => {
      const c = citations.find((x) => x.spanId === e.spanId);
      if (c) return openCitation(c);
      openSources({ documentId: e.documentId, documentName: e.documentName, page: e.page, citations, excerpts, messageId: id });
    },
    [citations, excerpts, id, openCitation, openSources],
  );

  const openAll = useCallback(() => {
    const first = citations[0] ?? excerpts[0];
    if (!first) return;
    openSources({ documentId: first.documentId, documentName: first.documentName, page: first.page, citations, excerpts, messageId: id }, 'all');
  }, [citations, excerpts, id, openSources]);

  return { openCitation, openExcerpt, openAll };
}
