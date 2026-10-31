"""Summary templates per document type (BRD §9), with the patterns the stub uses to find a
supporting sentence for each field. A field with no matching sentence stays empty (FR-16).

Each field lists its patterns in priority order: the first pattern that matches anywhere in the
document wins, so a specific signal ("we hold") beats a generic one ("held that").
"""

import re
from dataclasses import dataclass

_MONTH = r"(january|february|march|april|may|june|july|august|september|october|november|december)"
_DATE = rf"\b{_MONTH}\s+\d{{1,2}},\s+\d{{4}}\b"
_COURT = r"\b(court of appeals|district court|supreme court|superior court|circuit court|court of)\b"
_PARTIES = r"\b(plaintiffs?|defendants?|appellants?|appellees?|petitioners?|respondents?)\b"


@dataclass(frozen=True, slots=True)
class Field:
    section: str
    label: str
    patterns: tuple[re.Pattern[str], ...]


def _f(section: str, label: str, *patterns: str) -> Field:
    return Field(section, label, tuple(re.compile(p, re.IGNORECASE) for p in patterns))


TEMPLATES: dict[str, list[Field]] = {
    "contract": [
        _f(
            "Parties and dates",
            "Parties and roles",
            r"\bby and between\b",
            r"\bbetween\b.*\b(llc|llp|inc|corporation|ltd|l\.p)\b",
        ),
        _f(
            "Parties and dates",
            "Effective date",
            r"\b(entered into|dated|effective) as of\b",
            r"\beffective date\b",
        ),
        _f(
            "Parties and dates",
            "Initial term",
            r"\binitial term\b",
            r"\bterm of this agreement\b",
            r"\bshall commence\b",
        ),
        _f("Parties and dates", "Renewal", r"\brenews? automatically\b", r"\brenewal term\b", r"\brenew"),
        _f(
            "Obligations",
            "Provider obligations",
            r"\b(provider|vendor|supplier|licensor|contractor|seller) shall\b",
        ),
        _f("Obligations", "Customer obligations", r"\b(customer|client|licensee|subscriber|buyer) shall\b"),
        _f(
            "Payment",
            "Payment terms",
            r"\bpay (each|all|any)?\s*(undisputed )?invoices?\b",
            r"\binvoices?\b.*\bwithin\b.*\bdays\b",
            r"\bpayment terms\b|\bnet \d+\b",
        ),
        _f(
            "Payment",
            "Price changes",
            r"\b(increase|adjust)\w*\s+(its\s+)?(fees|prices|rates)\b",
            r"\b(fees|prices|rates)\b.*\bincrease",
        ),
        _f(
            "Termination",
            "Termination rights",
            r"\bmay terminate\b.*\bfor convenience\b",
            r"\bmay terminate\b",
        ),
        _f(
            "Termination",
            "Notice periods",
            r"\bdays['’]?\s+(prior\s+)?(written\s+)?notice\b",
            r"\bnotice of non-renewal\b",
        ),
        _f(
            "Termination",
            "Effect of termination",
            r"\b(upon|on|following|after) (any )?(termination|expiration)\b",
        ),
        _f(
            "Risk allocation",
            "Limitation of liability",
            r"\bin no event\b",
            r"\baggregate liability\b|\bshall not exceed\b",
        ),
        _f(
            "Risk allocation",
            "Indemnification",
            r"\bshall (defend,?\s+)?indemnify\b",
            r"\bshall defend\b.*\bclaims?\b",
            r"\bindemnify\b",
        ),
        _f(
            "Assignment and change of control",
            "Assignment",
            r"\b(may not|shall not|neither party may) assign\b",
            r"\bassign (or transfer )?this agreement\b",
        ),
        _f(
            "Assignment and change of control",
            "Change of control",
            r"\bchange of control\b",
            r"\bmerger\b|\bacquisition of\b",
        ),
        _f(
            "Governing law and disputes",
            "Governing law",
            r"\bgoverned by (and construed in accordance with )?the laws?\b",
            r"\bgoverning law\b",
        ),
        _f(
            "Governing law and disputes",
            "Dispute resolution",
            r"\barbitrat",
            r"\b(exclusive jurisdiction|exclusively in the)\b",
            r"\bvenue\b",
        ),
    ],
    "opinion": [
        _f("Case", "Court", _COURT),
        _f("Case", "Parties", _PARTIES),
        _f(
            "Case",
            "Procedural posture",
            r"\bappeal(s|ed)? from\b",
            r"\bsummary judgment\b|\bmotion to dismiss\b|\b(granted|denied) the motion\b",
        ),
        _f("Facts", "Key facts", rf"\b(in|on) {_MONTH}\b", r"\bentered into\b|\bwas employed\b"),
        _f("Issues presented", "Issue", r"\b(issue|question)\b.*\bwhether\b", r"\bwhether\b"),
        _f("Holding", "Holding", r"\bwe (hold|conclude)\b", r"\bwe agree\b", r"\bheld that\b"),
        _f("Reasoning", "Reasoning", r"\bbecause\b", r"\bthe (plain )?(language|text)\b"),
        _f(
            "Disposition",
            "Disposition",
            r"\b(is|are) (affirmed|reversed|remanded|vacated)\b",
            r"\bwe (affirm|reverse|vacate)\b",
        ),
        _f("Disposition", "Concurrences and dissents", r"\bdissent", r"\bconcurr"),
    ],
    "pleading": [
        _f("Case", "Court", _COURT),
        _f("Case", "Parties", _PARTIES),
        _f("Case", "Causes of action", r"\bcause of action\b", r"\bcount (one|two|three|i|ii|iii|\d)\b"),
        _f(
            "Relief sought",
            "Relief sought",
            r"\bprays?\b|\bprayer\b|\bdemands? judgment\b",
            r"\bdamages\b|\binjunct",
        ),
        _f(
            "Key factual allegations",
            "Key factual allegations",
            r"\bwas employed\b|\bon or about\b",
            r"\balleges?\b",
        ),
        _f(
            "Legal theories",
            "Legal theories asserted",
            r"\bin violation of\b|\bbreach of\b",
            r"\bretaliat|\bnegligen|\bwrongful",
        ),
        _f("Dates and deadlines", "Dates appearing in the document", _DATE, r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
    ],
    "other": [
        _f(
            "Overview",
            "Document type",
            r"\b(agreement|memorandum|minutes|letter|report|notice|policy|order)\b",
        ),
        _f("Overview", "Parties", r"\b(between|among|from|to)\b.*\b(llc|inc|corporation|ltd|company|esq)\b"),
        _f("Overview", "Key dates", _DATE),
    ],
}

# Case-brief sections drawn from the opinion template, in conventional order (FR-18).
BRIEF_SECTIONS = [
    ("Procedural posture", "Procedural posture"),
    ("Facts", "Key facts"),
    ("Issue", "Issue"),
    ("Holding", "Holding"),
    ("Reasoning", "Reasoning"),
    ("Disposition", "Disposition"),
    ("Separate opinions", "Concurrences and dissents"),
]

# The field used for a source's background in a memo's Statement of Facts.
FACT_FIELD = {
    "contract": "Parties and roles",
    "opinion": "Key facts",
    "pleading": "Key factual allegations",
    "other": "Parties",
}


def template(doc_type: str) -> list[Field]:
    return TEMPLATES.get(doc_type, TEMPLATES["other"])


def find_field(doc_type: str, label: str) -> Field | None:
    return next((f for f in template(doc_type) if f.label == label), None)
