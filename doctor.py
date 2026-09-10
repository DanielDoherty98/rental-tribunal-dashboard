"""Environment diagnostic.  python doctor.py"""
from __future__ import annotations

import importlib
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "src"))

OK, BAD, WARN = "  [ OK ]", "  [FAIL]", "  [warn]"
problems: list[str] = []
warnings: list[str] = []


def line(title):
    print(f"\n{title}\n" + "-" * 62)


line("1. Interpreter")
print(f"  Python    : {sys.version.split()[0]}")
print(f"  Platform  : {platform.system()} {platform.release()}")
print(f"  Executable: {sys.executable}")
if sys.version_info < (3, 9):
    problems.append("Python is older than 3.9. Recreate the env with python=3.11.")

line("2. Project folder")
print(f"  Location: {HERE}")
for rel in ["config.py", "run_all.py", "src/rtscraper/money.py",
            "src/rtscraper/boxes.py", "docs/index.html",
            "tests/test_money.py", "tests/test_parser.py"]:
    ok = (HERE / rel).exists()
    print(f"{OK if ok else BAD} {rel}")
    if not ok:
        problems.append(f"Missing {rel} - you may be one folder level out.")

line("3. Dependencies")
for mod, pkg in [("requests", "requests"), ("bs4", "beautifulsoup4"), ("lxml", "lxml"),
                 ("pandas", "pandas"), ("openpyxl", "openpyxl"),
                 ("dateutil", "python-dateutil"), ("tqdm", "tqdm")]:
    try:
        importlib.import_module(mod); print(f"{OK} {pkg}")
    except ImportError:
        print(f"{BAD} {pkg}")
        problems.append(f"Missing {pkg}. Run: pip install -r requirements.txt")

pdf_ok = False
for mod, pkg in [("fitz", "pymupdf"), ("pdfminer", "pdfminer.six")]:
    try:
        importlib.import_module(mod); print(f"{OK} {pkg} (PDF reader)"); pdf_ok = True
    except ImportError:
        print(f"       {pkg} not installed")
if not pdf_ok:
    problems.append("No PDF reader. Run: pip install pymupdf pdfminer.six")

line("4. Project modules")
try:
    import config
    from rtscraper import parse, geo, record, dataset, extract, boxes, money, periods  # noqa: F401
    print(f"{OK} all modules import cleanly")
    print(f"  Model version   : {config.MODEL_VERSION}")
    print(f"  Weeks per year  : {config.WEEKS_PER_YEAR}")
    print(f"  RRA commencement: {config.RRA_COMMENCEMENT}")
except Exception as exc:  # noqa: BLE001
    print(f"{BAD} import failed: {exc}")
    problems.append(f"Module import failed: {exc}")

line("5. Money parsing (the V5.1 truncation bug)")
try:
    from rtscraper import money as M, periods as PD, boxes as BX
    for text, want in [("£1300", 1300.0), ("£1175", 1175.0), ("£12500", 12500.0),
                       ("£1,050.00", 1050.0), ("£675", 675.0)]:
        hits = M.find_all(text)
        got = hits[0][0] if hits else None
        good = got == want
        print(f"{OK if good else BAD} {text} -> {got}")
        if not good:
            problems.append(f"Money parsing wrong for {text}: got {got}, expected {want}")

    for name, got, want in [("weekly 150 -> pcm", PD.to_monthly(150, "Weekly"), 650.0),
                            ("annual 12000 -> pcm", PD.to_monthly(12000, "Annual"), 1000.0)]:
        good = abs(got - want) < 0.01
        print(f"{OK if good else BAD} {name}: {got}")
        if not good:
            problems.append(f"Conversion wrong for {name}")

    v, p, _, sc = BX.read_numbered_box("1.   The rent is   £1175   per calendar month")
    good = v == 1175.0 and p == "Monthly"
    print(f"{OK if good else BAD} numbered box reads £{v} {p}")
    if not good:
        problems.append("The numbered-box reader is not working.")
except Exception as exc:  # noqa: BLE001
    print(f"{BAD} {exc}")
    problems.append(str(exc))

line("6. Geography")
try:
    from rtscraper import geo
    g = geo.resolve("21 Kingsley Street, Birkenhead, Wirral CH41 0BQ")
    good = g["postcode"] == "CH41 0BQ" and g["city"] == "Birkenhead"
    print(f"{OK if good else BAD} {g['postcode']} -> {g['city']}")
    if not good:
        problems.append("Postcode-to-city mapping is not working.")
except Exception as exc:  # noqa: BLE001
    print(f"{BAD} {exc}"); problems.append(str(exc))

line("7. Write permissions")
for folder in ["data", "output", "docs/data"]:
    p = HERE / folder
    try:
        p.mkdir(parents=True, exist_ok=True)
        probe = p / ".write_test"; probe.write_text("ok", encoding="utf-8"); probe.unlink()
        print(f"{OK} {folder} is writable")
    except Exception as exc:  # noqa: BLE001
        print(f"{BAD} {folder}: {exc}")
        problems.append(f"Cannot write to {folder}.")

line("8. Network reachability (optional)")
try:
    import requests
    r = requests.get("https://www.gov.uk/api/search.json",
                     params={"filter_format": "residential_property_tribunal_decision",
                             "count": 1},
                     headers={"User-Agent": "RentalTribunalScraper/5.2 doctor"},
                     timeout=20)
    if r.ok:
        print(f"{OK} gov.uk reachable - {r.json().get('total', '?')} decisions visible")
    else:
        print(f"{WARN} gov.uk returned status {r.status_code}")
        warnings.append(f"gov.uk returned {r.status_code}. Offline stages unaffected.")
except Exception as exc:  # noqa: BLE001
    print(f"{WARN} network check skipped: {type(exc).__name__}")
    warnings.append("Network check could not run. Offline stages unaffected.")

print("\n" + "=" * 62)
if warnings:
    print(f"{len(warnings)} warning(s):\n")
    for i, w in enumerate(warnings, 1):
        print(f"  {i}. {w}")
    print()
if problems:
    print(f"{len(problems)} blocking issue(s):\n")
    for i, p in enumerate(problems, 1):
        print(f"  {i}. {p}")
    raise SystemExit(1)
print("Environment is healthy.")
raise SystemExit(0)
