# Finding 03 — The same names, month after month

**Status:** Verified
**Series:** RTT · Provider persistence
**Article:** `/findings/03` on The Interval

Finding 01 measured a sixty-point gap between providers in a single month and
said, honestly, that it could not tell whether the same providers stayed at the
top and bottom over time. This is that analysis.

Across 29 monthly files and four treatment functions — Gastroenterology
(`C_301`), Ophthalmology (`C_130`), Ear, Nose and Throat (`C_120`) and Trauma
and Orthopaedics (`C_110`) — the spread turns out to be a durable property of
providers rather than monthly noise, in every specialty tested.

## Contents

- `analysis/` — the pipeline, the figure spec and the figure code
- `data/` — `SOURCES.md`; the monthly extracts are referenced, not duplicated
- `figures/` — light and dark renders of every published figure
- `outputs/` — every derived table quoted in the article

## Reproducing it

```bash
python analysis/finding_03_pipeline.py   # rebuild the tables from the monthly series
python analysis/make_figures.py          # redraw every figure from those tables
```

The pipeline refuses to go any further than its first step unless it reproduces
Finding 01's published April 2026 figures exactly — 119 providers, 361,130
pathways, a 71.5% mean, a 13.01pp standard deviation, and `RJL` and `RTF` at the
endpoints. A pipeline that cannot rebuild the earlier finding is not trusted to
extend it.

## Verification

Written independently of the Finding 01 and 02 code and checked twice: the
provider-month panel was reconciled row-for-row against a separately written
extraction (6,320 gastroenterology rows, zero differences), and the variance
decomposition was recomputed from scratch for a specialty the original author
had never analysed.
