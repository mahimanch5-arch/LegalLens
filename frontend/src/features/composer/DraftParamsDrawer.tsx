import { BookOpenText, FileSignature } from 'lucide-react';
import type { ReactNode } from 'react';
import type { DraftTone, LegalDocument } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { cn } from '@/lib/cn';
import { useComposer } from '@/stores/composer';
import { DocumentChecklist } from './DocumentChecklist';

const TYPES = [
  { value: 'memo' as const, label: 'Legal memo', icon: <FileSignature />, structure: 'Question Presented → Short Answer → Statement of Facts → Discussion → Conclusion' },
  { value: 'brief' as const, label: 'Case brief', icon: <BookOpenText />, structure: 'Posture → Facts → Issue → Holding → Reasoning → Disposition' },
];
const TONES: DraftTone[] = ['neutral', 'formal', 'persuasive'];
const AUDIENCES = ['Supervising partner', 'Client', 'Litigation team', 'File'];

const inputCls =
  'w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-ink placeholder:text-subtle focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/15';

function Field({ label, hint, htmlFor, required, children }: { label: string; hint?: string; htmlFor?: string; required?: boolean; children: ReactNode }) {
  return (
    <div>
      <label htmlFor={htmlFor} className="text-[13px] font-medium text-ink">
        {label}
        {required ? <span className="text-danger"> *</span> : <span className="font-normal text-subtle"> (optional)</span>}
      </label>
      {hint && <p className="mt-0.5 text-xs leading-5 text-muted">{hint}</p>}
      <div className="mt-1.5">{children}</div>
    </div>
  );
}

/** Draft parameters (FR-18, FR-19). A draft without sources cannot be grounded, so sources are required. */
export function DraftParamsDrawer({ documents, onGenerate }: { documents: LegalDocument[]; onGenerate: () => void }) {
  const { draftDrawerOpen, setDraftDrawerOpen, draftParams: p, setDraftParams, text } = useComposer();
  const question = p.questionPresented || text;
  const valid = question.trim().length > 0 && p.sourceDocumentIds.length > 0;
  const hasOpinion = documents.some((d) => d.status === 'ready' && d.type === 'opinion' && p.sourceDocumentIds.includes(d.id));

  return (
    <Dialog
      open={draftDrawerOpen}
      onOpenChange={setDraftDrawerOpen}
      side="right"
      title="Draft settings"
      description="Legal Lens writes only from the sources you choose, and cites every factual statement."
      footer={
        <>
          <Button variant="ghost" onClick={() => setDraftDrawerOpen(false)}>
            Done
          </Button>
          <Button
            variant="primary"
            disabled={!valid}
            onClick={() => {
              if (!p.questionPresented) setDraftParams({ questionPresented: question });
              setDraftDrawerOpen(false);
              onGenerate();
            }}
          >
            Generate draft
          </Button>
        </>
      }
    >
      <div className="space-y-5 pb-2">
        <div role="radiogroup" aria-label="Draft type" className="grid grid-cols-2 gap-2">
          {TYPES.map((t) => (
            <button
              key={t.value}
              type="button"
              role="radio"
              aria-checked={p.draftType === t.value}
              onClick={() => setDraftParams({ draftType: t.value })}
              className={cn(
                'rounded-xl border p-3 text-left transition-all',
                p.draftType === t.value ? 'border-primary bg-primary-soft/60 ring-1 ring-primary/30' : 'border-border hover:border-ink/25',
              )}
            >
              <span className={cn('flex items-center gap-2 text-sm font-medium [&_svg]:size-4', p.draftType === t.value ? 'text-primary' : 'text-ink')}>
                {t.icon}
                {t.label}
              </span>
              <span className="mt-1 block text-[11.5px] leading-4 text-muted">{t.structure}</span>
            </button>
          ))}
        </div>

        <Field label="Question presented" htmlFor="dp-q" required hint="The legal question the draft must answer.">
          <textarea
            id="dp-q"
            rows={3}
            value={p.questionPresented || text}
            onChange={(e) => setDraftParams({ questionPresented: e.target.value })}
            placeholder="e.g. Can Acme terminate the Northwind MSA for breach by giving notice by email alone?"
            className={cn(inputCls, 'resize-none')}
          />
        </Field>

        <Field label="Position to argue" htmlFor="dp-pos" hint="The draft argues from this position, without inventing support for it. Contrary points are noted, not hidden.">
          <textarea
            id="dp-pos"
            rows={2}
            value={p.position}
            onChange={(e) => setDraftParams({ position: e.target.value })}
            placeholder="e.g. Acme's email notice of breach was effective"
            className={cn(inputCls, 'resize-none')}
          />
        </Field>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="Audience" htmlFor="dp-aud">
            <input id="dp-aud" list="dp-aud-list" value={p.audience} onChange={(e) => setDraftParams({ audience: e.target.value })} className={inputCls} />
            <datalist id="dp-aud-list">
              {AUDIENCES.map((a) => (
                <option key={a} value={a} />
              ))}
            </datalist>
          </Field>
          <Field label="Tone" required>
            <div role="radiogroup" aria-label="Tone" className="flex rounded-lg bg-ink/[0.04] p-0.5">
              {TONES.map((t) => (
                <button
                  key={t}
                  type="button"
                  role="radio"
                  aria-checked={p.tone === t}
                  onClick={() => setDraftParams({ tone: t })}
                  className={cn('h-8 flex-1 rounded-md text-[13px] font-medium capitalize transition-all', p.tone === t ? 'bg-surface text-primary shadow-soft' : 'text-muted hover:text-ink')}
                >
                  {t}
                </button>
              ))}
            </div>
          </Field>
        </div>

        <Field
          label="Source documents"
          required
          hint={p.draftType === 'brief' ? 'A case brief is written from a judicial opinion — include at least one.' : 'Only these documents will be retrieved from and cited.'}
        >
          <div className="rounded-xl border border-border p-2">
            <DocumentChecklist
              documents={documents}
              selected={p.sourceDocumentIds}
              onChange={(ids) => setDraftParams({ sourceDocumentIds: ids })}
              preferType={p.draftType === 'brief' ? 'opinion' : undefined}
              maxHeight={220}
            />
          </div>
          {p.draftType === 'brief' && p.sourceDocumentIds.length > 0 && !hasOpinion && (
            <p className="mt-1.5 text-xs text-warning">None of the selected sources is an opinion, so a brief can’t be grounded.</p>
          )}
        </Field>
      </div>
    </Dialog>
  );
}
