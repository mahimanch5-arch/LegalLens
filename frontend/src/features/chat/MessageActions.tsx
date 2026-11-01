import { Check, Copy, Download, RefreshCw, ThumbsDown, ThumbsUp } from 'lucide-react';
import { useState } from 'react';
import { useSendFeedback } from '@/api/queries';
import type { AssistantMessage } from '@/api/types';
import { Button, IconButton } from '@/components/ui/Button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/Popover';
import { cn } from '@/lib/cn';
import { toast } from '@/stores/toast';
import { downloadMarkdown, toMarkdown } from '../draft/exportMarkdown';

const REASONS = [
  'Wrong or unsupported citation',
  'Answer not supported by the source',
  'Missed something in my documents',
  'Should have answered, but refused',
  'Other',
];

interface Props {
  conversationId: string;
  message: AssistantMessage;
  question?: string;
  title: string;
  onRetry?: () => void;
}

/** Copy, export, regenerate and feedback (FR-24, FR-25). */
export function MessageActions({ conversationId, message, question, title, onRetry }: Props) {
  const [copied, setCopied] = useState(false);
  const [downOpen, setDownOpen] = useState(false);
  const [reason, setReason] = useState<string | null>(null);
  const [comment, setComment] = useState('');
  const feedback = useSendFeedback();
  const rating = message.feedback?.rating;
  const persisted = !message.id.startsWith('tmp_');

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(toMarkdown(message, question));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      toast({ title: "Couldn't copy to the clipboard", description: 'Your browser blocked clipboard access. Use Export instead.', tone: 'warning' });
    }
  };

  const rate = (r: 'up' | 'down', extra?: { reason?: string; comment?: string }) => {
    feedback.mutate({ conversationId, messageId: message.id, rating: r, ...extra });
  };

  return (
    <div className="-ml-1.5 mt-3 flex items-center gap-0.5">
      <IconButton size="sm" label={copied ? 'Copied' : 'Copy as Markdown'} onClick={copy}>
        {copied ? <Check className="text-success" /> : <Copy />}
      </IconButton>
      <IconButton size="sm" label="Export as Markdown file" onClick={() => downloadMarkdown(title, toMarkdown(message, question))}>
        <Download />
      </IconButton>
      {onRetry && (
        <IconButton size="sm" label="Regenerate" onClick={onRetry}>
          <RefreshCw />
        </IconButton>
      )}
      {persisted && (
        <>
          <span className="mx-1 h-4 w-px bg-border" aria-hidden />
          <IconButton size="sm" label="Good response" active={rating === 'up'} aria-pressed={rating === 'up'} onClick={() => rate('up')}>
            <ThumbsUp className={cn(rating === 'up' && 'fill-primary/15')} />
          </IconButton>
          <Popover open={downOpen} onOpenChange={setDownOpen}>
            <PopoverTrigger asChild>
              <IconButton size="sm" label="Bad response" active={rating === 'down'} aria-pressed={rating === 'down'}>
                <ThumbsDown className={cn(rating === 'down' && 'fill-primary/15')} />
              </IconButton>
            </PopoverTrigger>
            <PopoverContent className="w-[320px] p-4" align="start">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  rate('down', { reason: reason ?? undefined, comment: comment.trim() || undefined });
                  setDownOpen(false);
                  toast({ title: 'Thanks for the feedback', description: 'It is linked to this answer and its retrieval trace for review.', tone: 'success' });
                }}
              >
                <p className="text-sm font-medium text-ink">What went wrong?</p>
                <div className="mt-2.5 flex flex-wrap gap-1.5" role="radiogroup" aria-label="Reason">
                  {REASONS.map((r) => (
                    <button
                      key={r}
                      type="button"
                      role="radio"
                      aria-checked={reason === r}
                      onClick={() => setReason(reason === r ? null : r)}
                      className={cn(
                        'rounded-full border px-2.5 py-1 text-xs transition-colors',
                        reason === r ? 'border-primary bg-primary-soft text-primary' : 'border-border text-muted hover:border-ink/25 hover:text-ink',
                      )}
                    >
                      {r}
                    </button>
                  ))}
                </div>
                <label className="mt-3 block text-xs font-medium text-muted" htmlFor={`fb-${message.id}`}>
                  Details (optional)
                </label>
                <textarea
                  id={`fb-${message.id}`}
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  rows={3}
                  placeholder="What should the answer have said?"
                  className="mt-1 w-full resize-none rounded-lg border border-border bg-bg px-2.5 py-2 text-sm placeholder:text-subtle focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/15"
                />
                <div className="mt-3 flex justify-end gap-2">
                  <Button size="sm" variant="ghost" onClick={() => setDownOpen(false)}>
                    Cancel
                  </Button>
                  <Button size="sm" variant="primary" type="submit">
                    Send feedback
                  </Button>
                </div>
              </form>
            </PopoverContent>
          </Popover>
        </>
      )}
    </div>
  );
}
