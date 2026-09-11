"""
RTT Waiting List Distribution Analysis
=======================================
Analyses the shape of NHS England waiting lists using RTT incomplete-pathway data.
Compares Feb 2025 with Apr 2026 to describe how the shares within 18 weeks and
over 52 weeks changed. These stock measures do not identify treatment speed or intent.

Rows coded NONC are excluded because NHS England's national elective access policy
excludes referrals from non-English commissioners from RTT reporting.

Data: NHS England RTT Waiting Times open data
      https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/
"""

import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[3]  # The Interval project root
DATA_DIR = BASE_DIR / "data" / "source_research"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
CHART_DIR  = Path(__file__).parent.parent / "figures"

OUTPUT_DIR.mkdir(exist_ok=True)
CHART_DIR.mkdir(exist_ok=True)

RTT_APR26 = str(DATA_DIR / "20260430-RTT-April-2026-full-extract.csv")
RTT_FEB25 = str(DATA_DIR / "20250228-RTT-February-2025-full-extract-revised.csv")

# ---------------------------------------------------------------------------
# Column name helpers
# ---------------------------------------------------------------------------
def week_col(i: int) -> str:
    """Return the exact RTT weekly band column name for week bucket starting at i."""
    if i == 104:
        return "Gt 104 Weeks SUM 1"
    return f"Gt {i:02d} To {i+1:02d} Weeks SUM 1"

# Column groups
COLS_0_18   = [week_col(i) for i in range(0, 18)]     # < 18 weeks (within standard)
COLS_18_52  = [week_col(i) for i in range(18, 52)]    # 18–52 weeks (over standard, not extreme)
COLS_52_104 = [week_col(i) for i in range(52, 104)]   # 52–104 weeks (very long wait)
COLS_104P   = [week_col(104)]                          # 104+ weeks (extreme)
COLS_52P    = COLS_52_104 + COLS_104P                  # 52+ weeks combined
ALL_WEEK_COLS = COLS_0_18 + COLS_18_52 + COLS_52P

# ---------------------------------------------------------------------------
# Specialties of interest
# NHS treatment function codes (prefixed C_ in this dataset)
# Procedural/high-volume: Gastroenterology, Ophthalmology, ENT, General Surgery, Orthopaedics
# Complex/lower-volume: Cardiology, Neurology, Neurosurgery (for contrast)
# ---------------------------------------------------------------------------
SPECIALTIES = {
    "C_301": "Gastroenterology",       # endoscopy proxy — our key specialty
    "C_130": "Ophthalmology",          # high-volume procedural
    "C_120": "ENT",                    # high-volume procedural
    "C_100": "General Surgery",        # high-volume
    "C_110": "Trauma & Orthopaedics",  # high-volume, often cited in backlog
    "C_320": "Cardiology",             # for contrast
    "C_400": "Neurology",              # for contrast
}

