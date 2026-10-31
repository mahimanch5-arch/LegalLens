import { AlertTriangle, ArrowDown, ArrowUp, Eye, FileText, Filter, MessageSquareText, MoreHorizontal, ScrollText, Search, Trash2, Upload, X } from 'lucide-react';
import { useCallback, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useDeleteDocument, useDocuments, useUploadDocuments, workspaceStats } from '@/api/queries';
import type { DocStatus, DocType, LegalDocument } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { EmptyState } from '@/components/ui/EmptyState';
import { Menu, MenuCheckItem, MenuContent, MenuItem, MenuLabel, MenuSeparator, MenuTrigger } from '@/components/ui/Menu';
import { cn } from '@/lib/cn';
import { DOC_TYPE_LABEL, docTitle, formatBytes, fullDateTime, relativeTime } from '@/lib/format';
import { askAbout, summarise } from '@/lib/startChat';
import { toast } from '@/stores/toast';
import { StatusPill } from './StatusPill';
import { TypeSelect } from './TypeSelect';
import { UploadDropzone } from './UploadDropzone';
import { validateFiles, type Rejection } from './uploadValidation';

type SortKey = 'name' | 'type' | 'pages' | 'status' | 'uploadedAt';
const STATUS_ORDER: Record<DocStatus, number> = { failed: 0, queued: 1, parsing: 2, indexing: 3, ready: 4 };

