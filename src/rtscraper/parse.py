"""
Stage 3 - turn decision text into a clean, correctly-aligned record.

Every money figure is captured together with the LABEL that produced it and the
PERIOD stated beside it. Nothing is positionally guessed.

V5.2 adds:
  * money.py           - fixed number pattern (see the bug note in that file)
  * boxes.py           - reads the numbered boxes on pre-RRA forms
  * sanity_check()     - flags determined rents that are implausible relative to
                         the original and sought figures, so a bad parse is
                         visible in the workbook instead of silently wrong.
"""
from __future__ import annotations

import datetime as _dt
import re

from dateutil import parser as dparser

import config
from . import patterns as P
from . import geo
from . import money as M
from . import periods as PD
from . import boxes as BX

NEG_LOOKBACK = 200

to_monthly = PD.to_monthly
detect_period = PD.detect
as_stated = PD.as_stated


# ================================================================== helpers
def money_near(text: str, label_rx: re.Pattern, window: int = 240,
               guard: re.Pattern | None = None):
    """Money figures following a label -> [(value, period, context), ...]."""
    out = []
    for m in label_rx.finditer(text or ""):
        chunk = text[m.end(): m.end() + window]
        if guard is not None:
            pre = text[max(0, m.start() - NEG_LOOKBACK): m.start()]
            if guard.search(pre) or guard.search(chunk):
                continue
        hits = M.find_all(chunk, loose=False)
        if not hits:
            continue
        value, s, e = hits[0]
        period = PD.detect(chunk[max(0, s - 40): e + 70]) \
            or PD.detect(text[max(0, m.start() - 150): m.end() + window])
        if not M.plausible(value, period):
            continue
        out.append((value, period or "", chunk[:200].strip()))
    return out


def first_money(text: str, label_rx: re.Pattern, **kw):
    hits = money_near(text, label_rx, **kw)
    return hits[0] if hits else (None, "", "")


def parse_date(fragment: str):
    m = P.ANY_DATE_RE.search(fragment or "")
    if not m:
        return None
    for dayfirst in (True, False):
        try:
            d = dparser.parse(m.group(0), dayfirst=dayfirst, fuzzy=False).date()
            if 1970 <= d.year <= _dt.date.today().year + 1:
                return d
        except (ValueError, OverflowError, dparser.ParserError):
            continue
    return None


def date_near(text: str, label_rx: re.Pattern, window: int = 160):
    for m in label_rx.finditer(text or ""):
        chunk = text[m.end(): m.end() + window]
        d = parse_date(chunk)
        if d:
            return d, chunk[:120].strip()
    return None, ""


def iso(d):
    return d.isoformat() if isinstance(d, _dt.date) else ""


# ================================================================== sections
def split_sections(text: str) -> dict[str, str]:
    marks = []
    for key, rx in P.SECTION_RE:
        for m in rx.finditer(text):
            marks.append((m.start(), m.end(), key))
    marks.sort()

    candidates: dict[str, list[tuple[int, str]]] = {}
    for i, (s, e, key) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        body = text[e:end].strip()
        if body:
            candidates.setdefault(key, []).append((s, body))

    sections: dict[str, str] = {}
    for key, items in candidates.items():
        if key == "reasoning":
            real = [b for _, b in items if len(b) >= 120]
            sections[key] = real[-1] if real else max((b for _, b in items),
                                                      key=len, default="")
        else:
            sections[key] = max((b for _, b in items), key=len, default="")

    for key, rx in P.INLINE_ANCHORS.items():
        if len(sections.get(key, "")) < 80:
            found = " ".join(m.group(1) for m in rx.finditer(text))
            if len(found) > len(sections.get(key, "")):
                sections[key] = found.strip()
    return sections


# ================================================================== parties
def clean_party(raw: str) -> str:
    if not raw:
        return ""
    s = raw.split("\n")[0]
    s = re.split(r"\s{3,}|(?:\s[-\u2013]\s)", s)[0]
    s = re.sub(r"^(?:and|the)\s+", "", s.strip(), flags=re.I)
    s = re.split(r",?\s*(?:\d+\s+[A-Z][a-z]|c/o\b|of\s+\d)", s)[0]
    s = re.sub(r"\((?:the\s+)?(?:landlord|tenant|applicant|respondent)s?\)", "",
               s, flags=re.I).strip(" ,;:.-")
    return s[:90].rsplit(" ", 1)[0] if len(s) > 90 else s


