"""Document-type classifier (FR-5): contract | opinion | pleading | other, with a confidence.

A keyword heuristic over the file name and opening pages. The AI layer can replace it; the
attorney can always override the result in the Library.
"""

import re

_SIGNALS: dict[str, list[tuple[str, float]]] = {
    "contract": [
        (r"\bagreement\b", 2.0),
        (r"\bentered into\b", 2.5),
        (r"\bby and between\b", 2.5),
        (r"\bwhereas\b", 1.5),
        (r"\b(hereto|hereunder|herein)\b", 1.0),
        (r"\bin witness whereof\b", 2.5),
        (r"\b(governing law|indemnif\w+|termination|effective date)\b", 1.0),
        (r"\b(msa|nda|sow|addendum|amendment|lease)\b", 1.5),
    ],
    "opinion": [
        (r"\bcourt of appeals\b", 3.0),
        (r"\b(affirmed|reversed|remanded|vacated)\b", 2.0),
        (r"\bopinion\b", 1.5),
        (r"\bcircuit judge\b", 3.0),
        (r"\bappellant|appellee\b", 2.5),
        (r"\bwe (hold|conclude|affirm|reverse)\b", 2.5),
        (r"\bdissent(ing)?\b", 1.5),
        (r"\b\w+ v\.? \w+", 1.0),
    ],
    "pleading": [
        (r"\bcomplaint\b", 3.0),
        (r"\bplaintiff\b", 1.5),
        (r"\bdefendant\b", 1.0),
        (r"\bcause of action\b", 3.0),
        (r"\bprayer for relief\b", 3.0),
        (r"\bjury (trial )?demand(ed)?\b", 2.0),
        (r"\b(petition|motion to)\b", 1.5),
        (r"\bcase no\.?\b", 1.0),
    ],
}


def classify(name: str, opening_text: str) -> tuple[str, float]:
    haystack = f"{name}\n{opening_text[:12000]}".lower()
    scores = {
        kind: sum(weight for pattern, weight in signals if re.search(pattern, haystack))
        for kind, signals in _SIGNALS.items()
    }
    best = max(scores, key=lambda k: scores[k])
    top = scores[best]
    if top < 3.0:
        return "other", round(min(0.6, 0.35 + top / 10), 2)
    runner_up = max(v for k, v in scores.items() if k != best)
    margin = (top - runner_up) / top
    return best, round(min(0.99, 0.6 + 0.25 * margin + min(top, 12) / 60), 2)