export function LibraryPage() {
  const { data: docs = [], isLoading, isError, refetch } = useDocuments();
  const upload = useUploadDocuments();
  const del = useDeleteDocument();
  const navigate = useNavigate();

  const [query, setQuery] = useState('');
  const [types, setTypes] = useState<DocType[]>([]);
  const [statuses, setStatuses] = useState<('ready' | 'processing' | 'failed')[]>([]);
  const [sort, setSort] = useState<{ key: SortKey; dir: 'asc' | 'desc' }>({ key: 'uploadedAt', dir: 'desc' });
  const [rejections, setRejections] = useState<Rejection[]>([]);
  const [toDelete, setToDelete] = useState<LegalDocument | null>(null);

  const stats = workspaceStats(docs);

  const onFiles = useCallback(
    (files: File[]) => {
      const { accepted, rejected } = validateFiles(files);
      setRejections(rejected);
      if (accepted.length === 0) return;
      upload.mutate(accepted, {
        onSuccess: ({ created, rejected: serverRejected }) => {
          if (serverRejected.length) setRejections((r) => [...r, ...serverRejected]);
          if (created.length) toast({ title: `Uploading ${created.length} document${created.length === 1 ? '' : 's'}`, description: 'You can keep working — we’ll let you know when each is ready.' });
        },
        onError: () => toast({ title: 'Upload failed', description: 'Check your connection and try again.', tone: 'danger' }),
      });
    },
    [upload],
  );

  const rows = useMemo(() => {
    const term = query.trim().toLowerCase();
    const filtered = docs.filter((d) => {
      if (term && !d.name.toLowerCase().includes(term)) return false;
      if (types.length && !types.includes(d.type)) return false;
      if (statuses.length) {
        const s = d.status === 'ready' ? 'ready' : d.status === 'failed' ? 'failed' : 'processing';
        if (!statuses.includes(s)) return false;
      }
      return true;
    });
    const dir = sort.dir === 'asc' ? 1 : -1;
    return filtered.sort((a, b) => {
      switch (sort.key) {
        case 'name':
          return dir * a.name.localeCompare(b.name);
        case 'type':
          return dir * a.type.localeCompare(b.type);
        case 'pages':
          return dir * ((a.pages ?? -1) - (b.pages ?? -1));
        case 'status':
          return dir * (STATUS_ORDER[a.status] - STATUS_ORDER[b.status]);
        default:
          return dir * a.uploadedAt.localeCompare(b.uploadedAt);
      }
    });
  }, [docs, query, types, statuses, sort]);

  const toggleSort = (key: SortKey) => setSort((s) => (s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: key === 'name' || key === 'type' ? 'asc' : 'desc' }));
  const filtersActive = query || types.length || statuses.length;

  const confirmDelete = () => {
    if (!toDelete) return;
    del.mutate(toDelete.id, {
      onSuccess: () => toast({ title: `${docTitle(toDelete.name)} deleted`, description: 'The file, its text and its search index entries are gone.', tone: 'success' }),
    });
    setToDelete(null);
  };

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-[1120px] px-4 pb-16 pt-4 sm:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="font-serif text-[30px] font-semibold leading-tight tracking-tight text-ink">Library</h2>
            <p className="mt-1 text-sm text-muted">
              {stats.documents === 0
                ? 'The documents Legal Lens answers from. Nothing outside this library is ever used.'
                : `${stats.documents} document${stats.documents === 1 ? '' : 's'} · ${stats.ready} ready${stats.processing ? ` · ${stats.processing} processing` : ''}${stats.failed ? ` · ${stats.failed} failed` : ''}`}
            </p>
          </div>
        </div>

        <div className="mt-5">
          <UploadDropzone onFiles={onFiles} compact={docs.length > 0} busy={upload.isPending} />
        </div>

        {rejections.length > 0 && (
          <div role="alert" className="mt-3 rounded-xl border border-danger/25 bg-danger-soft/60 p-3.5">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-danger" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-ink">
                  {rejections.length} file{rejections.length === 1 ? ' was' : 's were'} not uploaded. The others were not affected.
                </p>
                <ul className="mt-1.5 space-y-1 text-[13px]">
                  {rejections.map((r) => (
                    <li key={r.name} className="text-muted">
                      <span className="font-medium text-ink">{r.name}</span> — {r.reason}
                    </li>
                  ))}
                </ul>
              </div>
              <button onClick={() => setRejections([])} className="rounded p-1 text-muted hover:text-ink" aria-label="Dismiss">
                <X className="size-4" />
              </button>
            </div>
          </div>
        )}

        {isError ? (
          <EmptyState title="Couldn’t load your library" action={<Button onClick={() => refetch()}>Retry</Button>}>
            Check your connection and try again.
          </EmptyState>
        ) : isLoading ? (
          <TableSkeleton />
        ) : docs.length === 0 ? (
          <EmptyState icon={<FileText />} title="No documents yet" className="py-10">
            Upload contracts, judicial opinions or pleadings. Legal Lens reads them, classifies them, and makes them searchable — then every answer cites the exact passage it came from.
          </EmptyState>
        ) : (
          <>
            <div className="mt-6 flex flex-wrap items-center gap-2">
              <div className="relative min-w-[200px] flex-1 sm:max-w-xs">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-subtle" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search by name"
                  aria-label="Search documents by name"
                  className="h-9 w-full rounded-lg border border-border bg-surface pl-9 pr-3 text-sm placeholder:text-subtle focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/15"
                />
              </div>
              <Menu>
                <MenuTrigger asChild>
                  <Button size="md" icon={<Filter className="size-4" />} className={cn(types.length && 'border-primary/40 text-primary')}>
                    Type{types.length ? ` · ${types.length}` : ''}
                  </Button>
                </MenuTrigger>
                <MenuContent>
                  <MenuLabel>Document type</MenuLabel>
                  {(Object.keys(DOC_TYPE_LABEL) as DocType[]).map((t) => (
                    <MenuCheckItem key={t} checked={types.includes(t)} onSelect={() => setTypes(types.includes(t) ? types.filter((x) => x !== t) : [...types, t])}>
                      {DOC_TYPE_LABEL[t]}
                    </MenuCheckItem>
                  ))}
                </MenuContent>
              </Menu>
              <Menu>
                <MenuTrigger asChild>
                  <Button size="md" icon={<Filter className="size-4" />} className={cn(statuses.length && 'border-primary/40 text-primary')}>
                    Status{statuses.length ? ` · ${statuses.length}` : ''}
                  </Button>
                </MenuTrigger>
                <MenuContent>
                  <MenuLabel>Status</MenuLabel>
                  {(['ready', 'processing', 'failed'] as const).map((s) => (
                    <MenuCheckItem key={s} checked={statuses.includes(s)} onSelect={() => setStatuses(statuses.includes(s) ? statuses.filter((x) => x !== s) : [...statuses, s])}>
                      <span className="capitalize">{s}</span>
                    </MenuCheckItem>
                  ))}
                </MenuContent>
              </Menu>
              {filtersActive ? (
                <Button
                  variant="ghost"
                  onClick={() => {
                    setQuery('');
                    setTypes([]);
                    setStatuses([]);
                  }}
                >
                  Clear
                </Button>
              ) : null}
              <span className="ml-auto text-xs text-muted">
                {rows.length} of {docs.length}
              </span>
            </div>

            <div className="mt-3 overflow-hidden rounded-xl border border-border bg-surface shadow-soft">
              <table className="w-full table-fixed text-sm">
                <caption className="sr-only">Documents in your library</caption>
                <thead className="border-b border-border bg-bg/70 text-left text-xs text-muted">
                  <tr>
                    <SortHeader label="Name" k="name" sort={sort} onSort={toggleSort} className="w-auto pl-4" />
                    <SortHeader label="Type" k="type" sort={sort} onSort={toggleSort} className="hidden w-[150px] md:table-cell" />
                    <SortHeader label="Pages" k="pages" sort={sort} onSort={toggleSort} className="hidden w-[80px] text-right sm:table-cell" />
                    <SortHeader label="Status" k="status" sort={sort} onSort={toggleSort} className="w-[130px]" />
                    <SortHeader label="Uploaded" k="uploadedAt" sort={sort} onSort={toggleSort} className="hidden w-[120px] lg:table-cell" />
                    <th className="w-[96px]">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {rows.map((d) => (
                    <tr key={d.id} className="group transition-colors hover:bg-bg/60">
                      <td className="py-3 pl-4 pr-3 align-top">
                        <div className="flex items-start gap-3">
                          <FileBadge name={d.name} />
                          <div className="min-w-0">
                            {d.status === 'ready' ? (
                              <Link to={`/library/${d.id}`} className="block truncate font-medium text-ink hover:text-primary hover:underline" title={d.name}>
                                {docTitle(d.name)}
                              </Link>
                            ) : (
                              <span className="block truncate font-medium text-ink" title={d.name}>
                                {docTitle(d.name)}
                              </span>
                            )}
                            <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-muted">
                              <span>{formatBytes(d.sizeBytes)}</span>
                              <span className="md:hidden">· {DOC_TYPE_LABEL[d.type]}</span>
                              {d.lowOcrPages.length > 0 && (
                                <span className="inline-flex items-center gap-1 text-warning">
                                  <AlertTriangle className="size-3" />
                                  {d.lowOcrPages.length} low-confidence scanned page{d.lowOcrPages.length === 1 ? '' : 's'}
                                </span>
                              )}
                            </p>
                            {d.status === 'failed' && d.error && <p className="mt-1 text-xs leading-5 text-danger">{d.error}</p>}
                          </div>
                        </div>
                      </td>
                      <td className="hidden px-2 py-3 align-top md:table-cell">
                        <TypeSelect doc={d} />
                      </td>
                      <td className="hidden px-3 py-3 text-right align-top tabular-nums text-muted sm:table-cell">{d.pages ?? '—'}</td>
                      <td className="px-3 py-3 align-top">
                        <StatusPill doc={d} />
                      </td>
                      <td className="hidden px-3 py-3 align-top text-muted lg:table-cell" title={fullDateTime(d.uploadedAt)}>
                        {relativeTime(d.uploadedAt)}
                      </td>
                      <td className="py-2.5 pr-3 text-right align-top">
                        <div className="flex items-center justify-end gap-1">
                          {d.status === 'ready' && (
                            <Button size="sm" variant="ghost" className="hidden opacity-0 transition-opacity focus:opacity-100 group-hover:opacity-100 sm:inline-flex" onClick={() => askAbout(navigate, d.id)}>
                              Ask
                            </Button>
                          )}
                          <Menu>
                            <MenuTrigger
                              aria-label={`Actions for ${docTitle(d.name)}`}
                              className="flex size-8 items-center justify-center rounded-lg text-muted hover:bg-ink/[0.06] hover:text-ink data-[state=open]:bg-ink/[0.06]"
                            >
                              <MoreHorizontal className="size-4" />
                            </MenuTrigger>
                            <MenuContent align="end">
                              <MenuItem icon={<MessageSquareText />} disabled={d.status !== 'ready'} onSelect={() => askAbout(navigate, d.id)}>
                                Ask about this document
                              </MenuItem>
                              <MenuItem icon={<ScrollText />} disabled={d.status !== 'ready'} onSelect={() => summarise(navigate, d.id)}>
                                Summarise
                              </MenuItem>
                              <MenuItem icon={<Eye />} disabled={d.status !== 'ready'} onSelect={() => navigate(`/library/${d.id}`)}>
                                Open
                              </MenuItem>
                              <MenuSeparator />
                              <MenuItem icon={<Trash2 />} danger onSelect={() => setToDelete(d)}>
                                {d.status === 'failed' ? 'Remove' : 'Delete'}
                              </MenuItem>
                            </MenuContent>
                          </Menu>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {rows.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-4 py-10 text-center text-sm text-subtle">
                        No documents match these filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <p className="mt-3 flex items-center gap-1.5 text-xs text-subtle">
              <Upload className="size-3.5" /> Documents are encrypted at rest and only searchable once their status is Ready.
            </p>
          </>
        )}
      </div>

      <Dialog
        open={!!toDelete}
        onOpenChange={(o) => !o && setToDelete(null)}
        size="sm"
        title={`Delete ${toDelete ? docTitle(toDelete.name) : 'document'}?`}
        description="This permanently deletes the file, its extracted text and its search-index entries. It stops appearing in answers immediately, and it can’t be undone."
        footer={
          <>
            <Button variant="ghost" onClick={() => setToDelete(null)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={confirmDelete}>
              Delete permanently
            </Button>
          </>
        }
      >
        <p className="rounded-lg bg-bg px-3 py-2 text-[13px] leading-5 text-muted">
          Conversations that cited this document keep their text, but those citations will no longer open a source.
        </p>
      </Dialog>
    </div>
  );
}

function SortHeader({ label, k, sort, onSort, className }: { label: string; k: SortKey; sort: { key: SortKey; dir: 'asc' | 'desc' }; onSort: (k: SortKey) => void; className?: string }) {
  const active = sort.key === k;
  return (
    <th scope="col" aria-sort={active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'} className={cn('px-3 py-2.5 font-medium', className)}>
      <button onClick={() => onSort(k)} className={cn('inline-flex items-center gap-1 hover:text-ink', active && 'text-ink')}>
        {label}
        {active && (sort.dir === 'asc' ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />)}
      </button>
    </th>
  );
}

function FileBadge({ name }: { name: string }) {
  const ext = name.slice(name.lastIndexOf('.') + 1).toUpperCase();
  return (
    <span className="mt-0.5 flex h-8 w-7 shrink-0 items-end justify-center rounded-[5px] border border-border bg-bg pb-1 text-[8.5px] font-bold tracking-wide text-muted" aria-hidden>
      {ext.slice(0, 4)}
    </span>
  );
}

function TableSkeleton() {
  return (
    <div className="mt-6 space-y-3 rounded-xl border border-border bg-surface p-4" aria-busy aria-label="Loading documents">
      {[0, 1, 2, 3, 4].map((i) => (
        <div key={i} className="flex items-center gap-3">
          <div className="skeleton h-8 w-7" />
          <div className="skeleton h-4 flex-1" />
          <div className="skeleton h-5 w-20 rounded-full" />
        </div>
      ))}
    </div>
  );
}

