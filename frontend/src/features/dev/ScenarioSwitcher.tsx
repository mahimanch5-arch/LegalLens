import { useQueryClient } from '@tanstack/react-query';
import { FlaskConical, RotateCcw, Trash } from 'lucide-react';
import { useSyncExternalStore } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/Popover';
import { cn } from '@/lib/cn';
import { db } from '@/mocks/db';
import { scenario, type NextReply, type StreamSpeed } from '@/mocks/scenario';

const REPLIES: { value: NextReply; label: string; hint: string }[] = [
  { value: 'normal', label: 'Normal', hint: 'Grounded answer from the mock engine' },
  { value: 'refusal', label: 'Refusal', hint: '“Not in your documents” (TS-3)' },
  { value: 'llm_unavailable', label: 'AI unavailable', hint: 'Excerpts shown, no answer (NFR-6)' },
  { value: 'rate_limited', label: 'Rate limited', hint: '429 with retry countdown' },
  { value: 'timeout', label: 'Timeout', hint: 'Fails after the search stage' },
  { value: 'interrupted', label: 'Interrupted', hint: 'Stream cut mid-answer (NFR-7)' },
];

/** Development-only panel for forcing hard-to-reach states. Not part of the product. */
export default function ScenarioSwitcher() {
  const s = useSyncExternalStore(scenario.subscribe, scenario.get);
  const qc = useQueryClient();
  const navigate = useNavigate();

  const resetData = (emptyLibrary: boolean) => {
    db.reset({ keepSession: true, emptyLibrary });
    qc.removeQueries({ queryKey: ['conversation'] });
    void qc.invalidateQueries();
    navigate('/');
  };

  return (
    <Popover>
      <PopoverTrigger
        className={cn(
          'inline-flex h-7 items-center gap-1.5 rounded-full border px-2.5 text-xs font-medium transition-colors',
          s.nextReply !== 'normal' || s.nextUploadFails
            ? 'border-warning/40 bg-warning-soft text-warning'
            : 'border-border bg-surface text-muted hover:text-ink',
        )}
        aria-label="Mock data settings"
      >
        <FlaskConical className="size-3.5" />
        Mock data
        {s.nextReply !== 'normal' && <span className="hidden sm:inline">· {REPLIES.find((r) => r.value === s.nextReply)?.label}</span>}
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[320px] p-4">
        <p className="text-sm font-semibold text-ink">Mock scenarios</p>
        <p className="mt-0.5 text-xs leading-5 text-muted">Developer tool. Forces states that are hard to reach with the mock API.</p>

        <p className="mt-4 text-[11px] font-semibold uppercase tracking-[0.08em] text-subtle">Next reply</p>
        <div className="mt-1.5 space-y-0.5" role="radiogroup" aria-label="Next reply">
          {REPLIES.map((r) => (
            <button
              key={r.value}
              role="radio"
              aria-checked={s.nextReply === r.value}
              onClick={() => scenario.set({ nextReply: r.value })}
              className={cn('flex w-full items-start gap-2.5 rounded-lg px-2 py-1.5 text-left hover:bg-ink/[0.04]', s.nextReply === r.value && 'bg-primary-soft hover:bg-primary-soft')}
            >
              <span className={cn('mt-1 size-3 shrink-0 rounded-full border', s.nextReply === r.value ? 'border-[4px] border-primary' : 'border-ink/30')} />
              <span>
                <span className="block text-[13px] font-medium text-ink">{r.label}</span>
                <span className="block text-[11.5px] text-muted">{r.hint}</span>
              </span>
            </button>
          ))}
        </div>
        <label className="mt-2 flex items-center gap-2 px-2 text-[13px] text-ink">
          <input type="checkbox" checked={s.sticky} onChange={(e) => scenario.set({ sticky: e.target.checked })} className="accent-[rgb(var(--primary))]" />
          Keep applying (otherwise it resets after one reply)
        </label>

        <p className="mt-4 text-[11px] font-semibold uppercase tracking-[0.08em] text-subtle">Stream speed</p>
        <div className="mt-1.5 flex rounded-lg bg-ink/[0.04] p-0.5">
          {(['fast', 'normal', 'slow'] as StreamSpeed[]).map((sp) => (
            <button
              key={sp}
              onClick={() => scenario.set({ speed: sp })}
              className={cn('h-7 flex-1 rounded-md text-xs font-medium capitalize', s.speed === sp ? 'bg-surface text-primary shadow-soft' : 'text-muted')}
            >
              {sp}
            </button>
          ))}
        </div>

        <label className="mt-4 flex items-center gap-2 px-0.5 text-[13px] text-ink">
          <input type="checkbox" checked={s.nextUploadFails} onChange={(e) => scenario.set({ nextUploadFails: e.target.checked })} className="accent-[rgb(var(--primary))]" />
          Make the next uploaded file fail
        </label>

        <div className="mt-4 flex gap-2 border-t border-border pt-3">
          <Button size="sm" icon={<RotateCcw className="size-3.5" />} onClick={() => resetData(false)}>
            Reset demo data
          </Button>
          <Button size="sm" variant="ghost" icon={<Trash className="size-3.5" />} onClick={() => resetData(true)}>
            Empty workspace
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
