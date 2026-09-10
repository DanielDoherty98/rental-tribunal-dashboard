"""Regex vocabulary for the parser. Kept separate so it is easy to tune."""
from __future__ import annotations

import re

MONTHS = ("January|February|March|April|May|June|July|August|September|"
          "October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec")
ANY_DATE_RE = re.compile(
    rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MONTHS})\s+\d{{4}}\b"
    rf"|\b(?:{MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}\b"
    rf"|\b\d{{1,2}}[/.\-]\d{{1,2}}[/.\-]\d{{2,4}}\b"
    rf"|\b\d{{4}}-\d{{2}}-\d{{2}}\b", re.I)

CASE_REF_RE = re.compile(
    r"\b([A-Z]{2,4})\s?/\s?([0-9A-Z]{2,6})\s?/\s?([A-Z]{2,4})\s?/\s?(\d{4})\s?/\s?(\d{2,5})\b")
CASE_REF_SLUG_RE = re.compile(
    r"([a-z]{2,4})-slash-([0-9a-z]{2,6})-slash-([a-z]{2,4})-slash-(\d{4})-slash-(\d{2,5})", re.I)

TRIBUNAL_OFFICE = {
    "LON": "London", "MAN": "Manchester (Northern)", "BIR": "Birmingham (Midland)",
    "CAM": "Cambridge (Eastern)", "CHI": "Chichester (Southern)",
    "BRI": "Bristol (Western)", "NEW": "Newcastle (Northern)",
    "LIV": "Liverpool (Northern)", "LEE": "Leeds (Northern)",
    "EAS": "Eastern", "MID": "Midland", "NOR": "Northern",
    "SOU": "Southern", "WAL": "Wales", "WES": "Western",
}
CASE_TYPE = {
    "MNR": "Market rent - section 13 (assured shorthold)",
    "RAC": "Fair rent - Rent Act 1977",
    "FTR": "Fair rent - Rent Act 1977",
    "RAP": "Rent assessment panel",
    "HMK": "Housing Act market rent",
}


def label(*variants: str) -> re.Pattern:
    return re.compile(rf"(?:{'|'.join(variants)})\s*[:\-\u2013]?\s*", re.I)


L_CURRENT_RENT = label(
    r"rent\s+currently\s+payable", r"current\s+rent(?:\s+payable)?", r"existing\s+rent",
    r"rent\s+at\s+the\s+date\s+of\s+(?:the\s+)?(?:notice|application)",
    r"the\s+rent\s+payable\s+(?:immediately\s+)?(?:before|prior\s+to)",
    r"passing\s+rent", r"rent\s+under\s+the\s+(?:existing\s+)?tenancy",
    r"present\s+rent", r"rent\s+previously\s+payable", r"previous\s+rent",
    r"rent\s+payable\s+at\s+present")

L_LANDLORD_PROPOSED = label(
    r"rent\s+proposed\s+by\s+the\s+landlord", r"landlord'?s?\s+proposed\s+rent",
    r"proposed\s+(?:new\s+)?rent\s+(?:in|under|stated\s+in)\s+the\s+(?:section\s*13\s*)?notice",
    r"rent\s+sought(?:\s+by\s+the\s+landlord)?", r"new\s+rent\s+proposed",
    r"rent\s+specified\s+in\s+the\s+notice", r"the\s+landlord\s+(?:has\s+)?propos(?:ed|es)",
    r"landlord\s+seeks", r"rent\s+applied\s+for", r"proposed\s+rent")

L_TENANT_PROPOSED = label(
    r"rent\s+proposed\s+by\s+the\s+tenant", r"tenant'?s?\s+proposed\s+rent",
    r"the\s+tenant\s+(?:has\s+)?propos(?:ed|es)", r"tenant\s+suggested",
    r"tenant\s+contend(?:ed|s)\s+(?:for|that\s+the\s+rent)",
    r"tenant'?s?\s+(?:suggested|counter)\s+(?:figure|rent)")

L_DETERMINED = label(
    r"rent\s+determined\s+by\s+the\s+tribunal",
    r"the\s+tribunal\s+determines?(?:\s+that)?(?:\s+the)?\s*(?:a\s+)?rent",
    r"determined\s+rent", r"rent\s+determined", r"market\s+rent\s+determined",
    r"the\s+rent\s+(?:is|shall\s+be|will\s+be)\s+determined\s+at",
    r"decision\s*[:\-]?\s*rent", r"rent\s+for\s+the\s+(?:above\s+)?property\s+is")

