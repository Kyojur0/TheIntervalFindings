"""Percentiles of NHS RTT weekly bands, with explicit open-end handling.

Official definitions and current estimator context:
https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-statistics-user-guidance/

The NHS page describes the grouped-data estimates but does not print an algebraic
formula. The linear rule below is numerically identified against the published
full-precision commissioner workbook values (see method_source_research.md and
official_comparison.csv); it is not presented as a quoted NHS formula.

The first label 'Gt 00 To 01 Weeks SUM 1' actually includes days 0 through 7:
[0,1] weeks. Subsequent closed bands are (k,k+1] weeks, i.e. days 7*k+1 through
7*(k+1). Exactly 18 weeks belongs to the within-18 group. NHS interpolation uses
the numerical weekly boundaries k and k+1, not a half-day shift or sample-rank
correction. It estimates a position inside the containing band, not an observed
individual wait. This continuous approximation also applies to the first band.

The last entry is always OPEN: >104 weeks for modern files, >52 for the baseline.
Never pretend it has unit width. If the target lies inside it, return NaN. The
analysis emits open_band_checks.csv: cumulative closed-band share must exceed
99% to establish that every percentile below 99 is identifiable for that pooled
population. This is checked on the published populations, not assumed for every
tiny provider cohort.
"""
from __future__ import annotations
import numpy as np


def _counts(counts):
    a = np.asarray(counts, dtype=float)
    if a.ndim != 1 or len(a) < 2 or not np.isfinite(a).all() or (a < 0).any() or (a != np.floor(a)).any():
        raise ValueError('Band counts must be a finite non-negative integer vector')
    return a


def percentile(counts, fraction):
    a = _counts(counts)
    if not 0 < fraction < 1:
        raise ValueError('Percentile fraction must be strictly between zero and one')
    total = a.sum()
    if total == 0:
        return float('nan')
    cumulative = a.cumsum()
    target = fraction * total
    j = int(np.searchsorted(cumulative, target, side='left'))
    if j == len(a) - 1:
        return float('nan')
    preceding = cumulative[j - 1] if j else 0
    # Lower boundary plus fraction of the containing one-week interval.
    return float(j + (target - preceding) / a[j])


def summary(counts):
    a = _counts(counts)
    if len(a) not in (53, 105):
        raise ValueError('Only the documented 53- and 105-band schemas are allowed')
    n = int(a.sum())
    d = {'total': n, 'within18_count': int(a[:18].sum()),
         'middle_count': int(a[18:52].sum()), 'over52_count': int(a[52:].sum()),
         'open_count': int(a[-1]), 'closed_share': (n - a[-1]) / n if n else np.nan}
    for group in ('within18', 'middle', 'over52'):
        d[group + '_share'] = d[group + '_count'] / n if n else np.nan
    for p in (50, 75, 92, 95):
        value = percentile(a, p / 100)
        d[f'p{p}'] = value
        # Locate by target, not floor(value): an exact upper boundary belongs
        # to the preceding band.
        j = int(np.searchsorted(a.cumsum(), n * p / 100, side='left')) if n else -1
        d[f'p{p}_band_lower'] = j
    d['gap_weeks'] = d['p92'] - 18
    return d
