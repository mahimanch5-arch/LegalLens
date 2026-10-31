/**
 * Mock response engine. Stands in for the orchestration + RAG layer so the UI can be built
 * against realistic, *grounded* output: every citation it emits resolves to a real span in
 * the fixture page text, exactly as the real citation-verification gate will guarantee.
 */
import type {
  Citation,
  DocType,
  DraftMeta,
  Excerpt,
  Intent,
  LegalDocument,
  Refusal,
  ScopeUsed,
  SendMessageRequest,
  SummaryResult,
  SummarySection,
  Usage,
} from '@/api/types';
import { authoredPages, DOC_IDS } from './fixtures/documents';
import { excerptFor, locate, type DocRef } from './fixtures/pages';

export interface ResponsePlan {
  intent: Intent;
  scopeUsed: ScopeUsed;
  stages: string[];
  answerMd: string;
  citations: Citation[];
  excerpts: Excerpt[];
  refusal?: Refusal;
  summary?: SummaryResult;
  draft?: DraftMeta;
  usage: Usage;
}

// ---------- helpers ----------

export const displayName = (name: string) => name.replace(/\.(pdf|docx|txt)$/i, '');

class CitationBook {
  readonly citations: Citation[] = [];
  readonly excerpts: Excerpt[] = [];

  constructor(private docs: Map<string, LegalDocument>) {}

  /** Registers a citation and returns its marker, e.g. "[2]". Re-citing the same span reuses the number. */
  cite(docId: string, page: number, quote: string, section?: string): string {
    return `[${this.n(docId, page, quote, section)}]`;
  }

  n(docId: string, page: number, quote: string, section?: string): number {
    const doc = this.docs.get(docId);
    if (!doc) throw new Error(`Unknown fixture doc ${docId}`);
    const located = locate(ref(doc), page, quote, section);
    const existing = this.citations.find((c) => c.spanId === located.spanId);
    if (existing) return existing.n;
    const n = this.citations.length + 1;
    this.citations.push({ ...located, n });
    this.excerpts.push(excerptFor(located, Math.max(0.42, 0.93 - (n - 1) * 0.07)));
    return n;
  }
}

const ref = (d: LegalDocument): DocRef => ({ id: d.id, name: d.name, type: d.type });

function usageFor(text: string, sources: number): Usage {
  const outputTokens = Math.round(text.length / 4) + 20;
  const inputTokens = 900 + sources * 650;
  return {
    inputTokens,
    outputTokens,
    costUsd: Number((inputTokens * 0.000003 + outputTokens * 0.000015).toFixed(4)),
    latencyMs: 1800 + outputTokens * 18,
  };
}

function resolveScope(req: SendMessageRequest, docs: LegalDocument[]): { inScope: LegalDocument[]; scopeUsed: ScopeUsed } {
  const ready = docs.filter((d) => d.status === 'ready'); // FR-7
  if (req.scope.kind === 'workspace') {
    return {
      inScope: ready,
      scopeUsed: {
        kind: 'workspace',
        documentIds: ready.map((d) => d.id),
        label: `Whole workspace (${ready.length} document${ready.length === 1 ? '' : 's'})`,
      },
    };
  }
  const ids = new Set(req.scope.documentIds);
  const inScope = ready.filter((d) => ids.has(d.id));
  const label =
    inScope.length === 1
      ? displayName(inScope[0].name)
      : `${inScope.length} selected documents`;
  return { inScope, scopeUsed: { kind: 'documents', documentIds: inScope.map((d) => d.id), label } };
}

export function detectIntent(text: string): Intent {
  if (/\b(summari[sz]e|summary|overview|key terms|brief me on)\b/i.test(text)) return 'summary';
  if (/\b(draft|write (a|me a) (memo|brief)|prepare a (memo|brief)|memo|case brief)\b/i.test(text)) return 'draft';
  return 'ask';
}

// ---------- Ask: canned topics ----------

interface Point {
  doc: string;
  page: number;
  quote: string;
  section?: string;
  /** Sentence written before the citation marker. */
  says: string;
}

interface Topic {
  pattern: RegExp;
  intro: string;
  points: Point[];
  outro?: string;
}

