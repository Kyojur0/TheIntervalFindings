"""
Provider-Size Control Test
========================
Chart 2 shows: Gastroenterology 18-week performance varies across providers.
This script tests whether that descriptive spread remains among larger lists;
it does not identify whether the causes are operational or clinical.

The obvious rebuttal: small providers naturally look extreme (a 50-pathway list
swings more than a 5,000-pathway list). If the spread collapses once we drop
small providers, the finding may be an artefact of size.

This script tests that rebuttal at increasing size thresholds, and repeats the
test for three other high-volume specialties to check whether it is unique to
Gastroenterology.
"""

import pandas as pd
from pathlib import Path
import numpy as np

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

SPECIALTIES = {
    "C_301": "Gastroenterology", "C_130": "Ophthalmology", "C_120": "ENT",
    "C_100": "General Surgery", "C_110": "Trauma & Orthopaedics", "C_320": "Cardiology",
    "C_400": "Neurology",
}

def summarise(df: pd.DataFrame, col: str = "pct_within_18w") -> dict:
    return {
        "n_providers": len(df),
        "mean": round(df[col].mean(), 1),
        "std": round(df[col].std(), 1),
        "min": round(df[col].min(), 1),
        "p10": round(df[col].quantile(0.10), 1),
        "median": round(df[col].median(), 1),
        "p90": round(df[col].quantile(0.90), 1),
        "max": round(df[col].max(), 1),
        "iqr": round(df[col].quantile(0.75) - df[col].quantile(0.25), 1),
    }

def main():
    df = pd.read_csv(OUTPUT_DIR / "rtt_distribution_by_trust_specialty.csv")
    apr = df[df.period == "Apr-2026"].copy()

    thresholds = [0, 50, 100, 250, 500, 1000]

    print("=" * 90)
    print("TEST: Does provider variation survive size controls? (Apr 2026, % within 18 weeks)")
    print("=" * 90)

    results = []
    for code, name in [("C_301", "Gastroenterology"), ("C_130", "Ophthalmology"),
                       ("C_120", "ENT"), ("C_110", "Orthopaedics")]:
        spec = apr[apr.specialty_code == code].copy()
        print(f"\n### {name} ({code}) ###")
        print(f"{'min list size':>14} | {'n':>4} | {'mean':>5} | {'std':>5} | "
              f"{'min':>5} | {'p10':>5} | {'med':>5} | {'p90':>5} | {'max':>6} | {'IQR':>5}")
        print("-" * 90)
        for t in thresholds:
            sub = spec[spec.total_waiting >= t]
            if len(sub) < 5:
                continue
            s = summarise(sub)
            print(f"{t:>14} | {s['n_providers']:>4} | {s['mean']:>5} | {s['std']:>5} | "
                  f"{s['min']:>5} | {s['p10']:>5} | {s['median']:>5} | {s['p90']:>5} | "
                  f"{s['max']:>6} | {s['iqr']:>5}")
            results.append({"specialty": name, "min_size": t, **s})

    res_df = pd.DataFrame(results)
    res_df.to_csv(OUTPUT_DIR / "trust_size_control_results.csv", index=False)

    # Focused verdict for Gastroenterology at a serious size floor
    print("\n" + "=" * 90)
    print("VERDICT CHECK — Gastroenterology, providers with >= 500 pathways")
    print("=" * 90)
    g500 = apr[(apr.specialty_code == "C_301") & (apr.total_waiting >= 500)]
    s = summarise(g500)
    print(f"n={s['n_providers']} large providers | mean={s['mean']}% | std={s['std']}pp | "
          f"range {s['min']}%–{s['max']}% | IQR={s['iqr']}pp")
    print(f"\nIf std stays high (>8pp) and IQR stays wide (>10pp) among large providers,")
    print(f"the observed spread is not confined to small-provider lists.")

    # Coefficient of variation across thresholds — is spread shrinking as we filter?
    print("\n" + "=" * 90)
    print("Coefficient of variation (std/mean) — Gastroenterology, by size floor")
    print("(a roughly stable CoV indicates the spread is not confined to small providers)")
    print("=" * 90)
    spec = apr[apr.specialty_code == "C_301"].copy()
    for t in thresholds:
        sub = spec[spec.total_waiting >= t]
        if len(sub) < 5:
            continue
        cov = sub.pct_within_18w.std() / sub.pct_within_18w.mean()
        print(f"  min size {t:>5}: n={len(sub):>3}, CoV={cov:.3f}")

if __name__ == "__main__":
    main()
