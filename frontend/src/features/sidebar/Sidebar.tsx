import { ChevronsUpDown, Keyboard, Library, LogOut, PanelLeftClose, PanelLeftOpen, Search, Settings, SquarePen } from 'lucide-react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useDocuments, useLogout, useMe, workspaceStats } from '@/api/queries';
import { IconButton } from '@/components/ui/Button';
import { Kbd } from '@/components/ui/Kbd';
import { Logo, LogoMark } from '@/components/ui/Logo';
import { Menu, MenuContent, MenuItem, MenuSeparator, MenuTrigger } from '@/components/ui/Menu';
import { Tooltip } from '@/components/ui/Tooltip';
import { cn } from '@/lib/cn';
import { modKey } from '@/lib/format';
import { useUi } from '@/stores/ui';
import { ConversationList } from './ConversationList';

function LibraryHealth() {
  const { data } = useDocuments();
  const s = workspaceStats(data);
  const [dot, text] =
    s.processing > 0
      ? ['bg-warning animate-pulse', `${s.processing} processing`]
      : s.failed > 0
        ? ['bg-danger', `${s.failed} failed`]
        : s.documents > 0
          ? ['bg-success', 'All ready']
          : ['bg-subtle', 'Empty'];
  return (
    <span className="ml-auto flex items-center gap-1.5 text-xs text-muted" title={text}>
      <span className="tabular-nums">{s.documents}</span>
      <span className={cn('size-1.5 rounded-full', dot)} aria-label={text} />
    </span>
  );
}

function UserMenu({ compact }: { compact?: boolean }) {
  const { data: me } = useMe();
  const logout = useLogout();
  const navigate = useNavigate();
  const setShortcutsOpen = useUi((s) => s.setShortcutsOpen);
  if (!me) return null;
  const avatar = (
    <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-[12px] font-semibold text-white">{me.initials}</span>
  );
  return (
    <Menu>
      <MenuTrigger
        className={cn('flex w-full items-center gap-2.5 rounded-lg p-1.5 text-left transition-colors hover:bg-hover data-[state=open]:bg-hover', compact && 'w-auto')}
        aria-label="Account menu"
      >
        {avatar}
        {!compact && (
          <>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-ink">{me.name}</span>
              <span className="block truncate text-xs text-muted">{me.email}</span>
            </span>
            <ChevronsUpDown className="size-4 shrink-0 text-subtle" />
          </>
        )}
      </MenuTrigger>
      <MenuContent side="top" align="start" className="w-[240px]">
        <MenuItem icon={<Settings />} onSelect={() => navigate('/settings')}>
          Settings
        </MenuItem>
        <MenuItem icon={<Keyboard />} hint="?" onSelect={() => setShortcutsOpen(true)}>
          Keyboard shortcuts
        </MenuItem>
        <MenuSeparator />
        <MenuItem icon={<LogOut />} onSelect={() => logout.mutate(undefined, { onSuccess: () => navigate('/login') })}>
          Sign out
        </MenuItem>
      </MenuContent>
    </Menu>
  );
}

const navRow = 'flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5 text-sm text-ink/85 transition-colors hover:bg-hover';

export function Sidebar({ onNavigate, mobile }: { onNavigate?: () => void; mobile?: boolean }) {
  const { toggleSidebar, setCommandOpen } = useUi();
  const navigate = useNavigate();

  return (
    <div className="flex h-full w-[var(--sidebar-width)] flex-col bg-sidebar">
      <div className="flex h-14 shrink-0 items-center justify-between px-3">
        <Link to="/" onClick={onNavigate} aria-label="Legal Lens home" className="rounded-lg px-1 py-1">
          <Logo />
        </Link>
        {!mobile && (
          <IconButton label="Close sidebar" shortcut={`${modKey} ⇧ S`} onClick={toggleSidebar} tooltipSide="right">
            <PanelLeftClose />
          </IconButton>
        )}
      </div>

      <div className="space-y-0.5 px-2">
        <button
          onClick={() => {
            navigate('/');
            onNavigate?.();
          }}
          className="group mb-1.5 flex h-10 w-full items-center gap-2.5 rounded-xl border border-border bg-surface px-3 text-sm font-medium text-ink shadow-soft transition-all hover:border-ink/20"
        >
          <SquarePen className="size-4 text-primary" />
          New chat
          <span className="ml-auto hidden gap-0.5 opacity-0 transition-opacity group-hover:opacity-100 lg:flex">
            <Kbd>{modKey}</Kbd>
            <Kbd>⇧</Kbd>
            <Kbd>O</Kbd>
          </span>
        </button>
        <button onClick={() => setCommandOpen(true)} className={navRow}>
          <Search className="size-4 text-muted" />
          Search
          <span className="ml-auto flex gap-0.5">
            <Kbd>{modKey}</Kbd>
            <Kbd>K</Kbd>
          </span>
        </button>
        <NavLink to="/library" onClick={onNavigate} className={({ isActive }) => cn(navRow, isActive && 'bg-surface font-medium text-ink shadow-[0_0_0_1px_rgb(var(--border))]')}>
          <Library className="size-4 text-muted" />
          Library
          <LibraryHealth />
        </NavLink>
      </div>

      <div className="mx-4 my-3 h-px bg-border" />

      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-3">
        <ConversationList onNavigate={onNavigate} />
      </div>

      <div className="border-t border-border p-2">
        <UserMenu />
      </div>
    </div>
  );
}

/** Icon rail shown when the desktop sidebar is collapsed. */
export function SidebarRail() {
  const { toggleSidebar, setCommandOpen } = useUi();
  const navigate = useNavigate();
  return (
    <div className="flex h-full w-[60px] flex-col items-center gap-1 border-r border-border bg-sidebar py-3">
      <Tooltip content="Legal Lens" side="right">
        <Link to="/" aria-label="Legal Lens home" className="mb-2">
          <LogoMark />
        </Link>
      </Tooltip>
      <IconButton label="Open sidebar" shortcut={`${modKey} ⇧ S`} onClick={toggleSidebar} tooltipSide="right">
        <PanelLeftOpen />
      </IconButton>
      <IconButton label="New chat" shortcut={`${modKey} ⇧ O`} onClick={() => navigate('/')} tooltipSide="right">
        <SquarePen />
      </IconButton>
      <IconButton label="Search" shortcut={`${modKey} K`} onClick={() => setCommandOpen(true)} tooltipSide="right">
        <Search />
      </IconButton>
      <IconButton label="Library" onClick={() => navigate('/library')} tooltipSide="right">
        <Library />
      </IconButton>
      <div className="mt-auto">
        <UserMenu compact />
      </div>
    </div>
  );
}
