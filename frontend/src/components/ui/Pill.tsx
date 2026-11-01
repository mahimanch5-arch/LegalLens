import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

export type PillTone = 'neutral' | 'primary' | 'accent' | 'success' | 'warning' | 'danger';

const tones: Record<PillTone, string> = {
  neutral: 'bg-ink/[0.05] text-muted',
  primary: 'bg-primary-soft text-primary',
  accent: 'bg-accent-soft text-accent',
  success: 'bg-success-soft text-success',
  warning: 'bg-warning-soft text-warning',
  danger: 'bg-danger-soft text-danger',
};

export function Pill({ tone = 'neutral', icon, children, className }: { tone?: PillTone; icon?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex h-[22px] items-center gap-1 whitespace-nowrap rounded-full px-2 text-xs font-medium [&_svg]:size-3.5',
        tones[tone],
        className,
      )}
    >
      {icon}
      {children}
    </span>
  );
}
