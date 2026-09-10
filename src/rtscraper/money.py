"""
Money parsing - rebuilt in V5.2 after a critical truncation bug.

THE BUG (V5.0/V5.1)
-------------------
The old pattern was:

    £\\s?([0-9]{1,3}(?:,[0-9]{3})*(?:\\.[0-9]{1,2})?|[0-9]+(?:\\.[0-9]{1,2})?)

Regex alternation is ordered and the comma group used `*` (zero or more), so
for "£1300" the FIRST branch matched "130" and succeeded - the engine never
tried the second branch. Every rent written without a thousands separator was
silently truncated to three digits:

    £1300  -> 130      £1175  -> 117      £12500 -> 125

Because 130 still passes a plausibility check, the wrong value was written to
the workbook with no warning. This affected the majority of four-figure rents.

THE FIX
-------
Branch one now REQUIRES at least one comma group (`+`, not `*`), so it can only
match a fully comma-formatted number; otherwise the plain-digit branch runs and
consumes every digit. Lookarounds stop the pattern starting or ending
mid-number.

Two patterns are exposed:

  MONEY_RE       - requires the £ sign. Safe for scanning free text.
  MONEY_LOOSE_RE - £ optional. ONLY for use inside a verified box/table cell,
                   where the £ glyph is frequently lost by PDF extraction.
                   Always pair it with `looks_like_rent()`.
"""
from __future__ import annotations

import re

# Number core: comma-grouped (needs >=1 comma) OR a plain run of digits.
_NUM = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?"

# £ required. `(?<![\d.,])` stops a match starting mid-number; `(?!\d)` stops a
# short match leaving digits behind.
MONEY_RE = re.compile(rf"£\s?((?<![\d.,]){_NUM})(?!\d)")

# £ optional - box/cell context only.
MONEY_LOOSE_RE = re.compile(rf"(?<![\d.,])£?\s?({_NUM})(?!\d)")

# Things that look like money but are not rents.
_YEAR_RE = re.compile(r"^(19|20)\d{2}$")
_CASE_CONTEXT_RE = re.compile(
    r"/\s*\d{2,5}\s*$|case|reference|ref\b|paragraph|para\b|section\b|schedule\b"
    r"|article\b|page\b|act\s+\d{4}|regulation", re.I)


def to_float(raw: str) -> float | None:
    """'1,300.00' -> 1300.0"""
    if raw is None:
        return None
    try:
        return float(str(raw).replace(",", "").strip())
    except ValueError:
        return None


def find_all(text: str, loose: bool = False) -> list[tuple[float, int, int]]:
    """Return [(value, start, end), ...] for every money figure in `text`."""
    rx = MONEY_LOOSE_RE if loose else MONEY_RE
    out = []
    for m in rx.finditer(text or ""):
        v = to_float(m.group(1))
        if v is not None:
            out.append((v, m.start(), m.end()))
    return out


def looks_like_rent(value: float | None, raw: str = "", context: str = "",
                    period: str = "Monthly") -> bool:
    """
    Guard for values captured WITHOUT a £ sign.

    Rejects years, case-number fragments, and anything outside a sane monthly
    range once converted. Deliberately strict, because a false positive here
    writes a wrong number into the workbook.
    """
    if value is None:
        return False

    raw = (raw or "").strip()
    if _YEAR_RE.match(raw.replace(",", "")) and 1900 <= value <= 2099:
        return False
    if _CASE_CONTEXT_RE.search(context or ""):
        return False

    from .periods import to_monthly          # local import avoids a cycle
    monthly = to_monthly(value, period or "Monthly")
    if monthly is None:
        return False
    return 15.0 <= monthly <= 25000.0


def plausible(value: float | None, period: str = "Monthly") -> bool:
    """Range check for values captured WITH a £ sign."""
    if value is None:
        return False
    from .periods import to_monthly
    monthly = to_monthly(value, period or "Monthly")
    return monthly is not None and 15.0 <= monthly <= 25000.0
