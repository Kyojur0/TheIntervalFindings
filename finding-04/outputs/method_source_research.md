# NHS percentile convention: source research

Checked 12 September 2026. This is a methods source note, not the raw-file validation gate or the Finding 04 report.

## What the official guidance establishes

[NHS England RTT statistical user guidance](https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-statistics-user-guidance/), sections **Measuring RTT pathway length**, **Navigating published files**, and **Reproducibility and derived measures**, establishes:

- The first band includes days 0–7: **[0,1] weeks**, not (0,1]. Later finite bands exclude the lower endpoint and include the upper endpoint, e.g. days 8–14 for (1,2]. The final band starts at day 729, strictly beyond 104 weeks.
- National raw-CSV figures use `Part_2`, exclude `NONC`, and select the `Total` treatment-function rows. The inspected workbooks identify Total as `C_999`; **not `C_TOTAL`**. Adding specialty detail to Total double-counts pathways.
- Both the median and p92 are already published estimates from grouped data. The brief's claim that no published figure describes this is incorrect.
- Median estimation changed in October 2022 to align with percentile estimation. The guidance gives no algebraic formula.
- Commissioner workbooks contain national figures. Missing-trust estimates can change national overview totals; compare the submitted-data cohort with matching workbook figures.
- Community-service reporting changed in February 2024, affecting the comparability of the series start. Completed non-admitted pathways include non-treatment clock stops.

## Current calculation, identified numerically from official outputs

For finite containing band with lower endpoint `L`, pathway count `n`, cumulative count before it `C`, and total band count `N`, the current published values are reproduced by:

```text
q(p) = L + (p*N - C)/n
```

Find the first band whose cumulative count reaches `p*N`. This is linear interpolation across a one-week interval. No half-day offset, rank `p*(N+1)`, or additional half-observation term is needed for the inspected current outputs.

**Evidence and limit:** this is numerical identification from NHS England's own full-precision workbook results and weekly counts, not a formula quoted from its guidance. January 2024's workbook contains no formulas. The relevant current median/p92 cells contain values; April/May 2026 also contain unrelated percentage formulas. The [recording guidance PDF](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/10/Recording-and-reporting-RTT-waiting-times-guidance-v5.2-Feb25.pdf) contains no median, percentile or interpolation term.

Within the scan restricted to treatment-function codes beginning `C_`, across the `National` and `Sub-ICB` sheets of four workbooks, **16,905 finite-band numeric median/p92 values** agree with the formula to a maximum absolute difference of **4.973799150320701e-14 weeks**. There are another **five open-band p92 values**; all are stored as 104 and displayed as **104+**, using Excel format `[<104]0.0;[>=104]"104+"`. An example is May 2026 `Sub-ICB!DL208` (C_101). These are censored values, not exact percentiles. The Finding 04 engine should return a censored/not-computable result whenever the containing band is open-ended.

The comparison includes one first-band median exactly at its upper boundary: February 2025 `Sub-ICB` row 2832 (C_300), N=22, p50=1.0. It does **not** establish the convention for an interior first-band median; a January 2024 one-pathway first-band example is suppressed as `-`. No inference about unsuppressed interior first-band medians is made here.

The comparison CSV contains all 16,910 numeric comparisons, including the five deliberate open-band mismatches from an invalid finite-width extrapolation. Exclude `band=104` when summarising the finite-band result. It also includes **152** national specialty/total comparisons. The original research script selects codes beginning `C_`, so it excludes the `X` Other-service categories; it also skips suppressed or undefined cells. The separate verifier scans those Other-service categories as well. The differing comparison counts reflect the scan scope, not disagreement in the finite-band estimator.

## Official national values for the validation gate

All four are incomplete pathways, England, commissioner basis, all specialties once, NONC excluded. Each workbook has Total in `National!C38`, the code in `B38`, total count in `DE38`, median in `DH38`, and p92 in `DI38`.

| Month | Official median, full precision | Official p92, full precision | Pathways | Publication / revision |
|---|---:|---:|---:|---|
| January 2024 | 15.0395728510979 | 45.268384591488 | 7,575,914 | Published 14 March 2024; no incomplete revision |
| February 2025 | 14.2078621473788 | 42.2183233356486 | 7,401,153 | Published 10 April 2025; revised 10 July 2025 |
| April 2026 | 11.8956547031894 | 38.7020305382457 | 7,093,502 | Published 11 June 2026; unrevised |
| May 2026 | 12.4228168013959 | 38.5686655224201 | 7,153,655 | Published 9 July 2026; unrevised |

Workbook URLs (also stored with cells in `official_nhs_percentiles.csv`):

- [January 2024](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/03/Incomplete-Commissioner-Jan24-XLSX-4254K-55749.xlsx)
- [February 2025 revised](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/07/Incomplete-Commissioner-Feb25-XLSX-4M-revised.xlsx)
- [April 2026](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/06/Incomplete-Commissioner-Apr26-XLSX-4M-X7gGnn.xlsx)
- [May 2026](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/07/Incomplete-Commissioner-May26-XLSX-4M-3jBgba.xlsx)

These links were obtained from the official [2023–24](https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-data-2023-24/), [2024–25](https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-data-2024-25/) and [2026–27](https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-data-2026-27/) publication pages. All workbooks were downloaded and read successfully in memory using Python; web-tool errors on the binary files did not prevent verification. No canonical source data were changed.

## Files produced by this research

- `official_nhs_percentiles.csv`: eight full-precision official national values, source URLs, cells, totals and vintage notes.
- `method_identification_workbook_comparison.csv`: 16,910 worksheet comparisons, not the raw monthly-file validation result.
- This note.
- `../analysis/verify_nhs_workbook_method.py`: standalone standard-library reproduction, run with `./.venv311/bin/python`; downloads the four official workbooks in memory and recreates both CSVs. Its completed run reproduced the counts and maximum difference stated above.

The raw-CSV gate must still compare independently calculated January 2024 results against these official figures **before** the main series is computed. Applying the modern convention to February 2019 needs to be described as a comparable reconstruction; the official page explicitly records a later methodology change, so this note does not claim that the reconstructed 2019 median uses the exact historical official median method.
