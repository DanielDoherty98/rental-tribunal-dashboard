"""Stage 5 - Excel workbook (multi-tab), CSV, and the dashboard JSON payload."""
from __future__ import annotations

import json

import pandas as pd

import config
from .record import COLUMNS

DICTIONARY = [
    ("case_reference", "Tribunal case reference, e.g. MAN/00BU/MNR/2025/0690."),
    ("case_type", "From the third block of the case reference (MNR = section 13 market rent)."),
    ("tribunal_office", "From the first block of the case reference."),
    ("property", "Property address exactly as published by gov.uk."),
    ("city", "Major city/town from the postcode (district overrides first, then postcode area)."),
    ("postcode", "Postcode found in the address, OCR-corrected and normalised."),
    ("region", "Statistical region derived from the postcode area."),
    ("landlord_representative", "Organisation name if the landlord is a company, otherwise the person's name."),
    ("original_rent_period", "Whether the original rent was Weekly, Monthly, Fortnightly, Four-weekly, Quarterly or Annual."),
    ("original_rent_as_stated", "Original rent in the units used in the decision."),
    ("original_rent_monthly", "Original rent converted to a monthly figure."),
    ("rent_sought_as_stated", "Rent sought by the landlord in the section 13 notice, as stated."),
    ("rent_sought_monthly", "Rent sought converted to a monthly figure."),
    ("uplift_sought_pct", "(rent sought - original) / original, as a percentage."),
    ("tenant_proposed_rent_monthly", "Monthly rent proposed by the tenant, where one was put forward."),
    ("landlord_proposed_rent_monthly", "Same as rent_sought_monthly, beside the tenant's for comparison."),
    ("determined_rent_as_stated", "Rent determined by the tribunal, as stated."),
    ("determined_rent_monthly", "Determined rent converted to a monthly figure."),
    ("uplift_determined_pct", "(determined - original) / original, as a percentage."),
    ("determined_vs_sought_pct", "(determined - sought) / sought. Negative = below the landlord's ask."),
    ("outcome_category", "Determined / Rent confirmed / Withdrawn / Struck out / Invalid notice / Dismissed / No determination found."),
    ("weeks_per_year", f"{config.WEEKS_PER_YEAR} - the divisor basis, held constant."),
    ("conversion_method", config.CONVERSION_METHOD),
    ("tenant_evidence", "Comparables; the rent the tenant proposed; a descriptor of the evidence."),
    ("landlord_evidence", "Same structure as tenant_evidence, for the landlord."),
    ("tribunal_reasoning", "Concise summary of the reasons plus the determined figure and movement."),
    ("application_date", "Date the section 13 referral/application was made."),
    ("section13_notice_date", "Date of the landlord's section 13 notice."),
    ("rra_status", "Pre-RRA or Post-RRA, against the commencement date in config.py."),
    ("tribunal_can_exceed_landlord_proposal", "Yes for pre-RRA applications; No for post-RRA."),
    ("rra_basis_field", "Which date drove the RRA test: application, notice, or decision date as proxy."),
    ("form_type", "Pre-RRA single-page form or post-RRA full decision form."),
    ("determined_rent_source", "Which rule recovered the determined rent. 'numbered_box' means it was read from the boxes beside item 1 on the form."),
    ("determined_rent_context", "The exact text the determined rent was read from. Use this to audit any figure that looks wrong."),
    ("rent_sanity_flag", "Cross-check warnings, e.g. determined_far_below_original. Empty means the figures are internally consistent."),
    ("needs_review", "Yes when a sanity flag fired or confidence is Low. Filter on this first."),
    ("parse_confidence", "High / Medium / Low, based on fields recovered and sanity checks."),
    ("parse_flags", "Semicolon-separated list of fields that could not be recovered."),
    ("model_version", "Scraper version that produced the row."),
]

NUMERIC = ["original_rent_monthly", "rent_sought_monthly", "uplift_sought_pct",
           "tenant_proposed_rent_monthly", "landlord_proposed_rent_monthly",
           "determined_rent_monthly", "uplift_determined_pct",
           "determined_vs_sought_pct", "lat", "lon"]


