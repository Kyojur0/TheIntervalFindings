# Finding 04 — separate independent verification

**Verdict: verified within the declared submitted-data scope, with the report's reporting-gap and grouped-data caveats retained.** The audited report contains **268 ledger entries: 268 VERIFIED, 0 WRONG, 0 CANNOT-CHECK**. This count comprises 252 numeric occurrences, including written-out numbers, dates, identifiers and repeated occurrences, plus 16 quantified prose assertions. It is not a count of 268 distinct statistical findings. The complete ledger is [VERIFIED_CLAIMS.csv](VERIFIED_CLAIMS.csv).

The checked report is preserved in [verification_report_snapshot.md](verification_report_snapshot.md), SHA-256 `90dac13322fe31df5dd237207d3da539bedc943785492dee548bd2a0adcf3b57`. This verification did not modify the report or the primary analysis scripts. The final claim check was completed on 13 September 2026. No separate article draft existed in the Finding 04 working deliverables at this pass.

## Independence and coverage

[verify_independent.py](../analysis/verify_independent.py) was written before reading any primary percentile, parser or analysis implementation. It aggregates the original CSVs using a fresh DuckDB connection, traverses cumulative counts with a separate Python implementation, and reads the primary output only after producing independent results. It does not import the author's modules or read their cached band matrix. The original-file inventory and hashes are in [verification_raw_inventory.csv](verification_raw_inventory.csv); the verifier's own aggregates and measures are saved separately.

The raw pass covers 29 modern monthly files, the February 2019 baseline and two full extracts. It uses exact `Part_2` for incomplete pathways, `Part_1A` and `Part_1B` for completed pathways, excludes `NONC`, and counts national pathways once through `C_999`. It derives known-wait totals from the bands. Modern files have 105 bands; the baseline has 53. All 34 selected file/part national vectors equal their corresponding summed detailed-specialty vectors in every band.

| Comparison | Number checked | Result |
| --- | ---: | --- |
| Published percentiles: 232 monthly, 8 baseline and 32 completed populations, four percentiles each | 1,088 | No failures; maximum absolute difference 0.0000000000499902 weeks |
| Other published counts, shares and gaps | 2,720 | No failures at the verifier's stated tolerances |
| Finding 02 monthly specialty within-18-week counts and rounded percentages | 203 | Exact agreement |
| Live official national median/p92 values | 8 | No failures; maximum absolute difference 0.0000000000000355271 weeks |

The percentile difference against the primary CSV reflects its decimal serialization and is far below the brief's 0.01-week threshold. The comparison includes **every p50, p75, p92 and p95 in all_measures.csv**. See [verification_percentile_comparison.csv](verification_percentile_comparison.csv), [verification_measure_comparison.csv](verification_measure_comparison.csv) and [verification_finding02_reconciliation.csv](verification_finding02_reconciliation.csv).

## Official sources and method

All four workbook URLs were fetched afresh and returned HTTP 200. Their bytes were decoded independently using the XLSX XML contents. The actual national cells agree with both the claimed official values and the raw recomputation; their pathway totals also agree. The sources are the [January 2024 workbook](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/03/Incomplete-Commissioner-Jan24-XLSX-4254K-55749.xlsx), [revised February 2025 workbook](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/07/Incomplete-Commissioner-Feb25-XLSX-4M-revised.xlsx), [April 2026 workbook](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/06/Incomplete-Commissioner-Apr26-XLSX-4M-X7gGnn.xlsx) and [May 2026 workbook](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/07/Incomplete-Commissioner-May26-XLSX-4M-3jBgba.xlsx). Retrieval status, resolved URLs and content hashes are in [verification_live_sources.csv](verification_live_sources.csv).

The [January statistical release](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/03/Jan24-RTT-SPN-Publication-PDF-437K.pdf) and [NHS statistical guidance](https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-statistics-user-guidance/) also resolved. The January computed median is 15.0395728511 weeks, versus 15.0 at published precision: the 0.0395728511-week difference passes the 0.1-week gate.

The independent method finds the band containing `p × N`, then calculates `lower + (p × N − preceding cumulative count) / containing count`. The first band includes days zero through seven; later bands include their upper endpoint. An open final band has no identifiable exact percentile and returns an unavailable estimate. The algebra is numerically identified from official outputs, not quoted as an explicit formula in the guidance.

An additional workbook scan reproduced **20,861 finite-band numeric median/p92 values**, with maximum absolute difference **4.9737991503 × 10⁻¹⁴ weeks**. Five further numeric workbook values fell in the open band and were correctly treated as censored by the verifier. These are small workbook populations, not any of the 272 published Finding 04 populations. See [verification_workbook_band_comparison.csv](verification_workbook_band_comparison.csv).

