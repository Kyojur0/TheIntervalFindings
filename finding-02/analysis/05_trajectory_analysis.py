"""
RTT Trajectory Analysis — v2.0
================================
Describes how the within-18-week and over-52-week shares changed from
Jan 2024 to May 2026, including month-to-month movements.

Loads the 29 monthly Part_2-filtered CSVs listed in the project manifest, then
builds a time-series panel of distribution metrics per specialty.

Rows coded NONC are excluded because NHS England's national elective access policy
excludes referrals from non-English commissioners from RTT reporting.

Feb 2019 baseline is handled separately (different column structure).
"""

import json
import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
from pathlib import Path
import datetime

# ---------------------------------------------------------------------------
# Paths (relative to script location)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR   = SCRIPT_DIR.parent.parent.parent  # project root
SERIES_DIR = BASE_DIR / "data" / "rtt_monthly_series"
MANIFEST   = SERIES_DIR / "manifest.json"
OUTPUT_DIR = SCRIPT_DIR.parent / "outputs"
CHART_DIR  = SCRIPT_DIR.parent / "figures"

OUTPUT_DIR.mkdir(exist_ok=True)
CHART_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Column helpers (modern schema — 105 band columns)
# ---------------------------------------------------------------------------
def week_col(i: int) -> str:
    if i == 104:
        return "Gt 104 Weeks SUM 1"
    return f"Gt {i:02d} To {i+1:02d} Weeks SUM 1"

COLS_0_18   = [week_col(i) for i in range(0, 18)]
COLS_18_52  = [week_col(i) for i in range(18, 52)]
COLS_52_104 = [week_col(i) for i in range(52, 104)]
COLS_104P   = [week_col(104)]
COLS_52P    = COLS_52_104 + COLS_104P
ALL_COLS    = COLS_0_18 + COLS_18_52 + COLS_52P

SPECIALTIES = {
    "C_301": "Gastroenterology",
    "C_130": "Ophthalmology",
    "C_120": "ENT",
    "C_100": "General Surgery",
    "C_110": "Trauma & Orthopaedics",
    "C_320": "Cardiology",
    "C_400": "Neurology",
}

# ---------------------------------------------------------------------------
# Build SQL expressions for band sums
# ---------------------------------------------------------------------------
def band_sum_sql(cols: list) -> str:
    return " + ".join([f'COALESCE("{c}", 0)' for c in cols])

SUM_0_18  = band_sum_sql(COLS_0_18)
SUM_18_52 = band_sum_sql(COLS_18_52)
SUM_52P   = band_sum_sql(COLS_52P)
SUM_ALL   = band_sum_sql(ALL_COLS)

