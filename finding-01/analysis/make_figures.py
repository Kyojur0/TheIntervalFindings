#!/usr/bin/env python3
"""
Finding 01 — The 18-week standard, becoming the exception
=========================================================

The Interval · reproducibility pack

Produces every figure and summary statistic in Finding 01 from the CSVs in
`data/`. Run from anywhere:

    python analysis/make_figures.py

Outputs
-------
figures/fig1_median_series.png      national median wait vs the 18-week standard
figures/fig2_specialty_bars.png     median wait by specialty vs the standard
figures/fig3_regional_tiles.png     median wait by NHS region (tile map)
figures/fig4_dumbbell_2019.png      same month 2019 vs latest, by specialty
outputs/national_summary.csv        crossing month, latest median, distance past standard
outputs/table1_summary.csv          the published summary table, with breach flags

Data vintage: SAMPLE data for the design preview. The verified NHS England RTT
extracts drop into `data/` with the same column names; the code does not change.

Pipeline: DuckDB for derivation, pandas for shaping, matplotlib for figures.
Requires: python >= 3.10, duckdb, pandas, matplotlib.
"""

from pathlib import Path

import duckdb
import pandas as pd

try:  # managed runtime helper (The Interval's own environment)
    from daimon_runtime import setup_plot

    setup_plot()
except ImportError:  # standalone: any reader's machine
    import matplotlib

    matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# ----------------------------------------------------------------------------
# The Interval figure specification
# ----------------------------------------------------------------------------
PAPER = "#FBFAF6"
INK = "#1C1B17"
MUTED = "#6E6A5E"
HAIRLINE = "#D8D3C6"
TEAL = "#2E6F6A"
VERMILION = "#C2492B"
MONO = "DejaVu Sans Mono"
STANDARD = 18.0
SOURCE_LINE = "SAMPLE DATA · SOURCE: NHS ENGLAND RTT STATISTICS · ANALYSIS: THE INTERVAL"

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIGS = ROOT / "figures"
OUTS = ROOT / "outputs"
FIGS.mkdir(exist_ok=True)
OUTS.mkdir(exist_ok=True)


def style_ax(ax):
    """Shared canvas: paper background, hairline grid, no chart furniture."""
    ax.set_facecolor(PAPER)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0, colors=MUTED, labelsize=9)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontfamily(MONO)


def standard_line(ax, x=None, y=None):
    """The dashed teal standard, drawn the same way on every figure."""
    if y is not None:
        ax.axhline(y, color=TEAL, lw=1.1, ls=(0, (5, 4)), zorder=1)
    if x is not None:
        ax.axvline(x, color=TEAL, lw=1.1, ls=(0, (5, 4)), zorder=1)


def header(fig, kicker, title, sub, y=0.97):
    """Left-aligned kicker / title / subtitle block, matching the site."""
    fig.text(0.06, y, kicker, fontfamily=MONO, fontsize=9, color=VERMILION)
    fig.text(0.06, y - 0.055, title, fontsize=14, fontweight="bold", color=INK)
    fig.text(0.06, y - 0.10, sub, fontsize=9.5, color=MUTED)


def footer(fig, note=SOURCE_LINE):
    fig.text(0.06, 0.02, note, fontfamily=MONO, fontsize=7, color=MUTED)


