"""Stub orchestrator: deterministic, offline, and grounded.

It stands in for the LangChain + RAG layer so the product works end to end before any LLM exists.
Answers are *extractive* — verbatim sentences from the attorney's documents, each cited — so every
citation resolves exactly, which is the same guarantee the real verification gate will give.
Usage reports zero cost because no model is called.
"""

import asyncio
import re
import time
from collections.abc import AsyncGenerator, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.orchestrator.interface import DocRef, HistoryTurn, TurnContext
from app.orchestrator.stub.retrieval import CitationBook, find_first, load_pages, retrieve
from app.orchestrator.stub.templates import BRIEF_SECTIONS, FACT_FIELD, find_field, template
from app.orchestrator.stub.text import display_name, is_meta_question, one_line
from app.schemas.common import Intent
from app.schemas.models import (
    ApiError,
    Coverage,
    DraftMeta,
    DraftParams,
    DraftSource,
    Refusal,
    RetrievalCandidate,
    SummaryField,
    SummaryResult,
    SummarySection,
    TraceRetrieval,
    Usage,
)
from app.schemas.stream import DoneData, StageData, StreamEvent, TokenData
from app.services.spans import make_span_id

MODEL_VERSION = "stub-extractive-0.1"

_SUMMARY = re.compile(r"\b(summari[sz]e|summary|overview|key terms|brief me on)\b", re.IGNORECASE)
_DRAFT = re.compile(
    r"\b(draft|write (a|me a) (memo|brief)|prepare a (memo|brief)|memo|case brief)\b", re.IGNORECASE
)
_TOKEN = re.compile(r"\S+\s*|\s+")
_MARKER = re.compile(r"\[(\d+)\]")

LLM_UNAVAILABLE = (
    "The AI model provider did not respond. Your documents were searched and the matching excerpts "
    "are shown, but no answer was written."
)
TIMEOUT = "The answer took too long to generate and was stopped. This is usually temporary."


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


