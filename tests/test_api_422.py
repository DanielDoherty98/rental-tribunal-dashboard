"""
422 regression tests against a fake GOV.UK Search API that reproduces the real
API's documented validation rules. Offline.

Run:  python tests/test_api_422.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))

import config                                            # noqa: E402
from rtscraper import govuk_api                          # noqa: E402
from rtscraper.httpclient import ApiValidationError      # noqa: E402

SCHEMA_FIELDS = {"title", "link", "description", "public_timestamp",
                 "tribunal_decision_decided_at", "tribunal_decision_category",
                 "tribunal_decision_sub_category", "tribunal_decision_landlord_type",
                 "tribunal_decision_decision_type"}
SORTABLE = {"public_timestamp", "-public_timestamp"}
DATE_FILTERABLE = {"public_timestamp"}
KNOWN = {"filter_format", "start", "count", "fields", "order", "q",
         "filter_tribunal_decision_category", "filter_tribunal_decision_decided_at",
         "filter_public_timestamp"}
CALLS = {"total": 0, "422": 0}
CORPUS = 4000


class Fake422(Exception):
    pass


def _validate(params: dict):
    for key, val in params.items():
        if key not in KNOWN:
            raise Fake422(f"Unexpected parameter: {key}")
        if key == "fields":
            names = val if isinstance(val, list) else [val]
            for n in names:
                if "," in str(n):
                    raise Fake422(f"Invalid value for fields: {n}")
                if str(n) not in SCHEMA_FIELDS:
                    raise Fake422(f"Unexpected field: {n}")
        if key == "order" and val and val not in SORTABLE:
            raise Fake422(f"Cannot sort by order: {val}")
        if key == "count" and int(val) > 1500:
            raise Fake422("count is too large")
        if key.startswith("filter_") and isinstance(val, str) and val.startswith("from:"):
            if key[len("filter_"):] not in DATE_FILTERABLE:
                raise Fake422(f"Cannot apply date range to {key[len('filter_'):]}")


def fake_get_json(url, params=None, raise_validation=True):
    CALLS["total"] += 1
    params = params or {}
    try:
        _validate(params)
    except Fake422 as exc:
        CALLS["422"] += 1
        if raise_validation:
            raise ApiValidationError(str(exc), params, json.dumps({"message": str(exc)}))
        return None
    count, start = int(params.get("count", 10)), int(params.get("start", 0))
    total = CORPUS
    for k, v in params.items():
        if k.startswith("filter_") and isinstance(v, str) and v.startswith("from:"):
            total = 140
            break
    n = max(0, min(count, total - start))
    salt = abs(hash(json.dumps(params, sort_keys=True, default=str))) % 99999
    return {"total": total, "results": [
        {"link": f"/residential-property-tribunal-decisions/case-{salt}-{start+i}",
         "title": f"1 Test Road, London SW1A 1AA: LON/00AA/MNR/2024/{start+i:04d}",
         "public_timestamp": "2024-06-01T00:00:00+00:00",
         "tribunal_decision_decided_at": "2024-06-01"} for i in range(n)]}


results = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" +
          ("" if ok else f"  (expected {want!r})"))
    results.append(ok)


def check_true(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' ' + detail) if detail else ''}")
    results.append(bool(cond))


govuk_api.get_json = fake_get_json
config.PREFLIGHT_CACHE = ROOT / "data" / "test_api_profile.json"
if config.PREFLIGHT_CACHE.exists():
    config.PREFLIGHT_CACHE.unlink()

print("\n[1] The comma-joined fields request is rejected; V5.2 never builds it")
try:
    fake_get_json(config.SEARCH_API, {
        "filter_format": config.FORMAT, "count": 100,
        "fields": "title,link,tribunal_decision_decided_at"})
    check_true("comma-joined fields -> 422", False, "(was accepted!)")
except ApiValidationError as exc:
    check_true("comma-joined fields -> 422", True, f"({exc})")

prof = govuk_api.negotiate(force=True, verbose=True)
built = govuk_api._params(prof, "rents", 0, 100, None)
check_true("fields sent as a LIST", isinstance(built.get("fields"), list))
check_true("no comma in any field name",
           all("," not in f for f in built.get("fields", [])))

print("\n[2] Negotiated profile avoids every rejected parameter")
check_true("all fields in schema", all(f in SCHEMA_FIELDS for f in prof["fields"]))
check("order avoids unsortable field", prof["order"], "-public_timestamp")
check("date filter falls back", prof["date_filter"], "public_timestamp")

print("\n[3] Full harvest with zero 422s")
CALLS.update({"total": 0, "422": 0})
rows = govuk_api.harvest(2022, 2024)
check_true("rows returned", len(rows) > 0, f"({len(rows)} rows)")
check("422s during harvest", CALLS["422"], 0)
check_true("URLs de-duplicated", len({r["decision_url"] for r in rows}) == len(rows))

print("\n[4] Deep windows bisect rather than paging past the ceiling")
seen = set()
deep = govuk_api._harvest_window(prof, "rents", None, seen)
check_true("respects the offset ceiling",
           len(deep) <= config.SAFE_OFFSET_CEILING + config.PAGE_SIZE,
           f"({len(deep)} rows)")

print("\n[5] A mid-harvest 422 is recovered, not retried blindly")
state = {"n": 0}
original = govuk_api.get_json


def flaky(url, params=None, raise_validation=True):
    state["n"] += 1
    if state["n"] == 1:
        raise ApiValidationError("Cannot sort by order: boom", {"order": "boom"},
                                 json.dumps({"message": "Cannot sort by order"}))
    return original(url, params, raise_validation)


govuk_api.get_json = flaky
prof2 = dict(prof)
out = govuk_api._fetch(prof2, "rents", 0, 10, None)
check_true("recovered after injected 422", out is not None)
check("offending parameter dropped", prof2["order"], "")
govuk_api.get_json = original

if config.PREFLIGHT_CACHE.exists():
    config.PREFLIGHT_CACHE.unlink()

passed, total = sum(results), len(results)
print(f"\n{'=' * 62}\n{passed}/{total} API checks passed\n{'=' * 62}")
raise SystemExit(0 if passed == total else 1)
