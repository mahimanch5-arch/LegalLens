import { EyeOff, Lock, ServerCog, ShieldCheck, Trash2 } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDeleteWorkspace, useDocuments, useMe, workspaceStats } from '@/api/queries';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { toast } from '@/stores/toast';

function Section({ title, description, children }: { title: string; description?: string; children: ReactNode }) {
  return (
    <section className="grid gap-4 border-b border-border py-7 md:grid-cols-[240px_1fr] md:gap-10">
      <div>
        <h3 className="text-[15px] font-semibold text-ink">{title}</h3>
        {description && <p className="mt-1 text-[13px] leading-5 text-muted">{description}</p>}
      </div>
      <div>{children}</div>
    </section>
  );
}

const DATA_POINTS = [
  { icon: <Lock />, title: 'Encrypted everywhere', body: 'TLS in transit; files, extracted text and search embeddings are encrypted at rest.' },
  { icon: <EyeOff />, title: 'Zero retention by the AI provider', body: 'The model provider operates under zero-retention terms and never trains on your content.' },
  { icon: <ServerCog />, title: 'No content in telemetry', body: 'Document content never reaches analytics, error tracking or third-party monitoring.' },
  { icon: <ShieldCheck />, title: 'Deletion is real', body: 'Deleting a document removes the file, its text and its index entries immediately.' },
];

export function SettingsPage() {
  const { data: me } = useMe();
  const { data: docs } = useDocuments();
  const stats = workspaceStats(docs);
  const del = useDeleteWorkspace();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState('');

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[960px] px-4 pb-16 pt-4 sm:px-8">
        <h2 className="font-serif text-[30px] font-semibold tracking-tight text-ink">Settings</h2>

        <Section title="Profile" description="Single-user workspace. Roles and sharing are not available in this version.">
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium text-muted">Name</dt>
              <dd className="mt-1 text-sm text-ink">{me?.name}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-muted">Email</dt>
              <dd className="mt-1 text-sm text-ink">{me?.email}</dd>
            </div>
          </dl>
        </Section>

        <Section title="How your data is handled" description="A plain statement you can rely on for your duty of technological competence (ABA Model Rule 1.1, cmt. 8).">
          <ul className="grid gap-3 sm:grid-cols-2">
            {DATA_POINTS.map((p) => (
              <li key={p.title} className="rounded-xl border border-border bg-surface p-4">
                <span className="flex size-8 items-center justify-center rounded-lg bg-primary-soft text-primary [&_svg]:size-4">{p.icon}</span>
                <p className="mt-2.5 text-sm font-medium text-ink">{p.title}</p>
                <p className="mt-1 text-[13px] leading-5 text-muted">{p.body}</p>
              </li>
            ))}
          </ul>
        </Section>

        <Section title="About Legal Lens output" description="What every answer, summary and draft is — and isn’t.">
          <div className="space-y-2 text-sm leading-6 text-ink">
            <p>Legal Lens answers only from the documents in your Library. If something is not in your documents, it says so rather than guessing.</p>
            <p>Every output is an attorney work-product aid, not legal advice. Drafts are marked as unreviewed AI output in the app and in every export, and you remain responsible for anything you rely on or file.</p>
          </div>
        </Section>

        <section className="py-7">
          <div className="rounded-xl border border-danger/30 p-5">
            <h3 className="text-[15px] font-semibold text-danger">Delete workspace</h3>
            <p className="mt-1 max-w-xl text-[13px] leading-5 text-muted">
              Permanently deletes all {stats.documents} documents, their extracted text and index entries, and every conversation. This cannot be undone.
            </p>
            <Button variant="danger" className="mt-4" icon={<Trash2 className="size-4" />} onClick={() => setOpen(true)} disabled={stats.documents === 0 && !docs}>
              Delete workspace…
            </Button>
          </div>
        </section>
      </div>

      <Dialog
        open={open}
        onOpenChange={(o) => {
          setOpen(o);
          if (!o) setConfirm('');
        }}
        size="sm"
        title="Delete the entire workspace?"
        description="All documents, extracted text, index entries and conversations will be permanently removed."
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              disabled={confirm !== 'DELETE'}
              loading={del.isPending}
              onClick={() =>
                del.mutate(undefined, {
                  onSuccess: () => {
                    setOpen(false);
                    toast({ title: 'Workspace deleted', description: 'Everything has been permanently removed.', tone: 'success' });
                    navigate('/');
                  },
                })
              }
            >
              Delete everything
            </Button>
          </>
        }
      >
        <label htmlFor="confirm-delete" className="text-[13px] text-muted">
          Type <span className="font-mono font-semibold text-ink">DELETE</span> to confirm
        </label>
        <input
          id="confirm-delete"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          autoComplete="off"
          className="mt-1.5 h-10 w-full rounded-lg border border-border px-3 font-mono text-sm focus:border-danger/50 focus:outline-none focus:ring-2 focus:ring-danger/15"
        />
      </Dialog>
    </div>
  );
}