# ---------------------------------------------------------------------------
# Build SQL for distribution stats
# DuckDB handles 80MB CSVs in-memory without issue
# ---------------------------------------------------------------------------
def build_distribution_sql(csv_path: str, label: str) -> str:
    """
    Returns SQL that computes per-provider × per-specialty distribution stats
    from an RTT incomplete pathways CSV.

    Filters to:
      - RTT Part Type = 'Part_2'  (Incomplete Pathways — the actual waiting list)
      - Commissioner Org Code != 'NONC' (official England reporting scope)
    """
    cols_0_18    = " + ".join([f'COALESCE("{c}", 0)' for c in COLS_0_18])
    cols_18_52   = " + ".join([f'COALESCE("{c}", 0)' for c in COLS_18_52])
    cols_52_plus = " + ".join([f'COALESCE("{c}", 0)' for c in COLS_52P])
    # NOTE: "Total" column is NULL for Incomplete Pathways (Part_2).
    # Must derive the total by summing all weekly band columns directly.
    cols_all     = " + ".join([f'COALESCE("{c}", 0)' for c in ALL_WEEK_COLS])

    return f"""
    SELECT
        '{label}'                               AS period,
        "Provider Org Code"                     AS provider_code,
        "Provider Org Name"                     AS provider_name,
        "Treatment Function Code"               AS specialty_code,
        "Treatment Function Name"               AS specialty_name,
        SUM({cols_all})                         AS total_waiting,
        SUM({cols_0_18})                        AS waiting_0_18w,
        SUM({cols_18_52})                       AS waiting_18_52w,
        SUM({cols_52_plus})                     AS waiting_52w_plus,
        -- Derived metrics
        ROUND(100.0 * SUM({cols_0_18})   / NULLIF(SUM({cols_all}), 0), 2) AS pct_within_18w,
        ROUND(100.0 * SUM({cols_52_plus}) / NULLIF(SUM({cols_all}), 0), 2) AS pct_over_52w
    FROM read_csv_auto('{csv_path}')
    WHERE "RTT Part Type" = 'Part_2'
      AND COALESCE("Commissioner Org Code", '') <> 'NONC'
    GROUP BY 1,2,3,4,5
    HAVING SUM({cols_all}) > 0
    """


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
def main():
    print("Connecting to DuckDB (in-memory)...")
    con = duckdb.connect()

    print("Loading Feb 2025 data...")
    df_feb25 = con.execute(build_distribution_sql(RTT_FEB25, "Feb-2025")).df()
    print(f"  → {len(df_feb25):,} rows (provider × specialty combinations)")

    print("Loading Apr 2026 data...")
    df_apr26 = con.execute(build_distribution_sql(RTT_APR26, "Apr-2026")).df()
    print(f"  → {len(df_apr26):,} rows")

    # Combine and save raw outputs
    df_all = pd.concat([df_feb25, df_apr26], ignore_index=True)
    df_all.to_csv(OUTPUT_DIR / "rtt_distribution_by_trust_specialty.csv", index=False)
    print(f"\nSaved: outputs/rtt_distribution_by_trust_specialty.csv")

    # ---------------------------------------------------------------------------
    # ANALYSIS 1: National picture — distribution shift Feb 2025 → Apr 2026
    # Aggregate across all providers per specialty
    # ---------------------------------------------------------------------------
    print("\n--- ANALYSIS 1: National distribution shift ---")

    national = df_all.groupby(["period", "specialty_code", "specialty_name"]).agg(
        total_waiting  = ("total_waiting",  "sum"),
        waiting_0_18w  = ("waiting_0_18w",  "sum"),
        waiting_18_52w = ("waiting_18_52w", "sum"),
        waiting_52w_plus = ("waiting_52w_plus", "sum"),
    ).reset_index()

    national["pct_within_18w"] = (national["waiting_0_18w"] / national["total_waiting"] * 100).round(2)
    national["pct_over_52w"]   = (national["waiting_52w_plus"] / national["total_waiting"] * 100).round(2)
    national.to_csv(OUTPUT_DIR / "rtt_national_by_specialty.csv", index=False)

    # Print summary for our key specialties
    key = national[national["specialty_code"].isin(SPECIALTIES.keys())].copy()
    key["specialty_name"] = key["specialty_code"].map(SPECIALTIES)
    pivot = key.pivot_table(
        index="specialty_name",
        columns="period",
        values=["pct_within_18w", "pct_over_52w", "total_waiting"]
    ).round(1)
    print(pivot.to_string())

    # ---------------------------------------------------------------------------
    # ANALYSIS 2: Endpoint distribution comparison.
    # Compare the absolute percentage-point gain within 18 weeks with the
    # absolute percentage-point reduction over 52 weeks. This describes queue
    # composition; it is not a measure of treatment speed or prioritisation.
    # ---------------------------------------------------------------------------
    print("\n--- ANALYSIS 2: Endpoint distribution comparison ---")

    feb = national[national["period"] == "Feb-2025"].set_index(["specialty_code"])
    apr = national[national["period"] == "Apr-2026"].set_index(["specialty_code"])

    comparison = pd.DataFrame({
        "specialty_name"      : apr["specialty_name"],
        "total_feb25"         : feb["total_waiting"],
        "total_apr26"         : apr["total_waiting"],
        "total_change"        : apr["total_waiting"] - feb["total_waiting"],
        "pct_18w_feb25"       : feb["pct_within_18w"],
        "pct_18w_apr26"       : apr["pct_within_18w"],
        "pct_18w_change"      : apr["pct_within_18w"] - feb["pct_within_18w"],
        "pct_52w_feb25"       : feb["pct_over_52w"],
        "pct_52w_apr26"       : apr["pct_over_52w"],
        "pct_52w_change"      : apr["pct_over_52w"] - feb["pct_over_52w"],   # negative = improvement
    }).reset_index()

    # Flag: is the within-18 percentage-point gain numerically larger than the
    # over-52 percentage-point reduction? No causal meaning is attached.
    comparison["short_pp_gain_larger"] = (
        comparison["pct_18w_change"] > comparison["pct_52w_change"].abs()
    )
    comparison.to_csv(OUTPUT_DIR / "rtt_endpoint_distribution_comparison.csv", index=False)

    key_comp = comparison[comparison["specialty_code"].isin(SPECIALTIES.keys())].copy()
    key_comp["specialty_name"] = key_comp["specialty_code"].map(SPECIALTIES)
    print(key_comp[[
        "specialty_name", "total_feb25", "total_apr26",
        "pct_18w_feb25", "pct_18w_apr26", "pct_18w_change",
        "pct_52w_feb25", "pct_52w_apr26", "pct_52w_change",
        "short_pp_gain_larger"
    ]].to_string(index=False))

    # ---------------------------------------------------------------------------
    # ANALYSIS 3: Provider-level variation within Gastroenterology
    # High variation within the same treatment function — the data question
    # ---------------------------------------------------------------------------
    print("\n--- ANALYSIS 3: Provider variation in Gastroenterology ---")

    gastro_apr26 = df_apr26[df_apr26["specialty_code"] == "C_301"].copy()
    gastro_apr26 = gastro_apr26[gastro_apr26["total_waiting"] >= 50]  # exclude tiny lists

    print(f"  Providers with Gastroenterology waiting list (n≥50): {len(gastro_apr26)}")
    print(f"  % within 18w — mean: {gastro_apr26['pct_within_18w'].mean():.1f}%  "
          f"std: {gastro_apr26['pct_within_18w'].std():.1f}%  "
          f"min: {gastro_apr26['pct_within_18w'].min():.1f}%  "
          f"max: {gastro_apr26['pct_within_18w'].max():.1f}%")
    print(f"  % over 52w  — mean: {gastro_apr26['pct_over_52w'].mean():.1f}%  "
          f"std: {gastro_apr26['pct_over_52w'].std():.1f}%  "
          f"min: {gastro_apr26['pct_over_52w'].min():.1f}%  "
          f"max: {gastro_apr26['pct_over_52w'].max():.1f}%")

    gastro_apr26.sort_values("pct_over_52w", ascending=False).to_csv(
        OUTPUT_DIR / "rtt_gastro_trust_variation_apr26.csv", index=False
    )

    # ---------------------------------------------------------------------------
    # CHARTS
    # ---------------------------------------------------------------------------
    print("\nGenerating charts...")
    _chart_distribution_shift(key_comp)
    _chart_trust_variation_gastro(
        gastro_apr26[gastro_apr26["total_waiting"] >= 500].copy()
    )
    print("Done. Check charts/ folder.")


