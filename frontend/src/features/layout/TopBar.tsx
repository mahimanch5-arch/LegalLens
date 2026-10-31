import { lazy, Suspense, useEffect } from 'react';
import { Menu, PanelLeftOpen, SquarePen } from 'lucide-react';
import { useMatch, useNavigate } from 'react-router-dom';
import { useConversation } from '@/api/queries';
import { IconButton } from '@/components/ui/Button';
import { modKey } from '@/lib/format';
import { useUi } from '@/stores/ui';

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== 'false';
const ScenarioSwitcher = USE_MOCKS ? lazy(() => import('../dev/ScenarioSwitcher')) : null;

function usePageTitle(): string {
  const convId = useMatch('/c/:conversationId')?.params.conversationId;
  const { data: conv } = useConversation(convId);
  const library = useMatch('/library/*');
  const settings = useMatch('/settings');
  if (convId) return conv?.title ?? '';
  if (library) return 'Library';
  if (settings) return 'Settings';
  return '';
}

export function TopBar() {
  const { sidebarCollapsed, toggleSidebar, setMobileSidebar } = useUi();
  const navigate = useNavigate();
  const title = usePageTitle();

  useEffect(() => {
    document.title = title && title !== 'New conversation' ? `${title} · Legal Lens` : 'Legal Lens';
  }, [title]);

  return (
    <header className="flex h-12 shrink-0 items-center gap-1.5 px-2 sm:px-3">
      <IconButton label="Open menu" className="lg:hidden" onClick={() => setMobileSidebar(true)}>
        <Menu />
      </IconButton>
      {sidebarCollapsed && (
        <span className="hidden lg:contents">
          <IconButton label="Open sidebar" shortcut={`${modKey} ⇧ S`} onClick={toggleSidebar}>
            <PanelLeftOpen />
          </IconButton>
        </span>
      )}
      <h1 className="min-w-0 flex-1 truncate px-1 text-sm font-medium text-ink">{title}</h1>
      {ScenarioSwitcher && (
        <Suspense fallback={null}>
          <ScenarioSwitcher />
        </Suspense>
      )}
      <IconButton label="New chat" className="lg:hidden" onClick={() => navigate('/')}>
        <SquarePen />
      </IconButton>
    </header>
  );
}
