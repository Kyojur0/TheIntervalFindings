"""
Pressure Test — try to break the two findings before we build an argument on them.

TEST 1: Stock change arithmetic check
  The <18w cohort holds far more pathways, so it can move more in % terms.
  Check ABSOLUTE pathway-count changes per cohort, not just percentages.
  Note: stock shrinkage ≠ treatment or clearance (pathways can leave via non-treatment stops).

TEST 2: Does provider variation survive controlling for size?
  Small providers naturally look more extreme. Check whether the spread in
  Gastroenterology 18w performance holds when we look only at larger providers.
"""

import duckdb
import pandas as pd
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

def main():
    df = pd.read_csv(OUTPUT_DIR / "rtt_distribution_by_trust_specialty.csv")

    SPECIALTIES = {
        "C_301": "Gastroenterology", "C_130": "Ophthalmology", "C_120": "ENT",
        "C_100": "General Surgery", "C_110": "Trauma & Orthopaedics", "C_320": "Cardiology",
        "C_400": "Neurology",
    }

    # ---- TEST 1: absolute pathway-count changes per cohort, national ----
    print("=" * 70)
    print("TEST 1: Stock change — ABSOLUTE pathway counts (not %)")
    print("=" * 70)

    nat = df[df["specialty_code"].isin(SPECIALTIES)].groupby(
        ["period", "specialty_code"]
    ).agg(
        w_0_18=("waiting_0_18w", "sum"),
        w_18_52=("waiting_18_52w", "sum"),
        w_52p=("waiting_52w_plus", "sum"),
    ).reset_index()

    feb = nat[nat.period == "Feb-2025"].set_index("specialty_code")
    apr = nat[nat.period == "Apr-2026"].set_index("specialty_code")

    out = pd.DataFrame({
        "specialty": [SPECIALTIES[c] for c in apr.index],
        "d_0_18w":  (apr.w_0_18  - feb.w_0_18).astype(int),
        "d_18_52w": (apr.w_18_52 - feb.w_18_52).astype(int),
        "d_52w_plus": (apr.w_52p - feb.w_52p).astype(int),
    })
    print(out.to_string(index=False))
    out.to_csv(OUTPUT_DIR / "pressure_test_absolute_numbers.csv", index=False)

    print("\nInterpretation:")
    print("  Negative = cohort shrank (pathway stock fell). Positive = cohort grew.")
    print("  Note: stock shrinkage reflects all reasons pathways leave the list,")
    print("  not treatment alone (includes non-treatment clock stops).")
    print("  Interpret these stock changes alongside the percentage-point results;")
    print("  they do not identify treatment speed, prioritisation, or cause.")

if __name__ == "__main__":
    main()
