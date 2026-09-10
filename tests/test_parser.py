"""
Offline parser regression tests. No network.

Group [1] reproduces the two failures reported against V5.1:
  MAN/00BU/MNR/2025/0690  - determined rent not found (boxed form)
  £1300                   - read as £130 (money truncation)

Run:  python tests/test_parser.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fixtures as fx                                    # noqa: E402
from rtscraper import record, dataset, parse as pr       # noqa: E402

results = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" +
          ("" if ok else f"  (expected {want!r})"))
    results.append(ok)


def approx(name, got, want, tol=0.02):
    ok = got is not None and abs(got - want) <= tol
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" +
          ("" if ok else f"  (expected ~{want})"))
    results.append(ok)


GOV = "https://www.gov.uk/residential-property-tribunal-decisions/"

print("\n[1] REPORTED FAILURES - these must never regress")
print("  -- MAN/00BU/MNR/2025/0690: rent is £1175 in the box beside item 1 --")
r = record.build({"decision_url": GOV + "a",
    "title": "4 Example Street, Manchester M14 5TG: MAN/00BU/MNR/2025/0690",
    "decided_at": "2025-07-28"}, fx.REAL_CASE_0690, "")
check("case_reference", r["case_reference"], "MAN/00BU/MNR/2025/0690")
approx("determined rent found", r["determined_rent_monthly"], 1175.00)
check("outcome", r["outcome_category"], "Determined")
check("read from the numbered box",
      r["determined_rent_source"].startswith("numbered_box"), True)
approx("original rent", r["original_rent_monthly"], 950.00)
approx("rent sought", r["rent_sought_monthly"], 1250.00)
check("no sanity flag", r["rent_sanity_flag"], "")
check("city", r["city"], "Manchester")

print("  -- £1300 must not be read as £130 --")
r2 = record.build({"decision_url": GOV + "b",
    "title": "Flat 3, 22 Example Gardens, London SE15 4TP: LON/00AH/MNR/2025/0412",
    "decided_at": "2025-05-19"}, fx.REAL_CASE_1300, "")
approx("determined rent is 1300 not 130", r2["determined_rent_monthly"], 1300.00)
approx("original rent", r2["original_rent_monthly"], 1100.00)
approx("rent sought", r2["rent_sought_monthly"], 1400.00)
approx("uplift determined %", r2["uplift_determined_pct"], 18.18)
check("no sanity flag", r2["rent_sanity_flag"], "")
check("city", r2["city"], "London")

print("  -- same form, one table cell per line --")
r3 = record.build({"decision_url": GOV + "c",
    "title": "9 Sample Avenue, Leeds LS6 2AA: LEE/00DA/MNR/2025/0155",
    "decided_at": "2025-06-04"}, fx.CELL_PER_LINE, "")
approx("determined rent from split cells", r3["determined_rent_monthly"], 1025.00)
check("city", r3["city"], "Leeds")

print("\n[2] Sanity check catches a bad parse")
check("130 vs 1100 original flags",
      "determined_far_below_original" in pr.sanity_check(1100.0, 1400.0, 130.0), True)
check("1300 vs 1100 original is clean", pr.sanity_check(1100.0, 1400.0, 1300.0), "")
check("implausibly low flagged",
      "determined_implausibly_low" in pr.sanity_check(1100.0, 1400.0, 90.0), True)

print("\n[3] Post-RRA full decision form")
r4 = record.build({"decision_url": GOV + "d",
    "title": "Flat 10 Langley Mansions, Langley Lane, London SW8 1TJ: LON/00AY/MNR/2026/0155",
    "decided_at": "2026-06-19"}, fx.POST_RRA, "")
check("case_reference", r4["case_reference"], "LON/00AY/MNR/2026/0155")
check("postcode", r4["postcode"], "SW8 1TJ")
check("landlord", r4["landlord_representative"], "Grainger Residential Management Limited")
approx("original pcm", r4["original_rent_monthly"], 780.00)
approx("sought pcm", r4["rent_sought_monthly"], 1050.00)
approx("tenant proposed pcm", r4["tenant_proposed_rent_monthly"], 914.07)
approx("determined pcm", r4["determined_rent_monthly"], 985.00)
check("RRA status", r4["rra_status"], "Post-RRA")
check("can exceed ask", r4["tribunal_can_exceed_landlord_proposal"], "No")
check("no sanity flag", r4["rent_sanity_flag"], "")
print("    tenant_evidence  ->", r4["tenant_evidence"])
print("    landlord_evidence->", r4["landlord_evidence"])

print("\n[4] Pre-RRA standalone box")
r5 = record.build({"decision_url": GOV + "e",
    "title": "21 Kingsley Street, Birkenhead, Wirral CH41 0BQ: MAN/00BY/MNR/2019/0044",
    "decided_at": "2019-02-26"}, fx.PRE_RRA_ONE_PAGE, "")
approx("determined 675", r5["determined_rent_monthly"], 675.00)
check("city override (not Chester)", r5["city"], "Birkenhead")
check("RRA status", r5["rra_status"], "Pre-RRA")
check("can exceed ask", r5["tribunal_can_exceed_landlord_proposal"], "Yes")

print("\n[5] Weekly rents on the 52/12 basis")
r6 = record.build({"decision_url": GOV + "f",
    "title": "5 Alcester Road, Birmingham B13 8AT: BIR/00CN/MNR/2023/0099",
    "decided_at": "2023-05-04"}, fx.WEEKLY_CASE, "")
check("period flag", r6["original_rent_period"], "Weekly")
check("as stated keeps units", r6["original_rent_as_stated"], "£150.00 pw")
approx("150pw -> pcm", r6["original_rent_monthly"], 650.00)
approx("185pw -> pcm", r6["rent_sought_monthly"], 801.67)
approx("172pw -> pcm", r6["determined_rent_monthly"], 745.33)

print("\n[6] Withdrawn case takes no figure")
r7 = record.build({"decision_url": GOV + "g",
    "title": "14 Sea View Terrace, Brighton BN2 3PL: CHI/00HN/MNR/2024/0210",
    "decided_at": "2024-09-19"}, fx.WITHDRAWN_CASE, "")
check("outcome", r7["outcome_category"], "Withdrawn")
check("no determined rent", r7["determined_rent_monthly"], None)
approx("original still captured", r7["original_rent_monthly"], 1100.00)

print("\n[7] Workbook builds")
df = dataset.to_frame([r, r2, r3, r4, r5, r6, r7])
check("rows", len(df), 7)
check("columns", len(df.columns), len(record.COLUMNS))
check("summary builds", len(dataset.summary_frame(df)) > 0, True)
check("review tab builds", isinstance(dataset.review_frame(df), type(df)), True)
check("source tab builds", len(dataset.source_frame(df)) > 0, True)

passed, total = sum(results), len(results)
print(f"\n{'=' * 62}\n{passed}/{total} parser checks passed\n{'=' * 62}")
raise SystemExit(0 if passed == total else 1)