# ---------------------------------------------------------------------------
# Load modern series (Jan 2024 → May 2026) from the manifest file list
# ---------------------------------------------------------------------------
def load_modern_series(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    Load all manifest-listed modern monthly files in one DuckDB pass.
    Groups to period × specialty_code level (national totals).
    Excludes the 2019 baseline which is handled separately.
    """
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = manifest.get("files", [])
    if len(entries) != 29:
        raise ValueError(f"Expected 29 modern files in manifest, found {len(entries)}")
    paths = [SERIES_DIR / item["filename"] for item in entries]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Manifest-listed files missing: {missing}")
    file_list_sql = "[" + ",".join(
        "'" + str(path).replace("'", "''") + "'" for path in paths
    ) + "]"
    sql = f"""
    SELECT
        "Period"                   AS period_raw,
        "Treatment Function Code"  AS specialty_code,
        "Treatment Function Name"  AS specialty_name,
        SUM({SUM_ALL})             AS total_waiting,
        SUM({SUM_0_18})            AS waiting_0_18w,
        SUM({SUM_18_52})           AS waiting_18_52w,
        SUM({SUM_52P})             AS waiting_52w_plus
    FROM read_csv_auto({file_list_sql}, union_by_name=true, ignore_errors=false)
    WHERE "RTT Part Type" = 'Part_2'
      AND COALESCE("Commissioner Org Code", '') <> 'NONC'
    GROUP BY 1, 2, 3
    HAVING SUM({SUM_ALL}) > 0
    """
    print(f"  Running DuckDB query across {len(paths)} manifest-listed files...")
    df = con.execute(sql).df()
    return df

# ---------------------------------------------------------------------------
# Load Feb 2019 baseline (53-column schema, bands stop at Gt 52 Weeks SUM 1)
# ---------------------------------------------------------------------------
COLS_0_18_2019  = COLS_0_18   # same names
COLS_18_52_2019 = [week_col(i) for i in range(18, 52)]  # same names
COL_52P_2019    = "Gt 52 Weeks SUM 1"  # single catch-all in 2019

def load_baseline(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    path = str(SERIES_DIR / "201902-RTT-February2019-incomplete-pathways.csv").replace("'", "''")
    s_0_18  = band_sum_sql(COLS_0_18_2019)
    s_18_52 = band_sum_sql(COLS_18_52_2019)
    sql = f"""
    SELECT
        'RTT-FEBRUARY-2019'          AS period_raw,
        "Treatment Function Code"    AS specialty_code,
        "Treatment Function Name"    AS specialty_name,
        SUM({s_0_18}) + SUM({s_18_52}) + SUM(COALESCE("{COL_52P_2019}", 0)) AS total_waiting,
        SUM({s_0_18})                AS waiting_0_18w,
        SUM({s_18_52})               AS waiting_18_52w,
        SUM(COALESCE("{COL_52P_2019}", 0)) AS waiting_52w_plus
    FROM read_csv_auto('{path}')
    WHERE "RTT Part Type" = 'Part_2'
      AND COALESCE("Commissioner Org Code", '') <> 'NONC'
    GROUP BY 1, 2, 3
    HAVING SUM({s_0_18}) + SUM({s_18_52}) + SUM(COALESCE("{COL_52P_2019}", 0)) > 0
    """
    df = con.execute(sql).df()
    return df

# ---------------------------------------------------------------------------
# Parse period strings → dates for sorting/plotting
# ---------------------------------------------------------------------------
MONTH_MAP = {
    "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4,
    "MAY": 5, "JUNE": 6, "JULY": 7, "AUGUST": 8,
    "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12,
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}

def parse_period(raw: str) -> datetime.date:
    # Format: "RTT-April-2026" or "RTT-FEBRUARY-2019"
    parts = raw.replace("RTT-", "").split("-")
    month_str, year_str = parts[0], parts[1]
    month = MONTH_MAP[month_str]
    return datetime.date(int(year_str), month, 1)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Connecting to DuckDB (in-memory)...")
    con = duckdb.connect()

    print("Loading modern series (Jan 2024 → May 2026)...")
    df_modern = load_modern_series(con)
    print(f"  → {len(df_modern):,} rows ({df_modern['period_raw'].nunique()} periods)")

    print("Loading Feb 2019 baseline...")
    df_base = load_baseline(con)
    print(f"  → {len(df_base):,} specialty rows")

    # Combine
    df = pd.concat([df_base, df_modern], ignore_index=True)

    # Parse dates, derive metrics
    df["date"] = df["period_raw"].apply(parse_period)
    df["pct_within_18w"] = (df["waiting_0_18w"] / df["total_waiting"] * 100).round(2)
    df["pct_over_52w"]   = (df["waiting_52w_plus"] / df["total_waiting"] * 100).round(2)
    df.sort_values("date", inplace=True)

    df.to_csv(OUTPUT_DIR / "rtt_trajectory_full_panel.csv", index=False)
    print(f"\nSaved: outputs/rtt_trajectory_full_panel.csv")

    # National aggregates per period (all providers pooled)
    nat = df.groupby(["date", "period_raw", "specialty_code"]).agg(
        total_waiting    = ("total_waiting",    "sum"),
        waiting_0_18w    = ("waiting_0_18w",    "sum"),
        waiting_18_52w   = ("waiting_18_52w",   "sum"),
        waiting_52w_plus = ("waiting_52w_plus", "sum"),
    ).reset_index()
    nat["pct_within_18w"] = (nat["waiting_0_18w"] / nat["total_waiting"] * 100).round(2)
    nat["pct_over_52w"]   = (nat["waiting_52w_plus"] / nat["total_waiting"] * 100).round(2)
    nat["specialty_name"] = nat["specialty_code"].map(SPECIALTIES)
    nat.sort_values("date", inplace=True)
    nat.to_csv(OUTPUT_DIR / "rtt_trajectory_national.csv", index=False)

    # -------------------------------------------------------------------------
    # ANALYSIS: Print the trajectory table for key specialties
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("TRAJECTORY: % within 18w and % over 52w — national, key specialties")
    print("=" * 80)
    key = nat[nat["specialty_code"].isin(SPECIALTIES)].copy()
    modern_only = key[key["date"] >= datetime.date(2024, 1, 1)]

    for spec_code, spec_name in SPECIALTIES.items():
        sub = modern_only[modern_only["specialty_code"] == spec_code].copy()
        if sub.empty:
            continue
        first = sub.iloc[0]
        last  = sub.iloc[-1]
        # Compute percentages unrounded from raw counts — rounding the monthly
        # columns first can shift the endpoint delta by 0.1pp
        first_18 = first.waiting_0_18w / first.total_waiting * 100
        last_18  = last.waiting_0_18w / last.total_waiting * 100
        first_52 = first.waiting_52w_plus / first.total_waiting * 100
        last_52  = last.waiting_52w_plus / last.total_waiting * 100
        d_short = last_18 - first_18
        d_tail  = last_52 - first_52
        print(f"\n{spec_name}:")
        print(f"  Jan 2024 → May 2026: % within 18w {first_18:.1f}% → {last_18:.1f}% "
              f"(Δ {d_short:+.1f}pp)")
        print(f"  Jan 2024 → May 2026: % over 52w   {first_52:.1f}% → {last_52:.1f}% "
              f"(Δ {d_tail:+.1f}pp)")
        ratio = abs(d_short) / max(abs(d_tail), 0.01)
        print(f"  Ratio (absolute pp terms): {ratio:.1f}×")

    # -------------------------------------------------------------------------
    # CHARTS
    # -------------------------------------------------------------------------
    print("\nGenerating charts...")
    _chart_trajectory(key)
    _chart_gastro_detail(key)
    print("Done. Check charts/ folder.")


def _chart_trajectory(key: pd.DataFrame):
    """
    For each key specialty: dual-line chart showing % within 18w (improving)
    vs % over 52w (also improving, but smaller magnitude), Jan 2024 → May 2026.
    The visual gap between the two rates shows the distribution pattern.
    """
    specs = [s for s in SPECIALTIES.items() if s[0] in key["specialty_code"].values]
    n = len(specs)
    cols = 4
    rows = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(17, rows * 4.2), sharey=True)
    axes = axes.flatten()

    modern = key[key["date"] >= datetime.date(2024, 1, 1)]

    for idx, (code, name) in enumerate(specs):
        ax = axes[idx]
        sub = modern[modern["specialty_code"] == code].sort_values("date")
        if sub.empty:
            ax.set_visible(False)
            continue

        ax.plot(sub["date"], sub["pct_within_18w"], color="#2196F3", linewidth=2,
                marker="o", markersize=3, label="% within 18 weeks")
        ax.plot(sub["date"], sub["pct_over_52w"],   color="#FF9800", linewidth=2,
                marker="o", markersize=3, label="% over 52 weeks")

        ax.axhline(92, color="darkgreen", linestyle=":", linewidth=0.8, alpha=0.6)
        ax.axhline(65, color="navy",      linestyle=":", linewidth=0.8, alpha=0.6)

        ax.set_title(name, fontsize=11, fontweight="bold")
        ax.set_xlabel("")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=35, ha="right", fontsize=7)
        ax.set_ylabel("% of pathways", fontsize=8)
        ax.grid(axis="y", alpha=0.3)

    # Hide empty subplots
    for idx in range(len(specs), len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle(
        "NHS elective recovery: short-wait cohort vs long-wait tail (Jan 2024 → May 2026)\n"
        "Blue = % within 18 weeks  |  Orange = % over 52 weeks  |  "
        "Green dotted line = 92% standard  |  Blue dotted line = 65% interim target",
        fontsize=11, y=1.01
    )
    fig.tight_layout()
    path = CHART_DIR / "chart3_trajectory_by_specialty.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path.name}")


def _chart_gastro_detail(key: pd.DataFrame):
    """
    Gastroenterology only — clean single chart with Feb 2019 baseline anchor.
    The headline chart for the brief.
    """
    gastro = key[key["specialty_code"] == "C_301"].sort_values("date")
    modern = gastro[gastro["date"] >= datetime.date(2024, 1, 1)]
    baseline = gastro[gastro["date"] < datetime.date(2024, 1, 1)]

    fig, ax = plt.subplots(figsize=(11, 5))

    ax.plot(modern["date"], modern["pct_within_18w"], color="#2196F3",
            linewidth=2.5, marker="o", markersize=4, label="% within 18 weeks (2024–2026)")
    ax.plot(modern["date"], modern["pct_over_52w"],   color="#FF9800",
            linewidth=2.5, marker="o", markersize=4, label="% over 52 weeks (2024–2026)")

    # Feb 2019 baseline anchors
    if not baseline.empty:
        b = baseline.iloc[0]
        ax.scatter([b.date], [b.pct_within_18w], color="#2196F3", s=80,
                   zorder=5, marker="D", label=f"Feb 2019 baseline (within 18w): {b.pct_within_18w:.1f}%")
        ax.scatter([b.date], [b.pct_over_52w],   color="#FF9800", s=80,
                   zorder=5, marker="D", label=f"Feb 2019 baseline (over 52w): {b.pct_over_52w:.2f}%")
        # Dashed line to show gap from baseline
        ax.axhline(b.pct_within_18w, color="#2196F3", linestyle="--", linewidth=0.8, alpha=0.4)

    ax.axhline(92, color="darkgreen", linestyle=":", linewidth=1,
               alpha=0.7, label="92% constitutional standard")
    ax.axhline(65, color="navy",      linestyle=":", linewidth=1,
               alpha=0.7, label="65% interim target (Mar 2026)")

    ax.set_xlabel("")
    ax.set_title("Gastroenterology — waiting list recovery: 18-week cohort vs 52-week tail\n"
                 "National aggregate, Part_2 incomplete pathways. Source: NHS England open data.",
                 fontsize=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=35, ha="right", fontsize=9)
    ax.set_ylabel("% of incomplete pathways")
    ax.legend(fontsize=8, loc="center right")
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    path = CHART_DIR / "chart4_gastro_trajectory_detail.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path.name}")


if __name__ == "__main__":
    main()
