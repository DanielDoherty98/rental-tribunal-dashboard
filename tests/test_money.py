"""
Money regex regression tests.

Test group [1] is the important one. It locks in the V5.0/V5.1 truncation bug
that produced £1300 -> 130 and £1175 -> 117. If anyone reverts the pattern to
the old ordered alternation, these fail immediately.

Run:  python tests/test_money.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))

from rtscraper import money as M            # noqa: E402
from rtscraper import periods as PD         # noqa: E402

results = []


def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got!r}" +
          ("" if ok else f"  (expected {want!r})"))
    results.append(ok)


def first(text, loose=False):
    hits = M.find_all(text, loose=loose)
    return hits[0][0] if hits else None


print("\n[1] THE TRUNCATION BUG - four-figure rents without a comma")
print("    (£1300 was being read as 130, £1175 as 117)")
for text, want in [("£1300", 1300.0), ("£1175", 1175.0), ("£1250", 1250.0),
                   ("£2400", 2400.0), ("£12500", 12500.0), ("£9999", 9999.0),
                   ("£1000", 1000.0), ("£1300 per calendar month", 1300.0),
                   ("the rent is £1175 per month", 1175.0)]:
    check(text, first(text), want)

print("\n[2] Comma-formatted and decimal amounts still work")
for text, want in [("£1,300", 1300.0), ("£1,050.00", 1050.0), ("£985.00", 985.0),
                   ("£675", 675.0), ("£12,500.50", 12500.5), ("£150", 150.0),
                   ("£1,234,567", 1234567.0)]:
    check(text, first(text), want)

print("\n[3] Whole number is consumed - no partial matches")
for text in ["£1300", "£1175", "£12500"]:
    hits = M.find_all(text)
    check(f"{text} yields exactly one match", len(hits), 1)

print("\n[4] Strict mode requires the pound sign")
check("bare 1300 ignored in strict mode", first("1300"), None)
check("bare 1300 found in loose mode", first("1300", loose=True), 1300.0)

print("\n[5] looks_like_rent rejects non-rents")
check("year 2025 rejected", M.looks_like_rent(2025.0, "2025", "decided in 2025"), False)
check("case number context rejected",
      M.looks_like_rent(690.0, "690", "Case Reference MAN/00BU/MNR/2025/0690"), False)
check("paragraph reference rejected",
      M.looks_like_rent(13.0, "13", "under section 13 of the Act"), False)
check("real rent accepted",
      M.looks_like_rent(1175.0, "1175", "the rent is 1175 per calendar month"), True)
check("absurdly high rejected", M.looks_like_rent(99000.0, "99000", "rent"), False)

print("\n[6] Conversions on the 52/12 basis")
check("150 weekly -> pcm", PD.to_monthly(150, "Weekly"), 650.0)
check("1175 monthly passthrough", PD.to_monthly(1175, "Monthly"), 1175.0)
check("12000 annual -> pcm", PD.to_monthly(12000, "Annual"), 1000.0)
check("300 fortnightly -> pcm", PD.to_monthly(300, "Fortnightly"), 650.0)

print("\n[7] Period detection")
for text, want in [("£1300 per calendar month", "Monthly"), ("£150 per week", "Weekly"),
                   ("£1300 pcm", "Monthly"), ("£150 pw", "Weekly"),
                   ("£15600 per annum", "Annual"), ("£600 per fortnight", "Fortnightly")]:
    check(text, PD.detect(text), want)

passed, total = sum(results), len(results)
print(f"\n{'=' * 62}\n{passed}/{total} money checks passed\n{'=' * 62}")
raise SystemExit(0 if passed == total else 1)
