import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

export function Kbd({ children, tone = 'light', className }: { children: ReactNode; tone?: 'light' | 'dark'; className?: string }) {
  return (
    <kbd
      className={cn(
        'inline-flex h-5 min-w-5 items-center justify-center rounded px-1 font-sans text-[11px] font-medium',
        tone === 'light' ? 'border border-border bg-surface text-muted shadow-[0_1px_0_rgb(var(--border))]' : 'bg-white/15 text-white/80',
        className,
      )}
    >
      {children}
    </kbd>
  );
}
