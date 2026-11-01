import { http, HttpResponse, delay } from 'msw';
import { UPLOAD_LIMITS, type DocType, type LegalDocument } from '@/api/types';
import { classify, db, save, startProcessing, tickDocuments, uid } from '../db';
import { buildPage, parseSpanId } from '../fixtures/pages';
import { scenario } from '../scenario';
import { requireAuth } from './auth';

const notFound = (what: string) =>
  HttpResponse.json({ code: 'unknown', message: `${what} not found.` }, { status: 404 });
const findDoc = (id: string) => db.state.documents.find((d) => d.id === id);

export const documentHandlers = [
  http.get('/api/documents', async () => {
    const denied = requireAuth();
    if (denied) return denied;
    await delay(250);
    tickDocuments();
    return HttpResponse.json({ items: db.state.documents, nextCursor: null });
  }),

  http.get('/api/documents/:id', async ({ params }) => {
    tickDocuments();
    const doc = findDoc(params.id as string);
    return doc ? HttpResponse.json(doc) : notFound('Document');
  }),

  http.get('/api/documents/:id/status', async ({ params }) => {
    tickDocuments();
    const doc = findDoc(params.id as string);
    return doc
      ? HttpResponse.json({ status: doc.status, progress: doc.progress, error: doc.error })
      : notFound('Document');
  }),

  http.get('/api/documents/:id/pages/:n', async ({ params }) => {
    await delay(180);
    const doc = findDoc(params.id as string);
    const n = Number(params.n);
    if (!doc || doc.status !== 'ready' || !doc.pages || n < 1 || n > doc.pages) return notFound('Page');
    return HttpResponse.json(buildPage(doc.id, n, doc.type, doc.lowOcrPages));
  }),

  http.post('/api/documents', async ({ request }) => {
    const denied = requireAuth();
    if (denied) return denied;
    const form = await request.formData();
    const files = form.getAll('files').filter((f): f is File => f instanceof File);
    await delay(400);
    const created: LegalDocument[] = [];
    const rejected: { name: string; reason: string }[] = [];
    for (const file of files) {
      const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
      if (!(UPLOAD_LIMITS.accept as readonly string[]).includes(ext)) {
        rejected.push({ name: file.name, reason: `${ext || 'This file type'} is not supported. Upload PDF, DOCX or TXT.` });
        continue;
      }
      if (file.size > UPLOAD_LIMITS.maxBytes) {
        rejected.push({ name: file.name, reason: `File is ${(file.size / 1048576).toFixed(1)} MB; the limit is 50 MB.` });
        continue;
      }
      const { type, confidence } = classify(file.name);
      const doc: LegalDocument = {
        id: uid('doc'),
        name: file.name,
        mimeType: file.type || 'application/octet-stream',
        sizeBytes: file.size,
        pages: null,
        type,
        typeConfidence: confidence,
        typeOverridden: false,
        status: 'queued',
        progress: 0,
        lowOcrPages: [],
        uploadedAt: new Date().toISOString(),
      };
      db.state.documents.unshift(doc);
      startProcessing(doc, { forceFail: scenario.consumeUploadFailure() });
      created.push(doc);
    }
    save();
    return HttpResponse.json({ created, rejected }, { status: 201 });
  }),

  http.patch('/api/documents/:id', async ({ params, request }) => {
    const doc = findDoc(params.id as string);
    if (!doc) return notFound('Document');
    const body = (await request.json()) as { type?: DocType };
    if (body.type) {
      doc.type = body.type;
      doc.typeOverridden = true;
    }
    save();
    await delay(200);
    return HttpResponse.json(doc);
  }),

  http.delete('/api/documents/:id', async ({ params }) => {
    await delay(350);
    const id = params.id as string;
    db.state.documents = db.state.documents.filter((d) => d.id !== id);
    delete db.state.processing[id];
    save();
    return new HttpResponse(null, { status: 204 });
  }),

  // Workspace-level hard delete (FR-26): documents, derived data and conversations quoting them.
  http.delete('/api/documents', async () => {
    await delay(700);
    db.state.documents = [];
    db.state.processing = {};
    db.state.conversations = [];
    save();
    return new HttpResponse(null, { status: 204 });
  }),

  http.get('/api/spans/:spanId', async ({ params }) => {
    await delay(120);
    const id = decodeURIComponent(params.spanId as string);
    const parsed = parseSpanId(id);
    const doc = parsed && findDoc(parsed.documentId);
    if (!parsed || !doc) return notFound('Source passage');
    const page = buildPage(doc.id, parsed.page, doc.type, doc.lowOcrPages);
    return HttpResponse.json({
      spanId: id,
      documentId: doc.id,
      documentName: doc.name,
      page: parsed.page,
      charStart: parsed.start,
      charEnd: parsed.end,
      text: page.text.slice(parsed.start, parsed.end),
    });
  }),
];