L_EFFECTIVE = label(
    r"effective\s+(?:from|date)", r"date\s+the\s+rent\s+takes?\s+effect",
    r"with\s+effect\s+from", r"rent\s+(?:to\s+)?(?:take|takes)\s+effect\s+(?:from|on)",
    r"starting\s+date", r"date\s+of\s+commencement")

L_APPLICATION_DATE = label(
    r"date\s+of\s+(?:the\s+)?application", r"application\s+(?:date|received|made)(?:\s+on)?",
    r"date\s+of\s+referral", r"date\s+of\s+tenant'?s?\s+(?:application|referral)",
    r"date\s+of\s+objection", r"referral\s+received")
L_NOTICE_DATE = label(
    r"date\s+of\s+(?:the\s+)?(?:section\s*13\s*)?notice",
    r"notice\s+(?:of\s+increase\s+)?(?:dated|served\s+on|date)",
    r"section\s*13\s+notice\s+(?:dated|served)")
L_HEARING_DATE = label(r"date\s+of\s+(?:the\s+)?hearing", r"hearing\s+date",
                       r"heard\s+(?:on|at\s+\S+\s+on)", r"date\s+of\s+inspection")
L_DECISION_DATE = label(r"date\s+of\s+(?:the\s+)?decision", r"decision\s+date",
                        r"date\s+of\s+determination", r"dated\s+this",
                        r"date\s+of\s+issue", r"signed\s+and\s+dated")

L_LANDLORD = label(r"landlord'?s?(?:\s*/\s*representative)?", r"applicant\s*\(landlord\)",
                   r"the\s+landlord\s+is", r"landlord\s+name", r"respondent\s+landlord")
L_LANDLORD_REP = label(r"landlord'?s?\s+representative", r"represented\s+by",
                       r"appearing\s+for\s+the\s+landlord",
                       r"agent\s+for\s+the\s+landlord", r"managing\s+agent")
L_TENANT = label(r"tenant'?s?(?:\s*/\s*representative)?", r"applicant\s*\(tenant\)",
                 r"the\s+tenant\s+is", r"tenant\s+name")

SECTION_HEADINGS = [
    ("tenant_evidence", r"(?:the\s+)?tenant'?s?\s+(?:case|evidence|submissions?|"
                        r"representations?|reply|response|position|statement|comments?)"
                        r"|evidence\s+(?:of|from|submitted\s+by)\s+the\s+tenant"
                        r"|submissions?\s+(?:of|by|from)\s+the\s+tenant"),
    ("landlord_evidence", r"(?:the\s+)?landlord'?s?\s+(?:case|evidence|submissions?|"
                          r"representations?|reply|response|position|statement|comments?)"
                          r"|evidence\s+(?:of|from|submitted\s+by)\s+the\s+landlord"
                          r"|submissions?\s+(?:of|by|from)\s+the\s+landlord"),
    ("reasoning", r"(?:the\s+)?tribunal'?s?\s+(?:decision\s+and\s+)?reasons?"
                  r"|reasons?\s+for\s+(?:the\s+)?decision"
                  r"|(?:the\s+)?tribunal'?s?\s+(?:consideration|deliberations?|assessment|"
                  r"determination|analysis|findings?|valuation)"
                  r"|^\s*reasons?\s*$|^\s*determination\s*$|^\s*decision\s+and\s+reasons?\s*$"
                  r"|consideration\s+and\s+determination"),
    ("property", r"(?:the\s+)?(?:property|premises|dwelling|subject\s+property)"
                 r"(?:\s+and\s+its\s+condition)?|description\s+of\s+the\s+(?:property|premises)"
                 r"|inspection"),
    ("law", r"(?:the\s+)?law|legal\s+(?:framework|background)|statutory\s+provisions"),
]
SECTION_RE = [(k, re.compile(rf"^\s*(?:\d+[.)]\s*)?(?:{p})\s*[:\.]?\s*$", re.I | re.M))
              for k, p in SECTION_HEADINGS]

