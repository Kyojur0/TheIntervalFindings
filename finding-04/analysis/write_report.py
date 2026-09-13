"""Render the report's numerical tables from the reviewed output CSVs."""
from pathlib import Path
import argparse
import pandas as pd


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |',*['| '+' | '.join(map(str,row))+' |' for row in rows]])


def write_report(r):
    n=pd.read_csv(r/'national_monthly.csv'); a,b=n.iloc[0],n.iloc[-1]
    e=pd.read_csv(r/'endpoint_changes.csv'); spec=e[e.code!='C_999']
    official=pd.read_csv(r/'official_comparison.csv'); med=official[official.percentile==.5]
    validation=table(['Month','Official median (weeks, published precision)','Computed median (weeks)','Difference (weeks)','Method note'],
        [[x.period,f'{x.press_precision_official:.1f}',f'{x.computed_value:.5f}',f'{x.difference_from_rounded:+.5f}','Publication rounded to one decimal; same linear band estimate'] for x in med.itertuples()])
    headlines=table(['Measure','January 2024','May 2026'],[
        ['Pathways still waiting',f'{a.total:,}',f'{b.total:,}'],
        ['Median: half of pathways within this wait',f'{a.p50:.1f} weeks',f'{b.p50:.1f} weeks'],
        ['p75: three quarters within this wait',f'{a.p75:.1f} weeks',f'{b.p75:.1f} weeks'],
        ['p92: 92% within this wait',f'{a.p92:.1f} weeks',f'{b.p92:.1f} weeks'],
        ['p95: 95% within this wait',f'{a.p95:.1f} weeks',f'{b.p95:.1f} weeks'],
        ['p92 minus the 18-week threshold',f'{a.gap_weeks:.1f} weeks',f'{b.gap_weeks:.1f} weeks'],
        ['Share within 18 weeks',f'{100*a.within18_share:.1f}%',f'{100*b.within18_share:.1f}%']])
    bands=table(['Waiting so far','January 2024: pathways / share','May 2026: pathways / share','Change in count'],
        [[label,f'{a[g+"_count"]:,} / {100*a[g+"_share"]:.1f}%',f'{b[g+"_count"]:,} / {100*b[g+"_share"]:.1f}%',f'{b[g+"_count"]-a[g+"_count"]:+,}'] for label,g in [('Within 18 weeks','within18'),('Over 18, up to 52 weeks','middle'),('Over 52 weeks','over52')]])
    specialty=table(['Specialty (code)','Median (weeks)','p92 (weeks)','Gap from 18 (weeks)','Middle: pathways / share'],
        [[f'{x.name} ({x.code})',f'{x.p50_end:.1f}',f'{x.p92_end:.1f}',f'{x.gap_weeks_end:.1f}',f'{x.middle_count_end:,} / {100*x.middle_share_end:.1f}%'] for x in spec.itertuples()])
    flow=pd.read_csv(r/'completed_measures.csv'); flow=flow[flow.code=='C_999']
    flows=table(['Month','Completed pathways, England all specialties','Known-wait pathways','Median (weeks)','p92 (weeks)'],
        [[x.period,'Admitted' if x.part=='Part_1A' else 'Non-admitted',f'{x.total:,}',f'{x.p50:.1f}',f'{x.p92:.1f}'] for x in flow.itertuples()])
    historic=pd.read_csv(r/'baseline_measures.csv'); h=historic[historic.code=='C_999'].iloc[0]
    text=f'''**Validation gate: PASS.** January's calculated median is {a.p50:.5f} weeks, compared with the official 15.0 weeks: a difference of {a.p50-15:.5f} weeks, inside the required 0.1-week tolerance. The later workbook comparisons below also pass.

**Declared scope:** Reported England-commissioned consultant-led referral-to-treatment pathways still waiting at month-end; no estimates added for missing providers; exact `Part_2`; commissioner `NONC` excluded. National figures aggregate submitted data and count all specialties once, using `C_999` Total rows, reconciled to the sum of the individual specialties. Specialty figures use only `C_100`, `C_110`, `C_120`, `C_130`, `C_301`, `C_320` and `C_400`. The main series covers January 2024 to May 2026. These are pathways, not unique people: a person can have more than one. Completed pathways and the historical baseline are labelled wherever used.

# Finding 04 — a shorter median, a promise still unmet

At the end of May 2026, half of the waiting pathways had been open for roughly **{b.p50:.1f} weeks or less**. Yet the wait that included **92%** of the list was **{b.p92:.1f} weeks**. This is the **92nd percentile**, or **p92**: the point below which that share of waiting pathways sits.

The standard requires at least 92% of incomplete pathways to be within 18 weeks. On the grouped-data estimate, the gap was therefore **{b.gap_weeks:.1f} weeks**. This is a description of how long the current list has been waiting so far. It is not a prediction of the wait faced by a new referral or the time remaining before treatment.

Both the median and p92 fell between the start and end of this submitted-data series. Reporting gaps mean this is not a fully constant provider population. The median fell by **{a.p50-b.p50:.1f} weeks**, while p92 fell by **{a.p92-b.p92:.1f} weeks**. Improvement and a missed standard coexist. A median inside eighteen weeks does not establish that patients are fine, or that the standard is being met: the standard protects far more than the middle patient.

## The official comparison

{validation}

The [January statistical release](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/03/Jan24-RTT-SPN-Publication-PDF-437K.pdf) supplies the initial comparison. Full-precision official values and cell references for every comparison are in [official_comparison.csv](official_comparison.csv). Across the four months' national median and p92 comparisons, the largest absolute difference from the official workbook is below 0.000000000001 weeks; pathway totals also match exactly. Differences from one-decimal values in the table are rounding, not a different method.

The [NHS statistical guidance](https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-statistics-user-guidance/) describes the band definitions and says median and p92 are estimated from grouped data. It does not print the interpolation formula. We identified the current linear convention from the full-precision outputs in NHS commissioner workbooks and checked it against their underlying bands. [The source-method note](method_source_research.md) distinguishes this numerical identification from a formula explicitly published in prose.

## What the distribution says

{headlines}

The national median remained below eighteen weeks throughout the series. The decline was not uninterrupted: it reached 11.3 weeks in March 2026, then rose to 11.9 in April and 12.4 in May. Month-end snapshots cannot establish what caused either the longer-term decline or these recent rises.

![The national median over time](../pack/figures/figure-01-median.png)

![The median and p92 compared with eighteen weeks](../pack/figures/figure-02-promise.png)

## The middle is substantial, but it is not the largest group

The middle means pathways open for **more than eighteen and no more than fifty-two weeks**. At the end of May 2026 it contained **{b.middle_count:,} pathways**, **{100*b.middle_share:.1f}%** of the list. The extracts cannot tell us how many unique people those pathways represent.

{bands}

The middle fell by **{a.middle_count-b.middle_count:,} pathways** across all specialties, and its share fell by **{100*(a.middle_share-b.middle_share):.1f} percentage points**. Across the seven named specialties alone, it fell by **{int(-spec.middle_count_change.sum()):,}**, reproducing Finding 02. The all-specialty reduction therefore extends that finding; it is not the same cohort total.

Within eighteen weeks is the largest group in every national month and in every month of each named specialty. The opposite claim in the brief fails the data check. The middle is, however, the largest group **among pathways already beyond eighteen weeks**. That conditional denominator is different from the whole waiting list.

![The three waiting groups as pathway counts](../pack/figures/figure-03-middle.png)

## Which specialties carry the most middle waiting?

These figures are for pathways still waiting in May 2026, in the same England scope:

{specialty}

Among the seven named specialties, trauma and orthopaedics has the largest middle **count**. ENT has the highest middle **share**. Each specialty has a median below eighteen weeks in the latest month, while each has a p92 above it. No single specialty is needed to produce the central contrast.

The gastroenterology comparison retains a known early coding break at Northern Lincolnshire and Goole: activity was reported under general medicine before appearing under gastroenterology. The counts do not identify a one-for-one transfer of pathways. Possible coding changes elsewhere are recorded in the anomaly audit; this analysis has not reassigned them.

## Waiting so far and waits on completed pathways

**Completed-pathway scope:** the next table describes pathways that closed during the named month, using `Part_1A` for admitted and `Part_1B` for non-admitted pathways, reported England, all specialties once, `NONC` excluded, with no estimates for missing providers. Only pathways with a known wait enter the band totals and percentiles; unknown clock starts are reported separately in the source audits.

{flows}

These completed-pathway medians answer a different question from the main table: how long the pathways that closed that month had lasted. Non-admitted completion can include a decision not to treat or other clock stops, so completion does not always mean treatment was delivered. The incomplete-pathway median measures how long the pathways still open have been waiting **so far**. Neither is an individual forecast, and the completed figures from these two months do not establish a continuous trend.

## Before the pandemic

**February 2019 baseline, reported incomplete pathways, England, all specialties once, `NONC` excluded, no missing-provider estimates:** the reconstructed median is **{h.p50:.1f} weeks** and p92 is **{h.p92:.1f} weeks**. The historical file has fifty-two closed weekly bands and one open band beyond fifty-two weeks. Both percentiles fall in closed bands, so both are computable. We did not assign an invented width to the final band.

This baseline uses the same current interpolation rule for comparability. It is not claimed to reproduce the historical official median convention, which NHS England later changed. Reporting scope and treatment-function categories also changed over time, so the baseline is a context point rather than an unchanged cohort followed through the pandemic.

## What is measured, and how precise is it?

For a percentile fraction p, locate the first weekly band whose cumulative pathway count reaches p times the total. Add to its lower boundary the fraction of that band's pathways needed to reach the target. The first band includes waits of zero through seven days; later bands exclude their lower boundary and include their upper boundary. A wait of exactly eighteen weeks is within the standard.

The extracts supply counts in bands, not exact individual waits. In May 2026 the median lies in the twelve-to-thirteen-week band and p92 in the thirty-eight-to-thirty-nine-week band. Using band midpoints instead gives 12.5 and 38.5 weeks; using lower bounds gives 12.0 and 38.0. The lower-bound p92 is about 0.57 weeks below the interpolated estimate, above the brief's 0.5-week sensitivity threshold. The headline should therefore say **about 39 weeks**, or retain **38.6 weeks as a band estimate**, rather than imply day-level accuracy. Its interpretation survives: even the lower bound is twenty weeks beyond the standard.

Across the national monthly medians, assigning lower bounds moves the estimate by at most 1.00 week and assigning midpoints by at most 0.50 week (rounded). [The sensitivity table](band_sensitivity.csv) includes all reported populations and percentiles.

The modern open-ended band is beyond 104 weeks. For every published modern population, over 99% of pathways are in closed bands; hence no percentile below the 99th can fall in the open band. [The open-band checks](open_band_checks.csv) show the counts, denominator and cumulative closed-band share. No reported percentile is censored. This check applies to the pooled populations reported here, not necessarily to every small provider.

![The latest month's full band distribution](../pack/figures/figure-04-shape.png)

## Stress tests and limits

Removing the six first-release months leaves twenty-three observations, ending in March 2026. The national p92 is then 38.3 weeks, with a 20.3-week gap; all seven specialty p92 values still exceed eighteen weeks. The result therefore does not depend on those provisional months. The first-release files are October and November 2025, January and February 2026, and April and May 2026; the supplied vintages are retained, not silently replaced.

All 203 month-by-specialty comparisons reproduce Finding 02's within-eighteen-week counts and its percentages to their published rounding. The earlier seven national median checks also agree to rounding. Their inclusion of both Total and detailed specialty rows doubled counts, but did not change the pooled percentile because those band vectors match exactly. This report removes that duplication from national counts.

NHS England already publishes median and p92. This finding's contribution is explaining them together, expressing the p92 gap in weeks, and documenting the middle and specialty breakdowns. It must not claim to discover an unpublished national statistic. Similarly, the brief's approximately 14.3 million pathways combines Total and specialty rows; the unduplicated latest count is {b.total:,}.

The raw files omit some provider submissions. Sheffield Teaching Hospitals (RHQ) is absent from July 2025 onwards; Barking, Havering and Redbridge (RF4) has a November 2025 gap; Torbay and South Devon (RA9) is absent from April 2026 onwards. The largest monthly count fall occurs in November 2025 and is partly a reporting-gap effect. March 2026 has the largest median fall, which remains when comparing only providers present in both adjacent months. That establishes a change in the submitted distribution, not its cause. The [anomaly report](ANOMALY_REPORT.md) records the gaps and official source evidence. A separate sensitivity restricted to provider codes present at both endpoints also shows falling medians, p92, middle counts and middle shares, nationally and across the named specialties. This is a different provider subset and is not used for headline values. Fixed codes cannot control changes in services or merger footprint; see [the sensitivity results](anomaly_endpoint_common_providers.csv).

Community-service reporting changed during the early part of the series, and provider reporting and specialty coding can change. A change in list composition can reflect entries, ageing, closures, validation, coding and reporting; these data cannot separate those mechanisms. They contain no patient-level case mix, staffing or booking evidence. Changes in snapshot counts are not treatment counts and do not establish cause.

## Anomalies and independent review

The dedicated [anomaly audit](ANOMALY_REPORT.md) and [author responses](AUTHOR_DISPOSITIONS.md) are retained separately. Every candidate has a recorded response in [the disposition table](anomaly_candidate_dispositions.csv).

- **Duplicated rollups:** national Total rows are counted once and reconciled to detailed specialties.
- **Blank cells:** retained as zero only after independent row totals certify that value; unresolved cases stop the parser.
- **Provider gaps and organisational changes:** missing submissions are named above, and the scope and charts exclude estimates explicitly. Documented mergers are kept distinct from unexplained gaps.
- **Specialty coding changes:** reported codes are retained, the gastroenterology baseline caveat is explicit, and other patterns remain candidates rather than proven transfers.
- **Large monthly moves and mixed vintages:** the largest median move is independently corroborated; revision effects and causes remain unidentified. Provider and release sensitivities are labelled separately.
- **Schema, ordering and open bands:** checks pass for all published populations, with the historical schema handled separately.

The [separate verification report](VERIFICATION_REPORT.md) and [numeric-claim ledger](VERIFIED_CLAIMS.csv) record the independent recalculation, official source checks, claim counts and any failures. This analytical draft is ready for owner review; it has not been promoted to the publication folder.
'''
    (r/'REPORT.md').write_text(text)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results-dir',type=Path,default=Path(__file__).resolve().parent.parent/'results')
    write_report(p.parse_args().results_dir)
