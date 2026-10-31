import * as RT from '@radix-ui/react-tooltip';
import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';
import { Kbd } from './Kbd';

export const TooltipProvider = RT.Provider;

interface Props {
  content: ReactNode;
  shortcut?: string;
  side?: 'top' | 'bottom' | 'left' | 'right';
  children: ReactNode;
  className?: string;
}

export function Tooltip({ content, shortcut, side = 'top', children, className }: Props) {
  return (
    <RT.Root>
      <RT.Trigger asChild>{children}</RT.Trigger>
      <RT.Portal>
        <RT.Content
          side={side}
          sideOffset={6}
          className={cn(
            'z-[80] flex max-w-xs animate-fade-in items-center gap-2 rounded-md bg-ink px-2 py-1 text-xs font-medium text-white shadow-pop',
            className,
          )}
        >
          {content}
          {shortcut && <Kbd tone="dark">{shortcut}</Kbd>}
        </RT.Content>
      </RT.Portal>
    </RT.Root>
  );
}