const TOPICS: Topic[] = [
  {
    pattern: /\b(terminat\w*|cancel\w*|exit|end the (agreement|contract)|get out)\b/i,
    intro: 'The Master Services Agreement gives each party three routes to terminate:',
    points: [
      { doc: DOC_IDS.acme, page: 14, section: '§11.1', quote: "Either party may terminate this Agreement for convenience upon one hundred twenty (120) days' prior written notice to the other party.", says: '**For convenience** — either party, on **120 days’ prior written notice**.' },
      { doc: DOC_IDS.acme, page: 14, section: '§11.2', quote: 'fails to cure such breach within thirty (30) days after receiving written notice describing the breach in reasonable detail', says: '**For cause** — on written notice after a material breach that is not cured within **30 days** of a notice describing the breach in reasonable detail.' },
      { doc: DOC_IDS.acme, page: 14, section: '§11.3', quote: 'Either party may terminate this Agreement immediately upon written notice if the other party becomes insolvent', says: '**Insolvency** — immediately on written notice if the other party becomes insolvent or enters bankruptcy proceedings not dismissed within 60 days.' },
      { doc: DOC_IDS.acme, page: 22, section: '§16.2', quote: 'Customer may terminate this Agreement within sixty (60) days after receiving notice of such change of control', says: 'Separately, **Customer alone** may terminate within **60 days** after notice of a change of control of Provider.' },
      { doc: DOC_IDS.helix, page: 4, section: '§3.2', quote: 'unless either party notifies the other of non-renewal at least sixty (60) days before the end of the current term', says: 'The Helix subscription has no termination-for-convenience right in the pages indexed; it ends by **non-renewal on 60 days’ notice** before the term ends.' },
    ],
    outro: 'On termination, Customer pays for Services performed through the effective date, and each party must return or destroy the other’s Confidential Information within 15 days.',
  },
  {
    pattern: /\b(renew\w*|initial term|how long|expir\w*|duration)\b/i,
    intro: 'Term and renewal across your agreements:',
    points: [
      { doc: DOC_IDS.acme, page: 3, section: '§2.1', quote: 'continues for an initial term of three (3) years', says: 'The **Acme–Northwind MSA** runs for an initial term of **three years** from March 1, 2024.' },
      { doc: DOC_IDS.acme, page: 3, section: '§2.2', quote: 'unless either party gives written notice of non-renewal at least ninety (90) days before the end of the then-current term', says: 'It then renews automatically for one-year periods unless either party gives non-renewal notice at least **90 days** before the term ends.' },
      { doc: DOC_IDS.exhibit, page: 2, quote: 'The Initial Term is ext3nded to f0ur (4) years', says: 'Amendment No. 2 appears to extend the initial term to **four years** — but this page has low OCR confidence, so check the original scan before relying on it.' },
      { doc: DOC_IDS.helix, page: 4, section: '§3.2', quote: 'The Subscription Term renews automatically for successive twelve (12) month periods', says: 'The **Helix subscription** renews automatically for successive 12-month periods, with **60 days’** non-renewal notice.' },
    ],
  },
  {
    pattern: /\b(assign\w*|change of control|merger|acqui\w*|successor|transfer)\b/i,
    intro: 'Assignment under the Acme–Northwind MSA:',
    points: [
      { doc: DOC_IDS.acme, page: 22, section: '§16.2', quote: 'Neither party may assign or transfer this Agreement, in whole or in part, without the prior written consent of the other party', says: 'The default rule is that **neither party may assign** without the other’s prior written consent.' },
      { doc: DOC_IDS.acme, page: 22, section: '§16.2', quote: 'either party may assign this Agreement without consent to a successor in connection with a merger, acquisition, or sale of all or substantially all of its assets, provided the successor assumes this Agreement in writing', says: 'There is a **carve-out for M&A**: either party may assign without consent to a successor in a merger, acquisition or sale of substantially all assets, if the successor assumes the Agreement in writing.' },
      { doc: DOC_IDS.acme, page: 22, section: '§16.2', quote: 'Any change of control of Provider shall be deemed an assignment for purposes of this Section 16.2', says: 'A **change of control of Provider** is deemed an assignment' },
      { doc: DOC_IDS.acme, page: 22, section: '§16.2', quote: 'Customer may terminate this Agreement within sixty (60) days after receiving notice of such change of control', says: 'and gives **Customer** a right to terminate within **60 days** of notice. This right is one-sided: there is no equivalent for a change of control of Customer.' },
    ],
  },
  {
    pattern: /\b(liabilit\w*|cap|damages|consequential|indemn\w*|gross negligence)\b/i,
    intro: 'Limitation of liability in your documents:',
    points: [
      { doc: DOC_IDS.acme, page: 18, section: '§13.1', quote: "IN NO EVENT SHALL EITHER PARTY'S AGGREGATE LIABILITY ARISING OUT OF THIS AGREEMENT EXCEED THE FEES PAID OR PAYABLE BY CUSTOMER IN THE TWELVE (12) MONTHS PRECEDING THE EVENT GIVING RISE TO THE CLAIM", says: '**Acme–Northwind MSA:** each party’s aggregate liability is capped at the **fees paid or payable in the prior 12 months**' },
      { doc: DOC_IDS.acme, page: 18, section: '§13.1', quote: "EXCEPT FOR BREACHES OF SECTION 9 (CONFIDENTIALITY) AND A PARTY'S INDEMNIFICATION OBLIGATIONS", says: 'with carve-outs for **confidentiality breaches and indemnification**.' },
      { doc: DOC_IDS.acme, page: 18, section: '§13.2', quote: 'NEITHER PARTY SHALL BE LIABLE FOR ANY INDIRECT, INCIDENTAL, CONSEQUENTIAL, SPECIAL OR PUNITIVE DAMAGES', says: 'Indirect, consequential and punitive damages and lost profits are excluded.' },
      { doc: DOC_IDS.helix, page: 11, section: '§9.1', quote: "Each party's total liability under this Agreement shall not exceed two times (2x) the fees paid by Subscriber in the twelve (12) months before the claim.", says: '**Helix subscription:** the cap is **2x** the prior 12 months’ fees' },
      { doc: DOC_IDS.helix, page: 11, section: '§9.2', quote: "for which Helix's liability is capped at five times (5x) such fees", says: 'rising to **5x** for Helix’s data-protection obligations.' },
      { doc: DOC_IDS.bayview, page: 10, quote: 'A limitation-of-liability clause negotiated between sophisticated commercial parties is enforceable according to its terms, but does not shield a party from liability for its own gross negligence.', says: 'On enforceability, *Bayview Freight Lines v. Delmar Shipping* holds that such a clause is enforceable between sophisticated parties but **does not shield a party from its own gross negligence**.' },
    ],
  },
  {
    pattern: /\b(pay\w*|invoice\w*|late|fee\w*|price|rate increase)\b/i,
    intro: 'Payment terms under the Acme–Northwind MSA:',
    points: [
      { doc: DOC_IDS.acme, page: 9, section: '§6.2', quote: 'Customer shall pay all undisputed invoices within thirty (30) days of receipt.', says: 'Undisputed invoices are due **within 30 days** of receipt.' },
      { doc: DOC_IDS.acme, page: 9, section: '§6.2', quote: 'Late amounts bear interest at the lesser of 1.0% per month or the maximum rate permitted by law.', says: 'Late amounts bear interest at **1.0% per month** or the legal maximum, whichever is lower.' },
      { doc: DOC_IDS.acme, page: 9, section: '§6.4', quote: "by no more than five percent (5%), on sixty (60) days' written notice", says: 'The original MSA allowed one rate increase a year of up to **5%** on 60 days’ notice' },
      { doc: DOC_IDS.exhibit, page: 1, quote: "by no more than three percent (3%), on ninety (90) days' written notice", says: '— but **Amendment No. 2 replaced that clause**: increases are now limited to **3%** on **90 days’** notice.' },
    ],
  },
  {
    pattern: /\b(governing law|jurisdiction|venue|forum|dispute\w*|which court)\b/i,
    intro: 'Governing law and forum:',
    points: [
      { doc: DOC_IDS.acme, page: 23, section: '§16.5', quote: 'This Agreement is governed by the laws of the State of Delaware, without regard to its conflict-of-laws principles.', says: 'The Acme–Northwind MSA is governed by **Delaware law**.' },
      { doc: DOC_IDS.acme, page: 23, section: '§16.5', quote: 'Any dispute shall be resolved exclusively in the state or federal courts located in Wilmington, Delaware.', says: 'Disputes go **exclusively** to the state or federal courts in **Wilmington, Delaware**.' },
    ],
  },
  {
    pattern: /\b(email|e-mail|written notice|notice)\b/i,
    intro: 'Whether email counts as written notice:',
    points: [
      { doc: DOC_IDS.smith, page: 12, quote: 'We hold that, absent language in the contract requiring a specific method of delivery, an email that identifies the breach with reasonable particularity and is sent to the contractually designated contact constitutes written notice.', says: 'In *Smith v. Jones Holdings*, the Ninth Circuit held that, **absent contract language requiring a specific delivery method**, an email that identifies the breach with reasonable particularity and goes to the designated contact is written notice.' },
      { doc: DOC_IDS.acme, page: 22, section: '§16.1', quote: 'with a copy by courier for any notice of breach or termination', says: 'The Acme–Northwind MSA **does** specify delivery: email is permitted, but notices of breach or termination also require **a copy by courier**' },
      { doc: DOC_IDS.smith, page: 27, quote: 'I would hold that "written notice," without more, requires a signed writing delivered by a recognized physical method.', says: 'Note the dissent in *Smith*, which would require physical delivery.' },
    ],
    outro: 'Because §16.1 prescribes a method, the *Smith* rule may not help a party that sent an email alone under the MSA. That is an inference for you to evaluate, not something either document states.',
  },
  {
    pattern: /\b(reyes|retaliat\w*|whistle\w*|wrongful termination|fired|coastal)\b/i,
    intro: 'The Reyes complaint alleges:',
    points: [
      { doc: DOC_IDS.reyes, page: 4, quote: 'On January 6, 2025, Plaintiff reported to Defendant\'s regional operations manager, in writing, that drivers were being instructed to falsify hours-of-service logs.', says: 'Reyes reported in writing on **January 6, 2025** that drivers were being told to falsify hours-of-service logs' },
      { doc: DOC_IDS.reyes, page: 4, quote: 'On January 21, 2025, Plaintiff repeated her report to Defendant\'s human-resources department and requested an investigation.', says: 'and repeated the report to HR on **January 21, 2025**.' },
      { doc: DOC_IDS.reyes, page: 4, quote: 'Less than four weeks later, Defendant terminated Plaintiff\'s employment, citing "restructuring." No other dispatch supervisor was terminated.', says: 'She was terminated **less than four weeks later**, on February 14, 2025, for stated "restructuring", and no other dispatch supervisor was terminated.' },
      { doc: DOC_IDS.reyes, page: 11, quote: 'Defendant retaliated against Plaintiff for those disclosures by terminating her employment.', says: 'The complaint pleads wrongful termination in violation of public policy and retaliation under Labor Code section 1102.5.' },
    ],
  },
  {
    pattern: /\b(data breach|security incident|breach notification|personal data|data protection)\b/i,
    intro: 'Security-incident obligations:',
    points: [
      { doc: DOC_IDS.helix, page: 7, section: '§6.2', quote: 'within seventy-two (72) hours, after becoming aware of a Security Incident affecting Subscriber Data', says: 'Helix must notify Subscriber without undue delay and **within 72 hours** of becoming aware of a Security Incident' },
      { doc: DOC_IDS.helix, page: 7, section: '§6.3', quote: 'Helix shall make Subscriber Data available for export for thirty (30) days and shall then delete it.', says: 'and on termination must make data available for export for **30 days**, then delete it.' },
    ],
  },
];

