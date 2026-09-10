"""Assemble one fully-typed record per decision, with an explicit column order."""
from __future__ import annotations

import datetime as _dt

import config
from . import parse as pr
from . import patterns as P
from . import geo
from . import periods as PD
from . import summarise as sm

COLUMNS = [
    "case_reference", "case_type", "tribunal_office",
    "property", "city", "postcode", "postcode_outward", "region",
    "landlord_representative", "landlord_is_organisation",
    "landlord_representative_detail", "tenant_name",
    "original_rent_period", "original_rent_as_stated", "original_rent_monthly",
    "rent_sought_as_stated", "rent_sought_monthly", "uplift_sought_pct",
    "tenant_proposed_rent_monthly", "landlord_proposed_rent_monthly",
    "determined_rent_as_stated", "determined_rent_monthly",
    "uplift_determined_pct", "determined_vs_sought_pct", "outcome_category",
    "weeks_per_year", "conversion_method",
    "tenant_evidence", "tenant_comparables_count", "tenant_comparables_examples",
    "landlord_evidence", "landlord_comparables_count", "landlord_comparables_examples",
    "tribunal_reasoning",
    "application_date", "section13_notice_date", "hearing_date",
    "decision_date", "effective_date", "decision_year", "decision_month",
    "rra_status", "tribunal_can_exceed_landlord_proposal",
    "rra_basis_date", "rra_basis_field",
    "form_type", "decision_url", "document_url",
    "determined_rent_source", "determined_rent_context",
    "rent_sanity_flag", "needs_review",
    "parse_confidence", "parse_flags", "lat", "lon", "text_chars",
    "model_version", "scraped_at",
]


def _pct(new, old):
    return None if (new is None or not old) else round((new - old) / old * 100.0, 2)


def _confidence(det, orig, sought, ref, postcode, sanity) -> str:
    score = (2 if det is not None else 0) + (1 if orig is not None else 0) \
        + (1 if sought is not None else 0) + (1 if ref else 0) + (1 if postcode else 0)
    if sanity:
        score -= 3
    return "High" if score >= 5 else ("Medium" if score >= 3 else "Low")


