import { BadgeCheck, FileSearch, Lock } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ApiError } from '@/api/client';
import { useLogin, useMe } from '@/api/queries';
import { Button } from '@/components/ui/Button';
import { Logo } from '@/components/ui/Logo';

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== 'false';

const POINTS = [
  { icon: <FileSearch />, title: 'Grounded in your documents', body: 'Answers come only from files you upload — never from the open web.' },
  { icon: <BadgeCheck />, title: 'A citation behind every sentence', body: 'Click any citation to see the exact passage, highlighted in its page.' },
  { icon: <Lock />, title: 'Confidential by design', body: 'Encrypted at rest, zero-retention AI, nothing used for training.' },
];

const inputCls =
  'h-11 w-full rounded-lg border border-border bg-surface px-3.5 text-[15px] text-ink placeholder:text-subtle focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/15';

export function LoginPage() {
  const { data: me } = useMe();
  const login = useLogin();
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/';
  const [email, setEmail] = useState(USE_MOCKS ? 'dana@whitfieldlaw.com' : '');
  const [password, setPassword] = useState('');

  if (me) return <Navigate to={from} replace />;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    login.mutate({ email, password }, { onSuccess: () => navigate(from, { replace: true }) });
  };

  const error = login.error instanceof ApiError ? login.error.message : login.error ? 'Couldn’t reach Legal Lens. Check your connection.' : null;

  return (
    <div className="flex min-h-dvh bg-bg">
      <aside className="relative hidden w-[46%] max-w-[620px] flex-col justify-between overflow-hidden bg-primary p-12 text-white lg:flex">
        <div className="pointer-events-none absolute -right-24 -top-24 size-[420px] rounded-full border-[48px] border-white/[0.04]" />
        <div className="pointer-events-none absolute -bottom-32 -left-20 size-[360px] rounded-full border-[40px] border-white/[0.04]" />
        <span className="flex items-center gap-2.5">
          <svg viewBox="0 0 32 32" className="size-8" aria-hidden>
            <rect width="32" height="32" rx="8" fill="#F4E3B8" />
            <circle cx="14.5" cy="14.5" r="6.5" fill="none" stroke="rgb(31 58 95)" strokeWidth="2.5" />
            <path d="M19.5 19.5 25 25" stroke="rgb(31 58 95)" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
          <span className="font-serif text-xl font-semibold">Legal Lens</span>
        </span>
        <div className="relative">
          <h2 className="max-w-md font-serif text-[34px] font-semibold leading-[1.2]">Read, question and draft from your own documents — with proof.</h2>
          <ul className="mt-10 space-y-6">
            {POINTS.map((p) => (
              <li key={p.title} className="flex gap-4">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-white/10 text-[#F4E3B8] [&_svg]:size-[18px]">{p.icon}</span>
                <span>
                  <span className="block font-medium">{p.title}</span>
                  <span className="mt-0.5 block text-sm leading-6 text-white/70">{p.body}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-white/50">An attorney work-product aid. Not legal advice.</p>
      </aside>

      <main className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-[380px]">
          <Logo className="mb-10 lg:hidden" />
          <h1 className="font-serif text-[28px] font-semibold tracking-tight text-ink">Sign in</h1>
          <p className="mt-1.5 text-sm text-muted">Welcome back. Sign in to your workspace.</p>

          <form onSubmit={submit} className="mt-8 space-y-4" noValidate>
            <div>
              <label htmlFor="email" className="text-[13px] font-medium text-ink">
                Email
              </label>
              <input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={`${inputCls} mt-1.5`} />
            </div>
            <div>
              <div className="flex items-center justify-between">
                <label htmlFor="password" className="text-[13px] font-medium text-ink">
                  Password
                </label>
                <button type="button" className="text-xs font-medium text-primary hover:underline" onClick={() => alert('Password reset is not part of this prototype.')}>
                  Forgot password?
                </button>
              </div>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                aria-invalid={!!error}
                aria-describedby={error ? 'login-error' : undefined}
                className={`${inputCls} mt-1.5`}
              />
            </div>
            {error && (
              <p id="login-error" role="alert" className="rounded-lg bg-danger-soft px-3 py-2 text-[13px] text-danger">
                {error}
              </p>
            )}
            <Button type="submit" variant="primary" size="lg" className="w-full" loading={login.isPending} disabled={!email || !password}>
              Sign in
            </Button>
          </form>

          {USE_MOCKS && (
            <p className="mt-6 rounded-lg border border-dashed border-border px-3 py-2.5 text-xs leading-5 text-muted">
              <span className="font-medium text-ink">Demo:</span> any email with a password of 4+ characters signs in. Use the password <span className="font-mono">wrong</span> to see the error state.
            </p>
          )}
        </div>
      </main>
    </div>
  );
}
