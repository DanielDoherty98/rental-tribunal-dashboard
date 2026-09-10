"""Diagnose the GOV.UK Search API from your machine."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))
import requests, config
S = requests.Session(); S.headers.update({"User-Agent": config.USER_AGENT})
F = config.FORMAT
TESTS = [
    ("bare endpoint", {"count": 1}),
    ("format filter", {"filter_format": F, "count": 1}),
    ("format + category", {"filter_format": F,
                           "filter_tribunal_decision_category": "rents", "count": 1}),
    ("fields as REPEATED params (correct)",
     {"filter_format": F, "count": 1, "fields": ["title", "link"]}),
    ("fields COMMA-JOINED (expected to FAIL)",
     {"filter_format": F, "count": 1, "fields": "title,link"}),
    ("order -public_timestamp",
     {"filter_format": F, "count": 1, "order": "-public_timestamp"}),
    ("date filter on public_timestamp",
     {"filter_format": F, "count": 1,
      "filter_public_timestamp": "from:2024-01-01,to:2024-12-31"}),
    ("count=100", {"filter_format": F, "count": 100}),
    ("deep page start=900", {"filter_format": F, "count": 100, "start": 900}),
]
print(f"Endpoint: {config.SEARCH_API}\n" + "=" * 78)
for name, params in TESTS:
    try:
        r = S.get(config.SEARCH_API, params=params, timeout=30)
        if r.status_code == 200:
            try: total = json.loads(r.text).get("total", "?")
            except json.JSONDecodeError: total = "unparseable"
            print(f"PASS  {name:<48} total={total}")
        else:
            print(f"FAIL  {name:<48} HTTP {r.status_code}")
            print(f"      {r.text[:200]}")
    except Exception as exc:
        print(f"ERR   {name:<48} {type(exc).__name__}")
print("=" * 78)
