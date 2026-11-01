import { AlertTriangle, CheckCircle2, Info, X, XCircle } from 'lucide-react';
import { cn } from '@/lib/cn';
import { useToasts, type ToastTone } from '@/stores/toast';

const icons: Record<ToastTone, JSX.Element> = {
  neutral: <Info className="size-[18px] text-primary" />,
  success: <CheckCircle2 className="size-[18px] text-success" />,
  warning: <AlertTriangle className="size-[18px] text-warning" />,
  danger: <XCircle className="size-[18px] text-danger" />,
};

export function Toaster() {
  const { toasts, dismiss } = useToasts();
  return (
    <div
      aria-live="polite"
      aria-relevant="additions"
      className="pointer-events-none fixed bottom-4 right-4 z-[90] flex w-[360px] max-w-[calc(100vw-32px)] flex-col gap-2"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className={cn('pointer-events-auto flex animate-slide-in-right items-start gap-3 rounded-xl border border-border bg-surface p-3.5 shadow-pop')}
        >
          <span className="mt-px">{icons[t.tone]}</span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-ink">{t.title}</p>
            {t.description && <p className="mt-0.5 text-[13px] leading-5 text-muted">{t.description}</p>}
            {t.action && (
              <button
                className="mt-1.5 text-[13px] font-medium text-primary hover:underline"
                onClick={() => {
                  t.action!.onClick();
                  dismiss(t.id);
                }}
              >
                {t.action.label}
              </button>
            )}
          </div>
          <button onClick={() => dismiss(t.id)} className="-m-1 rounded p-1 text-subtle hover:text-ink" aria-label="Dismiss notification">
            <X className="size-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
