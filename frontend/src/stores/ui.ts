import { create } from 'zustand';
import type { Citation, Excerpt } from '@/api/types';

const PREFS_KEY = 'legallens.ui.v1';

interface Prefs {
  sidebarCollapsed: boolean;
  sourcesWidth: number;
}

function loadPrefs(): Prefs {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (raw) return { sidebarCollapsed: false, sourcesWidth: 440, ...(JSON.parse(raw) as Partial<Prefs>) };
  } catch {
    /* storage unavailable */
  }
  return { sidebarCollapsed: false, sourcesWidth: 440 };
}

function savePrefs(p: Prefs) {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(p));
  } catch {
    /* ignore */
  }
}

/** What the Sources panel is showing. */
export interface SourcesTarget {
  documentId: string;
  documentName: string;
  page: number;
  /** Character span to highlight on the page. */
  highlight?: { start: number; end: number };
  /** Which citation was clicked, if any. */
  citationN?: number;
  /** The answer's citations and excerpts, for the "All sources" tab. */
  citations: Citation[];
  excerpts: Excerpt[];
  messageId?: string;
}

interface UiState extends Prefs {
  mobileSidebarOpen: boolean;
  commandOpen: boolean;
  shortcutsOpen: boolean;
  sources: SourcesTarget | null;
  sourcesTab: 'passage' | 'all';

  toggleSidebar: () => void;
  setMobileSidebar: (open: boolean) => void;
  setCommandOpen: (open: boolean) => void;
  setShortcutsOpen: (open: boolean) => void;
  setSourcesWidth: (w: number) => void;
  openSources: (t: SourcesTarget, tab?: 'passage' | 'all') => void;
  setSourcesPage: (page: number) => void;
  setSourcesTab: (tab: 'passage' | 'all') => void;
  closeSources: () => void;
}

export const useUi = create<UiState>((set, get) => ({
  ...loadPrefs(),
  mobileSidebarOpen: false,
  commandOpen: false,
  shortcutsOpen: false,
  sources: null,
  sourcesTab: 'passage',

  toggleSidebar: () => {
    const sidebarCollapsed = !get().sidebarCollapsed;
    set({ sidebarCollapsed });
    savePrefs({ sidebarCollapsed, sourcesWidth: get().sourcesWidth });
  },
  setMobileSidebar: (mobileSidebarOpen) => set({ mobileSidebarOpen }),
  setCommandOpen: (commandOpen) => set({ commandOpen }),
  setShortcutsOpen: (shortcutsOpen) => set({ shortcutsOpen }),
  setSourcesWidth: (w) => {
    const sourcesWidth = Math.round(Math.min(720, Math.max(360, w)));
    set({ sourcesWidth });
    savePrefs({ sidebarCollapsed: get().sidebarCollapsed, sourcesWidth });
  },
  openSources: (sources, tab = 'passage') => set({ sources, sourcesTab: tab }),
  setSourcesPage: (page) => {
    const s = get().sources;
    if (s) set({ sources: { ...s, page, highlight: undefined, citationN: undefined }, sourcesTab: 'passage' });
  },
  setSourcesTab: (sourcesTab) => set({ sourcesTab }),
  closeSources: () => set({ sources: null }),
}));