const OUTSIDE_LAW = /\b(statute of limitations|case law|precedent|what does (the )?law say|under (california|new york|federal) law|is it legal|other cases|recent cases)\b/i;

const STOP = new Set('a an the of to in on for and or is are was were be by with what which who when where how does do did can could should would may this that these those my our your any all from at as it its under about there their them me we us i'.split(' '));

function keywordSearch(question: string, inScope: LegalDocument[]): { doc: LegalDocument; page: number; sentence: string; score: number }[] {
  const terms = question.toLowerCase().match(/[a-z]{3,}/g)?.filter((t) => !STOP.has(t)) ?? [];
  if (terms.length === 0) return [];
  const hits: { doc: LegalDocument; page: number; sentence: string; score: number }[] = [];
  for (const doc of inScope) {
    for (const [pageStr, text] of Object.entries(authoredPages[doc.id] ?? {})) {
      const sentences = text.match(/[^.\n]+[.]/g) ?? [];
      for (const raw of sentences) {
        const sentence = raw.trim();
        const lower = sentence.toLowerCase();
        const score = new Set(terms.filter((t) => lower.includes(t))).size;
        if (score >= 2 && sentence.length > 40) hits.push({ doc, page: Number(pageStr), sentence, score });
      }
    }
  }
  return hits.sort((a, b) => b.score - a.score).slice(0, 3);
}

