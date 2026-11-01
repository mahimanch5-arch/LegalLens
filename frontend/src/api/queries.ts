import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { api } from './client';
import type {
  Conversation,
  ConversationDetail,
  DocType,
  DocumentPage,
  Feedback,
  LegalDocument,
  Page,
  User,
  WorkspaceStats,
} from './types';

export const qk = {
  me: ['me'] as const,
  conversations: ['conversations'] as const,
  conversation: (id: string) => ['conversation', id] as const,
  documents: ['documents'] as const,
  page: (docId: string, n: number) => ['document-page', docId, n] as const,
};

// ---------- auth ----------

export function useMe() {
  return useQuery({
    queryKey: qk.me,
    queryFn: () => api.get<User>('/api/auth/me'),
    retry: false,
    staleTime: Infinity,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; password: string }) => api.post<User>('/api/auth/login', body),
    onSuccess: (user) => qc.setQueryData(qk.me, user),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<void>('/api/auth/logout'),
    onSuccess: () => {
      qc.clear();
      qc.setQueryData(qk.me, null);
    },
  });
}

// ---------- conversations ----------

export function useConversations() {
  return useQuery({
    queryKey: qk.conversations,
    queryFn: () => api.get<Page<Conversation>>('/api/conversations'),
    select: (p) => p.items,
  });
}

export function useConversation(id: string | undefined) {
  return useQuery({
    queryKey: qk.conversation(id ?? ''),
    queryFn: () => api.get<ConversationDetail>(`/api/conversations/${id}`),
    enabled: !!id,
    staleTime: Infinity, // kept current by the stream, not by refetching
  });
}

export async function createConversation(qc: QueryClient): Promise<Conversation> {
  const conv = await api.post<Conversation>('/api/conversations');
  qc.setQueryData<ConversationDetail>(qk.conversation(conv.id), { ...conv, messages: [] });
  qc.setQueryData<Page<Conversation>>(qk.conversations, (old) =>
    old ? { ...old, items: [conv, ...old.items] } : { items: [conv], nextCursor: null },
  );
  return conv;
}

function patchConversationLists(qc: QueryClient, id: string, patch: Partial<Conversation> | null) {
  qc.setQueryData<Page<Conversation>>(qk.conversations, (old) =>
    old
      ? {
          ...old,
          items: patch === null ? old.items.filter((c) => c.id !== id) : old.items.map((c) => (c.id === id ? { ...c, ...patch } : c)),
        }
      : old,
  );
}

export function useUpdateConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; title?: string; pinned?: boolean }) =>
      api.patch<Conversation>(`/api/conversations/${id}`, body),
    onMutate: ({ id, ...body }) => patchConversationLists(qc, id, body),
    onSuccess: (conv) => {
      patchConversationLists(qc, conv.id, conv);
      qc.setQueryData<ConversationDetail>(qk.conversation(conv.id), (old) => (old ? { ...old, ...conv } : old));
    },
  });
}

export function useDeleteConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/api/conversations/${id}`),
    onMutate: (id) => patchConversationLists(qc, id, null),
    onSettled: (_d, _e, id) => qc.removeQueries({ queryKey: qk.conversation(id) }),
  });
}

export function useSendFeedback() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { conversationId: string; messageId: string } & Feedback) => api.post<void>('/api/feedback', body),
    onMutate: ({ conversationId, messageId, rating, reason, comment }) => {
      qc.setQueryData<ConversationDetail>(qk.conversation(conversationId), (old) =>
        old
          ? {
              ...old,
              messages: old.messages.map((m) =>
                m.id === messageId && m.role === 'assistant' ? { ...m, feedback: { rating, reason, comment } } : m,
              ),
            }
          : old,
      );
    },
  });
}

// ---------- documents ----------

const inFlight = (d: LegalDocument) => d.status !== 'ready' && d.status !== 'failed';

export function useDocuments() {
  return useQuery({
    queryKey: qk.documents,
    queryFn: () => api.get<Page<LegalDocument>>('/api/documents'),
    select: (p) => p.items,
    // Poll only while something is processing (FR-3).
    refetchInterval: (q) => (q.state.data?.items.some(inFlight) ? 900 : false),
  });
}

export function workspaceStats(docs: LegalDocument[] | undefined): WorkspaceStats {
  const list = docs ?? [];
  return {
    documents: list.length,
    ready: list.filter((d) => d.status === 'ready').length,
    processing: list.filter(inFlight).length,
    failed: list.filter((d) => d.status === 'failed').length,
  };
}

export function useUploadDocuments() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (files: File[]) => {
      const form = new FormData();
      files.forEach((f) => form.append('files', f));
      return api.upload<{ created: LegalDocument[]; rejected: { name: string; reason: string }[] }>('/api/documents', form);
    },
    onSuccess: ({ created }) => {
      qc.setQueryData<Page<LegalDocument>>(qk.documents, (old) =>
        old ? { ...old, items: [...created, ...old.items] } : { items: created, nextCursor: null },
      );
      void qc.invalidateQueries({ queryKey: qk.documents });
    },
  });
}

export function useUpdateDocumentType() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, type }: { id: string; type: DocType }) => api.patch<LegalDocument>(`/api/documents/${id}`, { type }),
    onMutate: ({ id, type }) =>
      qc.setQueryData<Page<LegalDocument>>(qk.documents, (old) =>
        old ? { ...old, items: old.items.map((d) => (d.id === id ? { ...d, type, typeOverridden: true } : d)) } : old,
      ),
  });
}

export function useDeleteDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/api/documents/${id}`),
    onMutate: (id) =>
      qc.setQueryData<Page<LegalDocument>>(qk.documents, (old) => (old ? { ...old, items: old.items.filter((d) => d.id !== id) } : old)),
  });
}

export function useDeleteWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.delete('/api/documents'),
    onSuccess: () => {
      qc.setQueryData<Page<LegalDocument>>(qk.documents, { items: [], nextCursor: null });
      qc.setQueryData<Page<Conversation>>(qk.conversations, { items: [], nextCursor: null });
      qc.removeQueries({ queryKey: ['conversation'] });
    },
  });
}

export function useDocumentPage(docId: string | undefined, n: number | undefined) {
  return useQuery({
    queryKey: qk.page(docId ?? '', n ?? 0),
    queryFn: () => api.get<DocumentPage>(`/api/documents/${docId}/pages/${n}`),
    enabled: !!docId && !!n,
    staleTime: Infinity,
  });
}
