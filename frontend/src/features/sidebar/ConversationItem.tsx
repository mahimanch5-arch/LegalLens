import { MessageSquareText, MoreHorizontal, PenLine, Pencil, Pin, PinOff, ScrollText, Trash2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { NavLink } from 'react-router-dom';
import type { Conversation } from '@/api/types';
import { Menu, MenuContent, MenuItem, MenuSeparator, MenuTrigger } from '@/components/ui/Menu';
import { Spinner } from '@/components/ui/Spinner';
import { cn } from '@/lib/cn';
import { relativeTime } from '@/lib/format';

const ICONS = { ask: MessageSquareText, summary: ScrollText, draft: PenLine } as const;

interface Props {
  conversation: Conversation;
  streaming: boolean;
  onRename: (title: string) => void;
  onTogglePin: () => void;
  onDelete: () => void;
  onNavigate?: () => void;
}

export function ConversationItem({ conversation: c, streaming, onRename, onTogglePin, onDelete, onNavigate }: Props) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(c.title);
  const input = useRef<HTMLInputElement>(null);
  const Icon = ICONS[c.lastIntent ?? 'ask'];

  useEffect(() => {
    if (editing) {
      setTitle(c.title);
      requestAnimationFrame(() => input.current?.select());
    }
  }, [editing, c.title]);

  const commit = () => {
    setEditing(false);
    if (title.trim() && title.trim() !== c.title) onRename(title.trim());
  };

  if (editing) {
    return (
      <div className="flex h-9 items-center gap-2.5 rounded-lg bg-surface px-2.5 ring-2 ring-primary/30">
        <Icon className="size-4 shrink-0 text-subtle" />
        <input
          ref={input}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit();
            if (e.key === 'Escape') setEditing(false);
          }}
          aria-label="Conversation title"
          className="min-w-0 flex-1 bg-transparent text-sm text-ink focus:outline-none"
          maxLength={120}
        />
      </div>
    );
  }

  return (
    <div className="group relative">
      <NavLink
        to={`/c/${c.id}`}
        onClick={onNavigate}
        onDoubleClick={() => setEditing(true)}
        title={`${c.title} · ${relativeTime(c.updatedAt)}`}
        className={({ isActive }) =>
          cn(
            'flex h-9 items-center gap-2.5 rounded-lg pl-2.5 pr-8 text-sm transition-colors',
            isActive ? 'bg-surface font-medium text-ink shadow-[0_0_0_1px_rgb(var(--border))]' : 'text-ink/85 hover:bg-hover',
          )
        }
      >
        {streaming ? <Spinner className="size-4 shrink-0 text-primary" label="Responding" /> : <Icon className="size-4 shrink-0 text-subtle" />}
        <span className="truncate">{c.title}</span>
      </NavLink>
      <Menu>
        <MenuTrigger
          aria-label={`Options for ${c.title}`}
          className="absolute right-1 top-1/2 flex size-7 -translate-y-1/2 items-center justify-center rounded-md text-muted opacity-0 transition-opacity hover:bg-ink/[0.07] hover:text-ink focus-visible:opacity-100 group-hover:opacity-100 data-[state=open]:bg-ink/[0.07] data-[state=open]:opacity-100"
        >
          <MoreHorizontal className="size-4" />
        </MenuTrigger>
        <MenuContent align="start">
          <MenuItem icon={<Pencil />} onSelect={() => setEditing(true)}>
            Rename
          </MenuItem>
          <MenuItem icon={c.pinned ? <PinOff /> : <Pin />} onSelect={onTogglePin}>
            {c.pinned ? 'Unpin' : 'Pin to top'}
          </MenuItem>
          <MenuSeparator />
          <MenuItem icon={<Trash2 />} danger onSelect={onDelete}>
            Delete
          </MenuItem>
        </MenuContent>
      </Menu>
    </div>
  );
}