INLINE_ANCHORS = {
    "tenant_evidence": re.compile(
        r"(the\s+tenant(?:s)?'?s?\s+(?:said|stated|submitted|argued|contended|asserted|"
        r"provided|supplied|produced|relied|referred|maintained|told\s+the\s+tribunal)[^\n]{0,600})", re.I),
    "landlord_evidence": re.compile(
        r"(the\s+landlord(?:s)?'?s?\s+(?:said|stated|submitted|argued|contended|asserted|"
        r"provided|supplied|produced|relied|referred|maintained|told\s+the\s+tribunal)[^\n]{0,600})", re.I),
    "reasoning": re.compile(
        r"((?:the\s+tribunal|the\s+panel|we)\s+(?:considered|concluded|determined|found|"
        r"decided|assessed|had\s+regard|took\s+into\s+account)[^\n]{0,800})", re.I),
}

COMPARABLE_RE = re.compile(
    r"\bcomparable(?:s)?\b|\bcomparator(?:s)?\b|\bevidence\s+of\s+similar\s+propert", re.I)
NO_COMPARABLE_RE = re.compile(
    r"\bno\s+(?:comparable|comparator)[s]?\b"
    r"|\b(?:did\s+not|had\s+not|does\s+not|failed\s+to)\s+(?:provide|submit|supply|produce|"
    r"adduce|put\s+forward)\s+(?:any\s+)?(?:comparable|comparator|evidence)"
    r"|\bwithout\s+(?:any\s+)?(?:detailed\s+)?(?:supporting\s+)?evidence"
    r"|\bno\s+(?:supporting\s+)?evidence\s+(?:was\s+)?(?:provided|submitted|supplied)"
    r"|\bno\s+(?:written\s+)?(?:representations?|submissions?)\s+(?:were\s+)?(?:received|made)", re.I)

NO_DETERMINATION_RE = re.compile(
    r"\b(?:makes?|made|making)\s+no\s+determination\b"
    r"|\bno\s+determination\s+(?:of|is|was|has)\b"
    r"|\bdoes\s+not\s+determine\b|\bdid\s+not\s+determine\b"
    r"|\bdeclines?\s+to\s+determine\b|\bunable\s+to\s+determine\b"
    r"|\bno\s+jurisdiction\s+to\s+determine\b"
    r"|\bapplication\s+(?:is|was|has\s+been)\s+withdrawn\b"
    r"|\bapplication\s+(?:is|was)\s+struck\s+out\b", re.I)

OUTCOME_PATTERNS = [
    ("Withdrawn", r"\bwithdraw(?:n|al|s|)\b|\bapplication\s+is\s+withdrawn\b"),
    ("Struck out", r"\bstruck\s+out\b|\bstrike\s+out\b|\bstriking\s+out\b"),
    ("Invalid notice", r"\bnotice\s+(?:is|was)\s+invalid\b|\binvalid\s+(?:section\s*13\s*)?notice\b"
                       r"|\bno\s+jurisdiction\b|\bnot\s+a\s+valid\s+notice\b"),
    ("Transferred", r"\btransferred\s+to\b"),
    ("Dismissed", r"\bapplication\s+is\s+dismissed\b|\bdismisse[sd]\b"),
]
OUTCOME_RE = [(k, re.compile(p, re.I)) for k, p in OUTCOME_PATTERNS]

ORG_SUFFIX_RE = re.compile(
    r"\b(?:limited|ltd\.?|llp|plc|p\.l\.c\.|inc\.?|holdings?|properties|property|estates?|"
    r"homes?|housing(?:\s+association|\s+group|\s+trust)?|association|trust|group|"
    r"partnership|management|lettings?|residential|investments?|developments?|"
    r"council|borough|city\s+council|county\s+council|corporation|society|"
    r"co-?operative|charity|company)\b", re.I)

NAME_RE = re.compile(
    r"\b((?:Mr|Mrs|Ms|Miss|Dr|Prof|Sir)\.?\s+(?:[A-Z]\.?\s*)*[A-Z][A-Za-z'\-]+"
    r"(?:\s+[A-Z][A-Za-z'\-]+){0,2})\b")
ORG_NAME_RE = re.compile(
    r"\b((?:[A-Z][A-Za-z&'\-\.]+\s+){0,4}[A-Z][A-Za-z&'\-\.]+\s+"
    r"(?:Limited|Ltd\.?|LLP|PLC|Housing\s+Association|Housing\s+Trust|Housing\s+Group|"
    r"Properties|Property\s+Group|Estates|Homes|Council|Trust|Group|Management))\b")

NOISE_LINE_RE = re.compile(
    r"^(?:page\s+\d+|\d+\s+of\s+\d+|first[- ]tier\s+tribunal|property\s+chamber|"
    r"residential\s+property|hm\s+courts|crown\s+copyright|©.*|<<<PLAIN>>>)$", re.I)
