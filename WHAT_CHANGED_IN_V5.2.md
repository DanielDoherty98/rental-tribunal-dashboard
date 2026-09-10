# What changed in V5.2 — the rent figures

Two defects were making the rent columns unreliable. Both are fixed, and both
now have permanent regression tests that run before any scrape.

---

## Defect 1 — four-figure rents were being truncated

**Symptom you saw:** a decision stating £1300 was recorded as **£130**.

**Cause.** The money pattern was:

```
£\s?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)
```

Regex alternation is *ordered*, and the comma group used `*` (zero or more).
For `£1300` the first branch matched `130` and succeeded — the engine never
tried the second branch. Every rent written without a thousands separator lost
its last digit:

| Text | Recorded | Should be |
|---|---|---|
| £1300 | 130 | 1300 |
| £1175 | 117 | 1175 |
| £12500 | 125 | 12500 |
| £1,300 | 1,300 ✓ | *(comma form was unaffected)* |

Because 130 is still a "plausible" number, it was written to the workbook with
no warning. This is why some rents looked fine and others were nonsense — the
difference was purely whether the tribunal typed a comma.

**Fix.** Branch one now *requires* at least one comma group (`+` not `*`), so
it can only match a fully comma-formatted number; otherwise the plain-digit
branch runs and consumes every digit. Lookarounds prevent starting or ending
mid-number.

```
£\s?((?<![\d.,])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?)(?!\d)
```

---

## Defect 2 — the boxed determination on pre-RRA forms was missed

**Symptom you saw:** MAN/00BU/MNR/2025/0690 got no determined rent at all,
despite the form clearly stating "the rent is £1175 per month".

**Cause.** Older decisions are a one-page form where the operative figure sits
in boxes beside a numbered item:

```
1.   The rent is        [ £1175 ]   [ per calendar month ]
```

The parser only did free-text label matching. PDF extraction flattens that
table unpredictably — sometimes one line, sometimes one cell per line, and the
`£` glyph is often lost entirely — so the figure was frequently unreachable.

**Fix, in two parts.**

*Layout-aware PDF extraction.* Text is now read as positioned blocks, grouped
into visual rows by vertical overlap, and joined left-to-right. The three boxes
above come out as a single line instead of scattered fragments.

*A numbered-box reader* (`src/rtscraper/boxes.py`). It finds the numbered item,
reads the amount box and the period box **together** as you described, stops at
the next numbered item so item 2's fee figure can't be picked up, and accepts a
bare number when the `£` has been lost — guarded so years, case numbers and
paragraph references are rejected.

On the pre-RRA form the numbered box is now tried **first**, because it is the
authoritative statement of the decision.

---

## New: bad figures are now visible instead of silent

The deeper problem was that a wrong number looked exactly like a right one. Two
additions fix that.

**`rent_sanity_flag`** cross-checks the three figures against each other. A
determined rent less than half the original, or more than triple it, or an
implausibly low value, raises a flag. The £130-against-£1100 case would have
been caught immediately by `determined_far_below_original`.

**`determined_rent_source` and `determined_rent_context`** record which rule
found the figure and the exact text it came from, so any number can be audited
in seconds.

These feed a **`needs_review`** column, a new **Needs Review** tab in the
workbook, and a dashboard filter that hides flagged rows by default so they
cannot skew your medians.

---

## Apply the fix to data you have already scraped

You do **not** need to re-download anything. Documents are cached, so:

```bat
8_REPARSE_CACHED.bat
```

or `python run_all.py --reparse`. This rebuilds every record from the files
already on disk — minutes, not hours — and corrected rents appear across the
whole dataset.

---

## Verifying it

```bat
2_TEST_OFFLINE.bat
```

runs three suites: **36 money checks**, **46 parser checks**, **12 API checks**.
The parser suite includes both cases you reported, by reference, so they can
never silently regress. The GitHub workflow runs all three before each weekly
scrape, so a broken parser cannot reach the published dashboard.

After re-parsing, open the workbook and check in this order:

1. **Needs Review** — anything the model is unsure about, worst first
2. **Rent Source** — how many rents came from the numbered box versus labels
3. **Summary** — the "Rows needing review" count
