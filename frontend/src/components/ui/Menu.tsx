import * as DM from '@radix-ui/react-dropdown-menu';
import { Check } from 'lucide-react';
import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

export const Menu = DM.Root;
export const MenuTrigger = DM.Trigger;

export function MenuContent({ children, align = 'start', side, className }: { children: ReactNode; align?: 'start' | 'end' | 'center'; side?: 'top' | 'bottom' | 'left' | 'right'; className?: string }) {
  return (
    <DM.Portal>
      <DM.Content
        align={align}
        side={side}
        sideOffset={6}
        collisionPadding={12}
        className={cn('z-[70] min-w-[200px] animate-pop-in rounded-xl border border-border bg-surface p-1.5 shadow-pop', className)}
      >
        {children}
      </DM.Content>
    </DM.Portal>
  );
}

interface ItemProps {
  children: ReactNode;
  icon?: ReactNode;
  onSelect?: (e: Event) => void;
  danger?: boolean;
  disabled?: boolean;
  hint?: ReactNode;
}

export function MenuItem({ children, icon, onSelect, danger, disabled, hint }: ItemProps) {
  return (
    <DM.Item
      onSelect={onSelect}
      disabled={disabled}
      className={cn(
        'flex cursor-pointer select-none items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm outline-none transition-colors data-[disabled]:pointer-events-none data-[disabled]:opacity-40 [&_svg]:size-4',
        danger ? 'text-danger data-[highlighted]:bg-danger-soft' : 'text-ink data-[highlighted]:bg-ink/[0.05]',
      )}
    >
      {icon && <span className={cn('shrink-0', danger ? 'text-danger' : 'text-muted')}>{icon}</span>}
      <span className="flex-1">{children}</span>
      {hint && <span className="text-xs text-subtle">{hint}</span>}
    </DM.Item>
  );
}

export function MenuCheckItem({ children, checked, onSelect, description }: { children: ReactNode; checked: boolean; onSelect: () => void; description?: string }) {
  return (
    <DM.Item
      onSelect={onSelect}
      className="flex cursor-pointer select-none items-start gap-2.5 rounded-lg px-2.5 py-2 text-sm outline-none data-[highlighted]:bg-ink/[0.05]"
    >
      <span className="mt-0.5 flex size-4 shrink-0 items-center justify-center text-primary">{checked && <Check className="size-4" />}</span>
      <span>
        <span className="block text-ink">{children}</span>
        {description && <span className="block text-xs text-muted">{description}</span>}
      </span>
    </DM.Item>
  );
}

export function MenuLabel({ children }: { children: ReactNode }) {
  return <DM.Label className="px-2.5 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-subtle">{children}</DM.Label>;
}

export function MenuSeparator() {
  return <DM.Separator className="-mx-1.5 my-1.5 h-px bg-border" />;
}
