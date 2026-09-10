"""
Numbered-box reader for pre-Renters'-Rights-Act decision forms.

WHY THIS EXISTS
---------------
Older decisions (and many 2025 ones) are a single-page form. The operative
figure sits in boxes beside a numbered item, typically:

    1.   The rent is        [ £1300 ]   [ per calendar month ]

PDF text extraction flattens that table in unpredictable ways:

    "1. The rent is £1300 per calendar month"       (one line)
    "1.\nThe rent is\n£1300\nper calendar month"    (cell per line)
    "1.  The rent is   1300   per calendar month"   (£ glyph lost)

Free-text label matching misses all but the first. This module finds the
numbered item and reads the boxes that follow it as a unit - the amount box and
the period box - which is how the form is meant to be read.

The £ sign is frequently dropped by PDF extractors, so bare numbers are
accepted inside a confirmed box context, guarded by `looks_like_rent()` to keep
out years, case numbers and paragraph references.
"""
from __future__ import annotations

import re

from . import money as M
from . import periods as PD

# The numbered item that carries the determination. Item 1 on the standard
# form; item 2/3 are accepted at lower score as some variants renumber.
ITEM_RE = re.compile(r"(?m)^\s*(\d{1,2})\s*[\.\)]\s*")

# Wording that marks the determination line itself.
RENT_LINE_RE = re.compile(
    r"the\s+rent\s+(?:for\s+the\s+(?:above\s+)?(?:propert|premises)\w*\s+)?"
    r"(?:is|shall\s+be|will\s+be|was)\b"
    r"|^\s*rent\s*(?:determined|payable)?\s*[:\-]?\s*$"
    r"|market\s+rent\s+(?:is|of)\b"
    r"|determines?\s+(?:a\s+|the\s+)?(?:market\s+)?rent\s+(?:of|at|to\s+be)\b"
    r"|rent\s+determined\s+(?:by\s+the\s+tribunal\s+)?(?:is|at|of)\b",
    re.I)

# Wording that means the figure is NOT the determination.
NOT_DETERMINED_RE = re.compile(
    r"\bproposed\b|\bnotice\b|\bcurrently\s+payable\b|\bcurrent\s+rent\b"
    r"|\bexisting\s+rent\b|\bsought\b|\bapplied\s+for\b|\bpassing\s+rent\b"
    r"|\bprevious(?:ly)?\s+rent\b|\btenant'?s?\s+propos", re.I)

DATE_NEAR_RE = re.compile(
    r"\b\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}\b|\b(19|20)\d{2}\b")


def _lines(text: str) -> list[str]:
    return (text or "").split("\n")


def _window(lines: list[str], idx: int, span: int = 12) -> str:
    return "\n".join(lines[idx: idx + span])


def read_numbered_box(text: str) -> tuple[float | None, str, str, int]:
    """
    Read the determined rent from the numbered boxes.

    Returns (value, period, context, score). Score is 0 when nothing credible
    was found; higher is more confident.
    """
    lines = _lines(text)
    best: tuple[float | None, str, str, int] = (None, "", "", 0)

    for i, line in enumerate(lines):
        m = ITEM_RE.match(line)
        if not m:
            continue
        item_no = int(m.group(1))
        if item_no > 3:
            continue

        window = _window(lines, i, 12)

        # The determination wording must appear in the item or just after it.
        if not RENT_LINE_RE.search(window):
            continue

        # Cut the window at the next numbered item so we don't read item 2's box.
        nxt = ITEM_RE.search(window[len(line):])
        if nxt:
            window = window[: len(line) + nxt.start()]

        for value, s, e in M.find_all(window, loose=True):
            raw = window[s:e].replace("£", "").strip()
            around = window[max(0, s - 90): e + 90]

            if DATE_NEAR_RE.search(around) and not re.search(r"£", around):
                # a bare number sitting next to a date is probably part of it
                if not PD.detect(around):
                    continue

            period = PD.detect(around) or PD.detect(window) or "Monthly"
            if not M.looks_like_rent(value, raw, around, period):
                continue

            score = 4 if item_no == 1 else 2
            if "£" in around:
                score += 3
            if RENT_LINE_RE.search(around):
                score += 3
            if PD.detect(around):
                score += 2
            if NOT_DETERMINED_RE.search(around):
                score -= 6

            if score > best[3]:
                best = (value, period, around.strip()[:220], score)

    return best


def read_standalone_box(text: str) -> tuple[float | None, str, str, int]:
    """
    Fallback for forms with no numbering: a money figure alone on a short line,
    scored on the wording immediately around it.
    """
    lines = _lines(text)
    best: tuple[float | None, str, str, int] = (None, "", "", 0)

    for i, line in enumerate(lines):
        s = line.strip()
        if not s or len(s) > 60:
            continue
        hits = M.find_all(s, loose=("£" in s))
        if not hits:
            continue

        ctx = "\n".join(lines[max(0, i - 4): i + 5])
        for value, a, b in hits:
            raw = s[a:b].replace("£", "").strip()
            period = PD.detect(s) or PD.detect(ctx) or "Monthly"
            if not M.looks_like_rent(value, raw, ctx, period):
                continue

            score = 0
            if "£" in s:
                score += 3
            if re.search(r"\brent\b", ctx, re.I):
                score += 3
            if RENT_LINE_RE.search(ctx):
                score += 3
            if len(s) <= 22:
                score += 2
            if NOT_DETERMINED_RE.search(ctx):
                score -= 6

            if score > best[3]:
                best = (value, period, ctx.strip()[:220], score)

    return best