def extract_party(text: str, label_rx: re.Pattern, rep_rx: re.Pattern | None = None):
    name = ""
    for m in label_rx.finditer(text):
        chunk = text[m.end(): m.end() + 200]
        org = P.ORG_NAME_RE.search(chunk)
        if org:
            name = clean_party(org.group(1)); break
        per = P.NAME_RE.search(chunk)
        if per:
            name = clean_party(per.group(1)); break
        cand = clean_party(chunk)
        if cand and len(cand) > 2 and not P.NOISE_LINE_RE.match(cand):
            name = cand; break

    rep = ""
    if rep_rx is not None:
        for m in rep_rx.finditer(text):
            chunk = text[m.end(): m.end() + 160]
            hit = P.ORG_NAME_RE.search(chunk) or P.NAME_RE.search(chunk)
            rep = clean_party(hit.group(1) if hit else chunk)
            if rep:
                break
    return (name or rep), rep


def is_organisation(name: str) -> bool:
    return bool(name) and bool(P.ORG_SUFFIX_RE.search(name))


# ================================================================== case ref
def case_reference(text: str, url: str, title: str) -> str:
    for src in (title, text[:4000], text):
        m = P.CASE_REF_RE.search(src or "")
        if m:
            return "/".join(g.upper() for g in m.groups())
    m = P.CASE_REF_SLUG_RE.search(url or "")
    return "/".join(g.upper() for g in m.groups()) if m else ""


def tribunal_office(ref: str) -> str:
    if not ref:
        return ""
    head = ref.split("/")[0].upper()
    return P.TRIBUNAL_OFFICE.get(head, head)


def case_type(ref: str) -> str:
    parts = ref.split("/")
    return P.CASE_TYPE.get(parts[2].upper(), parts[2].upper()) if len(parts) >= 3 else ""


# ================================================================== address
def property_address(title: str, text: str) -> str:
    addr = P.CASE_REF_RE.sub("", title).strip(" :;,-\u2013") if title else ""
    if not addr or len(addr) < 8:
        m = re.search(r"(?:property|premises|address)\s*[:\-]\s*([^\n]{10,140})", text, re.I)
        if m:
            addr = m.group(1).strip(" :;,-")
    if not addr:
        pc = geo.find_postcode(text[:3000])
        if pc:
            i = text.find(pc)
            addr = text[max(0, i - 120): i + len(pc)].split("\n")[-1].strip()
    return re.sub(r"\s{2,}", " ", addr).strip(" :;,-")


# ================================================================== rents
def extract_rents(text: str, sections: dict, pre_rra: bool) -> dict:
    r: dict = {}

    v, p, _ = first_money(text, P.L_CURRENT_RENT)
    r["original_rent_value"] = v
    r["original_rent_period"] = p or ("Monthly" if v else "")

    v2, p2, _ = first_money(text, P.L_LANDLORD_PROPOSED)
    r["landlord_proposed_value"] = v2
    r["landlord_proposed_period"] = p2 or r["original_rent_period"] or ("Monthly" if v2 else "")

    hits = money_near(text, P.L_TENANT_PROPOSED)
    if not hits and sections.get("tenant_evidence"):
        hits = money_near(sections["tenant_evidence"],
                          P.label(r"propos(?:ed|es)", r"suggested", r"contended\s+for",
                                  r"submitted\s+that\s+the\s+rent", r"should\s+be"))
    v3, p3, _ = hits[0] if hits else (None, "", "")
    r["tenant_proposed_value"] = v3
    r["tenant_proposed_period"] = p3 or r["original_rent_period"] or ("Monthly" if v3 else "")

    v4, p4, ctx4, src = _determined(text, sections)
    r["determined_rent_value"] = v4
    r["determined_rent_period"] = p4 or r["original_rent_period"] or ("Monthly" if v4 else "")
    r["determined_rent_source"] = src
    r["determined_rent_context"] = ctx4
    return r


