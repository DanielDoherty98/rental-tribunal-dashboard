"""Stage 1 - build the index of decision URLs (API first, HTML fallback)."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

import config
from . import httpclient as http
from . import govuk_api

SLUG_RE = re.compile(r"/residential-property-tribunal-decisions/(.+)$")


def slug(url: str) -> str:
    m = SLUG_RE.search(url)
    return m.group(1) if m else url


def _norm(s: str) -> str:
    from dateutil import parser as dp
    try:
        return dp.parse(s, dayfirst=True).date().isoformat()
    except Exception:  # noqa: BLE001
        return ""


def from_html(category: str, max_pages: int = 500) -> list[dict]:
    rows, seen, page = [], set(), 1
    while page <= max_pages:
        html = http.get(f"{config.BASE}{config.INDEX_PATH}",
                        params={"tribunal_decision_category[]": category, "page": page})
        if not html:
            break
        soup = BeautifulSoup(html, "lxml")
        new = 0
        for a in soup.select("a[href*='/residential-property-tribunal-decisions/']"):
            href = a.get("href", "").split("?")[0]
            if href.rstrip("/").endswith("residential-property-tribunal-decisions"):
                continue
            full = config.BASE + href if href.startswith("/") else href
            if full in seen:
                continue
            seen.add(full); new += 1
            block = a.find_parent(["li", "div"])
            txt = block.get_text(" ", strip=True) if block else ""
            m = re.search(r"\b(\d{1,2}\s+\w+\s+\d{4})\b", txt)
            rows.append({"decision_url": full, "title": a.get_text(" ", strip=True),
                         "decided_at": _norm(m.group(1)) if m else "",
                         "category": category, "sub_category": "",
                         "landlord_type": "", "decision_type": ""})
        if new == 0:
            break
        if page % 10 == 0:
            print(f"  html page {page}: running total {len(rows)}")
        page += 1
    print(f"[html] {len(rows)} decisions from finder pages")
    return rows


def build_index(year_from: int = 2000, year_to: int | None = None,
                use_api: bool = True, use_html: bool = True) -> list[dict]:
    collected: list[dict] = []
    if use_api:
        try:
            collected += govuk_api.harvest(year_from, year_to)
        except Exception as exc:  # noqa: BLE001
            print(f"[api] unavailable ({exc})")
            print("[api] continuing with the HTML fallback")

    if use_html and len(collected) < 100:
        print("[index] API yield low - topping up from the finder HTML")
        for cat in config.DECISION_CATEGORIES:
            collected += from_html(cat)

    merged: dict[str, dict] = {}
    for row in collected:
        url = row.get("decision_url")
        if not url:
            continue
        if url in merged:
            for k, v in row.items():
                if v and not merged[url].get(k):
                    merged[url][k] = v
        else:
            merged[url] = row
    out = sorted(merged.values(), key=lambda r: r.get("decided_at") or "", reverse=True)
    print(f"[index] {len(out)} unique decisions")
    return out
