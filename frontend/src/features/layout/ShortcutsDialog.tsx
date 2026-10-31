import { Dialog } from '@/components/ui/Dialog';
import { Kbd } from '@/components/ui/Kbd';
import { modKey } from '@/lib/format';
import { useUi } from '@/stores/ui';

const GROUPS: { title: string; items: [string, string[]][] }[] = [
  {
    title: 'General',
    items: [
      ['Search conversations and documents', [modKey, 'K']],
      ['New chat', [modKey, '⇧', 'O']],
      ['Toggle sidebar', [modKey, '⇧', 'S']],
      ['Show keyboard shortcuts', ['?']],
    ],
  },
  {
    title: 'Composer',
    items: [
      ['Focus the message box', ['/']],
      ['Send', ['Enter']],
      ['New line', ['⇧', 'Enter']],
    ],
  },
  {
    title: 'Sources',
    items: [
      ['Close the sources panel or a dialog', ['Esc']],
      ['Move between citations and buttons', ['Tab']],
    ],
  },
];

export function ShortcutsDialog() {
  const { shortcutsOpen, setShortcutsOpen } = useUi();
  return (
    <Dialog open={shortcutsOpen} onOpenChange={setShortcutsOpen} title="Keyboard shortcuts" size="md">
      <div className="space-y-5 pb-3">
        {GROUPS.map((g) => (
          <section key={g.title}>
            <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-subtle">{g.title}</h3>
            <ul className="divide-y divide-border">
              {g.items.map(([label, keys]) => (
                <li key={label} className="flex items-center justify-between py-2 text-sm text-ink">
                  {label}
                  <span className="flex gap-1">
                    {keys.map((k) => (
                      <Kbd key={k}>{k}</Kbd>
                    ))}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </Dialog>
  );
}
