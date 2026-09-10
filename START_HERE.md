# START HERE

Never type a folder path. Every `.bat` finds its own location.

## If you already have scraped data

Your rents were affected by a parsing bug (see `WHAT_CHANGED_IN_V5.2.md`).
Copy your existing `data/` folder into this project, then run:

| Step | File | What it does |
|---|---|---|
| 1 | `1_SETUP.bat` | Creates the environment (~5 min, once) |
| 2 | `2_TEST_OFFLINE.bat` | 94 offline tests. Must all pass |
| 3 | `8_REPARSE_CACHED.bat` | **Re-parses cached documents with the fixed reader. No downloading.** |
| 4 | `5_VIEW_DASHBOARD.bat` | Check the corrected figures |

## Starting fresh

| # | File | Time |
|---|---|---|
| 1 | `1_SETUP.bat` | ~5 min, once |
| 2 | `2_TEST_OFFLINE.bat` | ~30 sec |
| 3 | `3_DIAGNOSE_API.bat` | ~30 sec — run this if you see a 422 |
| 4 | `4_TEST_SCRAPE_10.bat` | ~2 min |
| 5 | `5_VIEW_DASHBOARD.bat` | instant |
| 6 | `6_RUN_FULL_SCRAPE.bat` | several hours |
| 7 | `7_WEEKLY_REFRESH.bat` | minutes |
| 8 | `8_REPARSE_CACHED.bat` | after any parser fix |
| 9 | `9_SCRAPE_NO_API.bat` | fallback if a proxy blocks the API |

**If step 1 says conda was not found**, open **Anaconda Prompt** from the Start
menu — not PowerShell, not Command Prompt.

## Expected results

Step 2 must show `36/36`, `46/46`, then `12/12 checks passed`.

## Checking the rent figures

Open `output\rental_tribunal_decisions_v5.xlsx` and work through:

1. **Needs Review** — rows the model flagged as suspect, worst first. Each has
   `determined_rent_context` showing the exact text the figure came from.
2. **Rent Source** — how many rents came from the numbered box versus labels.
3. **Summary** — the "Rows needing review" count.

In the dashboard, flagged rows are hidden by default so they cannot skew the
medians. Untick "Hide rows needing review" to inspect them.
