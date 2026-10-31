"""Lexical retrieval for the stub: FTS5 picks candidate pages, then sentences are scored by how
many distinct query terms they contain (weighted by rarity). Deterministic and explainable."""

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentPage
from app.ingestion import search_index
from app.orchestrator.interface import DocRef
from app.orchestrator.stub.templates import TEMPLATES
from app.orchestrator.stub.text import (
    Sentence,
    heading_words,
    name_terms,
    paragraph_around,
    query_terms,
    section_label,
    sentences,
    stem,
    word_stems,
)
from app.schemas.models import Citation, Excerpt
from app.services.spans import make_span_id


@dataclass(slots=True)
class Hit:
    doc: DocRef
    page: int
    page_text: str
    sentence: Sentence
    score: float
    matched: int


async def retrieve(
    db: AsyncSession, query: str, docs: list[DocRef], k: int = 5, per_page: int = 2
) -> tuple[list[str], list[Hit]]:
    """Returns the query terms and up to ``k`` supporting sentences, best first."""
    terms = query_terms(query)
    all_docs = docs
    docs, terms = focus_on_named_documents(docs, terms)
    if not terms or not docs:
        return terms, []
    by_id = {d.id: d for d in docs}
    pages = await search_index.search_pages(db, terms, list(by_id), limit=24)
    term_stems = {t: stem(t) for t in terms}
    concepts = [c for c in CONCEPTS if c.key in term_stems.values()]
    if concepts and len(docs) < len(all_docs):
        # The question names its documents and a legal concept: read those documents in full, since
        # the clause that answers it may not use the question's words ("parties" → "by and between").
        seen = {(p.document_id, p.page_no) for p in pages}
        for d in docs:
            for page_no, text, low in await load_pages(db, d.id):
                if not low and (d.id, page_no) not in seen:
                    pages.append(search_index.PageHit(d.id, page_no, text, 0.0))
    if not pages:
        return terms, []

    candidates: list[tuple[DocRef, int, str, Sentence, set[str], set[str], float]] = []
    df: Counter[str] = Counter()
    for p in pages:
        for s in sentences(p.text):
            present = {t for t, st in term_stems.items() if st in word_stems(s.text)}
            heading = word_stems(heading_words(p.text, s.start))
            in_heading = {t for t, st in term_stems.items() if st in heading}
            concept = max((c.match(s.text) for c in concepts), default=0.0)
            if present or concept:
                candidates.append((by_id[p.document_id], p.page_no, p.text, s, present, in_heading, concept))
                df.update(present)

    n = max(1, len(candidates))
    idf = {t: math.log(1 + n / (1 + df[t])) + 0.2 for t in terms}
    # One- and two-term questions need one matching term; longer ones need at least two, and about
    # 40% of their terms — a single generic word ("policy") is not support (correct refusals, BRD §5).
    need = 1 if len(terms) <= 2 else max(2, round(len(terms) * 0.4))
    page_rank = {(p.document_id, p.page_no): i for i, p in enumerate(pages)}
    pairs = list(zip(terms, terms[1:], strict=False))
    concept_terms = {t for t, st in term_stems.items() for c in concepts if st == c.key}

    hits: list[Hit] = []
    for doc, page, text, s, present, in_heading, concept in candidates:
        # A sentence matching the question's legal concept covers the concept's words too.
        covered = present | in_heading | (concept_terms if concept else set())
        if len(covered) < need:
            continue
        words = {w.lower() for w in _WORDS.findall(s.text)}
        score = sum(idf[t] for t in present)
        score += sum(0.3 * idf[t] for t in present if t in words)  # exact form, not just the stem
        score += sum(0.8 * idf[t] for t in in_heading)  # the clause's own heading names the topic
        score += sum(0.5 for a, b in pairs if _near(s.text, term_stems[a], term_stems[b]))
        score += concept
        score -= 0.02 * min(page_rank[(doc.id, page)], 24)
        hits.append(Hit(doc, page, text, s, score, len(covered)))
    hits.sort(key=lambda h: (-h.score, h.doc.id, h.page, h.sentence.start))

    chosen: list[Hit] = []
    per: Counter[tuple[str, int]] = Counter()
    for h in hits:
        key = (h.doc.id, h.page)
        if per[key] >= per_page:
            continue
        per[key] += 1
        chosen.append(h)
        if len(chosen) >= k:
            break
    return terms, chosen


_WORDS = re.compile(r"[A-Za-z][A-Za-z\-']+")
_LABEL_FILLER = frozenset(
    {"and", "of", "the", "in", "key", "document", "appearing", "dates", "legal", "type", "effect"}
)