function refusalFor(scopeUsed: ScopeUsed, reason: string, extra: string[] = []): Refusal {
  const suggestions = [...extra];
  if (scopeUsed.kind === 'documents') suggestions.push('Widen the scope to the whole workspace.');
  suggestions.push('Upload the document that covers this topic.');
  suggestions.push('Rephrase using the words the document is likely to use (for example "assignment" rather than "handing over").');
  return { reason, scopeLabel: scopeUsed.label, suggestions };
}

function planAsk(text: string, inScope: LegalDocument[], scopeUsed: ScopeUsed, docMap: Map<string, LegalDocument>): Omit<ResponsePlan, 'usage' | 'stages'> {
  const book = new CitationBook(docMap);
  const scopeIds = new Set(inScope.map((d) => d.id));

  if (OUTSIDE_LAW.test(text)) {
    return {
      intent: 'ask', scopeUsed, answerMd: '', citations: [], excerpts: [],
      refusal: refusalFor(scopeUsed, 'Legal Lens answers only from the documents you have uploaded. It does not search statutes, regulations or case law outside your workspace, so it cannot answer this without a source.', ['Upload the authority you want analysed, then ask about it.']),
    };
  }

  const topic = TOPICS.find((t) => t.pattern.test(text) && t.points.some((p) => scopeIds.has(p.doc)));
  if (topic) {
    const lines = topic.points
      .filter((p) => scopeIds.has(p.doc))
      .map((p) => `- ${p.says} ${book.cite(p.doc, p.page, p.quote, p.section)}`);
    const md = [topic.intro, '', ...lines, ...(topic.outro ? ['', topic.outro] : [])].join('\n');
    return { intent: 'ask', scopeUsed, answerMd: md, citations: book.citations, excerpts: book.excerpts };
  }

  const hits = keywordSearch(text, inScope);
  if (hits.length > 0) {
    const lines = hits.map((h) => `- *${displayName(h.doc.name)}*, p.${h.page}: “${h.sentence}” ${book.cite(h.doc.id, h.page, h.sentence)}`);
    const md = ['These are the passages in your documents that address this most directly:', '', ...lines, '', 'They may not answer the question completely; open each source to read it in context.'].join('\n');
    return { intent: 'ask', scopeUsed, answerMd: md, citations: book.citations, excerpts: book.excerpts };
  }

  return {
    intent: 'ask', scopeUsed, answerMd: '', citations: [], excerpts: [],
    refusal: refusalFor(scopeUsed, `I couldn't find anything in ${scopeUsed.kind === 'workspace' ? 'your documents' : 'the selected documents'} that answers this question, so I won't guess.`),
  };
}

// ---------- Summary ----------

type Cite = [page: number, quote: string, section?: string];
interface FieldData { value: string; cites: Cite[]; flag?: string }

const TEMPLATES: Record<DocType, { title: string; fields: string[] }[]> = {
  contract: [
    { title: 'Parties and dates', fields: ['Parties and roles', 'Effective date', 'Initial term', 'Renewal'] },
    { title: 'Obligations', fields: ['Provider obligations', 'Customer obligations'] },
    { title: 'Payment', fields: ['Payment terms', 'Price changes'] },
    { title: 'Termination', fields: ['Termination rights', 'Notice periods', 'Effect of termination'] },
    { title: 'Risk allocation', fields: ['Limitation of liability', 'Indemnification'] },
    { title: 'Assignment and change of control', fields: ['Assignment', 'Change of control'] },
    { title: 'Governing law and disputes', fields: ['Governing law', 'Dispute resolution'] },
  ],
  opinion: [
    { title: 'Case', fields: ['Court', 'Parties', 'Procedural posture'] },
    { title: 'Facts', fields: ['Key facts'] },
    { title: 'Issues presented', fields: ['Issue'] },
    { title: 'Holding', fields: ['Holding'] },
    { title: 'Reasoning', fields: ['Reasoning'] },
    { title: 'Disposition', fields: ['Disposition', 'Concurrences and dissents'] },
  ],
  pleading: [
    { title: 'Case', fields: ['Court', 'Parties', 'Causes of action'] },
    { title: 'Relief sought', fields: ['Relief sought'] },
    { title: 'Key factual allegations', fields: ['Key factual allegations'] },
    { title: 'Legal theories', fields: ['Legal theories asserted'] },
    { title: 'Dates and deadlines', fields: ['Dates appearing in the document'] },
  ],
  other: [{ title: 'Overview', fields: ['Document type', 'Parties', 'Key dates'] }],
};