**Source-note clarification reported to the author:** the primary methods note's 16,905 finite comparisons used only `C_` treatment-function codes. The independent broader scan includes the five `X` service categories and therefore has a larger comparison count. The numerical method agrees in both selections. The author clarified the narrower selection in the source note; this required no change to the finding's calculated measures.

## Sensitivity and attempts to break the finding

In May 2026 the independently computed national median is **12.4228168014 weeks** and p92 is **38.5686655224 weeks**, a **20.5686655224-week** gap from the standard. Lower-bound assignment gives 12 and 38 weeks; midpoint assignment gives 12.5 and 38.5 weeks. The lower-bound p92 differs by **0.5686655224 weeks**, exceeding the brief's 0.5-week sensitivity threshold. The report explicitly states this and describes the value as a band estimate. The contrast survives even at the lower bound.

Across national monthly medians, the maximum absolute lower-bound shift is **0.997676016 weeks** and the maximum midpoint shift is **0.497676016 weeks**. The report's rounded 1.00 and 0.50 values are correct. Across the 264 modern published populations, the minimum cumulative share before the open band is **99.6254681648%**. Thus the reported p50, p75, p92 and p95 are all identifiable, and percentiles below the 99th are outside the open band in these populations. Both February 2019 headline percentiles are below its open-band boundary, with reconstructed national p50 **6.7 weeks** and p92 **22.1 weeks** at report precision. These statements do not extend to every small provider.

Removing the six first-release months leaves **23** observations ending in March 2026. The national p92 is **38.339914 weeks** at that endpoint; every one of the **161** retained month-by-specialty p92 values exceeds 18 weeks. In the latest month all seven specialty medians are below 18 weeks and all seven p92 values exceed it.

The brief's largest-middle premise fails: within 18 weeks is the largest block in all **29 national months** and all **203 named-specialty months**. The middle is largest only after conditioning on pathways already beyond 18 weeks. The report makes that distinction. Its latest national middle count **2,361,713**, the all-specialty endpoint fall **571,536**, and the seven-specialty fall **246,987** reproduce the raw files.

The national median and p92 both fell across the reported series. The report also identifies the March-to-May median rise. Its wording does not turn the latest movements into a claim of general deterioration, attribute causes, or imply that a shorter median proves patients are fine.

## Scope, wording and reporting limits

No numeric scope-mixing, stock/flow conflation, incorrect rounding direction or upgrade of a percentile into a typical completed wait was found in the checked report. It declares reported England-commissioned pathways with no estimates for missing providers; completed-pathway and historical-baseline figures are explicitly labelled. It distinguishes pathways from unique people, waiting so far from completed durations, and grouped estimates from individual forecasts.

The narrow independent provider checks support the report's RHQ, RF4 and RA9 reporting-gap caveats. The largest national count fall is in November 2025; the largest median fall is in March 2026. A separately recomputed March comparison restricted to providers present in both adjacent months still shows the median fall. These checks establish properties of submitted data, not the reason a provider stopped reporting or the cause of distributional change. Their evidence is in [verification_provider_claims.csv](verification_provider_claims.csv) and [verification_march_common_providers.csv](verification_march_common_providers.csv).

The ledger's zero CANNOT-CHECK count concerns the extracted numeric/quantified claims in this report, not an assertion that omitted-provider waits, unique-patient counts or causal mechanisms are observable. Provider coding and missing submissions remain material interpretation limits. Dedicated anomaly hunting, the author's anomaly dispositions, and visual inspection of figures are separate review work and are not certified by this numerical pass.

## Failures and reproducibility

**No wrong or unverifiable report numeric claims remain in the checked snapshot.** Seven initial unresolved ledger entries arose solely because the verifier's tokenizer included trailing sentence commas in numeric tokens. The tokenizer was repaired, the ledger rerun against the unchanged report hash, and all seven mapped to already independently verified evidence. These were verifier extraction defects, not errors in the report.

To reproduce from the original project data, run its Python 3.11 environment with `verify_independent.py --source-root <project-root> --results-dir <results-folder> --provider-checks`, then run `verify_claims.py --results-dir <results-folder>`. The results folder must contain the candidate `REPORT.md`, `all_measures.csv` and `official_nhs_percentiles.csv`. For a prose-only recheck, reuse the verifier's already saved evidence and run only `verify_claims.py`; it writes a new ledger and snapshot without changing the report. The summary is [verification_summary.json](verification_summary.json).