def _determined(text: str, sections: dict):
    """
    Cascade for the determined rent.

    The numbered box is tried FIRST when it scores strongly, because on the
    pre-RRA single-page form it is the authoritative statement of the decision
    and free-text label matching frequently misses it.
    """
    guard = P.NO_DETERMINATION_RE

    box_v, box_p, box_ctx, box_score = BX.read_numbered_box(text)
    if box_v is not None and box_score >= 9 and not guard.search(text):
        return box_v, box_p, box_ctx, f"numbered_box(score={box_score})"

    v, p, ctx = first_money(text, P.L_DETERMINED, guard=guard)
    if v is not None:
        return v, p, ctx, "label:determined"

    if box_v is not None and box_score >= 5 and not guard.search(text):
        return box_v, box_p, box_ctx, f"numbered_box_low(score={box_score})"

    if guard.search(text):
        return None, "", "", "negated"

    sb_v, sb_p, sb_ctx, sb_score = BX.read_standalone_box(text)
    if sb_v is not None and sb_score >= 6:
        return sb_v, sb_p, sb_ctx, f"standalone_box(score={sb_score})"

    if sections.get("reasoning"):
        v, p, ctx = _last_money(sections["reasoning"])
        if v is not None:
            return v, p, ctx, "reasoning_last_figure"
    return None, "", "", ""


def _last_money(text: str):
    hits = M.find_all(text, loose=False)
    for value, s, e in reversed(hits):
        period = PD.detect(text[max(0, s - 60): e + 70]) or "Monthly"
        if M.plausible(value, period):
            return value, period, text[max(0, s - 90): e + 60].strip()
    return None, "", ""


# ================================================================== sanity
def sanity_check(original_m, sought_m, determined_m) -> str:
    """
    Cross-check the monthly figures against each other.

    A determined rent an order of magnitude below the original is almost always
    a parse error, not a decision. Returning a flag rather than silently
    accepting the number is what makes a bad parse visible in the workbook.
    """
    flags = []
    if determined_m is not None and original_m:
        ratio = determined_m / original_m
        if ratio < 0.5:
            flags.append("determined_far_below_original")
        elif ratio > 3.0:
            flags.append("determined_far_above_original")
    if determined_m is not None and sought_m:
        if determined_m > sought_m * 1.5:
            flags.append("determined_far_above_sought")
    if sought_m and original_m and sought_m < original_m * 0.9:
        flags.append("sought_below_original")
    for name, val in (("original", original_m), ("sought", sought_m),
                      ("determined", determined_m)):
        if val is not None and val < 100:
            flags.append(f"{name}_implausibly_low")
    return ";".join(flags)


# ================================================================== outcome
def outcome(text: str, determined_value) -> str:
    if determined_value is not None and not P.NO_DETERMINATION_RE.search(text):
        return "Determined"
    if determined_value is not None:
        for name, rx in P.OUTCOME_RE:
            if rx.search(text):
                return name
        return "Determined"
    head = text[:2500] + "\n" + text[-2500:]
    for name, rx in P.OUTCOME_RE:
        if rx.search(head):
            return name
    if re.search(r"\brent\s+(?:is\s+)?confirmed\b|\bno\s+change\s+to\s+the\s+rent\b", text, re.I):
        return "Rent confirmed"
    return "No determination found"


# ================================================================== RRA flag
def rra_flags(application_date, notice_date, decision_date) -> dict:
    ref = application_date or notice_date
    basis = ("Application date" if application_date
             else "Section 13 notice date" if notice_date
             else "Decision date (proxy)")
    if ref is None:
        ref = decision_date
    if ref is None:
        return {"rra_status": "Unknown", "rra_basis_date": "", "rra_basis_field": basis,
                "tribunal_can_exceed_landlord_proposal": "Unknown"}
    post = ref >= config.RRA_COMMENCEMENT
    return {"rra_status": "Post-RRA" if post else "Pre-RRA",
            "rra_basis_date": iso(ref), "rra_basis_field": basis,
            "tribunal_can_exceed_landlord_proposal": "No" if post else "Yes"}
