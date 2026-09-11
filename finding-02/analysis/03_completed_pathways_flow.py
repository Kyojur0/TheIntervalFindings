"""
Completed Pathways (FLOW) Analysis
===================================
The Incomplete Pathways data (Part_2) is a STOCK snapshot — who is waiting.
Completed Pathways (Part_1A admitted + Part_1B non-admitted) is FLOW — of the
pathways COMPLETED this period (treatment or other clock stop),
how long had those patients waited?

This adds limited flow context to the stock analysis. Because Part_1B combines
outpatient treatment with non-treatment clock stops, it cannot distinguish why
every pathway closed and does not identify treatment prioritisation.

Compares Feb 2025 vs Apr 2026 throughput by waiting-time cohort and specialty.
Rows coded NONC are excluded to match official England RTT reporting scope.
"""

import duckdb
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]  # The Interval project root
DATA_DIR = BASE_DIR / "data" / "source_research"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"

OUTPUT_DIR.mkdir(exist_ok=True)

RTT_APR26 = str(DATA_DIR / "20260430-RTT-April-2026-full-extract.csv")
RTT_FEB25 = str(DATA_DIR / "20250228-RTT-February-2025-full-extract-revised.csv")

def week_col(i: int) -> str:
    if i == 104:
        return "Gt 104 Weeks SUM 1"
    return f"Gt {i:02d} To {i+1:02d} Weeks SUM 1"

COLS_0_18   = [week_col(i) for i in range(0, 18)]
COLS_18_52  = [week_col(i) for i in range(18, 52)]
COLS_52P    = [week_col(i) for i in range(52, 104)] + [week_col(104)]
ALL_WEEK_COLS = COLS_0_18 + COLS_18_52 + COLS_52P

SPECIALTIES = {
    "C_301": "Gastroenterology", "C_130": "Ophthalmology", "C_120": "ENT",
    "C_100": "General Surgery", "C_110": "Trauma & Orthopaedics", "C_320": "Cardiology",
    "C_400": "Neurology",
}

def flow_sql(csv_path: str, label: str) -> str:
    """Completed pathways = Part_1A (admitted) + Part_1B (non-admitted).
    Note: Part 1B includes non-treatment clock stops (e.g. patient declined, DNA).
    These are pathway completions, not pure treatment counts."""
    c_0_18 = " + ".join([f'COALESCE("{c}", 0)' for c in COLS_0_18])
    c_18_52 = " + ".join([f'COALESCE("{c}", 0)' for c in COLS_18_52])
    c_52p = " + ".join([f'COALESCE("{c}", 0)' for c in COLS_52P])
    c_all = " + ".join([f'COALESCE("{c}", 0)' for c in ALL_WEEK_COLS])
    return f"""
    SELECT
        '{label}' AS period,
        "Treatment Function Code" AS specialty_code,
        SUM({c_all})  AS completed_total,
        SUM({c_0_18}) AS completed_0_18w,
        SUM({c_18_52}) AS completed_18_52w,
        SUM({c_52p})  AS completed_52w_plus
    FROM read_csv_auto('{csv_path}')
    WHERE "RTT Part Type" IN ('Part_1A', 'Part_1B')
      AND COALESCE("Commissioner Org Code", '') <> 'NONC'
    GROUP BY 1, 2
    HAVING SUM({c_all}) > 0
    """

def main():
    con = duckdb.connect()
    print("Loading completed pathways (flow) for both periods...")
    feb = con.execute(flow_sql(RTT_FEB25, "Feb-2025")).df()
    apr = con.execute(flow_sql(RTT_APR26, "Apr-2026")).df()
    df = pd.concat([feb, apr], ignore_index=True)
    df.to_csv(OUTPUT_DIR / "rtt_completed_pathways_flow.csv", index=False)

    key = df[df.specialty_code.isin(SPECIALTIES)].copy()
    key["specialty"] = key.specialty_code.map(SPECIALTIES)

    print("\n" + "=" * 78)
    print("MONTHLY THROUGHPUT by waiting cohort — pathways COMPLETED in the month")
    print("=" * 78)
    for period in ["Feb-2025", "Apr-2026"]:
        sub = key[key.period == period]
        print(f"\n--- {period} ---")
        show = sub[["specialty", "completed_0_18w", "completed_18_52w", "completed_52w_plus"]]
        print(show.to_string(index=False))

    # Share of completed pathways going to the long-wait tail
    print("\n" + "=" * 78)
    print("SHARE of monthly completed pathways going to the 52w+ tail")
    print("=" * 78)
    key["pct_completed_from_tail"] = (key.completed_52w_plus / key.completed_total * 100).round(2)
    pivot = key.pivot_table(index="specialty", columns="period",
                            values="pct_completed_from_tail")
    print(pivot.round(2).to_string())
    key.to_csv(OUTPUT_DIR / "rtt_flow_tail_share.csv", index=False)

if __name__ == "__main__":
    main()
