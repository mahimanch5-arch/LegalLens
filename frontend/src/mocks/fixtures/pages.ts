import type { Citation, DocType, DocumentPage, Excerpt } from '@/api/types';
import { authoredPages } from './documents';

const CONTRACT_FILLER = [
  'Each party shall comply with all laws and regulations applicable to its performance under this Agreement.',
  'Headings are for convenience only and do not affect the interpretation of this Agreement.',
  'No waiver of any provision is effective unless it is in writing and signed by the waiving party.',
  'If any provision is held invalid or unenforceable, the remaining provisions remain in full force and effect.',
  'This Agreement may be executed in counterparts, each of which is deemed an original.',
  'Any amendment to this Agreement must be in writing and signed by authorized representatives of both parties.',
  'The parties shall cooperate in good faith to give effect to the intent of this Agreement.',
  'References to a Section include all of its subsections unless the context otherwise requires.',
];

const OPINION_FILLER = [
  'We review the district court\'s grant of summary judgment de novo, viewing the evidence in the light most favorable to the non-moving party.',
  'The interpretation of a contract is a question of law where, as here, the relevant language is unambiguous.',
  'The parties do not dispute the authenticity of the documents in the record.',
  'We decline to reach arguments raised for the first time on appeal.',
  'The record reflects that both parties were represented by counsel throughout the negotiation.',
  'We therefore turn to the language the parties actually chose.',
];

const PLEADING_FILLER = [
  'Plaintiff is informed and believes, and on that basis alleges, that each Defendant was the agent of each other Defendant.',
  'Plaintiff incorporates by reference each preceding paragraph as though fully set forth herein.',
  'Venue is proper in this County because the acts complained of occurred here.',
  'Plaintiff has exhausted all required administrative remedies.',
];

function filler(type: DocType, page: number): string {
  const pool = type === 'opinion' ? OPINION_FILLER : type === 'pleading' ? PLEADING_FILLER : CONTRACT_FILLER;
  const paras: string[] = [];
  for (let i = 0; i < 4; i++) {
    const a = pool[(page * 3 + i) % pool.length];
    const b = pool[(page * 5 + i + 1) % pool.length];
    paras.push(`${a} ${b}`);
  }
  return paras.join('\n\n');
}

export function getPageText(documentId: string, page: number, type: DocType): string {
  return authoredPages[documentId]?.[page] ?? filler(type, page);
}

export function buildPage(
  documentId: string,
  page: number,
  type: DocType,
  lowOcrPages: number[],
): DocumentPage {
  const lowOcr = lowOcrPages.includes(page);
  return {
    documentId,
    page,
    text: getPageText(documentId, page, type),
    ocrConfidence: lowOcr ? 0.58 : 0.99,
    lowOcr,
  };
}

/** Span ids encode their location, so GET /api/spans/{id} can be resolved without a lookup table. */
export function spanId(documentId: string, page: number, start: number, end: number): string {
  return `${documentId}~p${page}~${start}-${end}`;
}

export function parseSpanId(id: string): { documentId: string; page: number; start: number; end: number } | null {
  const m = /^(.+)~p(\d+)~(\d+)-(\d+)$/.exec(id);
  if (!m) return null;
  return { documentId: m[1], page: Number(m[2]), start: Number(m[3]), end: Number(m[4]) };
}

export interface DocRef {
  id: string;
  name: string;
  type: DocType;
}

/** Locates `quote` on the page and returns a citation with exact character offsets. */
export function locate(doc: DocRef, page: number, quote: string, section?: string): Omit<Citation, 'n'> {
  const text = getPageText(doc.id, page, doc.type);
  const start = text.indexOf(quote);
  if (start < 0) throw new Error(`Fixture quote not found on ${doc.id} p.${page}: "${quote.slice(0, 40)}…"`);
  const end = start + quote.length;
  return {
    spanId: spanId(doc.id, page, start, end),
    documentId: doc.id,
    documentName: doc.name,
    page,
    charStart: start,
    charEnd: end,
    quote,
    section,
  };
}

/** The paragraph containing a citation, used as the retrieved excerpt. */
export function excerptFor(c: Omit<Citation, 'n'>, score: number): Excerpt {
  const doc = { id: c.documentId, type: 'contract' as DocType };
  const text = getPageText(doc.id, c.page, doc.type);
  const paraStart = text.lastIndexOf('\n\n', c.charStart) + 1;
  const paraEndIdx = text.indexOf('\n\n', c.charEnd);
  const paraEnd = paraEndIdx < 0 ? text.length : paraEndIdx;
  return {
    spanId: c.spanId,
    documentId: c.documentId,
    documentName: c.documentName,
    page: c.page,
    section: c.section,
    text: text.slice(paraStart, paraEnd).trim(),
    score,
  };
}