const SUMMARY_DATA: Record<string, Record<string, FieldData>> = {
  [DOC_IDS.acme]: {
    'Parties and roles': { value: 'Northwind Analytics, LLC (Provider, a Delaware LLC) and Acme Industrial Holdings, Inc. (Customer, an Ohio corporation).', cites: [[1, 'by and between Northwind Analytics, LLC, a Delaware limited liability company ("Provider"), and Acme Industrial Holdings, Inc., an Ohio corporation ("Customer")']] },
    'Effective date': { value: 'March 1, 2024.', cites: [[1, 'is entered into as of March 1, 2024 (the "Effective Date")']] },
    'Initial term': { value: 'Three years from the Effective Date.', cites: [[3, 'continues for an initial term of three (3) years', '§2.1']] },
    Renewal: { value: 'Automatic one-year renewals unless either party gives non-renewal notice at least 90 days before the term ends.', cites: [[3, 'unless either party gives written notice of non-renewal at least ninety (90) days before the end of the then-current term', '§2.2']] },
    'Provider obligations': { value: 'Perform Services in a professional and workmanlike manner; maintain 99.9% monthly platform availability, with service credits as the sole remedy.', cites: [[5, 'Provider shall perform the services described in each SOW (the "Services") in a professional and workmanlike manner', '§3.1'], [5, 'Provider shall make the hosted reporting platform available at least 99.9% of each calendar month', '§3.2']] },
    'Customer obligations': { value: 'Provide timely access to systems, data and personnel; approve or reject deliverables within 10 business days, failing which they are deemed accepted.', cites: [[6, 'Customer shall provide Provider with timely access to the systems, data and personnel reasonably necessary', '§4.1'], [6, 'A deliverable not rejected in writing within that period is deemed accepted.', '§4.2']] },
    'Payment terms': { value: 'Undisputed invoices due within 30 days; late interest at the lesser of 1.0% per month or the legal maximum.', cites: [[9, 'Customer shall pay all undisputed invoices within thirty (30) days of receipt.', '§6.2'], [9, 'Late amounts bear interest at the lesser of 1.0% per month or the maximum rate permitted by law.', '§6.2']] },
    'Price changes': { value: 'One increase per 12 months, capped at 5%, on 60 days’ notice. (Amended to 3% on 90 days’ notice by Amendment No. 2, a separate document.)', cites: [[9, "Provider may increase its rates no more than once in any twelve (12) month period, and by no more than five percent (5%), on sixty (60) days' written notice.", '§6.4']] },
    'Termination rights': { value: 'For convenience (either party); for uncured material breach; on insolvency; and Customer-only on a change of control of Provider.', cites: [[14, 'Either party may terminate this Agreement for convenience', '§11.1'], [14, 'if the other party materially breaches this Agreement', '§11.2'], [14, 'if the other party becomes insolvent', '§11.3']] },
    'Notice periods': { value: '120 days for convenience; 30-day cure period for breach; immediate for insolvency.', cites: [[14, "upon one hundred twenty (120) days' prior written notice to the other party", '§11.1'], [14, 'fails to cure such breach within thirty (30) days after receiving written notice', '§11.2']] },
    'Effect of termination': { value: 'Customer pays for Services through the termination date; Confidential Information returned or destroyed within 15 days; up to 90 days’ paid transition assistance on request.', cites: [[15, 'Customer shall pay Provider for all Services performed through the effective date of termination', '§11.4'], [15, 'Provider shall provide reasonable transition assistance for up to ninety (90) days at its then-current rates', '§11.5']] },
    'Limitation of liability': { value: 'Aggregate cap equal to fees paid or payable in the prior 12 months, excluding confidentiality breaches and indemnities; indirect and consequential damages excluded.', cites: [[18, 'EXCEED THE FEES PAID OR PAYABLE BY CUSTOMER IN THE TWELVE (12) MONTHS PRECEDING THE EVENT GIVING RISE TO THE CLAIM', '§13.1'], [18, 'NEITHER PARTY SHALL BE LIABLE FOR ANY INDIRECT, INCIDENTAL, CONSEQUENTIAL, SPECIAL OR PUNITIVE DAMAGES', '§13.2']] },
    Indemnification: { value: 'Provider defends third-party US IP-infringement claims; Customer defends claims arising from Customer Data or unlawful use of deliverables.', cites: [[19, 'Provider shall defend Customer against any third-party claim alleging that the Services or deliverables infringe any United States patent, copyright or trademark', '§14.1'], [19, 'Customer shall defend Provider against any third-party claim arising from Customer Data', '§14.2']] },
    Assignment: { value: 'No assignment without consent, except to a successor in a merger, acquisition or sale of substantially all assets that assumes the Agreement in writing.', cites: [[22, 'Neither party may assign or transfer this Agreement, in whole or in part, without the prior written consent of the other party', '§16.2']] },
    'Change of control': { value: 'A change of control of Provider is deemed an assignment, and Customer may terminate within 60 days of notice.', cites: [[22, 'Any change of control of Provider shall be deemed an assignment for purposes of this Section 16.2', '§16.2']], flag: 'One-sided: only Customer gets a change-of-control exit right' },
    'Governing law': { value: 'Delaware, without regard to conflict-of-laws principles.', cites: [[23, 'This Agreement is governed by the laws of the State of Delaware', '§16.5']] },
    'Dispute resolution': { value: 'Exclusive jurisdiction of the state or federal courts in Wilmington, Delaware. No arbitration clause.', cites: [[23, 'Any dispute shall be resolved exclusively in the state or federal courts located in Wilmington, Delaware.', '§16.5']] },
  },
  [DOC_IDS.helix]: {
    'Parties and roles': { value: 'Helix Cloud Software, Inc. (provider) and Acme Industrial Holdings, Inc. (Subscriber).', cites: [[1, 'between Helix Cloud Software, Inc. ("Helix") and Acme Industrial Holdings, Inc. ("Subscriber")']] },
    'Effective date': { value: 'January 15, 2025.', cites: [[1, 'This SaaS Subscription Agreement is made on January 15, 2025']] },
    'Initial term': { value: 'Twelve months from the Order Start Date.', cites: [[4, 'The Subscription Term begins on the Order Start Date and continues for twelve (12) months.', '§3.1']] },
    Renewal: { value: 'Automatic 12-month renewals unless either party gives 60 days’ notice.', cites: [[4, 'unless either party notifies the other of non-renewal at least sixty (60) days before the end of the current term', '§3.2']] },
    'Price changes': { value: 'Helix may raise fees on renewal with 75 days’ notice; no cap on the increase appears.', cites: [[4, 'Helix may increase subscription fees on renewal by giving written notice at least seventy-five (75) days before the renewal date.', '§3.3']], flag: 'No cap on renewal price increases' },
    'Limitation of liability': { value: '2x the prior 12 months’ fees; 5x for Helix’s data-protection obligations.', cites: [[11, 'shall not exceed two times (2x) the fees paid by Subscriber', '§9.1'], [11, "Helix's liability is capped at five times (5x) such fees", '§9.2']] },
  },
  [DOC_IDS.exhibit]: {
    'Parties and roles': { value: 'Northwind Analytics, LLC (Provider) and Acme Industrial Holdings, Inc. (Customer); amends the March 1, 2024 MSA.', cites: [[1, 'between Northwind Analytics, LLC ("Provider") and Acme Industrial Holdings, Inc. ("Customer")']] },
    'Effective date': { value: 'September 1, 2025.', cites: [[1, 'This Amendment No. 2 is made effective September 1, 2025']] },
    'Price changes': { value: 'Replaces MSA §6.4: one increase per 12 months, capped at 3%, on 90 days’ notice.', cites: [[1, "by no more than three percent (3%), on ninety (90) days' written notice"]] },
    'Initial term': { value: 'Appears to extend the initial term to four years. Low OCR confidence on this page; verify against the scan.', cites: [[2, 'The Initial Term is ext3nded to f0ur (4) years']], flag: 'Low OCR confidence' },
  },
  [DOC_IDS.smith]: {
    Court: { value: 'United States Court of Appeals for the Ninth Circuit.', cites: [[1, 'UNITED STATES COURT OF APPEALS\nFOR THE NINTH CIRCUIT']] },
    Parties: { value: 'Daniel Smith (plaintiff-appellee) v. Jones Holdings, Inc. (defendant-appellant).', cites: [[1, 'DANIEL SMITH, Plaintiff-Appellee']] },
    'Procedural posture': { value: 'Appeal from a judgment for Smith in the Northern District of California, which held an email could satisfy the notice requirement.', cites: [[1, 'The district court held that it can, and entered judgment for Smith.']] },
    'Key facts': { value: 'A 2019 license required "written notice" and a 30-day cure before termination for breach, without specifying a delivery method. Smith’s general counsel emailed the designated contact on June 3, 2021, identifying unpaid invoices; Jones Holdings did not pay, and Smith terminated on July 6, 2021.', cites: [[3, 'The agreement designated a contact person and an email address for each party but did not specify any method of delivering notices.'], [3, "On June 3, 2021, Smith's general counsel emailed Jones Holdings' designated contact"]] },
    Issue: { value: 'Whether an email to a party’s designated contact satisfies a contractual "written notice" requirement where the contract prescribes no delivery method.', cites: [[8, 'The sole question on appeal is whether an email sent to a party\'s designated contact satisfies a contractual requirement of "written notice" where the contract does not prescribe a method of delivery.']] },
    Holding: { value: 'Yes. Absent contract language requiring a specific delivery method, an email identifying the breach with reasonable particularity and sent to the designated contact is written notice.', cites: [[12, 'We hold that, absent language in the contract requiring a specific method of delivery, an email that identifies the breach with reasonable particularity and is sent to the contractually designated contact constitutes written notice.']] },
    Reasoning: { value: 'Notice-and-cure provisions exist to inform the breaching party and give it a chance to cure, which the email did. The parties required certified mail elsewhere in the same agreement (§18), so its absence in §12 was deliberate. No prejudice: receipt was acknowledged the next day.', cites: [[12, 'The purpose of a notice-and-cure provision is to inform the breaching party of the default and give it a fair opportunity to remedy it.'], [14, 'Section 18 requires that any notice of an intellectual-property claim be sent "by certified mail, return receipt requested."'], [14, 'Its designated contact acknowledged receipt of the June 3 email the following day']] },
    Disposition: { value: 'Affirmed.', cites: [[26, 'The judgment of the district court is AFFIRMED.']] },
    'Concurrences and dissents': { value: 'Judge Alvarez dissented, arguing "written notice" without more requires a signed writing delivered by a physical method.', cites: [[27, 'I would hold that "written notice," without more, requires a signed writing delivered by a recognized physical method.']] },
  },
  [DOC_IDS.bayview]: {
    Court: { value: 'United States District Court for the Southern District of New York.', cites: [[1, 'UNITED STATES DISTRICT COURT\nSOUTHERN DISTRICT OF NEW YORK']] },
    Parties: { value: 'Bayview Freight Lines, Inc. (plaintiff) v. Delmar Shipping Co. (defendant).', cites: [[1, 'BAYVIEW FREIGHT LINES, INC., Plaintiff']] },
    'Procedural posture': { value: 'Bayview’s motion for partial summary judgment on the enforceability of the liability cap, after discovery.', cites: [[2, 'Following discovery, Bayview moved for partial summary judgment on the enforceability of Section 9 of the carriage agreement']] },
    'Key facts': { value: 'Refrigerated pharmaceuticals spoiled in Delmar’s custody; the crew disabled the container’s refrigeration alarm for eleven hours.', cites: [[2, 'a cargo of refrigerated pharmaceuticals spoiled while in Delmar\'s custody'], [10, "The record shows that Delmar's crew disabled the refrigeration alarm on the affected container for eleven hours."]] },
    Holding: { value: 'The negotiated cap is enforceable but does not protect a party from liability for its own gross negligence.', cites: [[10, 'A limitation-of-liability clause negotiated between sophisticated commercial parties is enforceable according to its terms, but does not shield a party from liability for its own gross negligence.']] },
    Disposition: { value: 'Granted in part (cap does not limit gross-negligence damages) and denied in part (gross negligence is for the jury).', cites: [[30, 'Bayview\'s motion is GRANTED to the extent it seeks a declaration that Section 9 does not limit damages caused by gross negligence']] },
  },
  [DOC_IDS.reyes]: {
    Court: { value: 'Superior Court of California, County of Los Angeles.', cites: [[1, 'SUPERIOR COURT OF THE STATE OF CALIFORNIA\nFOR THE COUNTY OF LOS ANGELES']] },
    Parties: { value: 'Maria Reyes (plaintiff) v. Coastal Logistics, Inc. and Does 1–20 (defendants).', cites: [[1, 'MARIA REYES, an individual, Plaintiff']] },
    'Causes of action': { value: '(1) Wrongful termination in violation of public policy; (2) retaliation under Labor Code §1102.5.', cites: [[1, '1. Wrongful termination in violation of public policy;\n2. Retaliation in violation of Labor Code section 1102.5;']] },
    'Relief sought': { value: 'Compensatory damages (lost wages and benefits), emotional-distress damages, punitive damages, civil penalties under §1102.5(f), attorneys’ fees and costs.', cites: [[21, 'For compensatory damages, including lost wages and benefits, in an amount to be proven at trial;'], [21, 'For punitive damages;'], [21, "For reasonable attorneys' fees and costs;"]] },
    'Key factual allegations': { value: 'Reyes reported falsified hours-of-service logs in writing (Jan 6, 2025) and to HR (Jan 21, 2025); she was terminated for "restructuring" less than four weeks later, the only dispatch supervisor let go.', cites: [[4, 'On January 6, 2025, Plaintiff reported to Defendant\'s regional operations manager, in writing'], [4, 'Less than four weeks later, Defendant terminated Plaintiff\'s employment, citing "restructuring."']] },
    'Legal theories asserted': { value: 'Termination motivated by reports of regulatory violations tied to fundamental public policy; retaliation for protected disclosures to a person with authority.', cites: [[9, "Plaintiff's reports were a substantial motivating reason for Defendant's decision to terminate her employment."], [11, 'Plaintiff disclosed information she had reasonable cause to believe disclosed a violation of a state or federal statute or regulation']] },
    'Dates appearing in the document': { value: 'Employment from April 2019; reports on January 6 and January 21, 2025; termination on February 14, 2025.', cites: [[4, 'Plaintiff was employed by Defendant as a dispatch supervisor from April 2019 until her termination on February 14, 2025.']] },
  },
};

