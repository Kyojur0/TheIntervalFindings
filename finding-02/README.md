# Finding 02 — Where the recovery reaches

**Status:** ✅ Verified
**Series:** RTT · Specialties
**Article:** `/findings/02` on The Interval

This is the verified reproducibility pack for Finding 02. It covers 29 monthly
NHS England RTT observations from January 2024 through May 2026. Across seven
major elective specialties, the short end (within 18 weeks) improved more than
the over-52-week tail in absolute percentage-point terms, while the tail fell
further in relative terms.

## Contents

- `analysis/` — canonical Python analysis scripts
- `data/` — no large raw extracts are duplicated; see `SOURCES.md`
- `figures/` — verified charts from the analysis
- `outputs/` — verified derived CSV tables
- `SOURCES.md` — source URLs, manifest hashes, scope, and reproduction notes

## Reproduce

From the project root, ensure the manifest-listed extracts in
`data/rtt_monthly_series/` are present, then run:

```bash
cd final-uploads/finding-02
python analysis/make_figures.py
```

The scripts filter exact `Part_2` rows, exclude `NONC`, sum the weekly bands,
and write figures to `figures/` and derived tables to `outputs/`. Requires
Python 3.10+ with DuckDB, pandas, and matplotlib.

## Scope note

The February 2019 baseline uses the historical 52+ schema documented in the
manifest. Several recent monthly extracts were first releases when this
package was assembled and should be re-pulled after NHS England revisions.
