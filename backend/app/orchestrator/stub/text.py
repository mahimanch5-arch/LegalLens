"""Text utilities for the stub: query terms, sentence spans, section labels."""

import re
from dataclasses import dataclass

_STOPWORDS_TEXT = """
a about above after again against all am an and any are as at be because been before being
below between both but by can could did do does doing down during each few for from further had
has have having he her here hers herself him himself his how i if in into is it its itself just
me more most my myself no nor not now of off on once only or other our ours ourselves out over
own same she should so some such than that the their theirs them themselves then there these
they this those through to too under until up very was we were what when where which while who
whom why will with would you your yours yourself yourselves tell please explain describe give
list find show say says said document documents agreement contract anything something also
whether
seek seeks sought long happen happens happened much many mean means meaning regarding concerning
relating related kind type exactly specifically any there get gets got need needs required
"""
STOPWORDS = frozenset(_STOPWORDS_TEXT.split())

# Words too common in legal documents to identify one ("the Acme agreement" → "acme" counts, "agreement" doesn't).
_GENERIC_NAME_WORDS = frozenset(
    [
        "agreement",
        "contract",
        "inc",
        "llc",
        "ltd",
        "corp",
        "co",
        "company",
        "holdings",
        "services",
        "service",
        "master",
        "no",
        "signed",
        "scan",
        "pdf",
        "docx",
        "txt",
        "amendment",
        "exhibit",
        "v",
        "vs",
        "the",
        "of",
        "and",
        "cir",
        "court",
    ]
)

_WORD = re.compile(r"[A-Za-z][A-Za-z\-']+|\d+")
_SENT_END = re.compile(
    r"(?<=[.!?;])([\"”’)]*)\s+(?=[\"“(]?[A-Z0-9§(])|\n\s*\n|\n(?=\s*(?:\(?[a-z0-9]{1,3}[.)]|[A-Z][A-Z ]{3,}\n))"
)
_NUMBERED = re.compile(r"^\s*(?:Section\s+|§\s*)?(\d{1,3}(?:\.\d{1,3})+|\d{1,3}\.)\s+\S")
_CAPS_HEADING = re.compile(r"^(?:[IVXLC]+\.\s+)?[A-Z][A-Z0-9 ,'&\-]{3,60}$")

MAX_QUOTE = 420
# "11.1 Termination for Convenience." — a clause heading, not a statement worth quoting.
_HEADING_SENTENCE = re.compile(r"(?:Section\s+|§\s*)?\d{1,3}(?:\.\d{1,3})*\.?\s+[A-Z][\w ,'&()\-]{0,60}\.?")
_ABBREV = re.compile(
    r"(?:\b(?:Inc|Co|Corp|Ltd|LLC|L\.P|No|Nos|Sec|Secs|Art|para|v|vs|e\.g|i\.e|U\.S|St|Mr|Ms|Mrs|Dr|Cir|App|Supp|Cal|Fed|Ct|cf|et al|Jr|Sr|Ex)|\b[A-Z])\.$"
)
_SUFFIXES = (
    "ations", "ation", "ating", "ated", "ates", "ate", "ments", "ment", "ings", "ing",
    "ions", "ion", "ities", "ity", "ies", "ied", "als", "al", "ed", "es", "s",
)  # fmt: skip


def stem(word: str) -> str:
    """Crude suffix stripping plus a length cap, so terminate / termination / terminated meet.
    A trailing "e" is dropped after stripping, so invoice / invoices and notice / notices meet too."""
    w = word.lower().strip("'-")
    if w.endswith("'s"):
        w = w[:-2]
    for suffix in _SUFFIXES:
        if len(w) > len(suffix) + 3 and w.endswith(suffix):
            # parties → party, applied → apply: keep the "y" so the singular and plural meet
            w = w[: -len(suffix)] + ("y" if suffix in ("ies", "ied") else "")
            break
    if len(w) > 4 and w.endswith("e"):
        w = w[:-1]
    return w[:7]


def is_meta_question(text: str) -> bool:
    """Greetings and "what can you do?" — questions about Legal Lens, not about the documents."""
    t = re.sub(r"[^a-z ]", " ", text.lower()).split()
    joined = " ".join(t)
    if not t or joined in {"hi", "hello", "hey", "test", "help", "thanks", "thank you", "ok", "okay"}:
        return True
    return bool(
        re.search(r"\b(what|which)( \w+){0,3} (questions|things)\b.*\b(you|i)\b", joined)
        or re.search(
            r"\bwhat (can|do) you (do|answer|help)\b|\bhow (do|can) (i|you) use\b|\bwho are you\b", joined
        )
        or re.fullmatch(r"(test|testing)( \w+)?", joined)
    )


