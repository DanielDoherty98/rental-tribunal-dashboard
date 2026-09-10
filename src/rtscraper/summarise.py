"""
Stage 4 - concise, consistently formatted free-text columns.

House style:
    "No comparables; the tenant proposed £914.07pcm with no detailed
     supporting evidence"

Three deterministic parts: <comparables>; <proposed rent>; <evidence>.
"""
from __future__ import annotations

import json
import re

import config
from . import patterns as P
from . import geo

MAXW = config.SUMMARY_MAX_WORDS

EVIDENCE_TERMS = [
    (r"photograph|photo\b|images?\b", "photographs"),
    (r"disrepair|damp|mould|leak|defect|poor\s+condition|dilapidat", "evidence of disrepair"),
    (r"schedule\s+of\s+(?:works|condition|dilapidations)", "a schedule of condition"),
    (r"rightmove|zoopla|onthemarket|spareroom|gumtree", "online listing evidence"),
    (r"letting\s+agent|estate\s+agent|agent'?s?\s+particulars", "letting agent particulars"),
    (r"valuation\s+report|surveyor|survey\s+report|rics", "a professional valuation or survey"),
    (r"tenancy\s+agreement", "the tenancy agreement"),
    (r"rent\s+statement|rent\s+account|payment\s+history", "rent account evidence"),
    (r"improvement|tenant'?s?\s+own\s+works|installed\s+by\s+the\s+tenant", "tenant improvements"),
    (r"epc|energy\s+performance", "EPC evidence"),
    (r"housing\s+benefit|universal\s+credit|lha\b|local\s+housing\s+allowance", "benefit or LHA data"),
    (r"witness\s+statement|statement\s+of\s+truth", "a witness statement"),
    (r"market\s+(?:data|report|analysis)|index|ons\b", "market data"),
    (r"floor\s?plan|square\s+(?:feet|metres)|sq\s?(?:ft|m)", "floor area evidence"),
    (r"inspection|inspected\s+the\s+propert", "the tribunal inspection"),
    (r"service\s+charge|council\s+tax|utilit", "outgoings evidence"),
]
ATTENDANCE_TERMS = [
    (r"did\s+not\s+attend|non[- ]attendance|absent|no\s+appearance", "did not attend"),
    (r"written\s+representations?\s+only|paper\s+determination|without\s+a\s+hearing",
     "written representations only"),
    (r"attended\s+the\s+hearing|gave\s+oral\s+evidence|appeared\s+in\s+person", "gave oral evidence"),
]
REASON_KEYWORDS = [
    (r"comparable|comparator", 3), (r"market\s+rent|open\s+market", 3),
    (r"condition|disrepair|damp|mould|repair", 3),
    (r"deduct|discount|adjust|reduc|uplift|increase", 3),
    (r"tenant'?s?\s+improvement", 3),
    (r"determined|concluded|satisfied\s+that|find\s+that|we\s+consider", 2),
    (r"location|size|amenit|specification|furnish", 2),
    (r"white\s+goods|carpet|central\s+heating|double\s+glazing|garden|parking", 1),
    (r"evidence", 1),
]
ADDRESS_LIKE_RE = re.compile(
    r"\b\d{1,4}[a-zA-Z]?\s+[A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){0,3}\s+"
    r"(?:Road|Rd|Street|St|Avenue|Ave|Close|Court|Ct|Drive|Dr|Lane|Ln|Way|Place|Pl|"
    r"Terrace|Gardens|Grove|Crescent|Park|Row|Walk|Rise|View|Hill|Square|Sq)\b")


def _pounds(x) -> str:
    return f"£{x:,.2f}pcm" if x is not None else ""


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.;!?])\s+(?=[A-Z£0-9])", re.sub(r"\s+", " ", text or ""))
    return [p.strip() for p in parts if len(p.strip()) > 25]


def _cap(text: str, max_words: int = MAXW) -> str:
    w = text.split()
    return text if len(w) <= max_words else " ".join(w[:max_words]).rstrip(" ,;.") + "..."


def _dedupe(items):
    seen, out = set(), []
    for i in items:
        if i.lower() not in seen:
            seen.add(i.lower()); out.append(i)
    return out


