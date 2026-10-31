import * as RD from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  size?: 'sm' | 'md' | 'lg';
  /** Side sheet instead of a centred modal. */
  side?: 'right';
  className?: string;
  hideClose?: boolean;
}

const widths = { sm: 'max-w-md', md: 'max-w-lg', lg: 'max-w-2xl' };

export function Dialog({ open, onOpenChange, title, description, children, footer, size = 'md', side, className, hideClose }: DialogProps) {
  return (
    <RD.Root open={open} onOpenChange={onOpenChange}>
      <RD.Portal>
        <RD.Overlay className="fixed inset-0 z-[60] animate-fade-in bg-ink/25 backdrop-blur-[2px]" />
        <RD.Content
          className={cn(
            'fixed z-[61] flex flex-col bg-surface shadow-pop focus:outline-none',
            side === 'right'
              ? 'inset-y-0 right-0 w-full max-w-[480px] animate-slide-in-right border-l border-border'
              : cn('left-1/2 top-1/2 max-h-[88vh] w-[calc(100vw-32px)] -translate-x-1/2 -translate-y-1/2 animate-pop-in rounded-2xl border border-border', widths[size]),
            className,
          )}
        >
          <div className="flex items-start justify-between gap-4 px-6 pb-2 pt-5">
            <div className="min-w-0">
              <RD.Title className="text-[17px] font-semibold leading-snug text-ink">{title}</RD.Title>
              {description ? (
                <RD.Description className="mt-1 text-sm text-muted">{description}</RD.Description>
              ) : (
                <RD.Description className="sr-only">{typeof title === 'string' ? title : 'Dialog'}</RD.Description>
              )}
            </div>
            {!hideClose && (
              <RD.Close className="-mr-2 -mt-1 rounded-lg p-1.5 text-muted hover:bg-ink/[0.06] hover:text-ink" aria-label="Close">
                <X className="size-[18px]" />
              </RD.Close>
            )}
          </div>
          {children && <div className="min-h-0 flex-1 overflow-y-auto px-6 py-3">{children}</div>}
          {footer && <div className="flex items-center justify-end gap-2 border-t border-border px-6 py-3.5">{footer}</div>}
        </RD.Content>
      </RD.Portal>
    </RD.Root>
  );
}
