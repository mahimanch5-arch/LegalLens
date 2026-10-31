import { UPLOAD_LIMITS } from '@/api/types';
import { formatBytes } from '@/lib/format';

export interface Rejection {
  name: string;
  reason: string;
}

/**
 * Client-side checks before upload (FR-2). Each rejection names the limit and the actual
 * value. The page-count limit can only be checked by the server after parsing.
 */
export function validateFiles(files: File[]): { accepted: File[]; rejected: Rejection[] } {
  const accepted: File[] = [];
  const rejected: Rejection[] = [];
  for (const f of files) {
    const dot = f.name.lastIndexOf('.');
    const ext = dot >= 0 ? f.name.slice(dot).toLowerCase() : '';
    if (!(UPLOAD_LIMITS.accept as readonly string[]).includes(ext)) {
      rejected.push({ name: f.name, reason: `${ext ? ext.toUpperCase().slice(1) + ' files are' : 'This file type is'} not supported. Upload PDF, DOCX or TXT.` });
    } else if (f.size > UPLOAD_LIMITS.maxBytes) {
      rejected.push({ name: f.name, reason: `This file is ${formatBytes(f.size)}; the limit is 50 MB.` });
    } else if (f.size === 0) {
      rejected.push({ name: f.name, reason: 'This file is empty.' });
    } else {
      accepted.push(f);
    }
  }
  return { accepted, rejected };
}
