"""
GOV.UK Search API client with capability negotiation - the 422 fix.

The API validates parameters strictly: an unknown parameter, or a known one
with an invalid value, is rejected with HTTP 422. V5.x probes the API once,
learns what it accepts, caches that profile, and only sends validated params.

Critically, `fields` MUST be sent as REPEATED parameters (fields=a&fields=b).
A single comma-joined string is one invalid field name and returns 422.
Passing a Python list to requests produces the correct repeated form.
"""
from __future__ import annotations

import datetime as _dt
import json

import config
from .httpclient import ApiValidationError, get_json


def _probe(params: dict) -> tuple[bool, str]:
    try:
        data = get_json(config.SEARCH_API, {**params, "count": 0}, raise_validation=True)
        return (True, "") if data is not None else (False, "UNREACHABLE")
    except ApiValidationError as exc:
        return False, str(exc)


def negotiate(force: bool = False, verbose: bool = True) -> dict:
    cache = config.PREFLIGHT_CACHE
    if cache.exists() and not force:
        try:
            prof = json.loads(cache.read_text("utf-8"))
            age = (_dt.date.today() - _dt.date.fromisoformat(prof["probed_at"][:10])).days
            if age <= config.PREFLIGHT_MAX_AGE_DAYS:
                if verbose:
                    print(f"[api] reusing cached profile (probed {prof['probed_at'][:10]})")
                return prof
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    say = print if verbose else (lambda *a, **k: None)
    say("[api] negotiating capabilities (this is what prevents 422s)")

    base = {"filter_format": config.FORMAT}
    ok, why = _probe(base)
    if not ok:
        if why == "UNREACHABLE":
            raise RuntimeError(
                "Could not reach https://www.gov.uk/api/search.json.\n"
                "This is a connectivity problem, not a 422. Check your network\n"
                "or proxy, or run:  python run_all.py --no-api")
        raise RuntimeError(f"The API rejected the base format filter: {why}")
    say(f"    format filter '{config.FORMAT}' accepted")

    category_filter = None
    ok, why = _probe({**base, "filter_tribunal_decision_category":
                      config.DECISION_CATEGORIES[0]})
    if ok:
        category_filter = "tribunal_decision_category"
        say("    category filter accepted")
    else:
        say(f"    category filter rejected -> {why[:90]}")

    fields: list[str] = []
    for f in config.CANDIDATE_FIELDS:
        ok, _ = _probe({**base, "fields": [f]})
        if ok:
            fields.append(f)
    rejected = [f for f in config.CANDIDATE_FIELDS if f not in fields]
    say(f"    {len(fields)}/{len(config.CANDIDATE_FIELDS)} candidate fields accepted")
    if rejected:
        say(f"    dropped unsupported fields: {', '.join(rejected)}")
    if "link" not in fields:
        fields.append("link")

    order = ""
    for cand in config.CANDIDATE_ORDERS:
        if not cand:
            break
        ok, why = _probe({**base, "order": cand})
        if ok:
            order = cand
            say(f"    order '{cand}' accepted")
            break
        say(f"    order '{cand}' rejected -> {why[:80]}")
    if not order:
        say("    no sortable order accepted; sorting client-side instead")

    date_filter = None
    for cand in config.CANDIDATE_DATE_FILTERS:
        ok, why = _probe({**base, f"filter_{cand}": "from:2024-01-01,to:2024-12-31"})
        if ok:
            date_filter = cand
            say(f"    date filter '{cand}' accepted")
            break
        say(f"    date filter '{cand}' rejected -> {why[:80]}")
    if not date_filter:
        say("    no date filter accepted; will window client-side")

    prof = {"fields": fields, "order": order, "date_filter": date_filter,
            "category_filter": category_filter,
            "probed_at": _dt.datetime.now().isoformat(timespec="seconds")}
    cache.write_text(json.dumps(prof, indent=2), encoding="utf-8")
    return prof


