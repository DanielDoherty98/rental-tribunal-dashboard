"""
RentalTribunalScraper V5.2 - one-command pipeline.

    python run_all.py --check          # probe the API, no scraping
    python run_all.py --test 10        # 10-record smoke test
    python run_all.py                  # incremental refresh
    python run_all.py --no-api         # HTML only, bypasses the Search API
    python run_all.py --reparse        # re-parse cached documents, no downloads
    python run_all.py --full           # rebuild everything

--reparse is the one to use after a parser fix: it rebuilds every record from
documents already on disk, so a fix is applied to the whole dataset in minutes
without touching the network.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "src"))

from tqdm import tqdm  # noqa: E402

import config  # noqa: E402
from rtscraper import index as idx  # noqa: E402
from rtscraper import govuk_api, extract, record, dataset  # noqa: E402

INDEX_FILE = config.DATA / "index.json"
RECORDS_FILE = config.DATA / "records.json"


def load(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text("utf-8"))
        except json.JSONDecodeError:
            return default
    return default


def save(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", type=int, default=0)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--reparse", action="store_true",
                    help="re-parse cached documents without downloading")
    ap.add_argument("--since", default="")
    ap.add_argument("--skip-index", action="store_true")
    ap.add_argument("--no-api", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    print(f"RentalTribunalScraper v{config.MODEL_VERSION}")
    print(f"[setup] project folder: {HERE}\n")

    if args.check:
        prof = govuk_api.negotiate(force=True)
        print("\nNegotiated profile:")
        print(json.dumps(prof, indent=2))
        print("\nNo 422s. These parameters are safe to use.")
        return 0

    if args.reparse or args.skip_index:
        entries = load(INDEX_FILE, [])
        print(f"[index] reusing {len(entries)} cached entries")
    else:
        entries = idx.build_index(use_api=not args.no_api)
        save(INDEX_FILE, entries)

    if args.since:
        entries = [e for e in entries if (e.get("decided_at") or "") >= args.since]
        print(f"[index] {len(entries)} decisions on/after {args.since}")
    if args.test:
        entries = entries[:args.test]
        print(f"[index] TEST MODE - {len(entries)} decisions")
    if not entries:
        print("[index] nothing to do.")
        return 1

    # --reparse and --full both ignore cached records; --reparse additionally
    # relies purely on documents already downloaded.
    existing = {} if (args.full or args.reparse or config.FULL_REFRESH) else \
        {r["decision_url"]: r for r in load(RECORDS_FILE, [])}
    if args.reparse:
        print("[parse] re-parsing cached documents (no downloads)")
    else:
        print(f"[parse] {len(existing)} records already cached")

    records = []
    for e in tqdm(entries, desc="decisions", unit="doc"):
        url = e["decision_url"]
        if url in existing:
            records.append(existing[url]); continue
        try:
            text, doc_url = extract.full_text(url)
            if not text:
                continue
            records.append(record.build(e, text, doc_url))
        except Exception as exc:  # noqa: BLE001
            print(f"\n  ! {url}: {exc}")

    if not (args.full or args.reparse):
        seen = {r["decision_url"] for r in records}
        records += [r for r in existing.values() if r["decision_url"] not in seen]

    save(RECORDS_FILE, records)
    print(f"[parse] {len(records)} records total")

    df = dataset.to_frame(records)
    dataset.write_excel(df); dataset.write_csv(df); dataset.write_dashboard_json(df)

    print("\n--- summary ---")
    print(dataset.summary_frame(df).to_string(index=False))

    needs = int((df["needs_review"] == "Yes").sum())
    if needs:
        print(f"\n{needs} row(s) flagged for review - see the 'Needs Review' tab.")
    print("\nRun 5_VIEW_DASHBOARD.bat to preview.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
