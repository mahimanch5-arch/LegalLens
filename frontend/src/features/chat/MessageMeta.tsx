import { Info, Search, Sparkles } from 'lucide-react';
import type { AssistantMessage, Mode } from '@/api/types';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/Popover';
import { formatUsd, INTENT_LABEL } from '@/lib/format';

/** Scope used (FR-9), routed intent in Auto mode, and reproducibility details (NFR-12). */
export function MessageMeta({ message, userMode }: { message: AssistantMessage; userMode?: Mode }) {
  const { scopeUsed, intent, usage } = message;
  if (!scopeUsed && !intent) return null;

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
      {scopeUsed && (
        <span className="inline-flex items-center gap-1.5">
          <Search className="size-3.5 text-subtle" />
          {intent === 'draft' ? 'Sources' : intent === 'summary' ? 'Document' : 'Searched'}:
          <span className="font-medium text-ink">{scopeUsed.label}</span>
        </span>
      )}
      {userMode === 'auto' && intent && (
        <span className="inline-flex items-center gap-1.5">
          <Sparkles className="size-3.5 text-accent" />
          Handled as <span className="font-medium text-ink">{INTENT_LABEL[intent]}</span>
        </span>
      )}
      {message.status !== 'streaming' && message.traceId && (
        <Popover>
          <PopoverTrigger className="inline-flex items-center gap-1 rounded px-1 text-subtle hover:text-ink" aria-label="Response details">
            <Info className="size-3.5" />
            Details
          </PopoverTrigger>
          <PopoverContent className="w-[290px] p-3.5 text-xs" align="start">
            <p className="text-[13px] font-medium text-ink">Response details</p>
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5">
              <dt className="text-muted">Trace</dt>
              <dd className="truncate font-mono text-[11px] text-ink">{message.traceId}</dd>
              {message.modelVersion && (
                <>
                  <dt className="text-muted">Model</dt>
                  <dd className="font-mono text-[11px] text-ink">{message.modelVersion}</dd>
                </>
              )}
              {message.promptVersion && (
                <>
                  <dt className="text-muted">Prompt</dt>
                  <dd className="font-mono text-[11px] text-ink">{message.promptVersion}</dd>
                </>
              )}
              {usage && (
                <>
                  <dt className="text-muted">Tokens</dt>
                  <dd className="text-ink">
                    {usage.inputTokens.toLocaleString()} in · {usage.outputTokens.toLocaleString()} out
                  </dd>
                  <dt className="text-muted">Cost</dt>
                  <dd className="text-ink">{formatUsd(usage.costUsd)}</dd>
                  <dt className="text-muted">Time</dt>
                  <dd className="text-ink">{(usage.latencyMs / 1000).toFixed(1)} s</dd>
                </>
              )}
            </dl>
            <p className="mt-3 border-t border-border pt-2.5 leading-5 text-muted">
              An attorney work-product aid, not legal advice. You remain responsible for any use of this output.
            </p>
          </PopoverContent>
        </Popover>
      )}
    </div>
  );
}
