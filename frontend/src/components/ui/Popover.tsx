import * as RP from '@radix-ui/react-popover';
import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

export const Popover = RP.Root;
export const PopoverTrigger = RP.Trigger;
export const PopoverClose = RP.Close;
export const PopoverAnchor = RP.Anchor;

export function PopoverContent({
  children,
  className,
  align = 'start',
  side = 'bottom',
  onOpenAutoFocus,
}: {
  children: ReactNode;
  className?: string;
  align?: 'start' | 'center' | 'end';
  side?: 'top' | 'bottom' | 'left' | 'right';
  onOpenAutoFocus?: (e: Event) => void;
}) {
  return (
    <RP.Portal>
      <RP.Content
        align={align}
        side={side}
        sideOffset={8}
        collisionPadding={12}
        onOpenAutoFocus={onOpenAutoFocus}
        className={cn('z-[70] animate-pop-in rounded-xl border border-border bg-surface shadow-pop focus:outline-none', className)}
      >
        {children}
      </RP.Content>
    </RP.Portal>
  );
}
