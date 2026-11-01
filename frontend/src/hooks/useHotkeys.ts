import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useComposer } from '@/stores/composer';
import { useUi } from '@/stores/ui';

const isTyping = (t: EventTarget | null) =>
  t instanceof HTMLElement && (t.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName));

/** Global keyboard shortcuts (NFR-13). Listed in the shortcuts dialog. */
export function useHotkeys() {
  const navigate = useNavigate();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      const ui = useUi.getState();
      const key = e.key.toLowerCase();

      if (mod && !e.shiftKey && key === 'k') {
        e.preventDefault();
        ui.setCommandOpen(!ui.commandOpen);
      } else if (mod && e.shiftKey && key === 'o') {
        e.preventDefault();
        navigate('/');
        useComposer.getState().focus();
      } else if (mod && e.shiftKey && key === 's') {
        e.preventDefault();
        if (window.matchMedia('(min-width: 1024px)').matches) ui.toggleSidebar();
        else ui.setMobileSidebar(!ui.mobileSidebarOpen);
      } else if (!mod && !isTyping(e.target) && document.querySelectorAll('[role="dialog"]').length === 0) {
        if (e.key === '/') {
          e.preventDefault();
          useComposer.getState().focus();
        } else if (e.key === '?') {
          e.preventDefault();
          ui.setShortcutsOpen(true);
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [navigate]);
}
