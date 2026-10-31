import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

export function EmptyState({ icon, title, children, action, className }: { icon?: ReactNode; title: string; children?: ReactNode; action?: ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-col items-center px-6 py-14 text-center', className)}>
      {icon && <div className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-primary-soft text-primary [&_svg]:size-6">{icon}</div>}
      <h2 className="text-base font-semibold text-ink">{title}</h2>
      {children && <div className="mt-1.5 max-w-md text-sm leading-6 text-muted">{children}</div>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