class StubOrchestrator:
    model_version = MODEL_VERSION

    def __init__(self, sessions: async_sessionmaker[AsyncSession], token_delay_ms: Callable[[], int]) -> None:
        self._sessions = sessions
        self._token_delay_ms = token_delay_ms

    # ---------- routing ----------

    async def route(self, text: str, history: list[HistoryTurn]) -> Intent:
        if _SUMMARY.search(text):
            return "summary"
        if _DRAFT.search(text):
            return "draft"
        return "ask"

    # ---------- Ask ----------

    async def answer(self, ctx: TurnContext) -> AsyncGenerator[StreamEvent]:
        t0 = time.perf_counter()
        yield self._stage(ctx, "Understanding your question…")
        if is_meta_question(ctx.text):
            # A question about Legal Lens itself, not the documents: explain what it does instead of
            # refusing. No factual claim about the documents is made, so nothing needs citing.
            md = self._help_text(ctx)
            async for ev in self._stream(ctx, md, CitationBook()):
                yield ev
            async for ev in self._finish(ctx, md, 0, t0):
                yield ev
            return
        if not ctx.documents:
            yield self._no_documents(ctx)
            async for ev in self._finish(ctx, "", 0, t0):
                yield ev
            return
        yield self._stage(ctx, f"Searching {_plural(len(ctx.documents), 'document')}…")

        async with self._sessions() as db:
            ctx.trace.begin("retrieval")
            terms, hits = await retrieve(db, ctx.text, ctx.documents)
            ctx.trace.retrieval = TraceRetrieval(
                query=" ".join(terms),
                candidates=[
                    RetrievalCandidate(
                        span_id=make_span_id(h.doc.id, h.page, h.sentence.start, h.sentence.end),
                        score=round(h.score, 3),
                    )
                    for h in hits
                ],
            )
            ctx.trace.end(f"{len(hits)} passages")
        yield self._stage(ctx, "Reading the most relevant passages…")

        if ctx.scenario == "timeout":
            await asyncio.sleep(1.5)
            yield StreamEvent("error", ApiError(code="timeout", message=TIMEOUT))
            return

        refuse = ctx.scenario == "refusal" or not hits
        book = CitationBook()
        if not refuse:
            top = hits[0].score
            for h in hits:
                book.cite(h.doc, h.page, h.page_text, h.sentence, score=0.42 + 0.53 * (h.score / top))
        for ex in book.excerpts:
            yield StreamEvent("excerpt", ex)

        if ctx.scenario == "llm_unavailable":
            await asyncio.sleep(0.6)
            yield StreamEvent("error", ApiError(code="llm_unavailable", message=LLM_UNAVAILABLE))
            return

        if refuse:
            yield StreamEvent(
                "refusal",
                Refusal(
                    reason="I couldn't find anything in your documents that answers this question, so I won't guess.",
                    scope_label=ctx.scope_used.label,
                    suggestions=[
                        "Widen the scope to the whole workspace."
                        if ctx.scope_used.kind == "documents"
                        else "Upload the document that covers this topic.",
                        "Rephrase the question using the words the document is likely to use.",
                    ],
                ),
            )
            async for ev in self._finish(ctx, "", 0, t0):
                yield ev
            return

        lines = [
            "These passages in your documents bear most directly on the question, quoted verbatim:",
            "",
        ]
        for c in book.citations:
            where = f"{display_name(c.document_name)}, p. {c.page}" + (f" ({c.section})" if c.section else "")
            lines.append(f"- **{where}** — “{one_line(c.quote)}” [{c.n}]")
        lines += [
            "",
            "_Extractive answer: passages were selected by keyword relevance and are quoted, not paraphrased. "
            "Read them in context before relying on them._",
        ]
        md = "\n".join(lines)
        async for ev in self._stream(ctx, md, book):
            yield ev
        if ctx.scenario == "interrupted":
            return
        async for ev in self._finish(ctx, md, len(book.citations), t0):
            yield ev

    # ---------- Summary ----------

    async def summarize(self, ctx: TurnContext) -> AsyncGenerator[StreamEvent]:
        t0 = time.perf_counter()
        target = ctx.summary_document
        if target is None:
            yield self._stage(ctx, "Checking scope…")
            yield self._no_documents(ctx)
            async for ev in self._finish(ctx, "", 0, t0):
                yield ev
            return

        yield self._stage(ctx, f"Identifying document type ({target.type})…")
        yield self._stage(ctx, "Retrieving passages for each template field…")
        async with self._sessions() as db:
            ctx.trace.begin("field extraction")
            pages = await load_pages(db, target.id)
        yield self._stage(ctx, f"Reading {_plural(target.pages, 'page')}…")

        if ctx.scenario == "timeout":
            await asyncio.sleep(1.5)
            yield StreamEvent("error", ApiError(code="timeout", message=TIMEOUT))
            return

        book = CitationBook()
        sections: list[SummarySection] = []
        used: set[tuple[int, int]] = set()
        for fld in template(target.type):
            if not sections or sections[-1].title != fld.section:
                sections.append(SummarySection(title=fld.section, fields=[]))
            found = None if ctx.scenario == "refusal" else find_first(pages, fld.patterns, used)
            if found is None:
                sections[-1].fields.append(SummaryField(label=fld.label, value=None, citations=[]))  # FR-16
                continue
            page_no, text, s = found
            used.add((page_no, s.start))
            n = book.cite(target, page_no, text, s)
            sections[-1].fields.append(SummaryField(label=fld.label, value=one_line(s.text), citations=[n]))
        ctx.trace.end(f"{len(book.citations)} fields supported")

        for ex in book.excerpts:
            yield StreamEvent("excerpt", ex)
        if ctx.scenario == "llm_unavailable":
            yield StreamEvent("error", ApiError(code="llm_unavailable", message=LLM_UNAVAILABLE))
            return

        skipped = list(target.low_ocr_pages)
        note = None
        if skipped:
            pages_word = "Pages" if len(skipped) > 1 else "Page"
            verb = "were" if len(skipped) > 1 else "was"
            note = (
                f"{pages_word} {', '.join(map(str, skipped))} could not be read (no text layer) "
                f"and {verb} not covered."
            )
        summary = SummaryResult(
            document_id=target.id,
            document_name=target.name,
            doc_type=target.type,
            sections=sections,
            coverage=Coverage(
                pages_total=target.pages,
                pages_covered=target.pages - len(skipped),
                skipped_pages=skipped,
                note=note,
            ),
        )
        for c in book.citations:
            yield StreamEvent("citation", c)
        yield StreamEvent("summary", summary)

        all_fields = [f for s in sections for f in s.fields]
        filled = sum(1 for f in all_fields if f.value)
        kind = "" if target.type == "other" else f"{target.type} "
        md = (
            f"Structured {kind}summary of **{display_name(target.name)}**. {filled} of {len(all_fields)} "
            "template fields are addressed in the document; the rest are marked as not addressed rather "
            "than inferred."
        )
        async for ev in self._stream(ctx, md, book, already_sent=True):
            yield ev
        if ctx.scenario == "interrupted":
            return
        async for ev in self._finish(ctx, md, len(book.citations), t0):
            yield ev

    # ---------- Draft ----------

    async def draft(self, ctx: TurnContext) -> AsyncGenerator[StreamEvent]:
        t0 = time.perf_counter()
        params = ctx.draft_params or DraftParams(
            draft_type="memo",
            question_presented=ctx.text,
            audience="Supervising partner",
            source_document_ids=[d.id for d in ctx.documents],
        )
        sources = ctx.documents
        yield self._stage(ctx, "Planning outline…")

        if not sources:
            yield StreamEvent(
                "refusal",
                Refusal(
                    reason="A draft needs at least one ready source document. Without sources it cannot be "
                    "grounded, so nothing was written.",
                    scope_label="No sources selected",
                    suggestions=["Open the draft settings and choose one or more source documents."],
                ),
            )
            async for ev in self._finish(ctx, "", 0, t0):
                yield ev
            return

        if params.draft_type == "brief" and not any(d.type == "opinion" for d in sources):
            yield StreamEvent(
                "refusal",
                Refusal(
                    reason="A case brief is written from a judicial opinion, and none of the selected sources "
                    "is classified as an opinion.",
                    scope_label=ctx.scope_used.label,
                    suggestions=[
                        "Add an opinion to the sources, or switch the draft type to a legal memo.",
                        "If a document is misclassified, change its type in the Library.",
                    ],
                ),
            )
            async for ev in self._finish(ctx, "", 0, t0):
                yield ev
            return

        yield self._stage(ctx, "Retrieving sources for each section…")
        book = CitationBook()
        async with self._sessions() as db:
            ctx.trace.begin("retrieval")
            if params.draft_type == "brief":
                title, md = await self._brief(db, book, next(d for d in sources if d.type == "opinion"))
            else:
                title, md = await self._memo(db, book, params, sources)
            ctx.trace.end(f"{len(book.citations)} passages")
        yield self._stage(ctx, "Writing sections…")

        if ctx.scenario == "timeout":
            await asyncio.sleep(1.5)
            yield StreamEvent("error", ApiError(code="timeout", message=TIMEOUT))
            return
        for ex in book.excerpts:
            yield StreamEvent("excerpt", ex)
        if ctx.scenario == "llm_unavailable":
            yield StreamEvent("error", ApiError(code="llm_unavailable", message=LLM_UNAVAILABLE))
            return
        yield self._stage(ctx, "Verifying citations…")

        meta = DraftMeta(
            draft_type=params.draft_type,
            title=title,
            params=params,
            sources=[DraftSource(document_id=d.id, document_name=d.name) for d in sources],
        )
        yield StreamEvent("draft", meta)
        async for ev in self._stream(ctx, md, book):
            yield ev
        if ctx.scenario == "interrupted":
            return
        async for ev in self._finish(ctx, md, len(book.citations), t0):
            yield ev

    async def _brief(self, db: AsyncSession, book: CitationBook, opinion: DocRef) -> tuple[str, str]:
        pages = await load_pages(db, opinion.id)
        title = f"Case brief — {display_name(opinion.name)}"
        lines = [f"# {title}"]
        used: set[tuple[int, int]] = set()
        for heading, label in BRIEF_SECTIONS:
            fld = find_field("opinion", label)
            found = find_first(pages, fld.patterns, used) if fld else None
            if found is None:
                if heading == "Separate opinions":
                    continue
                lines += ["", f"## {heading}", "_Not addressed in the opinion._"]
                continue
            page_no, text, s = found
            used.add((page_no, s.start))
            n = book.cite(opinion, page_no, text, s)
            lines += ["", f"## {heading}", f"“{one_line(s.text)}” [{n}]"]
        return title, "\n".join(lines)

    async def _memo(
        self, db: AsyncSession, book: CitationBook, params: DraftParams, sources: list[DocRef]
    ) -> tuple[str, str]:
        qp = params.question_presented.strip()
        title = f"Memorandum — {qp.rstrip('?')[:80]}"
        _terms, hits = await retrieve(db, f"{qp} {params.position}", sources, k=6)

        facts: list[str] = []
        for d in sources:
            fld = find_field(d.type, FACT_FIELD.get(d.type, "Parties"))
            found = find_first(await load_pages(db, d.id), fld.patterns) if fld else None
            if found:
                page_no, text, s = found
                n = book.cite(d, page_no, text, s)
                facts.append(f"- *{display_name(d.name)}*: “{one_line(s.text)}” [{n}]")

        cited = [(h, book.cite(h.doc, h.page, h.page_text, h.sentence)) for h in hits]
        discussion = [
            f"{display_name(h.doc.name)} (p. {h.page}) provides: “{one_line(h.sentence.text)}” [{n}]"
            for h, n in cited
        ]
        position = params.position.strip().rstrip(".")
        lines = [
            f"# {title}",
            "",
            f"**To:** {params.audience or 'File'}  ",
            f"**Re:** {qp}",
            "",
            "## Question Presented",
            qp,
            "",
            "## Short Answer",
            (
                f"The sources address this most directly in {display_name(cited[0][0].doc.name)}, "
                f"p. {cited[0][0].page} [{cited[0][1]}]. The analysis below is limited to the "
                f"{_plural(len(sources), 'source document')} selected for this draft."
            )
            if cited
            else "The selected sources do not answer this question.",
            "",
            "## Statement of Facts",
            *(facts or ["_No factual background could be grounded in the selected sources._"]),
            "",
            "## Discussion",
        ]
        if position:
            lines += [
                f"Consistent with the position that {position}, the most relevant passages in the sources are "
                "set out below; passages that cut the other way are included rather than omitted.",
                "",
            ]
        lines += (
            ["\n\n".join(discussion)]
            if discussion
            else [
                "_The selected sources do not contain passages that bear directly on the question presented. "
                "A discussion cannot be grounded in them; add the relevant documents and regenerate._"
            ]
        )
        lines += [
            "",
            "## Conclusion",
            "On the sources provided, the passages cited above bear on the question presented. Any authority "
            "not among the selected sources has not been considered and must be researched and verified "
            "separately."
            if cited
            else "No conclusion can be drawn from the selected sources.",
        ]
        return title, "\n".join(lines)

    # ---------- shared ----------

    @staticmethod
    def _stage(ctx: TurnContext, label: str) -> StreamEvent:
        ctx.trace.begin(label.rstrip("…").lower())
        return StreamEvent("stage", StageData(label=label))

    @staticmethod
    def _help_text(ctx: TurnContext) -> str:
        lines = [
            "I answer questions **only from the documents in your workspace**, and every answer quotes and "
            "cites the passage it comes from. I don't answer general legal questions or use outside knowledge.",
            "",
            "Ask about something these documents actually contain, for example:",
            "",
            "- *What are the termination rights and notice periods?*",
            "- *Who are the parties to the Helix agreement?*",
            "- *What did the court hold in Smith v. Jones?*",
            "",
            "You can also switch the mode to **Summary** for a structured summary of one document, or "
            "**Draft** for a memo or case brief built from the documents you choose.",
        ]
        if ctx.documents:
            lines += ["", f"**Searchable now ({_plural(len(ctx.documents), 'document')}):**", ""]
            lines += [f"- {display_name(d.name)}" for d in ctx.documents[:12]]
            if len(ctx.documents) > 12:
                lines.append(f"- …and {len(ctx.documents) - 12} more")
        else:
            lines += ["", "There are no ready documents yet — upload some in the **Library** first."]
        return "\n".join(lines)

    @staticmethod
    def _no_documents(ctx: TurnContext) -> StreamEvent:
        return StreamEvent(
            "refusal",
            Refusal(
                reason="There are no ready documents in this scope to search.",
                scope_label=ctx.scope_used.label,
                suggestions=["Upload documents in the Library, or wait for processing to finish."],
            ),
        )

    async def _stream(
        self, ctx: TurnContext, md: str, book: CitationBook, already_sent: bool = False
    ) -> AsyncGenerator[StreamEvent]:
        """Streams ``md`` word by word, sending each citation just before its first marker."""
        ctx.trace.begin("generation")
        by_n = {c.n: c for c in book.citations}
        sent: set[int] = set(by_n) if already_sent else set()
        tokens = _TOKEN.findall(md)
        cut = int(len(tokens) * 0.4) if ctx.scenario == "interrupted" else len(tokens)
        delay = self._token_delay_ms() / 1000
        for i, tok in enumerate(tokens):
            if i >= cut:
                return  # no terminal event: the client marks the answer incomplete (NFR-7)
            for m in _MARKER.finditer(tok):
                n = int(m.group(1))
                if n in by_n and n not in sent:
                    sent.add(n)
                    yield StreamEvent("citation", by_n[n])
            yield StreamEvent("token", TokenData(text=tok))
            if delay:
                await asyncio.sleep(delay * (4 if tok.endswith("\n") else 1))
        ctx.trace.end(f"{len(tokens)} tokens")

    async def _finish(
        self, ctx: TurnContext, md: str, sources: int, t0: float
    ) -> AsyncGenerator[StreamEvent]:
        ctx.trace.end()
        context_chars = sum(len(c) for c in [ctx.text, *(t.text for t in ctx.history)])
        yield StreamEvent(
            "usage",
            Usage(
                input_tokens=context_chars // 4 + 400 * sources,
                output_tokens=len(md) // 4,
                cost_usd=0.0,  # no model was called
                latency_ms=int((time.perf_counter() - t0) * 1000),
            ),
        )
        yield StreamEvent(
            "done", DoneData(model_version=self.model_version, prompt_version=f"{ctx.intent}-stub-v1")
        )