def to_frame(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = None
    df = df[COLUMNS]
    for c in NUMERIC:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.sort_values("decision_date", ascending=False, na_position="last")


def _agg(df: pd.DataFrame, by: str) -> pd.DataFrame:
    d = df[df[by].astype(str).str.len() > 0]
    if d.empty:
        return pd.DataFrame()
    return d.groupby(by).agg(
        decisions=("case_reference", "count"),
        determined=("determined_rent_monthly", "count"),
        median_original_pcm=("original_rent_monthly", "median"),
        median_sought_pcm=("rent_sought_monthly", "median"),
        median_determined_pcm=("determined_rent_monthly", "median"),
        median_uplift_sought_pct=("uplift_sought_pct", "median"),
        median_uplift_determined_pct=("uplift_determined_pct", "median"),
        median_determined_vs_sought_pct=("determined_vs_sought_pct", "median"),
    ).round(2).reset_index().sort_values("decisions", ascending=False)


def summary_frame(df: pd.DataFrame) -> pd.DataFrame:
    det = df["determined_rent_monthly"].dropna()
    rows = [
        ("Model version", config.MODEL_VERSION),
        ("Decisions scraped", len(df)),
        ("Decisions with a determined rent", int(det.count())),
        ("Determined-rent capture rate", f"{det.count() / max(len(df), 1) * 100:.1f}%"),
        ("Rows needing review", int((df["needs_review"] == "Yes").sum())),
        ("Rows with a sanity flag", int(df["rent_sanity_flag"].astype(str).str.len().gt(0).sum())),
        ("High-confidence records", int((df["parse_confidence"] == "High").sum())),
        ("Read from the numbered box", int(df["determined_rent_source"].astype(str)
                                           .str.startswith("numbered_box").sum())),
        ("Cities identified", int(df["city"].astype(str).str.len().gt(0).sum())),
        ("Pre-RRA applications", int((df["rra_status"] == "Pre-RRA").sum())),
        ("Post-RRA applications", int((df["rra_status"] == "Post-RRA").sum())),
        ("Weekly-basis original rents", int((df["original_rent_period"] == "Weekly").sum())),
        ("Monthly-basis original rents", int((df["original_rent_period"] == "Monthly").sum())),
        ("Median original rent (pcm)", round(df["original_rent_monthly"].median(), 2)),
        ("Median rent sought (pcm)", round(df["rent_sought_monthly"].median(), 2)),
        ("Median determined rent (pcm)", round(det.median(), 2) if len(det) else None),
        ("Median uplift sought (%)", round(df["uplift_sought_pct"].median(), 2)),
        ("Median uplift determined (%)", round(df["uplift_determined_pct"].median(), 2)),
        ("Median determined vs sought (%)", round(df["determined_vs_sought_pct"].median(), 2)),
        ("Earliest decision", df["decision_date"].replace("", None).dropna().min()),
        ("Latest decision", df["decision_date"].replace("", None).dropna().max()),
    ]
    return pd.DataFrame(rows, columns=["Metric", "Value"])


def review_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Rows to check by hand, worst first. Includes the source text."""
    d = df[df["needs_review"] == "Yes"].copy()
    if d.empty:
        return pd.DataFrame(columns=["case_reference", "property", "rent_sanity_flag"])
    cols = ["case_reference", "property", "city", "original_rent_monthly",
            "rent_sought_monthly", "determined_rent_monthly", "rent_sanity_flag",
            "parse_flags", "determined_rent_source", "determined_rent_context",
            "parse_confidence", "decision_url"]
    return d[cols].sort_values("rent_sanity_flag", ascending=False)


def rra_frame(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["rra_status"].isin(["Pre-RRA", "Post-RRA"])].copy()
    if d.empty:
        return pd.DataFrame()
    d["determined_above_landlord_ask"] = d["determined_rent_monthly"] > d["rent_sought_monthly"]
    return d.groupby("rra_status").agg(
        decisions=("case_reference", "count"),
        median_uplift_sought_pct=("uplift_sought_pct", "median"),
        median_uplift_determined_pct=("uplift_determined_pct", "median"),
        median_determined_vs_sought_pct=("determined_vs_sought_pct", "median"),
        cases_determined_above_landlord_ask=("determined_above_landlord_ask", "sum"),
    ).round(2).reset_index()


def quality_frame(df: pd.DataFrame) -> pd.DataFrame:
    flags = (df["parse_flags"].fillna("").str.split(";").explode()
             .str.strip().replace("", None).dropna())
    sanity = (df["rent_sanity_flag"].fillna("").str.split(";").explode()
              .str.strip().replace("", None).dropna())
    both = pd.concat([flags, sanity])
    if both.empty:
        return pd.DataFrame(columns=["issue", "records", "share_pct"])
    q = both.value_counts().reset_index()
    q.columns = ["issue", "records"]
    q["share_pct"] = (q["records"] / len(df) * 100).round(1)
    return q


def source_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Which rule found each determined rent - shows the box reader's value."""
    s = df["determined_rent_source"].fillna("").replace("", "not found")
    s = s.str.replace(r"\(score=\d+\)", "", regex=True)
    q = s.value_counts().reset_index()
    q.columns = ["determined_rent_source", "records"]
    q["share_pct"] = (q["records"] / len(df) * 100).round(1)
    return q


def write_excel(df: pd.DataFrame, path=None):
    path = path or (config.OUTPUT / "rental_tribunal_decisions_v5.xlsx")
    with pd.ExcelWriter(path, engine="openpyxl") as xl:
        df.to_excel(xl, sheet_name="Decisions", index=False)
        summary_frame(df).to_excel(xl, sheet_name="Summary", index=False)
        review_frame(df).to_excel(xl, sheet_name="Needs Review", index=False)
        _agg(df, "city").to_excel(xl, sheet_name="By City", index=False)
        _agg(df, "region").to_excel(xl, sheet_name="By Region", index=False)
        _agg(df, "decision_month").to_excel(xl, sheet_name="By Month", index=False)
        _agg(df, "outcome_category").to_excel(xl, sheet_name="By Outcome", index=False)
        rra_frame(df).to_excel(xl, sheet_name="RRA Comparison", index=False)
        quality_frame(df).to_excel(xl, sheet_name="Parse Quality", index=False)
        source_frame(df).to_excel(xl, sheet_name="Rent Source", index=False)
        pd.DataFrame(DICTIONARY, columns=["Column", "Definition"]).to_excel(
            xl, sheet_name="Data Dictionary", index=False)
        for ws in xl.book.worksheets:
            ws.freeze_panes = "A2"
            for col in ws.columns:
                w = max((len(str(c.value)) for c in col[:200] if c.value), default=10)
                ws.column_dimensions[col[0].column_letter].width = min(max(w + 2, 10), 60)
    print(f"[write] {path}")
    return path


def write_csv(df: pd.DataFrame, path=None):
    path = path or (config.OUTPUT / "rental_tribunal_decisions_v5.csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[write] {path}")
    return path


DASH_COLS = [
    "case_reference", "property", "city", "postcode", "region",
    "landlord_representative", "landlord_is_organisation",
    "original_rent_period", "original_rent_monthly", "rent_sought_monthly",
    "uplift_sought_pct", "tenant_proposed_rent_monthly",
    "landlord_proposed_rent_monthly", "determined_rent_monthly",
    "uplift_determined_pct", "determined_vs_sought_pct", "outcome_category",
    "tenant_evidence", "landlord_evidence", "tribunal_reasoning",
    "application_date", "decision_date", "decision_month", "decision_year",
    "rra_status", "tribunal_can_exceed_landlord_proposal",
    "decision_url", "parse_confidence", "needs_review", "rent_sanity_flag",
    "lat", "lon",
]


def write_dashboard_json(df: pd.DataFrame):
    slim = df[DASH_COLS].copy()
    slim = slim.where(pd.notnull(slim), None)
    payload = {
        "generated_at": pd.Timestamp.utcnow().isoformat(timespec="seconds"),
        "model_version": config.MODEL_VERSION,
        "rra_commencement": config.RRA_COMMENCEMENT.isoformat(),
        "weeks_per_year": config.WEEKS_PER_YEAR,
        "conversion_method": config.CONVERSION_METHOD,
        "count": int(len(slim)), "columns": DASH_COLS,
        "rows": json.loads(slim.to_json(orient="records")),
    }
    path = config.DOCS_DATA / "decisions.json"
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    (config.DOCS_DATA / "summary.json").write_text(
        summary_frame(df).to_json(orient="records"), encoding="utf-8")
    print(f"[write] {path} ({path.stat().st_size / 1e6:.2f} MB)")
    return path