function planSummary(target: LegalDocument, scopeUsed: ScopeUsed, docMap: Map<string, LegalDocument>): Omit<ResponsePlan, 'usage' | 'stages'> {
  const book = new CitationBook(docMap);
  const data = SUMMARY_DATA[target.id] ?? {};
  const sections: SummarySection[] = TEMPLATES[target.type].map((s) => ({
    title: s.title,
    fields: s.fields.map((label) => {
      const f = data[label];
      if (!f) return { label, value: null, citations: [] }; // FR-16: never filled by inference
      return { label, value: f.value, citations: f.cites.map(([p, q, sec]) => book.n(target.id, p, q, sec)), flag: f.flag };
    }),
  }));

  const pagesTotal = target.pages ?? 0;
  const skipped = target.lowOcrPages;
  const summary: SummaryResult = {
    documentId: target.id,
    documentName: target.name,
    docType: target.type,
    sections,
    coverage: {
      pagesTotal,
      pagesCovered: pagesTotal - skipped.length,
      skippedPages: skipped,
      note: skipped.length
        ? `Page${skipped.length > 1 ? 's' : ''} ${skipped.join(', ')} had low OCR confidence and ${skipped.length > 1 ? 'were' : 'was'} read with reduced reliability.`
        : undefined,
    },
  };

  const filled = sections.flatMap((s) => s.fields).filter((f) => f.value).length;
  const total = sections.flatMap((s) => s.fields).length;
  const answerMd = `Structured ${target.type === 'other' ? '' : target.type + ' '}summary of **${displayName(target.name)}**. ${filled} of ${total} template fields are addressed in the document; the rest are marked as not addressed rather than inferred.`;
  return { intent: 'summary', scopeUsed, answerMd, citations: book.citations, excerpts: book.excerpts, summary };
}

