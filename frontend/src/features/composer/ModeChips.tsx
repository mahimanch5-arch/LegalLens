import { MessageSquareText, PenLine, ScrollText, Sparkles } from 'lucide-react';
import type { Mode } from '@/api/types';
import { Tooltip } from '@/components/ui/Tooltip';
import { cn } from '@/lib/cn';

const MODES: { mode: Mode; label: string; icon: JSX.Element; hint: string }[] = [
  { mode: 'auto', label: 'Auto', icon: <Sparkles />, hint: 'Legal Lens decides whether to answer, summarise or draft' },
  { mode: 'ask', label: 'Ask', icon: <MessageSquareText />, hint: 'A cited answer to a question' },
  { mode: 'summary', label: 'Summary', icon: <ScrollText />, hint: 'A structured summary of one document' },
  { mode: 'draft', label: 'Draft', icon: <PenLine />, hint: 'A first-draft memo or case brief' },
];

export function ModeChips({ value, onChange, disabled }: { value: Mode; onChange: (m: Mode) => void; disabled?: boolean }) {
  return (
    <div role="radiogroup" aria-label="Mode" className="flex items-center gap-0.5 rounded-lg bg-ink/[0.04] p-0.5">
      {MODES.map((m) => {
        const active = value === m.mode;
        return (
          <Tooltip key={m.mode} content={m.hint}>
            <button
              type="button"
              role="radio"
              aria-checked={active}
              disabled={disabled}
              onClick={() => onChange(m.mode)}
              className={cn(
                'inline-flex h-7 items-center gap-1.5 rounded-md px-2 text-[13px] font-medium transition-all [&_svg]:size-3.5',
                active ? 'bg-surface text-primary shadow-[0_1px_2px_rgb(28_27_25/0.08),0_0_0_1px_rgb(var(--border))]' : 'text-muted hover:text-ink',
              )}
            >
              {m.icon}
              <span className={cn(!active && 'hidden sm:inline')}>{m.label}</span>
            </button>
          </Tooltip>
        );
      })}
    </div>
  );
}
