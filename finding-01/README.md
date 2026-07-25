# Finding 01 — The 18-week standard, becoming the exception

**Status:** In verification
**Series:** RTT · England
**Article:** `/findings/01` on The Interval

This folder is the reproducibility pack for Finding 01. Everything a reader
needs to reproduce every number published in the article lives here.

## Contents

- `analysis/` — the Python pipeline (DuckDB + pandas) that produces every figure and statistic
- `data/` — the raw NHS England RTT files used, or a `SOURCES.md` with direct links and download dates
- `figures/` — matplotlib outputs rendered to The Interval's figure specification
- `README.md` — this file

## Rules

- Every number in the article must be reproducible end-to-end from these files
- Quote the data vintage (publication month) next to every output
- If a figure appears in the article, the code that drew it is in `analysis/`
