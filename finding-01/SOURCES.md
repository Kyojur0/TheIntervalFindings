# Data sources — Finding 01

The upload package contains derived outputs, figures, and the scripts that regenerate them. The large NHS England extracts are kept in the project data directory and are not duplicated here.

## Finding 01 extracts

| Extract | Local project path | SHA-256 / provenance |
|---|---|---|
| April 2026 full extract | `data/source_research/20260430-RTT-April-2026-full-extract.csv` | SHA-256 `0486aca5891a96af4f15e2f4559795138baef08b0ed580602b8c3a7aec6a56e9`; official ZIP URL: [Full CSV data file Apr26](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/06/Full-CSV-data-file-Apr26-ZIP-3M-X7gGnn.zip) |
| February 2025 revised full extract | `data/source_research/20250228-RTT-February-2025-full-extract-revised.csv` | Used for the endpoint comparison; official ZIP URL recorded in `data/rtt_monthly_series/manifest.json` |

## Scope

Scripts filter exact `RTT Part Type = Part_2` rows and exclude commissioner code `NONC`, matching the published England scope. Weekly bands are summed from the raw extract; `Total` is not used for incomplete pathways.


## Retrieval and reproducibility

The canonical analysis scripts are copied into `analysis/`. Run `python analysis/make_figures.py` from this pack after installing Python 3.10+, DuckDB, pandas, and matplotlib. Outputs are written to `outputs/` and figures to `figures/`.
