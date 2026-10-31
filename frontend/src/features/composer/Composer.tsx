import { ArrowUp, Paperclip, SlidersHorizontal, Square, Upload } from 'lucide-react';
import { useEffect, useRef, type KeyboardEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDocuments, useUploadDocuments } from '@/api/queries';
import { UPLOAD_LIMITS, type SendMessageRequest } from '@/api/types';
import { Button, IconButton } from '@/components/ui/Button';
import { Tooltip } from '@/components/ui/Tooltip';
import { cn } from '@/lib/cn';
import { docTitle } from '@/lib/format';
import { useComposer } from '@/stores/composer';
import { toast } from '@/stores/toast';
import { DraftParamsDrawer } from './DraftParamsDrawer';
import { ModeChips } from './ModeChips';
import { ScopePicker, SummaryDocPicker } from './ScopePicker';

const PLACEHOLDER = {
  auto: 'Ask, summarise or draft from your documents…',
  ask: 'Ask a question about your documents…',
  summary: 'Anything to focus on? (optional)',
  draft: 'What should the draft address?',
};

interface Props {
  onSubmit: (req: SendMessageRequest) => void;
  streaming?: boolean;
  onStop?: () => void;
  autoFocus?: boolean;
  className?: string;
}

export function Composer({ onSubmit, streaming, onStop, autoFocus, className }: Props) {
  const c = useComposer();
  const { data: documents = [] } = useDocuments();
  const upload = useUploadDocuments();
  const navigate = useNavigate();
  const ta = useRef<HTMLTextAreaElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const ready = documents.filter((d) => d.status === 'ready');
  const noDocs = ready.length === 0;
  const summaryDoc = ready.find((d) => d.id === c.summaryDocumentId);

  // Grow with content, up to a cap.
  useEffect(() => {
    const el = ta.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 240)}px`;
  }, [c.text]);

  useEffect(() => {
    if (c.focusTick > 0 || autoFocus) ta.current?.focus();
  }, [c.focusTick, autoFocus]);

  const canSend =
    !streaming &&
    !noDocs &&
    (c.mode === 'summary' ? !!summaryDoc : c.mode === 'draft' ? !!(c.text.trim() || c.draftParams.questionPresented.trim()) : !!c.text.trim());

  const submit = () => {
    const s = useComposer.getState(); // fresh state: the draft drawer may have just updated it
    if (streaming || noDocs) return;
    const text = s.text.trim();

    if (s.mode === 'summary') {
      const doc = ready.find((d) => d.id === s.summaryDocumentId);
      if (!doc) return;
      onSubmit({
        text: text ? `Summarize ${docTitle(doc.name)} — focus: ${text}` : `Summarize ${docTitle(doc.name)}`,
        mode: 'summary',
        scope: { kind: 'documents', documentIds: [doc.id] },
        summaryDocumentId: doc.id,
      });
    } else if (s.mode === 'draft') {
      const params = { ...s.draftParams, questionPresented: s.draftParams.questionPresented.trim() || text };
      if (!params.questionPresented) return;
      if (params.sourceDocumentIds.length === 0) {
        s.setDraftParams({ questionPresented: params.questionPresented });
        s.setDraftDrawerOpen(true);
        return;
      }
      onSubmit({
        text: text || `Draft a ${params.draftType === 'memo' ? 'memo' : 'case brief'}: ${params.questionPresented}`,
        mode: 'draft',
        scope: { kind: 'documents', documentIds: params.sourceDocumentIds },
        draftParams: params,
      });
      s.setDraftParams({ questionPresented: '' });
    } else {
      if (!text) return;
      onSubmit({ text, mode: s.mode, scope: s.scope });
    }
    s.resetAfterSend();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  const onFiles = (files: FileList | null) => {
    if (!files?.length) return;
    upload.mutate(Array.from(files), {
      onSuccess: ({ created, rejected }) => {
        if (created.length)
          toast({
            title: `Uploading ${created.length} document${created.length === 1 ? '' : 's'}`,
            description: 'They become searchable as soon as processing finishes.',
            action: { label: 'View in Library', onClick: () => navigate('/library') },
          });
        rejected.forEach((r) => toast({ title: `${r.name} was not uploaded`, description: r.reason, tone: 'danger' }));
      },
    });
  };

  const draftSummary = (() => {
    const n = c.draftParams.sourceDocumentIds.length;
    return `${c.draftParams.draftType === 'memo' ? 'Memo' : 'Case brief'} · ${n ? `${n} source${n === 1 ? '' : 's'}` : 'choose sources'}`;
  })();

  return (
    <div className={cn('w-full', className)}>
      {noDocs && (
        <div className="mb-2 flex items-center gap-3 rounded-xl border border-border bg-surface px-3.5 py-2.5 text-sm shadow-soft">
          <Upload className="size-4 shrink-0 text-primary" />
          <span className="flex-1 text-muted">
            {documents.length === 0 ? 'Upload documents to start — Legal Lens only answers from your own files.' : 'Your documents are still processing. You can ask as soon as one is ready.'}
          </span>
          <Button size="sm" variant="outline" onClick={() => navigate('/library')}>
            Library
          </Button>
        </div>
      )}

      <div
        className={cn(
          'rounded-2xl border border-border bg-surface shadow-soft transition-shadow focus-within:border-ink/20 focus-within:shadow-pop',
          noDocs && 'opacity-80',
        )}
      >
        <label htmlFor="composer-input" className="sr-only">
          Message Legal Lens
        </label>
        <textarea
          id="composer-input"
          ref={ta}
          rows={1}
          value={c.text}
          onChange={(e) => c.setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={noDocs ? 'Upload a document to get started' : PLACEHOLDER[c.mode]}
          disabled={noDocs}
          className="block max-h-[240px] min-h-[56px] w-full resize-none bg-transparent px-4 pb-1 pt-3.5 text-[15px] leading-6 text-ink placeholder:text-subtle focus:outline-none disabled:cursor-not-allowed"
        />

        <div className="flex flex-wrap items-center gap-1.5 px-2.5 pb-2.5 pt-1">
          <IconButton label="Upload documents" size="sm" onClick={() => fileInput.current?.click()} className="size-8">
            <Paperclip />
          </IconButton>
          <input
            ref={fileInput}
            type="file"
            multiple
            hidden
            accept={UPLOAD_LIMITS.accept.join(',')}
            onChange={(e) => {
              onFiles(e.target.files);
              e.target.value = '';
            }}
          />
          <ModeChips value={c.mode} onChange={c.setMode} />
          <span className="mx-0.5 hidden h-5 w-px bg-border sm:block" aria-hidden />
          {c.mode === 'summary' ? (
            <SummaryDocPicker value={c.summaryDocumentId} onChange={c.setSummaryDocument} documents={documents} />
          ) : c.mode === 'draft' ? (
            <button
              type="button"
              onClick={() => c.setDraftDrawerOpen(true)}
              className={cn(
                'inline-flex h-8 items-center gap-1.5 rounded-lg px-2 text-[13px] font-medium transition-colors hover:bg-ink/[0.05] [&_svg]:size-3.5',
                c.draftParams.sourceDocumentIds.length ? 'text-muted hover:text-ink' : 'text-primary',
              )}
            >
              <SlidersHorizontal />
              {draftSummary}
            </button>
          ) : (
            <ScopePicker scope={c.scope} onChange={c.setScope} documents={documents} />
          )}

          <div className="ml-auto">
            {streaming ? (
              <Tooltip content="Stop generating">
                <button
                  type="button"
                  onClick={onStop}
                  aria-label="Stop generating"
                  className="flex size-9 items-center justify-center rounded-xl bg-ink text-white transition-colors hover:bg-ink/85"
                >
                  <Square className="size-3.5 fill-current" />
                </button>
              </Tooltip>
            ) : (
              <Tooltip content={c.mode === 'draft' && c.draftParams.sourceDocumentIds.length === 0 ? 'Choose sources' : 'Send'} shortcut="Enter">
                <button
                  type="button"
                  onClick={submit}
                  disabled={!canSend}
                  aria-label="Send"
                  className="flex size-9 items-center justify-center rounded-xl bg-primary text-white transition-colors hover:bg-primary-hover disabled:bg-ink/10 disabled:text-subtle"
                >
                  <ArrowUp className="size-[18px]" strokeWidth={2.4} />
                </button>
              </Tooltip>
            )}
          </div>
        </div>
      </div>

      <p className="mt-2 px-2 text-center text-[11.5px] leading-4 text-subtle">
        Legal Lens answers only from your documents and cites every claim. It is a work-product aid, not legal advice — verify before you rely on it.
      </p>

      <DraftParamsDrawer documents={documents} onGenerate={submit} />
    </div>
  );
}