def name_terms(name: str) -> tuple[set[str], set[str]]:
    """(distinctive word stems, acronyms) that identify a document by name.
    'Acme–Northwind Master Services Agreement' → ({acme, northwi}, {msa, nmsa, …})."""
    words = [w.lower() for w in _WORD.findall(display_name(name)) if not w.isdigit()]
    distinctive = {
        stem(w) for w in words if w not in _GENERIC_NAME_WORDS and w not in STOPWORDS and len(w) > 2
    }
    acronyms = {"".join(w[0] for w in words[i : i + n]) for n in (2, 3, 4) for i in range(len(words) - n + 1)}
    return distinctive, {a for a in acronyms if len(a) >= 3}


def is_caps_heading(text: str) -> bool:
    """'UNITED STATES COURT OF APPEALS' — a short all-caps line is a heading, not a quotable statement.
    Long all-caps clauses (e.g. a limitation-of-liability paragraph) are kept."""
    letters = [ch for ch in text if ch.isalpha()]
    return (
        bool(letters) and len(text.split()) <= 10 and sum(ch.isupper() for ch in letters) / len(letters) > 0.9
    )


def query_terms(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for w in _WORD.findall(text):
        lw = w.lower()
        if lw in STOPWORDS or (len(lw) < 3 and not lw.isdigit()):
            continue
        seen.setdefault(lw, None)
    return list(seen)[:16]


def word_stems(text: str) -> set[str]:
    return {stem(w) for w in _WORD.findall(text)}


@dataclass(frozen=True, slots=True)
class Sentence:
    start: int
    end: int
    text: str


def sentences(page_text: str) -> list[Sentence]:
    """Sentence-ish spans with exact offsets into the page text."""
    out: list[Sentence] = []
    pos = 0
    for m in [*_SENT_END.finditer(page_text), None]:
        if (
            m is not None
            and m.group(1) is not None
            and _ABBREV.search(page_text, max(0, m.start() - 12), m.start())
        ):
            continue  # "Holdings, Inc. and", "Smith v. Jones", "Sec. 4" — not a sentence end
        end = m.start() + len(m.group(1) or "") if m else len(page_text)
        raw = page_text[pos:end]
        lead = len(raw) - len(raw.lstrip())
        s, e = pos + lead, pos + len(raw.rstrip())
        if (
            e - s >= 25
            and not _HEADING_SENTENCE.fullmatch(page_text, s, e)
            and not is_caps_heading(page_text[s:e])
        ):
            if e - s > MAX_QUOTE:  # keep quotes readable; cut on a word boundary
                cut = page_text.rfind(" ", s, s + MAX_QUOTE)
                e = cut if cut > s + MAX_QUOTE // 2 else s + MAX_QUOTE
            out.append(Sentence(s, e, page_text[s:e]))
        pos = m.end() if m else len(page_text)
    return out


def paragraph_around(page_text: str, start: int, end: int, limit: int = 900) -> str:
    p0 = page_text.rfind("\n\n", 0, start)
    p0 = 0 if p0 < 0 else p0 + 2
    p1 = page_text.find("\n\n", end)
    p1 = len(page_text) if p1 < 0 else p1
    if p1 - p0 > limit:
        p0 = max(p0, start - limit // 3)
        p1 = min(p1, max(end, p0 + limit))
    return page_text[p0:p1].strip()


def section_label(page_text: str, start: int) -> str | None:
    """'§11.2' when the passage sits in a numbered clause, else the nearest caps heading."""
    p0 = page_text.rfind("\n\n", 0, start)
    para = page_text[(0 if p0 < 0 else p0 + 2) : start + 40]
    m = _NUMBERED.match(para)
    if m:
        return f"§{m.group(1).rstrip('.')}"
    for line in reversed(page_text[:start].split("\n")):
        line = line.strip()
        if line and _CAPS_HEADING.match(line) and not line.endswith("."):
            return line.title() if len(line) > 4 else line
    return None


_LEAD_HEADING = re.compile(r"\s*(?:Section\s+|§\s*)?\d{1,3}(?:\.\d{1,3})*\.?\s+([A-Z][^.\n]{0,80})\.")


def heading_words(page_text: str, start: int) -> str:
    """The words of the heading a passage sits under: its clause's lead-in ("11.1 Termination for
    Convenience.") and the nearest all-caps heading above it ("13. LIMITATION OF LIABILITY")."""
    p0 = page_text.rfind("\n\n", 0, start)
    p0 = 0 if p0 < 0 else p0 + 2
    parts = []
    m = _LEAD_HEADING.match(page_text, p0)
    if m and m.start(1) <= start:
        parts.append(m.group(1))
    for line in reversed(page_text[:p0].split("\n")):
        line = line.strip()
        if line and is_caps_heading(line):
            parts.append(line)
            break
    return " ".join(parts)


def display_name(name: str) -> str:
    return re.sub(r"\.(pdf|docx|txt)$", "", name, flags=re.IGNORECASE)


def one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
