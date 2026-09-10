"""Populate docs/data so the dashboard renders before the first real scrape."""
import sys, random, datetime as dt
from pathlib import Path
R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fixtures as fx
from rtscraper import record, dataset, geo

random.seed(7)
GOV = "https://www.gov.uk/residential-property-tribunal-decisions/"
base = [
    record.build({"decision_url": GOV+"a",
        "title": "4 Example Street, Manchester M14 5TG: MAN/00BU/MNR/2025/0690",
        "decided_at": "2025-07-28"}, fx.REAL_CASE_0690, ""),
    record.build({"decision_url": GOV+"b",
        "title": "Flat 3, 22 Example Gardens, London SE15 4TP: LON/00AH/MNR/2025/0412",
        "decided_at": "2025-05-19"}, fx.REAL_CASE_1300, ""),
    record.build({"decision_url": GOV+"c",
        "title": "5 Alcester Road, Birmingham B13 8AT: BIR/00CN/MNR/2023/0099",
        "decided_at": "2023-05-04"}, fx.WEEKLY_CASE, ""),
]
CITIES = [("London","SW8 1TJ"),("Manchester","M14 6LT"),("Birmingham","B13 8AT"),
          ("Leeds","LS6 2AA"),("Bristol","BS5 9QT"),("Birkenhead","CH41 0BQ"),
          ("Brighton and Hove","BN2 3PL"),("Nottingham","NG7 2FF"),
          ("Sheffield","S10 1FL"),("Newcastle upon Tyne","NE2 4AA")]
rows = list(base)
for i in range(260):
    r = dict(base[i % 3]); city, pc = random.choice(CITIES)
    d = dt.date(2024,1,1) + dt.timedelta(days=random.randint(0, 980))
    app = d - dt.timedelta(days=70)
    orig = round(random.uniform(420, 1900), 2)
    sought = round(orig * random.uniform(1.05, 1.45), 2)
    outcome = random.choices(["Determined","Rent confirmed","Withdrawn",
                             "No determination found"], [86,6,5,3])[0]
    det = round(orig * random.uniform(1.0, 1.32), 2) if outcome == "Determined" else None
    lat, lon = geo.latlon(pc)
    r.update({"case_reference": f"LON/00AY/MNR/{d.year}/{1000+i}", "city": city,
        "postcode": pc, "region": geo.city_from_postcode(pc)[1],
        "property": f"{random.randint(1,180)} Sample Road, {city} {pc}",
        "original_rent_monthly": orig, "rent_sought_monthly": sought,
        "landlord_proposed_rent_monthly": sought,
        "tenant_proposed_rent_monthly": round(orig*random.uniform(1.0,1.15),2),
        "determined_rent_monthly": det,
        "uplift_sought_pct": round((sought-orig)/orig*100,2),
        "uplift_determined_pct": round((det-orig)/orig*100,2) if det else None,
        "determined_vs_sought_pct": round((det-sought)/sought*100,2) if det else None,
        "decision_date": d.isoformat(), "decision_year": d.year,
        "decision_month": d.strftime("%Y-%m"), "application_date": app.isoformat(),
        "rra_status": "Post-RRA" if app >= dt.date(2026,5,1) else "Pre-RRA",
        "tribunal_can_exceed_landlord_proposal": "No" if app >= dt.date(2026,5,1) else "Yes",
        "outcome_category": outcome,
        "original_rent_period": random.choices(["Monthly","Weekly"],[80,20])[0],
        "parse_confidence": random.choices(["High","Medium","Low"],[74,20,6])[0],
        "rent_sanity_flag": "", "needs_review": "No",
        "lat": lat, "lon": lon,
        "decision_url": "https://www.gov.uk/residential-property-tribunal-decisions"})
    if r["parse_confidence"] == "Low":
        r["needs_review"] = "Yes"
    rows.append(r)

df = dataset.to_frame(rows)
dataset.write_dashboard_json(df)
dataset.write_excel(df, R / "output" / "SAMPLE_rental_tribunal_decisions_v5.xlsx")
print(f"sample built: {len(df)} rows")
