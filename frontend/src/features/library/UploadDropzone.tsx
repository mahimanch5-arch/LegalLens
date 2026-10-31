import { FileUp, UploadCloud } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { UPLOAD_LIMITS } from '@/api/types';
import { cn } from '@/lib/cn';

interface Props {
  onFiles: (files: File[]) => void;
  compact?: boolean;
  busy?: boolean;
}

/** Multi-file drag-and-drop plus file picker (FR-1). Also catches files dropped anywhere on the page. */
export function UploadDropzone({ onFiles, compact, busy }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [pageDrag, setPageDrag] = useState(false);

  useEffect(() => {
    let depth = 0;
    const hasFiles = (e: DragEvent) => Array.from(e.dataTransfer?.types ?? []).includes('Files');
    const enter = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      depth++;
      setPageDrag(true);
    };
    const leave = () => {
      depth = Math.max(0, depth - 1);
      if (depth === 0) setPageDrag(false);
    };
    const over = (e: DragEvent) => hasFiles(e) && e.preventDefault();
    const drop = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      e.preventDefault();
      depth = 0;
      setPageDrag(false);
      const files = Array.from(e.dataTransfer?.files ?? []);
      if (files.length) onFiles(files);
    };
    window.addEventListener('dragenter', enter);
    window.addEventListener('dragleave', leave);
    window.addEventListener('dragover', over);
    window.addEventListener('drop', drop);
    return () => {
      window.removeEventListener('dragenter', enter);
      window.removeEventListener('dragleave', leave);
      window.removeEventListener('dragover', over);
      window.removeEventListener('drop', drop);
    };
  }, [onFiles]);

  return (
    <>
      <button
        type="button"
        onClick={() => input.current?.click()}
        onDragEnter={() => setOver(true)}
        onDragLeave={() => setOver(false)}
        onDrop={() => setOver(false)}
        disabled={busy}
        className={cn(
          'group flex w-full items-center rounded-2xl border-2 border-dashed text-left transition-colors',
          compact ? 'gap-3 px-4 py-3' : 'flex-col justify-center gap-3 px-6 py-12 text-center',
          over ? 'border-primary bg-primary-soft/50' : 'border-border bg-surface hover:border-primary/40 hover:bg-primary-soft/20',
        )}
      >
        <span className={cn('flex shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary', compact ? 'size-9' : 'size-12')}>
          <UploadCloud className={compact ? 'size-[18px]' : 'size-6'} />
        </span>
        <span className="min-w-0">
          <span className={cn('block font-medium text-ink', !compact && 'text-base')}>
            Drop files here or <span className="text-primary underline-offset-2 group-hover:underline">browse</span>
          </span>
          <span className="block text-[13px] text-muted">PDF, DOCX or TXT · up to 50 MB and 500 pages each · several at once</span>
        </span>
      </button>
      <input
        ref={input}
        type="file"
        multiple
        hidden
        accept={UPLOAD_LIMITS.accept.join(',')}
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          if (files.length) onFiles(files);
          e.target.value = '';
        }}
      />

      {pageDrag && (
        <div className="pointer-events-none fixed inset-0 z-[95] flex animate-fade-in items-center justify-center bg-primary/10 p-6 backdrop-blur-[1px]">
          <div className="flex flex-col items-center rounded-2xl border-2 border-dashed border-primary bg-surface px-10 py-8 shadow-pop">
            <FileUp className="size-8 text-primary" />
            <p className="mt-3 text-base font-semibold text-ink">Drop to upload</p>
            <p className="mt-1 text-sm text-muted">Files are encrypted at rest and never used for training.</p>
          </div>
        </div>
      )}
    </>
  );
}
