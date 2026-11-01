import * as RD from '@radix-ui/react-dialog';
import { Outlet } from 'react-router-dom';
import { useDocumentStatusToasts } from '@/hooks/useDocumentStatusToasts';
import { useHotkeys } from '@/hooks/useHotkeys';
import { cn } from '@/lib/cn';
import { useUi } from '@/stores/ui';
import { useStreaming } from '../chat/stream';
import { CommandPalette } from '../sidebar/CommandPalette';
import { Sidebar, SidebarRail } from '../sidebar/Sidebar';
import { SourcesPanel } from '../sources/SourcesPanel';
import { ShortcutsDialog } from './ShortcutsDialog';
import { TopBar } from './TopBar';

export function AppShell() {
  const { sidebarCollapsed, mobileSidebarOpen, setMobileSidebar } = useUi();
  const announcement = useStreaming((s) => s.announcement);
  useHotkeys();
  useDocumentStatusToasts();

  return (
    <div className="flex h-dvh overflow-hidden bg-bg">
      <a href="#main" className="skip-link">
        Skip to main content
      </a>

      {/* Desktop: full sidebar or icon rail. */}
      <aside className={cn('hidden shrink-0 border-r border-border lg:block')} aria-label="Sidebar">
        {sidebarCollapsed ? <SidebarRail /> : <Sidebar />}
      </aside>

      {/* Mobile and tablet: drawer. */}
      <RD.Root open={mobileSidebarOpen} onOpenChange={setMobileSidebar}>
        <RD.Portal>
          <RD.Overlay className="fixed inset-0 z-[60] animate-fade-in bg-ink/25 lg:hidden" />
          <RD.Content className="fixed inset-y-0 left-0 z-[61] animate-slide-in-left shadow-pop focus:outline-none lg:hidden" aria-label="Sidebar">
            <RD.Title className="sr-only">Navigation</RD.Title>
            <RD.Description className="sr-only">Conversations, library and account</RD.Description>
            <Sidebar mobile onNavigate={() => setMobileSidebar(false)} />
          </RD.Content>
        </RD.Portal>
      </RD.Root>

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main id="main" className="flex min-h-0 flex-1 flex-col" tabIndex={-1}>
          <Outlet />
        </main>
      </div>

      <SourcesPanel />
      <CommandPalette />
      <ShortcutsDialog />
      <p className="sr-only" role="status" aria-live="polite">
        {announcement}
      </p>
    </div>
  );
}
