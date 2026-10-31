import type { NavigateFunction } from 'react-router-dom';
import type { DraftParams, Mode, Scope } from '@/api/types';

export interface ChatPrefill {
  text?: string;
  mode?: Mode;
  scope?: Scope;
  summaryDocumentId?: string | null;
  draftParams?: Partial<DraftParams>;
  openDraftSettings?: boolean;
}

/** Opens a new chat with the composer prefilled (e.g. "Ask about this document" in the Library). */
export function startChatWith(navigate: NavigateFunction, prefill: ChatPrefill) {
  navigate('/', { state: { prefill } });
}

export const askAbout = (navigate: NavigateFunction, documentId: string) =>
  startChatWith(navigate, { mode: 'ask', scope: { kind: 'documents', documentIds: [documentId] } });

export const summarise = (navigate: NavigateFunction, documentId: string) =>
  startChatWith(navigate, { mode: 'summary', summaryDocumentId: documentId, scope: { kind: 'documents', documentIds: [documentId] } });
