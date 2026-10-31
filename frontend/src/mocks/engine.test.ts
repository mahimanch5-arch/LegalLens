import { describe, expect, it } from 'vitest';
import type { SendMessageRequest } from '@/api/types';
import { DOC_IDS, seedDocuments } from './fixtures/documents';
import { getPageText } from './fixtures/pages';
import { detectIntent, planResponse } from './engine';

const docs = seedDocuments;
const ws = { kind: 'workspace' } as const;
const ask = (text: string, scope: SendMessageRequest['scope'] = ws): SendMessageRequest => ({ text, mode: 'ask', scope });

/** Mirrors the backend citation gate (FR-21): every citation must resolve to its exact span. */
function expectCitationsResolve(req: SendMessageRequest) {
  const plan = planResponse(req, docs);
  for (const c of plan.citations) {
    const doc = docs.find((d) => d.id === c.documentId)!;
    expect(getPageText(c.documentId, c.page, doc.type).slice(c.charStart, c.charEnd)).toBe(c.quote);
  }
  for (const m of plan.answerMd.matchAll(/\[(\d+)\]/g)) {
    expect(plan.citations.some((c) => c.n === Number(m[1]))).toBe(true);
  }
  return plan;
}

describe('mock engine', () => {
  it.each([
    'What are the termination rights?',
    'When does the agreement renew?',
    'Can Northwind assign the contract after a merger?',
    'What is the liability cap?',
    'When are invoices due?',
    'Which governing law applies?',
    'Does an email count as written notice?',
    'When was Reyes fired?',
    'What happens after a security incident?',
  ])('grounds "%s" in resolvable citations', (q) => {
    const plan = expectCitationsResolve(ask(q));
    expect(plan.refusal).toBeUndefined();
    expect(plan.citations.length).toBeGreaterThan(0);
  });

  it('refuses when nothing in scope supports an answer', () => {
    const plan = planResponse(ask('Are there any non-compete restrictions on our employees?'), docs);
    expect(plan.refusal).toBeDefined();
    expect(plan.citations).toHaveLength(0);
  });

  it('refuses questions that need outside law', () => {
    expect(planResponse(ask('What is the statute of limitations for this claim?'), docs).refusal).toBeDefined();
  });

  it('never searches documents that are not ready (FR-7)', () => {
    const plan = planResponse(ask('termination rights'), docs);
    expect(plan.scopeUsed.documentIds).not.toContain(DOC_IDS.minutes);
  });

  it.each(Object.values(DOC_IDS).filter((id) => id !== DOC_IDS.minutes))('summarises %s with resolvable field citations', (id) => {
    const plan = expectCitationsResolve({ text: 'Summarize', mode: 'summary', scope: { kind: 'documents', documentIds: [id] }, summaryDocumentId: id });
    expect(plan.summary?.documentId).toBe(id);
  });

  it('drafts a memo and a case brief with resolvable citations', () => {
    const memo = expectCitationsResolve({
      text: 'Draft', mode: 'draft', scope: ws,
      draftParams: { draftType: 'memo', questionPresented: 'Can Acme terminate for breach by email notice?', audience: 'Partner', position: '', tone: 'neutral', sourceDocumentIds: [DOC_IDS.acme, DOC_IDS.smith] },
    });
    expect(memo.answerMd).toContain('## Question Presented');
    const brief = expectCitationsResolve({
      text: 'Brief', mode: 'draft', scope: ws,
      draftParams: { draftType: 'brief', questionPresented: 'x', audience: '', position: '', tone: 'neutral', sourceDocumentIds: [DOC_IDS.smith] },
    });
    expect(brief.answerMd).toContain('## Holding');
  });

  it('refuses a draft with no sources (FR-19)', () => {
    const plan = planResponse({ text: 'Draft', mode: 'draft', scope: ws, draftParams: { draftType: 'memo', questionPresented: 'q', audience: '', position: '', tone: 'neutral', sourceDocumentIds: [] } }, docs);
    expect(plan.refusal).toBeDefined();
  });

  it('detects intent in Auto mode', () => {
    expect(detectIntent('Summarize the MSA')).toBe('summary');
    expect(detectIntent('Draft a memo on termination')).toBe('draft');
    expect(detectIntent('What is the notice period?')).toBe('ask');
  });
});