def _chart_distribution_shift(key_comp: pd.DataFrame):
    """
    Chart 1: For each key specialty, show the Feb→Apr change in:
    - % within 18 weeks (improvement in short end)
    - % over 52 weeks (improvement in long tail)
    This is a descriptive comparison of two percentage-point changes.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    specialties = key_comp["specialty_name"].tolist()
    x = range(len(specialties))
    w = 0.35

    short_changes = key_comp["pct_18w_change"].to_numpy(dtype=float)
    tail_reductions = key_comp["pct_52w_change"].abs().to_numpy(dtype=float)
    bars1 = ax.bar([i - w/2 for i in x], short_changes, width=w,
                   label="Δ % within 18 weeks (positive = improvement)", color="#2196F3", alpha=0.85)
    bars2 = ax.bar([i + w/2 for i in x], tail_reductions, width=w,
                   label="Δ % over 52 weeks, inverted (positive = fewer 52w+ pathways)", color="#FF9800", alpha=0.85)
    ax.bar_label(bars1, fmt="%.1f", padding=2, fontsize=7)
    ax.bar_label(bars2, fmt="%.1f", padding=2, fontsize=7)

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(specialties, rotation=35, ha="right", fontsize=9)
    ax.set_ylabel("Percentage point change (Feb 2025 → Apr 2026)")
    ax.set_title("Short-wait vs long-wait improvement by specialty\n"
                 "Change in % within 18 weeks vs change in % over 52 weeks", fontsize=11)
    ax.legend(fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f pp"))

    fig.tight_layout()
    fig.savefig(CHART_DIR / "chart1_distribution_shift_by_specialty.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  Saved: chart1_distribution_shift_by_specialty.png")


def _chart_trust_variation_gastro(gastro: pd.DataFrame):
    """
    Chart 2: Distribution of % within 18 weeks across the headline cohort of
    Gastroenterology providers with at least 500 incomplete pathways.
    """
    fig, ax = plt.subplots(figsize=(9, 5))

    sns.histplot(gastro["pct_within_18w"], bins=20, ax=ax, color="#4CAF50", alpha=0.8, edgecolor="white")
    ax.axvline(gastro["pct_within_18w"].mean(), color="red", linestyle="--",
               linewidth=1.5, label=f"Mean: {gastro['pct_within_18w'].mean():.1f}%")
    ax.axvline(65, color="navy", linestyle=":", linewidth=1.5, label="65% interim target")
    ax.axvline(92, color="darkgreen", linestyle=":", linewidth=1.5, label="92% constitutional standard")

    ax.set_xlabel("% of pathways within 18 weeks (Apr 2026)")
    ax.set_ylabel("Number of providers")
    ax.set_title("Gastroenterology: 18-week performance across providers\n"
                 f"Providers with ≥500 incomplete pathways (n={len(gastro)}) — April 2026", fontsize=11)
    ax.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(CHART_DIR / "chart2_gastro_trust_variation.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  Saved: chart2_gastro_trust_variation.png")


if __name__ == "__main__":
    main()
