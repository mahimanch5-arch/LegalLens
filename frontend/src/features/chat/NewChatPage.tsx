import { useQueryClient } from '@tanstack/react-query';
import { FileUp, MessageSquareText, PenLine, ScrollText, ShieldCheck } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { createConversation, useDocuments, useMe } from '@/api/queries';
import type { DraftParams, LegalDocument, Mode, Scope, SendMessageRequest } from '@/api/types';
import { greeting, docTitle } from '@/lib/format';
import type { ChatPrefill } from '@/lib/startChat';
import { emptyDraftParams, useComposer } from '@/stores/composer';
import { toast } from '@/stores/toast';
import { useUi } from '@/stores/ui';
import { Composer } from '../composer/Composer';
import { sendMessage } from './stream';

interface Suggestion {
  icon: JSX.Element;
  label: string;
  detail: string;
  text: string;
  mode: Mode;
  scope?: Scope;
  summaryDocumentId?: string;
  draftParams?: Partial<DraftParams>;
}

/** Suggestions are built from what is actually in the library, so each one is answerable. */
function buildSuggestions(docs: LegalDocument[]): Suggestion[] {
  const ready = docs.filter((d) => d.status === 'ready');
  const contract = ready.find((d) => d.type === 'contract');
  const opinion = ready.find((d) => d.type === 'opinion');
  const out: Suggestion[] = [];
  if (contract)
    out.push({ icon: <MessageSquareText />, label: 'Ask', detail: docTitle(contract.name), text: 'What are the termination rights, and what notice is required?', mode: 'ask', scope: { kind: 'documents', documentIds: [contract.id] } });
  if (opinion)
    out.push({ icon: <ScrollText />, label: 'Summarise', detail: docTitle(opinion.name), text: '', mode: 'summary', summaryDocumentId: opinion.id });
  if (contract && opinion)
    out.push({
      icon: <PenLine />, label: 'Draft a memo', detail: 'Email notice of breach',
      text: '', mode: 'draft',
      draftParams: { draftType: 'memo', questionPresented: `Can a party terminate the ${docTitle(contract.name)} for breach by giving notice by email alone?`, sourceDocumentIds: [contract.id, opinion.id] },
    });
  if (ready.length > 1)
    out.push({ icon: <MessageSquareText />, label: 'Ask across everything', detail: `${ready.length} documents`, text: 'Compare the limitation-of-liability caps across my agreements.', mode: 'ask', scope: { kind: 'workspace' } });
  return out.slice(0, 4);
}

export function NewChatPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { data: me } = useMe();
  const { data: docs = [], isLoading } = useDocuments();
  const [busy, setBusy] = useState(false);
  const suggestions = useMemo(() => buildSuggestions(docs), [docs]);
  const closeSources = useUi((s) => s.closeSources);

  // Fresh composer on every visit, unless we arrived with a prefill (Library "Ask about this", etc.).
  const location = useLocation();
  useEffect(() => {
    closeSources();
    const c = useComposer.getState();
    c.setMode('auto');
    c.setScope({ kind: 'workspace' });
    c.setSummaryDocument(null);
    c.setDraftParams(emptyDraftParams());
    const prefill = (location.state as { prefill?: ChatPrefill } | null)?.prefill;
    if (prefill) {
      c.prefill(prefill);
      if (prefill.openDraftSettings) c.setDraftDrawerOpen(true);
      navigate('.', { replace: true, state: null });
    }
  }, [location.key]); // eslint-disable-line react-hooks/exhaustive-deps

  const start = async (req: SendMessageRequest) => {
    if (busy) return;
    setBusy(true);
    try {
      const conv = await createConversation(qc);
      navigate(`/c/${conv.id}`);
      void sendMessage(qc, conv.id, req);
    } catch {
      toast({ title: "Couldn't start a conversation", description: 'Check your connection and try again.', tone: 'danger' });
    } finally {
      setBusy(false);
    }
  };

  const applySuggestion = (s: Suggestion) => {
    const c = useComposer.getState();
    c.prefill({ text: s.text, mode: s.mode, scope: s.scope, summaryDocumentId: s.summaryDocumentId ?? null, draftParams: s.draftParams });
    if (s.mode === 'draft') c.setDraftDrawerOpen(true);
  };

  const firstName = me?.name.split(' ')[0];
  const noDocs = !isLoading && docs.length === 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <div className="mx-auto flex w-full max-w-[740px] flex-1 flex-col justify-center px-4 py-10 sm:px-6">
        <div className="mb-8 text-center">
          <h1 className="font-serif text-[34px] font-semibold leading-tight tracking-tight text-ink sm:text-[40px]">
            {greeting()}
            {firstName ? `, ${firstName}` : ''}
          </h1>
          <p className="mt-2 text-[15px] text-muted">
            {noDocs ? 'Upload your documents, then ask, summarise or draft — with a citation behind every sentence.' : 'What would you like to work on? Every answer cites your documents.'}
          </p>
        </div>

        {noDocs ? (
          <Link
            to="/library"
            className="group mx-auto mb-6 flex w-full max-w-md flex-col items-center rounded-2xl border-2 border-dashed border-border bg-surface px-6 py-8 text-center transition-colors hover:border-primary/40 hover:bg-primary-soft/30"
          >
            <span className="flex size-11 items-center justify-center rounded-xl bg-primary-soft text-primary">
              <FileUp className="size-5" />
            </span>
            <span className="mt-3 font-medium text-ink">Upload your first documents</span>
            <span className="mt-1 text-sm text-muted">Contracts, opinions or pleadings — PDF, DOCX or TXT, up to 50 MB each.</span>
          </Link>
        ) : null}

        <Composer onSubmit={start} autoFocus streaming={busy} />

        {suggestions.length > 0 && (
          <div className="mt-6 grid gap-2.5 sm:grid-cols-2">
            {suggestions.map((s) => (
              <button
                key={s.label + s.detail}
                onClick={() => applySuggestion(s)}
                className="group flex items-start gap-3 rounded-xl border border-border bg-surface/70 p-3.5 text-left transition-all hover:border-primary/30 hover:bg-surface hover:shadow-soft"
              >
                <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-bg text-muted transition-colors group-hover:bg-primary-soft group-hover:text-primary [&_svg]:size-4">
                  {s.icon}
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-medium text-ink">{s.label}</span>
                  <span className="block truncate text-[13px] text-muted">{s.text || s.detail}</span>
                </span>
              </button>
            ))}
          </div>
        )}

        <p className="mt-8 flex items-center justify-center gap-1.5 text-xs text-subtle">
          <ShieldCheck className="size-3.5" /> Your documents are encrypted and never used to train models.
        </p>
      </div>
    </div>
  );
}