def build(meta: dict, text: str, doc_url: str) -> dict:
    url, title = meta.get("decision_url", ""), meta.get("title", "")
    flags: list[str] = []

    ref = pr.case_reference(text, url, title)
    if not ref:
        flags.append("no_case_reference")

    app_d, _ = pr.date_near(text, P.L_APPLICATION_DATE)
    notice_d, _ = pr.date_near(text, P.L_NOTICE_DATE)
    hear_d, _ = pr.date_near(text, P.L_HEARING_DATE)
    dec_d, _ = pr.date_near(text, P.L_DECISION_DATE)
    eff_d, _ = pr.date_near(text, P.L_EFFECTIVE)
    if dec_d is None and meta.get("decided_at"):
        dec_d = pr.parse_date(meta["decided_at"])
    if dec_d is None:
        flags.append("no_decision_date")

    pre_rra = bool(dec_d and dec_d < config.NEW_FORM_FROM)
    form_type = "Pre-RRA single-page form" if (pre_rra or len(text) < 2500) \
        else "Post-RRA full decision form"

    sections = pr.split_sections(text)
    addr = pr.property_address(title, text)
    g = geo.resolve(addr, text[:4000])
    if not g["postcode"]:
        flags.append("no_postcode")
    if not g["city"]:
        flags.append("no_city")

    ll_name, ll_rep = pr.extract_party(text, P.L_LANDLORD, P.L_LANDLORD_REP)
    tn_name, _ = pr.extract_party(text, P.L_TENANT)
    if not ll_name:
        flags.append("no_landlord_name")

    r = pr.extract_rents(text, sections, pre_rra)
    orig_m = PD.to_monthly(r["original_rent_value"], r["original_rent_period"])
    sought_m = PD.to_monthly(r["landlord_proposed_value"], r["landlord_proposed_period"])
    tenant_m = PD.to_monthly(r["tenant_proposed_value"], r["tenant_proposed_period"])
    det_m = PD.to_monthly(r["determined_rent_value"], r["determined_rent_period"])

    if orig_m is None:
        flags.append("no_original_rent")
    if sought_m is None:
        flags.append("no_rent_sought")
    if det_m is None:
        flags.append("no_determined_rent")

    sanity = pr.sanity_check(orig_m, sought_m, det_m)
    outcome = pr.outcome(text, r["determined_rent_value"])

    t_sum = sm.party_evidence_summary("tenant", sections.get("tenant_evidence", ""), tenant_m)
    l_sum = sm.party_evidence_summary("landlord", sections.get("landlord_evidence", ""), sought_m)
    t_text = sm.maybe_llm("tenant's evidence", sections.get("tenant_evidence", ""), t_sum["summary"])
    l_text = sm.maybe_llm("landlord's evidence", sections.get("landlord_evidence", ""), l_sum["summary"])
    reasoning = sm.reasoning_summary(sections.get("reasoning", ""), det_m, orig_m, outcome)
    rra = pr.rra_flags(app_d, notice_d, dec_d)

    confidence = _confidence(det_m, orig_m, sought_m, ref, g["postcode"], sanity)

    return {
        "case_reference": ref,
        "case_type": pr.case_type(ref) or meta.get("sub_category", ""),
        "tribunal_office": pr.tribunal_office(ref),
        "property": addr, "city": g["city"], "postcode": g["postcode"],
        "postcode_outward": g["postcode_outward"], "region": g["region"],
        "landlord_representative": ll_name,
        "landlord_is_organisation": ("Organisation" if pr.is_organisation(ll_name)
                                    else ("Individual" if ll_name else "")),
        "landlord_representative_detail": ll_rep, "tenant_name": tn_name,
        "original_rent_period": r["original_rent_period"],
        "original_rent_as_stated": PD.as_stated(r["original_rent_value"], r["original_rent_period"]),
        "original_rent_monthly": orig_m,
        "rent_sought_as_stated": PD.as_stated(r["landlord_proposed_value"], r["landlord_proposed_period"]),
        "rent_sought_monthly": sought_m,
        "uplift_sought_pct": _pct(sought_m, orig_m),
        "tenant_proposed_rent_monthly": tenant_m,
        "landlord_proposed_rent_monthly": sought_m,
        "determined_rent_as_stated": PD.as_stated(r["determined_rent_value"], r["determined_rent_period"]),
        "determined_rent_monthly": det_m,
        "uplift_determined_pct": _pct(det_m, orig_m),
        "determined_vs_sought_pct": _pct(det_m, sought_m),
        "outcome_category": outcome,
        "weeks_per_year": config.WEEKS_PER_YEAR,
        "conversion_method": config.CONVERSION_METHOD,
        "tenant_evidence": t_text,
        "tenant_comparables_count": t_sum["comparables_count"],
        "tenant_comparables_examples": t_sum["comparables_examples"],
        "landlord_evidence": l_text,
        "landlord_comparables_count": l_sum["comparables_count"],
        "landlord_comparables_examples": l_sum["comparables_examples"],
        "tribunal_reasoning": reasoning,
        "application_date": pr.iso(app_d),
        "section13_notice_date": pr.iso(notice_d),
        "hearing_date": pr.iso(hear_d),
        "decision_date": pr.iso(dec_d),
        "effective_date": pr.iso(eff_d),
        "decision_year": dec_d.year if dec_d else None,
        "decision_month": dec_d.strftime("%Y-%m") if dec_d else "",
        **rra,
        "form_type": form_type, "decision_url": url, "document_url": doc_url,
        "determined_rent_source": r["determined_rent_source"],
        "determined_rent_context": (r.get("determined_rent_context") or "")[:300],
        "rent_sanity_flag": sanity,
        "needs_review": "Yes" if (sanity or confidence == "Low") else "No",
        "parse_confidence": confidence,
        "parse_flags": ";".join(flags),
        "lat": g["lat"], "lon": g["lon"], "text_chars": len(text),
        "model_version": config.MODEL_VERSION,
        "scraped_at": _dt.datetime.now().isoformat(timespec="seconds"),
    }
