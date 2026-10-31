import { create } from 'zustand';
import type { DraftParams, Mode, Scope } from '@/api/types';

export const emptyDraftParams = (sourceDocumentIds: string[] = []): DraftParams => ({
  draftType: 'memo',
  questionPresented: '',
  audience: 'Supervising partner',
  position: '',
  tone: 'neutral',
  sourceDocumentIds,
});

interface ComposerState {
  text: string;
  mode: Mode;
  scope: Scope;
  summaryDocumentId: string | null;
  draftParams: DraftParams;
  draftDrawerOpen: boolean;
  /** Bumped to ask the textarea to take focus. */
  focusTick: number;

  setText: (text: string) => void;
  setMode: (mode: Mode) => void;
  setScope: (scope: Scope) => void;
  setSummaryDocument: (id: string | null) => void;
  setDraftParams: (p: Partial<DraftParams>) => void;
  setDraftDrawerOpen: (open: boolean) => void;
  focus: () => void;
  /** Prefill from a suggestion or a library action. */
  prefill: (p: { text?: string; mode?: Mode; scope?: Scope; summaryDocumentId?: string | null; draftParams?: Partial<DraftParams> }) => void;
  resetAfterSend: () => void;
}

export const useComposer = create<ComposerState>((set, get) => ({
  text: '',
  mode: 'auto',
  scope: { kind: 'workspace' },
  summaryDocumentId: null,
  draftParams: emptyDraftParams(),
  draftDrawerOpen: false,
  focusTick: 0,

  setText: (text) => set({ text }),
  setMode: (mode) => set({ mode }),
  setScope: (scope) => set({ scope }),
  setSummaryDocument: (summaryDocumentId) => set({ summaryDocumentId }),
  setDraftParams: (p) => set({ draftParams: { ...get().draftParams, ...p } }),
  setDraftDrawerOpen: (draftDrawerOpen) => set({ draftDrawerOpen }),
  focus: () => set({ focusTick: get().focusTick + 1 }),
  prefill: (p) =>
    set({
      text: p.text ?? get().text,
      mode: p.mode ?? get().mode,
      scope: p.scope ?? get().scope,
      summaryDocumentId: p.summaryDocumentId !== undefined ? p.summaryDocumentId : get().summaryDocumentId,
      draftParams: p.draftParams ? { ...get().draftParams, ...p.draftParams } : get().draftParams,
      focusTick: get().focusTick + 1,
    }),
  resetAfterSend: () => set({ text: '' }),
}));
