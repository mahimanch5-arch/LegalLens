import { memo, useMemo } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Citation } from '@/api/types';
import { linkCitations } from '@/lib/citations';
import { cn } from '@/lib/cn';
import { CitationChip } from './CitationChip';

interface Props {
  md: string;
  citations: Citation[];
  onCite: (c: Citation) => void;
  activeCitation?: number;
  streaming?: boolean;
  className?: string;
}

export const Markdown = memo(function Markdown({ md, citations, onCite, activeCitation, streaming, className }: Props) {
  const components = useMemo<Components>(
    () => ({
      a({ href, children }) {
        const m = href?.match(/^#cite-(\d+)$/);
        if (m) {
          const c = citations.find((x) => x.n === Number(m[1]));
          // A marker with no verified citation is never shown as a link (FR-21).
          return c ? <CitationChip citation={c} onOpen={onCite} active={activeCitation === c.n} /> : null;
        }
        return (
          <a href={href} target="_blank" rel="noreferrer noopener" className="text-primary underline underline-offset-2">
            {children}
          </a>
        );
      },
    }),
    [citations, onCite, activeCitation],
  );

  return (
    <div className={cn('answer', streaming && 'stream-cursor', className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {linkCitations(md, streaming)}
      </ReactMarkdown>
    </div>
  );
});
