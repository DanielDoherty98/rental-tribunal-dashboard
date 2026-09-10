# RentalTribunalScraper V5.2

Scrapes section 13 rent determinations from
[GOV.UK residential property tribunal decisions](https://www.gov.uk/residential-property-tribunal-decisions?tribunal_decision_category%5B%5D=rents),
parses them into a correctly aligned dataset, and publishes an interactive
dashboard from `/docs` on GitHub Pages. Free and offline throughout.

**Read `WHAT_CHANGED_IN_V5.2.md` first** — it explains the two rent-figure
defects fixed in this version and how to apply the fix to data you already have.

**New here? Read `START_HERE.md`** and double-click the numbered `.bat` files.

---

## Reading the rent figures correctly

**Four-figure rents are no longer truncated.** The V5.0/V5.1 money pattern read
`£1300` as `130` because of ordered regex alternation with an optional comma
group. Fixed, with 36 regression tests.

**The boxed determination on pre-RRA forms is read properly.** PDFs are now
extracted layout-aware — positioned blocks grouped into visual rows — so

```
1.   The rent is   [ £1175 ]   [ per calendar month ]
```

arrives as one line. A dedicated numbered-box reader takes the amount box and
period box together, stops at the next numbered item, and copes when the `£`
glyph is lost by the extractor.

**Bad figures are visible, not silent.** `rent_sanity_flag` cross-checks the
original, sought and determined figures; `determined_rent_source` and
`determined_rent_context` show which rule produced each number and the exact
text behind it. Both feed `needs_review`, a workbook tab, and a dashboard filter.

---

## Columns

Identity `case_reference`, `case_type`, `tribunal_office`

Location `property`, `city`, `postcode`, `postcode_outward`, `region`

Parties `landlord_representative`, `landlord_is_organisation`,
`landlord_representative_detail`, `tenant_name`

Rent basis `original_rent_period`, `original_rent_as_stated`,
`original_rent_monthly`

Rent sought `rent_sought_as_stated`, `rent_sought_monthly`,
`uplift_sought_pct`, `tenant_proposed_rent_monthly`,
`landlord_proposed_rent_monthly` *(side by side)*

Determination `determined_rent_as_stated`, `determined_rent_monthly`,
`uplift_determined_pct`, `determined_vs_sought_pct`, `outcome_category`

Audit `determined_rent_source`, `determined_rent_context`, `rent_sanity_flag`,
`needs_review`, `parse_confidence`, `parse_flags`

Narrative `tenant_evidence`, `landlord_evidence`, `tribunal_reasoning`,
plus comparables counts and examples

Dates `application_date`, `section13_notice_date`, `hearing_date`,
`decision_date`, `effective_date`, `decision_year`, `decision_month`

RRA `rra_status`, `tribunal_can_exceed_landlord_proposal`, `rra_basis_date`,
`rra_basis_field`

---

## Command line

```bat
conda activate tribunal
pushd "<project folder>"

python doctor.py                  :: environment + money parsing check
python tests\test_money.py        :: 36 checks
python tests\test_parser.py       :: 46 checks
python tests\test_api_422.py      :: 12 checks
python run_all.py --check         :: confirm the API accepts our params
python run_all.py --test 10       :: small live test
python run_all.py --reparse       :: re-parse cached docs after a fix
python run_all.py                 :: full / incremental run
```

| Switch | Effect |
|---|---|
| `--reparse` | Rebuild every record from cached documents. No downloads |
| `--check` | Probe the API and exit |
| `--no-api` | Skip the Search API, use finder HTML only |
| `--test 25` | Parse only the newest 25 decisions |
| `--since 2026-01-01` | Only decisions on or after a date |
| `--full` | Ignore cached records entirely |

---

## Hosting on GitHub

1. Push to a repository on `main`.
2. **Settings → Pages → Source: GitHub Actions**.
3. **Settings → Actions → General → Workflow permissions → Read and write**.
4. **Actions → Weekly refresh → Run workflow**.

Live at `https://<username>.github.io/<repo>/`, refreshed every Monday 06:00 UTC.
All three test suites run *before* each scrape, so a parsing regression cannot
reach the published dashboard.

On GitHub's Free plan, Pages requires a **public** repository.

---

## Tuning

`config.py` — RRA commencement, weeks per year, offset ceiling, request delay.

`src/rtscraper/money.py` — the number pattern, with the bug note.

`src/rtscraper/boxes.py` — the numbered-box reader. If a form variant is missed,
add its wording to `RENT_LINE_RE`.

`src/rtscraper/patterns.py` — label vocabulary for the free-text fields.
