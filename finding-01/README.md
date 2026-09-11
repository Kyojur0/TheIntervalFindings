# Finding 01 — Sixty points within one specialty

**Status:** ✅ Verified
**Series:** RTT · England
**Article:** `/findings/01` on The Interval

This is the verified reproducibility pack for Finding 01. Among 119 provider
codes with at least 500 incomplete gastroenterology pathways in April 2026,
within-18-week performance ranges from 37.3% to 97.7% (a 60.4 percentage-point
spread). The spread remains after provider-size controls.

## Contents

- `analysis/` — canonical Python analysis and independent audit scripts
- `data/` — no large raw extract is duplicated; see `SOURCES.md`
- `figures/` — verified charts from the analysis
- `outputs/` — verified derived CSV tables
- `SOURCES.md` — source URLs, local paths, hashes, scope, and reproduction notes

## Reproduce

From the project root, ensure the raw extracts listed in `SOURCES.md` are
present, then run:

```bash
cd final-uploads/finding-01
python analysis/make_figures.py
```

The scripts filter exact `Part_2` rows, exclude `NONC`, sum the weekly bands,
and write figures to `figures/` and derived tables to `outputs/`. Requires
Python 3.10+ with DuckDB, pandas, and matplotlib.

## Scope note

The April 2026 extract was a first-release file when this package was
assembled and may later be revised by NHS England. Recheck against a revised
release when available.
