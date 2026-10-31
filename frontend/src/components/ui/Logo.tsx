import { cn } from '@/lib/cn';

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn('size-7', className)} aria-hidden>
      <rect width="32" height="32" rx="8" fill="rgb(var(--primary))" />
      <circle cx="14.5" cy="14.5" r="6.5" fill="none" stroke="#F4E3B8" strokeWidth="2.5" />
      <path d="M19.5 19.5 25 25" stroke="#F4E3B8" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn('flex items-center gap-2.5', className)}>
      <LogoMark />
      <span className="font-serif text-[19px] font-semibold tracking-tight text-ink">Legal Lens</span>
    </span>
  );
}