@dataclass(frozen=True, slots=True)
class Concept:
    """A legal concept from the summary templates ("Termination rights", "Holding", "Relief sought"),
    keyed by the stem of its first meaningful word, with patterns that find clauses expressing it."""

    key: str
    patterns: tuple[re.Pattern[str], ...]

    def match(self, text: str) -> float:
        for i, pattern in enumerate(self.patterns):
            if pattern.search(text):
                return 3.0 if i == 0 else 2.5
        return 0.0


def _concepts() -> list[Concept]:
    by_key: dict[str, list[re.Pattern[str]]] = {}
    for fields in TEMPLATES.values():
        for f in fields:
            words = [w for w in _WORDS.findall(f.label.lower()) if w not in _LABEL_FILLER]
            if words:
                by_key.setdefault(stem(words[0]), []).extend(
                    p for p in f.patterns if p not in by_key.get(stem(words[0]), [])
                )
    return [Concept(k, tuple(v)) for k, v in by_key.items()]


CONCEPTS = _concepts()


def _near(text: str, a: str, b: str, window: int = 3) -> bool:
    """Do two query words appear within ``window`` words of each other ("limitation of liability")?"""
    stems = [stem(w) for w in _WORDS.findall(text)]
    pos_a = [i for i, s in enumerate(stems) if s == a]
    pos_b = [i for i, s in enumerate(stems) if s == b]
    return any(0 < j - i <= window for i in pos_a for j in pos_b)


def focus_on_named_documents(docs: list[DocRef], terms: list[str]) -> tuple[list[DocRef], list[str]]:
    """A question that names documents ("the Helix agreement", "the Acme MSA", "Smith v. Jones") is
    searched in those documents only, and the naming words are not themselves searched for."""
    names = {d.id: name_terms(d.name) for d in docs}
    named: list[DocRef] = []
    naming_terms: set[str] = set()
    for d in docs:
        distinctive, acronyms = names[d.id]
        hit = {t for t in terms if stem(t) in distinctive or t in acronyms}
        if hit:
            named.append(d)
            naming_terms |= hit
    content = [t for t in terms if t not in naming_terms]
    if not content:  # the question is only a name ("Acme") — search for it as written
        return docs, terms
    return (named or docs), content


async def load_pages(db: AsyncSession, doc_id: str) -> list[tuple[int, str, bool]]:
    rows = await db.execute(
        select(DocumentPage.page_no, DocumentPage.text, DocumentPage.low_ocr)
        .where(DocumentPage.document_id == doc_id)
        .order_by(DocumentPage.page_no)
    )
    return [(r.page_no, r.text, r.low_ocr) for r in rows]


Located = tuple[int, str, Sentence]


def find_first(
    pages: Sequence[tuple[int, str, bool]],
    patterns: Sequence[re.Pattern[str]],
    used: set[tuple[int, int]] | None = None,
) -> Located | None:
    """The first sentence, in document order, matching the highest-priority pattern that matches at
    all. Sentences already used by another field are a fallback, so two fields can share a clause
    when it genuinely answers both. Low-OCR pages are never read."""
    split = [(n, text, sentences(text)) for n, text, low in pages if not low]
    fallback: Located | None = None
    for pattern in patterns:
        for page_no, text, sents in split:
            for s in sents:
                if not pattern.search(s.text):
                    continue
                if used and (page_no, s.start) in used:
                    fallback = fallback or (page_no, text, s)
                    continue
                return page_no, text, s
        if fallback:
            return fallback
    return None


class CitationBook:
    """Numbers citations in order of first use; re-citing the same span reuses its number."""

    def __init__(self) -> None:
        self.citations: list[Citation] = []
        self.excerpts: list[Excerpt] = []

    def cite(self, doc: DocRef, page: int, page_text: str, s: Sentence, score: float | None = None) -> int:
        span_id = make_span_id(doc.id, page, s.start, s.end)
        for c in self.citations:
            if c.span_id == span_id:
                return c.n
        n = len(self.citations) + 1
        section = section_label(page_text, s.start)
        self.citations.append(
            Citation(
                n=n,
                span_id=span_id,
                document_id=doc.id,
                document_name=doc.name,
                page=page,
                char_start=s.start,
                char_end=s.end,
                quote=page_text[s.start : s.end],
                section=section,
            )
        )
        self.excerpts.append(
            Excerpt(
                span_id=span_id,
                document_id=doc.id,
                document_name=doc.name,
                page=page,
                section=section,
                text=paragraph_around(page_text, s.start, s.end),
                score=round(score if score is not None else max(0.42, 0.93 - (n - 1) * 0.07), 2),
            )
        )
        return n