def _params(prof: dict, category: str, start: int, count: int, window) -> dict:
    p: dict = {"filter_format": config.FORMAT, "start": start, "count": count}
    if prof.get("category_filter"):
        p[f"filter_{prof['category_filter']}"] = category
    if prof.get("fields"):
        p["fields"] = list(prof["fields"])   # LIST, never ",".join(...)
    if prof.get("order"):
        p["order"] = prof["order"]
    if window and prof.get("date_filter"):
        a, b = window
        p[f"filter_{prof['date_filter']}"] = f"from:{a.isoformat()},to:{b.isoformat()}"
    return p


def _fetch(prof: dict, category: str, start: int, count: int, window):
    try:
        return get_json(config.SEARCH_API, _params(prof, category, start, count, window),
                        raise_validation=True)
    except ApiValidationError as exc:
        print(f"    ! 422 at start={start}: {exc}")
        changed = False
        for key in exc.offending:
            if prof.get("date_filter") and key.endswith(prof["date_filter"]):
                prof["date_filter"] = None; changed = True
            elif key == "order":
                prof["order"] = ""; changed = True
            elif key == "fields":
                prof["fields"] = ["link", "title"]; changed = True
        if not changed:
            prof["order"] = ""; prof["date_filter"] = None
            prof["fields"] = ["link", "title"]
        print("    recovering with a reduced parameter set")
        try:
            return get_json(config.SEARCH_API,
                            _params(prof, category, start, count, window),
                            raise_validation=True)
        except ApiValidationError as exc2:
            print(f"    ! still rejected: {exc2}")
            return None


def _first(v):
    if isinstance(v, list):
        v = v[0] if v else None
    if isinstance(v, dict):
        return v.get("label") or v.get("value") or v.get("slug")
    return v


def _row(r: dict) -> dict:
    link = r.get("link") or ""
    return {"decision_url": config.BASE + link if link.startswith("/") else link,
            "title": (r.get("title") or "").strip(),
            "decided_at": (r.get("tribunal_decision_decided_at")
                           or r.get("public_timestamp") or "")[:10],
            "category": _first(r.get("tribunal_decision_category")) or "",
            "sub_category": _first(r.get("tribunal_decision_sub_category")) or "",
            "landlord_type": _first(r.get("tribunal_decision_landlord_type")) or "",
            "decision_type": _first(r.get("tribunal_decision_decision_type")) or ""}


def _split(window):
    a, b = window
    span = (b - a).days
    if span <= 1:
        return [window]
    mid = a + _dt.timedelta(days=span // 2)
    return [(a, mid), (mid + _dt.timedelta(days=1), b)]


def _harvest_window(prof, category, window, seen, depth=0) -> list[dict]:
    rows: list[dict] = []
    probe = _fetch(prof, category, 0, 1, window)
    if probe is None:
        return rows
    total = probe.get("total", 0)
    if total == 0:
        return rows

    if total > config.SAFE_OFFSET_CEILING and window and depth < 6:
        for sub in _split(window):
            rows += _harvest_window(prof, category, sub, seen, depth + 1)
        return rows

    start = 0
    while start < min(total, config.SAFE_OFFSET_CEILING + config.PAGE_SIZE):
        data = _fetch(prof, category, start, config.PAGE_SIZE, window)
        if not data or not data.get("results"):
            break
        for res in data["results"]:
            row = _row(res)
            if row["decision_url"] and row["decision_url"] not in seen:
                seen.add(row["decision_url"])
                rows.append(row)
        start += config.PAGE_SIZE

    if rows:
        label = f"{window[0]}..{window[1]}" if window else "all"
        print(f"  {'  ' * depth}{label}: +{len(rows)} of {total} (running {len(seen)})")
    return rows


def harvest(year_from: int = 2000, year_to: int | None = None) -> list[dict]:
    year_to = year_to or _dt.date.today().year
    prof = negotiate()
    seen: set[str] = set()
    rows: list[dict] = []
    for category in config.DECISION_CATEGORIES:
        print(f"[api] harvesting category '{category}'")
        if prof.get("date_filter"):
            for y in range(year_to, year_from - 1, -1):
                rows += _harvest_window(prof, category,
                                        (_dt.date(y, 1, 1), _dt.date(y, 12, 31)), seen)
        else:
            rows += _harvest_window(prof, category, None, seen)
    return rows