// ---------- Draft ----------

function planDraft(req: SendMessageRequest, docs: LegalDocument[], scopeUsed: ScopeUsed, docMap: Map<string, LegalDocument>): Omit<ResponsePlan, 'usage' | 'stages'> {
  const params = req.draftParams ?? {
    draftType: 'memo' as const,
    questionPresented: req.text,
    audience: 'Supervising partner',
    position: '',
    tone: 'neutral' as const,
    sourceDocumentIds: scopeUsed.documentIds,
  };
  const sources = docs.filter((d) => params.sourceDocumentIds.includes(d.id) && d.status === 'ready');
  const draftScope: ScopeUsed = {
    kind: 'documents',
    documentIds: sources.map((d) => d.id),
    label: sources.length === 1 ? displayName(sources[0].name) : `${sources.length} source documents`,
  };

  if (sources.length === 0) {
    return {
      intent: 'draft', scopeUsed: draftScope, answerMd: '', citations: [], excerpts: [],
      refusal: { reason: 'A draft needs at least one ready source document. Without sources it cannot be grounded, so nothing was written.', scopeLabel: 'No sources selected', suggestions: ['Open the draft settings and choose one or more source documents.'] },
    };
  }

  const book = new CitationBook(docMap);
  const meta: DraftMeta = {
    draftType: params.draftType,
    title: '',
    params,
    sources: sources.map((d) => ({ documentId: d.id, documentName: d.name })),
  };

  if (params.draftType === 'brief') {
    const opinion = sources.find((d) => d.type === 'opinion');
    if (!opinion) {
      return {
        intent: 'draft', scopeUsed: draftScope, answerMd: '', citations: [], excerpts: [],
        refusal: { reason: 'A case brief is written from a judicial opinion, and none of the selected sources is classified as an opinion.', scopeLabel: draftScope.label, suggestions: ['Add an opinion to the sources, or switch the draft type to a legal memo.', 'If a document is misclassified, change its type in the Library.'] },
      };
    }
    const d = SUMMARY_DATA[opinion.id] ?? {};
    const part = (label: string) => {
      const f = d[label];
      if (!f) return '_Not addressed in the opinion._';
      return `${f.value} ${f.cites.map(([p, q, s]) => book.cite(opinion.id, p, q, s)).join('')}`;
    };
    meta.title = `Case brief — ${displayName(opinion.name)}`;
    const md = [
      `# ${meta.title}`,
      '',
      '## Procedural posture', part('Procedural posture'),
      '', '## Facts', part('Key facts'),
      '', '## Issue', part('Issue'),
      '', '## Holding', part('Holding'),
      '', '## Reasoning', part('Reasoning'),
      '', '## Disposition', part('Disposition'),
      ...(d['Concurrences and dissents'] ? ['', '## Separate opinions', part('Concurrences and dissents')] : []),
    ].join('\n');
    return { intent: 'draft', scopeUsed: draftScope, answerMd: md, citations: book.citations, excerpts: book.excerpts, draft: meta };
  }

  // Memo: Question Presented → Short Answer → Statement of Facts → Discussion → Conclusion (FR-18)
  const ids = new Set(sources.map((s) => s.id));
  const query = `${params.questionPresented} ${params.position}`;
  const topics = TOPICS.filter((t) => t.pattern.test(query) && t.points.some((p) => ids.has(p.doc)));
  const points = topics.flatMap((t) => t.points.filter((p) => ids.has(p.doc))).slice(0, 7);

  meta.title = `Memorandum — ${params.questionPresented.replace(/\?$/, '').slice(0, 80)}`;
  const factLines = sources
    .map((s) => {
      const f = SUMMARY_DATA[s.id]?.['Parties and roles'] ?? SUMMARY_DATA[s.id]?.['Key facts'] ?? SUMMARY_DATA[s.id]?.['Parties'];
      if (!f) return null;
      const [p, q, sec] = f.cites[0];
      return `*${displayName(s.name)}*: ${f.value} ${book.cite(s.id, p, q, sec)}`;
    })
    .filter(Boolean) as string[];

  const discussion = points.length
    ? points.map((p) => `${p.says} ${book.cite(p.doc, p.page, p.quote, p.section)}`).join(' ')
    : '_The selected sources do not contain provisions that bear directly on the question presented. A discussion cannot be grounded in them; add the relevant documents and regenerate._';

  const positionLine = params.position.trim()
    ? `Consistent with the position that ${params.position.trim().replace(/\.$/, '')}, the strongest support in the sources is set out below; points that cut the other way are noted rather than omitted.`
    : '';

  const md = [
    `# ${meta.title}`,
    '',
    `**To:** ${params.audience || 'File'}  `,
    `**Re:** ${params.questionPresented}`,
    '',
    '## Question Presented',
    params.questionPresented,
    '',
    '## Short Answer',
    points.length
      ? `${points[0].says} ${book.cite(points[0].doc, points[0].page, points[0].quote, points[0].section)} The analysis below is limited to the ${sources.length} source document${sources.length > 1 ? 's' : ''} selected for this draft.`
      : 'The selected sources do not answer this question.',
    '',
    '## Statement of Facts',
    ...(factLines.length ? factLines.map((l) => `- ${l}`) : ['_No factual background could be grounded in the selected sources._']),
    '',
    '## Discussion',
    ...(positionLine ? [positionLine, ''] : []),
    discussion,
    '',
    '## Conclusion',
    points.length
      ? 'On the sources provided, the provisions cited above control the question presented. Any authority not among the selected sources has not been considered and must be researched and verified separately.'
      : 'No conclusion can be drawn from the selected sources.',
  ].join('\n');

  return { intent: 'draft', scopeUsed: draftScope, answerMd: md, citations: book.citations, excerpts: book.excerpts, draft: meta };
}