def comparables(section: str):
    if not section or len(section) < 40:
        return 0, [], "No comparables"
    if P.NO_COMPARABLE_RE.search(section) and not re.search(
            r"\b(?:\d+|two|three|four|five|six)\s+comparable", section, re.I):
        return 0, [], "No comparables"

    examples = _dedupe([m.group(0).strip() for m in ADDRESS_LIKE_RE.finditer(section)])
    words = {"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10}
    n_word = re.search(r"\b(\d{1,2}|two|three|four|five|six|seven|eight|nine|ten)\s+comparable",
                       section, re.I)
    count = 0
    if n_word:
        tok = n_word.group(1).lower()
        count = words.get(tok, int(tok) if tok.isdigit() else 0)
    if not count:
        count = len(examples)
    if not count and P.COMPARABLE_RE.search(section):
        pcs = _dedupe([m.group(0) for m in geo.POSTCODE_RE.finditer(section)])
        count = len(pcs)
        if not count:
            return 0, [], "Comparables referred to but not itemised"
    if count == 0:
        return 0, [], "No comparables"
    labelled = f"{count} comparable{'s' if count != 1 else ''}"
    if examples:
        labelled += f" ({'; '.join(examples[:3])})"
    return count, examples[:5], labelled


def evidence_descriptor(section: str) -> str:
    if not section or len(section) < 40:
        return "no detailed supporting evidence"
    found = _dedupe([t for rx, t in EVIDENCE_TERMS if re.search(rx, section, re.I)])
    attend = next((t for rx, t in ATTENDANCE_TERMS if re.search(rx, section, re.I)), "")
    if not found:
        base = ("no detailed supporting evidence" if P.NO_COMPARABLE_RE.search(section)
                else "limited supporting evidence")
    else:
        base = ", ".join(found[:3])
    if attend:
        base = f"{base}; {attend}" if found else f"{base} ({attend})"
    return base


def party_evidence_summary(party: str, section: str, proposed_monthly) -> dict:
    n, examples, comp_phrase = comparables(section)
    desc = evidence_descriptor(section)
    mid = (f"the {party} proposed {_pounds(proposed_monthly)}" if proposed_monthly is not None
           else f"the {party} put forward no rent figure")
    return {"summary": _cap(f"{comp_phrase}; {mid} with {desc}", MAXW + 15),
            "comparables_count": n, "comparables_examples": "; ".join(examples),
            "evidence_types": desc}


def reasoning_summary(section: str, determined_monthly, original_monthly, outcome_label: str) -> str:
    if not section or len(section) < 60:
        return (f"No reasoning text captured; tribunal determined {_pounds(determined_monthly)}"
                if determined_monthly is not None
                else f"No reasoning text captured; outcome recorded as {outcome_label.lower()}")
    scored = []
    for s in _sentences(section):
        score = sum(w for rx, w in REASON_KEYWORDS if re.search(rx, s, re.I))
        if "£" in s:
            score += 2
        if len(s.split()) > 60:
            score -= 2
        scored.append((score, s))
    scored.sort(key=lambda t: -t[0])
    picked = [s for sc, s in scored[:3] if sc > 0] or _sentences(section)[:1]
    body = _cap(re.sub(r"^(?:The\s+Tribunal|The\s+Panel|We)\s+", "Tribunal ", " ".join(picked)), MAXW)
    tail = ""
    if determined_monthly is not None and original_monthly:
        delta = determined_monthly - original_monthly
        direction = "increase" if delta > 0 else ("decrease" if delta < 0 else "no change")
        tail = (f" Determined {_pounds(determined_monthly)} "
                f"({direction} of {abs(delta / original_monthly) * 100:.1f}%).")
    elif determined_monthly is not None:
        tail = f" Determined {_pounds(determined_monthly)}."
    return (body + tail).strip()


def ollama(prompt: str) -> str:
    import requests
    try:
        r = requests.post(config.OLLAMA_URL, timeout=120, json={
            "model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.1, "num_predict": 160}})
        return json.loads(r.text).get("response", "").strip()
    except Exception:  # noqa: BLE001
        return ""


def maybe_llm(kind: str, section: str, fallback: str) -> str:
    if config.SUMMARY_ENGINE != "ollama" or not section:
        return fallback
    prompt = (f"Summarise the {kind} from this UK rent tribunal decision in ONE sentence of "
              f"at most {MAXW} words. Use the exact style: 'No comparables; the tenant proposed "
              f"£914.07pcm with no detailed supporting evidence'. State comparables, the proposed "
              f"rent, and the supporting evidence. No preamble."
              f"\n\nTEXT:\n{section[:4000]}\n\nSUMMARY:")
    out = ollama(prompt)
    return _cap(out, MAXW + 15) if len(out) > 25 else fallback
