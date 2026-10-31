import * as RD from '@radix-ui/react-dialog';
import { CornerDownLeft, FileText, Keyboard, Library, MessageSquareText, PenLine, ScrollText, Search, Settings, SquarePen } from 'lucide-react';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { useConversations, useDocuments } from '@/api/queries';
import { Kbd } from '@/components/ui/Kbd';
import { cn } from '@/lib/cn';
import { docTitle, relativeTime } from '@/lib/format';
import { askAbout } from '@/lib/startChat';
import { useUi } from '@/stores/ui';

interface Item {
  id: string;
  group: 'Actions' | 'Conversations' | 'Documents';
  label: string;
  hint?: string;
  icon: ReactNode;
  run: () => void;
}

const INTENT_ICON = { ask: <MessageSquareText />, summary: <ScrollText />, draft: <PenLine /> };

export function CommandPalette() {
  const { commandOpen, setCommandOpen, setShortcutsOpen } = useUi();
  const navigate = useNavigate();
  const { data: convs = [] } = useConversations();
  const { data: docs = [] } = useDocuments();
  const [q, setQ] = useState('');
  const [index, setIndex] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (commandOpen) {
      setQ('');
      setIndex(0);
    }
  }, [commandOpen]);

  const items = useMemo<Item[]>(() => {
    const go = (to: string) => () => navigate(to);
    const actions: Item[] = [
      { id: 'new', group: 'Actions', label: 'New chat', icon: <SquarePen />, run: go('/') },
      { id: 'lib', group: 'Actions', label: 'Open Library', icon: <Library />, run: go('/library') },
      { id: 'settings', group: 'Actions', label: 'Settings', icon: <Settings />, run: go('/settings') },
      { id: 'keys', group: 'Actions', label: 'Keyboard shortcuts', icon: <Keyboard />, run: () => setShortcutsOpen(true) },
    ];
    const conversations: Item[] = convs
      .filter((c) => c.title !== 'New conversation')
      .map((c) => ({ id: c.id, group: 'Conversations', label: c.title, hint: relativeTime(c.updatedAt), icon: INTENT_ICON[c.lastIntent ?? 'ask'], run: go(`/c/${c.id}`) }));
    const documents: Item[] = docs.map((d) => ({
      id: d.id,
      group: 'Documents',
      label: docTitle(d.name),
      hint: d.status === 'ready' ? 'Ask about it' : d.status,
      icon: <FileText />,
      run: () => (d.status === 'ready' ? askAbout(navigate, d.id) : navigate('/library')),
    }));
    const term = q.trim().toLowerCase();
    if (!term) return [...actions, ...conversations.slice(0, 6)];
    return [...actions, ...conversations, ...documents].filter((i) => i.label.toLowerCase().includes(term)).slice(0, 30);
  }, [q, convs, docs, navigate, setShortcutsOpen]);

  useEffect(() => setIndex(0), [q]);
  useEffect(() => {
    listRef.current?.querySelector(`[data-index="${index}"]`)?.scrollIntoView({ block: 'nearest' });
  }, [index]);

  const run = (i: Item | undefined) => {
    if (!i) return;
    setCommandOpen(false);
    i.run();
  };

  let lastGroup = '';

  return (
    <RD.Root open={commandOpen} onOpenChange={setCommandOpen}>
      <RD.Portal>
        <RD.Overlay className="fixed inset-0 z-[60] animate-fade-in bg-ink/25 backdrop-blur-[2px]" />
        <RD.Content
          aria-label="Search"
          className="fixed left-1/2 top-[14vh] z-[61] w-[calc(100vw-32px)] max-w-[600px] -translate-x-1/2 animate-pop-in overflow-hidden rounded-2xl border border-border bg-surface shadow-pop focus:outline-none"
        >
          <RD.Title className="sr-only">Search</RD.Title>
          <RD.Description className="sr-only">Search conversations, documents and actions</RD.Description>
          <div className="flex items-center gap-3 border-b border-border px-4">
            <Search className="size-[18px] text-subtle" />
            <input
              autoFocus
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'ArrowDown') {
                  e.preventDefault();
                  setIndex((i) => Math.min(items.length - 1, i + 1));
                } else if (e.key === 'ArrowUp') {
                  e.preventDefault();
                  setIndex((i) => Math.max(0, i - 1));
                } else if (e.key === 'Enter') {
                  e.preventDefault();
                  run(items[index]);
                }
              }}
              placeholder="Search conversations, documents and actions…"
              role="combobox"
              aria-expanded
              aria-controls="cmd-list"
              aria-activedescendant={items[index] ? `cmd-${items[index].id}` : undefined}
              className="h-14 flex-1 bg-transparent text-[15px] text-ink placeholder:text-subtle focus:outline-none"
            />
            <Kbd>Esc</Kbd>
          </div>
          <div ref={listRef} id="cmd-list" role="listbox" className="max-h-[52vh] overflow-y-auto p-2">
            {items.length === 0 && <p className="px-3 py-8 text-center text-sm text-subtle">No results for “{q}”.</p>}
            {items.map((item, i) => {
              const header = item.group !== lastGroup ? item.group : null;
              lastGroup = item.group;
              return (
                <div key={item.group + item.id}>
                  {header && <p className="px-3 pb-1 pt-2.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-subtle">{header}</p>}
                  <div
                    id={`cmd-${item.id}`}
                    role="option"
                    aria-selected={i === index}
                    data-index={i}
                    onMouseMove={() => setIndex(i)}
                    onClick={() => run(item)}
                    className={cn('flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm [&_svg]:size-4', i === index ? 'bg-primary-soft text-ink' : 'text-ink/90')}
                  >
                    <span className={i === index ? 'text-primary' : 'text-subtle'}>{item.icon}</span>
                    <span className="min-w-0 flex-1 truncate">{item.label}</span>
                    {item.hint && <span className="shrink-0 text-xs capitalize text-subtle">{item.hint}</span>}
                    {i === index && <CornerDownLeft className="!size-3.5 shrink-0 text-subtle" />}
                  </div>
                </div>
              );
            })}
          </div>
        </RD.Content>
      </RD.Portal>
    </RD.Root>
  );
}
