"""Rent period detection and conversion to a monthly equivalent."""
from __future__ import annotations

import re

import config

WEEKS = config.WEEKS_PER_YEAR

PERIOD_PATTERNS = [
    ("Weekly", r"\bp\.?\s?w\b|\bper\s+week\b|\bweekly\b|\ba\s+week\b|\beach\s+week\b"
               r"|\bpw\b|\bper\s+wk\b"),
    ("Fortnightly", r"\bper\s+fortnight\b|\bfortnightly\b|\b(?:every\s+)?two\s+weeks\b"),
    ("Four-weekly", r"\bevery\s+four\s+weeks\b|\bfour[- ]weekly\b|\b4[- ]weekly\b"
                    r"|\bper\s+4\s+weeks\b"),
    ("Monthly", r"\bp\.?\s?c\.?\s?m\b|\bper\s+(?:calendar\s+)?month\b|\bmonthly\b"
                r"|\ba\s+month\b|\beach\s+month\b|\bpm\b(?!\s*\d)|\bcalendar\s+month\b"),
    ("Quarterly", r"\bper\s+quarter\b|\bquarterly\b"),
    ("Annual", r"\bper\s+annum\b|\bp\.?\s?a\b|\bannually\b|\byearly\b|\bper\s+year\b"),
]
PERIOD_RE = [(name, re.compile(pat, re.I)) for name, pat in PERIOD_PATTERNS]

PERIOD_TO_MONTHLY = {
    "Weekly": lambda v, w: v * w / 12.0,
    "Fortnightly": lambda v, w: v * (w / 2.0) / 12.0,
    "Four-weekly": lambda v, w: v * (w / 4.0) / 12.0,
    "Monthly": lambda v, w: v,
    "Quarterly": lambda v, w: v / 3.0,
    "Annual": lambda v, w: v / 12.0,
}

SUFFIX = {"Weekly": "pw", "Monthly": "pcm", "Annual": "pa",
          "Fortnightly": "per fortnight", "Four-weekly": "per 4 weeks",
          "Quarterly": "per quarter"}


def detect(fragment: str, default: str = "") -> str:
    """Return Weekly / Monthly / ... from the wording around a figure."""
    for name, rx in PERIOD_RE:
        if rx.search(fragment or ""):
            return name
    return default


def to_monthly(value, period: str):
    if value is None:
        return None
    fn = PERIOD_TO_MONTHLY.get(period or "Monthly")
    if fn is None:
        return None
    return round(fn(float(value), WEEKS), 2)


def as_stated(value, period: str) -> str:
    if value is None:
        return ""
    sfx = SUFFIX.get(period, "")
    return f"£{float(value):,.2f}{(' ' + sfx) if sfx else ''}".strip()
