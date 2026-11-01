import { useMemo, useState } from 'react';
import { useMatch, useNavigate } from 'react-router-dom';
import { useConversations, useDeleteConversation, useUpdateConversation } from '@/api/queries';
import type { Conversation } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { dateGroup, type DateGroup } from '@/lib/format';
import { toast } from '@/stores/toast';
import { useStreaming } from '../chat/stream';
import { ConversationItem } from './ConversationItem';

const ORDER: (DateGroup | 'Pinned')[] = ['Pinned', 'Today', 'Yesterday', 'Previous 7 days', 'Previous 30 days', 'Older'];

export function ConversationList({ onNavigate }: { onNavigate?: () => void }) {
  const { data, isLoading, isError, refetch } = useConversations();
  const update = useUpdateConversation();
  const del = useDeleteConversation();
  const active = useStreaming((s) => s.active);
  const navigate = useNavigate();
  const current = useMatch('/c/:conversationId')?.params.conversationId;
  const [toDelete, setToDelete] = useState<Conversation | null>(null);

  const groups = useMemo(() => {
    const map = new Map<string, Conversation[]>();
    const sorted = [...(data ?? [])]
      .filter((c) => c.title !== 'New conversation' || active[c.id] || c.id === current)
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
    for (const c of sorted) {
      const g = c.pinned ? 'Pinned' : dateGroup(c.updatedAt);
      map.set(g, [...(map.get(g) ?? []), c]);
    }
    return ORDER.filter((g) => map.has(g)).map((g) => ({ label: g, items: map.get(g)! }));
  }, [data, active, current]);

  if (isLoading) {
    return (
      <div className="space-y-2 px-2.5 pt-2" aria-busy aria-label="Loading conversations">
        <div className="skeleton h-3 w-16" />
        {[80, 65, 90, 55, 70].map((w, i) => (
          <div key={i} className="skeleton h-4" style={{ width: `${w}%` }} />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="px-3 py-4 text-[13px] text-muted">
        Couldn’t load conversations.{' '}
        <button className="font-medium text-primary hover:underline" onClick={() => refetch()}>
          Retry
        </button>
      </div>
    );
  }

  if (groups.length === 0) {
    return <p className="px-3 py-4 text-[13px] leading-5 text-subtle">No conversations yet. Your questions, summaries and drafts will appear here.</p>;
  }

  const confirmDelete = () => {
    if (!toDelete) return;
    const id = toDelete.id;
    del.mutate(id);
    setToDelete(null);
    if (id === current) navigate('/');
    toast({ title: 'Conversation deleted' });
  };

  return (
    <nav aria-label="Conversations" className="space-y-4">
      {groups.map((g) => (
        <section key={g.label}>
          <h3 className="sticky top-0 z-[1] bg-sidebar px-2.5 pb-1 pt-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-subtle">{g.label}</h3>
          <ul className="space-y-px">
            {g.items.map((c) => (
              <li key={c.id}>
                <ConversationItem
                  conversation={c}
                  streaming={!!active[c.id]}
                  onNavigate={onNavigate}
                  onRename={(title) => update.mutate({ id: c.id, title })}
                  onTogglePin={() => update.mutate({ id: c.id, pinned: !c.pinned })}
                  onDelete={() => setToDelete(c)}
                />
              </li>
            ))}
          </ul>
        </section>
      ))}

      <Dialog
        open={!!toDelete}
        onOpenChange={(o) => !o && setToDelete(null)}
        size="sm"
        title="Delete conversation?"
        description={
          <>
            “{toDelete?.title}” and its answers will be permanently deleted. Your documents are not affected.
          </>
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setToDelete(null)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={confirmDelete}>
              Delete
            </Button>
          </>
        }
      />
    </nav>
  );
}