// ---------- entry point ----------

export function planResponse(req: SendMessageRequest, docs: LegalDocument[]): ResponsePlan {
  const docMap = new Map(docs.map((d) => [d.id, d]));
  const { inScope, scopeUsed } = resolveScope(req, docs);
  const intent: Intent = req.mode === 'auto' ? detectIntent(req.text) : req.mode;

  let core: Omit<ResponsePlan, 'usage' | 'stages'>;
  let stages: string[];

  if (inScope.length === 0 && intent !== 'draft') {
    core = {
      intent, scopeUsed, answerMd: '', citations: [], excerpts: [],
      refusal: { reason: 'There are no ready documents in this scope to search.', scopeLabel: scopeUsed.label, suggestions: ['Upload documents in the Library, or wait for processing to finish.'] },
    };
    stages = ['Checking scope…'];
  } else if (intent === 'summary') {
    const named = inScope.find((d) => req.text.toLowerCase().includes(displayName(d.name).split(/[\s–-]/)[0].toLowerCase()));
    const target = docMap.get(req.summaryDocumentId ?? '') ?? (inScope.length === 1 ? inScope[0] : named) ?? inScope[0];
    core = planSummary(target, { kind: 'documents', documentIds: [target.id], label: displayName(target.name) }, docMap);
    stages = [`Identifying document type (${target.type})…`, 'Retrieving passages for each template field…', `Reading ${target.pages ?? 0} pages…`, 'Composing summary…'];
  } else if (intent === 'draft') {
    core = planDraft(req, docs, scopeUsed, docMap);
    stages = ['Planning outline…', 'Retrieving sources for each section…', 'Writing sections…', 'Verifying citations…'];
  } else {
    core = planAsk(req.text, inScope, scopeUsed, docMap);
    stages = ['Understanding your question…', `Searching ${inScope.length} document${inScope.length === 1 ? '' : 's'}…`, 'Reading the most relevant passages…'];
  }

  return { ...core, stages, usage: usageFor(core.answerMd, core.citations.length) };
}

/** Short title for a new conversation, derived from its first message. */
export function titleFrom(text: string, intent: Intent, docName?: string): string {
  if (intent === 'summary' && docName) return `Summary: ${displayName(docName)}`;
  const t = text.replace(/\s+/g, ' ').trim().replace(/[?.!]+$/, '');
  return t.length > 48 ? `${t.slice(0, 46).trimEnd()}…` : t || 'New conversation';
}