def save(fig, name):
    fig.savefig(FIGS / name, dpi=220, facecolor=PAPER, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote figures/{name}")


# ----------------------------------------------------------------------------
# Figure 1 — the national median series against the standard
# ----------------------------------------------------------------------------
def fig1_median_series():
    series = pd.read_csv(DATA / "rtt_median_series_sample.csv", parse_dates=["month"])
    derived = duckdb.sql(
        """
        SELECT month, median_weeks,
               median_weeks > 18 AS breaches,
               min(month) FILTER (WHERE median_weeks > 18) OVER () AS first_breach
        FROM series
        """
    ).df()

    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    style_ax(ax)
    ax.yaxis.grid(True, color=HAIRLINE, lw=0.8)
    standard_line(ax, y=STANDARD)

    breach = derived.loc[derived["breaches"]]
    within = derived.loc[~derived["breaches"]]
    # ink up to the crossing, vermilion beyond it, shaded breach area
    bridge = pd.concat([within.tail(1), breach.head(1)])
    ax.plot(pd.concat([within, breach.head(1)])["month"],
            pd.concat([within, breach.head(1)])["median_weeks"], color=INK, lw=1.8, zorder=3)
    ax.plot(bridge["month"], bridge["median_weeks"], color=INK, lw=1.8, zorder=3)
    ax.plot(breach["month"], breach["median_weeks"], color=VERMILION, lw=1.8, zorder=3)
    ax.fill_between(breach["month"], STANDARD, breach["median_weeks"],
                    color=VERMILION, alpha=0.12, zorder=2)

    last = derived.iloc[-1]
    ax.scatter([last["month"]], [last["median_weeks"]], color=VERMILION, s=28, zorder=4)
    ax.annotate(f"{last['median_weeks']:.1f} WEEKS", (last["month"], last["median_weeks"]),
                textcoords="offset points", xytext=(10, -2), fontfamily=MONO,
                fontsize=9.5, color=VERMILION)
    ax.text(derived["month"].iloc[-1], STANDARD - 0.9, "18 WKS · THE STANDARD",
            fontfamily=MONO, fontsize=8.5, color=TEAL, ha="right")

    ax.set_ylim(12, 25)
    ax.set_xlim(derived["month"].iloc[0], derived["month"].iloc[-1])
    header(fig, "FIG. 1", "The median wait has sat above the standard for over a year",
           "Median referral-to-treatment wait, completed admitted pathways, England (weeks)")
    footer(fig)
    fig.subplots_adjust(left=0.08, right=0.96, top=0.80, bottom=0.12)
    save(fig, "fig1_median_series.png")

    # national summary, derived in DuckDB
    summary = duckdb.sql(
        """
        SELECT
          strftime(min(month) FILTER (WHERE median_weeks > 18), '%Y-%m') AS first_breach_month,
          max(median_weeks)                                             AS latest_median_weeks,
          round(max(median_weeks) - 18, 1)                              AS weeks_past_standard
        FROM derived
        """
    ).df()
    summary.to_csv(OUTS / "national_summary.csv", index=False)
    print("  wrote outputs/national_summary.csv")


# ----------------------------------------------------------------------------
# Figure 2 — median wait by specialty against the standard
# ----------------------------------------------------------------------------
def fig2_specialty_bars():
    spec = duckdb.sql(
        f"""
        SELECT specialty, median_weeks, median_weeks > 18 AS breaches
        FROM '{DATA / 'specialty_medians_sample.csv'}'
        ORDER BY median_weeks ASC
        """
    ).df()

    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    style_ax(ax)
    ax.xaxis.grid(True, color=HAIRLINE, lw=0.8)
    colors = [VERMILION if b else TEAL for b in spec["breaches"]]
    ax.barh(spec["specialty"], spec["median_weeks"], color=colors, alpha=0.88, height=0.62, zorder=3)
    standard_line(ax, x=STANDARD)
    for i, (_, row) in enumerate(spec.iterrows()):
        ax.text(row["median_weeks"] + 0.35, i, f"{row['median_weeks']:.1f}",
                va="center", fontfamily=MONO, fontsize=9.5,
                color=VERMILION if row["breaches"] else TEAL)
    ax.text(STANDARD, len(spec) - 0.1, "18 WKS", fontfamily=MONO, fontsize=8.5,
            color=TEAL, ha="center", va="bottom")
    ax.set_xlim(0, 31)
    ax.set_xticks([0, 6, 12, 18, 24, 30])
    header(fig, "FIG. 2", "Trauma & orthopaedics waits run nine weeks past the standard",
           "Median referral-to-treatment wait by specialty, latest published month (weeks)")
    footer(fig)
    fig.subplots_adjust(left=0.22, right=0.95, top=0.80, bottom=0.13)
    save(fig, "fig2_specialty_bars.png")


# ----------------------------------------------------------------------------
# Figure 3 — the regional tile map
# ----------------------------------------------------------------------------
def fig3_regional_tiles():
    regions = pd.read_csv(DATA / "regional_medians_sample.csv")
    # tile grid positions, roughly where the regions sit on the map
    pos = {"NW": (0, 0), "NEY": (1, 0), "MID": (0, 1), "EoE": (1, 1),
           "SW": (0, 2), "LON": (1, 2), "SE": (2, 2)}
    vmin, vmax = regions["median_weeks"].min(), regions["median_weeks"].max()
    alpha = lambda v: 0.20 + (v - vmin) / (vmax - vmin) * 0.65

    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    ax.set_facecolor(PAPER)
    ax.set_xlim(-0.15, 5.6)
    ax.set_ylim(-0.15, 3.15)
    ax.invert_yaxis()
    ax.axis("off")

    for _, r in regions.iterrows():
        col, row = pos[r["code"]]
        a = alpha(r["median_weeks"])
        ax.add_patch(Rectangle((col, row), 0.9, 0.9, facecolor=VERMILION,
                               alpha=a, edgecolor=HAIRLINE, lw=0.8))
        ink = PAPER if a > 0.55 else INK
        ax.text(col + 0.09, row + 0.24, r["code"], fontfamily=MONO, fontsize=10,
                fontweight="bold", color=ink)
        ax.text(col + 0.09, row + 0.62, f"{r['median_weeks']:.1f}", fontsize=17, color=ink)
        ax.text(col + 0.09, row + 0.80, "WEEKS", fontfamily=MONO, fontsize=6.5, color=ink, alpha=0.8)

    ranked = regions.sort_values("median_weeks", ascending=False).reset_index(drop=True)
    ax.text(3.6, 0.06, "RANKED · MEDIAN WAIT (WEEKS)", fontfamily=MONO, fontsize=8, color=MUTED)
    for i, r in ranked.iterrows():
        y = 0.32 + i * 0.38
        ax.add_patch(Rectangle((3.6, y - 0.11), 0.09, 0.09, facecolor=VERMILION,
                               alpha=alpha(r["median_weeks"]), edgecolor="none"))
        ax.text(3.78, y, r["region"], fontsize=9.5, color=INK, va="center")
        ax.text(5.5, y, f"{r['median_weeks']:.1f}", fontfamily=MONO, fontsize=9.5,
                color=INK, va="center", ha="right")
    ax.text(3.6, 3.02, "THE STANDARD IS 18. ALL SEVEN REGIONS MISS IT.",
            fontfamily=MONO, fontsize=7.5, color=MUTED)

    header(fig, "FIG. 3", "Every region breaches; the South West sits furthest past the line",
           "Median referral-to-treatment wait by NHS region, latest published month (weeks)")
    footer(fig)
    fig.subplots_adjust(left=0.04, right=0.98, top=0.80, bottom=0.10)
    save(fig, "fig3_regional_tiles.png")


# ----------------------------------------------------------------------------
# Figure 4 — the five-year widening, dumbbells
# ----------------------------------------------------------------------------
def fig4_dumbbell():
    comp = duckdb.sql(
        f"""
        SELECT specialty, median_2019, median_latest,
               round(median_latest - median_2019, 1) AS change_weeks
        FROM '{DATA / 'specialty_2019_comparison_sample.csv'}'
        ORDER BY median_latest ASC
        """
    ).df()

    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    style_ax(ax)
    ax.xaxis.grid(True, color=HAIRLINE, lw=0.8)
    standard_line(ax, x=STANDARD)
    for i, (_, r) in enumerate(comp.iterrows()):
        ax.plot([r["median_2019"], r["median_latest"]], [i, i],
                color=HAIRLINE, lw=2.4, zorder=2, solid_capstyle="round")
        ax.scatter([r["median_2019"]], [i], color=TEAL, s=34, zorder=3)
        ax.scatter([r["median_latest"]], [i], color=VERMILION, s=44, zorder=3)
        ax.text(r["median_latest"] + 0.4, i, f"+{r['change_weeks']:.1f}",
                va="center", fontfamily=MONO, fontsize=9.5, color=VERMILION)
    ax.set_yticks(range(len(comp)))
    ax.set_yticklabels(comp["specialty"])
    ax.text(STANDARD, -0.75, "18 WKS", fontfamily=MONO, fontsize=8.5, color=TEAL, ha="center")
    ax.scatter([], [], color=TEAL, s=34, label="2019")
    ax.scatter([], [], color=VERMILION, s=44, label="NOW")
    ax.legend(loc="lower right", frameon=False, fontsize=9, handletextpad=0.2)
    ax.set_xlim(6, 31)
    ax.set_xticks([6, 12, 18, 24, 30])
    header(fig, "FIG. 4", "In five years, typical waits have roughly doubled",
           "Median referral-to-treatment wait by specialty, same month 2019 vs latest (weeks)")
    footer(fig)
    fig.subplots_adjust(left=0.22, right=0.95, top=0.80, bottom=0.13)
    save(fig, "fig4_dumbbell.png")


# ----------------------------------------------------------------------------
# Table 1 — the published summary, with breach flags derived in DuckDB
# ----------------------------------------------------------------------------
def table1():
    summary = duckdb.sql(
        f"""
        SELECT specialty, median_weeks, p92_weeks, within_18_pct,
               median_weeks > 18 AS median_breaches
        FROM '{DATA / 'table1_summary_sample.csv'}'
        """
    ).df()
    summary.to_csv(OUTS / "table1_summary.csv", index=False)
    print("  wrote outputs/table1_summary.csv")


if __name__ == "__main__":
    print("Finding 01 — building figures and outputs")
    fig1_median_series()
    fig2_specialty_bars()
    fig3_regional_tiles()
    fig4_dumbbell()
    table1()
    print("Done. Data vintage: SAMPLE (design preview).")
