#!/usr/bin/env python3
"""
Finding 02 — Where the longest waits concentrate
================================================

The Interval · reproducibility pack

Produces every figure and summary statistic in Finding 02 from the CSVs in
`data/`. Run from anywhere:

    python analysis/make_figures.py

Outputs
-------
figures/fig1_concentration_scatter.png  share of the waiting list vs median wait
figures/fig2_specialty_bars.png         median wait by specialty vs the standard
figures/fig3_dumbbell_2019.png          same month 2019 vs latest, by specialty
outputs/quadrant_classification.csv     each specialty classified by size and breach
outputs/spread_summary.csv              the specialty spread, latest and 2019
outputs/table1_summary.csv              the published summary table, with breach flags

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
AVG_SHARE = 7.0  # average specialty share of the national waiting list (%)
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
# Figure 1 — the concentration map: share of list against median wait
# ----------------------------------------------------------------------------
def fig1_concentration_scatter():
    points = duckdb.sql(
        f"""
        SELECT specialty, share_of_list_pct, median_weeks,
               median_weeks > 18      AS breaches,
               share_of_list_pct > 7  AS big_list
        FROM '{DATA / 'specialty_concentration_sample.csv'}'
        """
    ).df()

    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    style_ax(ax)
    ax.yaxis.grid(True, color=HAIRLINE, lw=0.8)
    standard_line(ax, y=STANDARD)
    ax.axvline(AVG_SHARE, color=HAIRLINE, lw=1.1, ls=(0, (2, 4)), zorder=1)

    for _, p in points.iterrows():
        colour = VERMILION if p["breaches"] else TEAL
        ax.scatter([p["share_of_list_pct"]], [p["median_weeks"]],
                   color=colour, s=44, alpha=0.9, zorder=3)
        short = (p["specialty"].replace("Trauma & orthopaedics", "Trauma & ortho.")
                 .replace("Ear nose & throat", "ENT"))
        ax.annotate(short, (p["share_of_list_pct"], p["median_weeks"]),
                    textcoords="offset points", xytext=(9, -2), fontfamily=MONO,
                    fontsize=8, color=INK if p["breaches"] else MUTED)

    ax.text(15.6, STANDARD + 0.35, "18 WKS", fontfamily=MONO, fontsize=8.5,
            color=TEAL, ha="right")
    ax.text(AVG_SHARE, 29.4, "AVG SHARE", fontfamily=MONO, fontsize=7.5,
            color=MUTED, ha="center")
    ax.text(15.4, 29.4, "HIGH VOLUME + LONG WAITS", fontfamily=MONO, fontsize=8,
            color=VERMILION, alpha=0.75, ha="right")

    ax.set_xlim(0, 16)
    ax.set_ylim(12, 30)
    ax.set_xticks([0, 4, 8, 12, 16])
    ax.set_xticklabels(["0%", "4%", "8%", "12%", "16%"])
    ax.set_xlabel("SHARE OF THE LIST", fontfamily=MONO, fontsize=8, color=MUTED, labelpad=8)
    header(fig, "FIG. 1", "Long waits concentrate in high-volume surgical specialties",
           "Share of the waiting list (%) against median wait (weeks), by specialty")
    footer(fig)
    fig.subplots_adjust(left=0.08, right=0.96, top=0.80, bottom=0.14)
    save(fig, "fig1_concentration_scatter.png")

    # quadrant classification, derived in DuckDB
    classified = duckdb.sql(
        """
        SELECT specialty, share_of_list_pct, median_weeks,
               breaches, big_list,
               CASE WHEN breaches AND big_list     THEN 'top_right · big and slow'
                    WHEN breaches AND NOT big_list THEN 'top_left · small and slow'
                    WHEN big_list                  THEN 'bottom_right · big and fast'
                    ELSE                                'bottom_left · small and fast'
               END AS quadrant
        FROM points
        ORDER BY share_of_list_pct DESC
        """
    ).df()
    classified.to_csv(OUTS / "quadrant_classification.csv", index=False)
    print("  wrote outputs/quadrant_classification.csv")


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

    # the spread, latest month, derived in DuckDB
    spread = duckdb.sql(
        """
        SELECT round(max(median_weeks), 1)              AS longest_median_weeks,
               round(min(median_weeks), 1)              AS shortest_median_weeks,
               round(max(median_weeks) - min(median_weeks), 1) AS spread_weeks
        FROM spec
        """
    ).df()
    spread.to_csv(OUTS / "spread_summary.csv", index=False)
    print("  wrote outputs/spread_summary.csv")


# ----------------------------------------------------------------------------
# Figure 3 — the five-year widening, dumbbells
# ----------------------------------------------------------------------------
def fig3_dumbbell():
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
    header(fig, "FIG. 3", "In five years, typical waits have roughly doubled",
           "Median referral-to-treatment wait by specialty, same month 2019 vs latest (weeks)")
    footer(fig)
    fig.subplots_adjust(left=0.22, right=0.95, top=0.80, bottom=0.13)
    save(fig, "fig3_dumbbell.png")


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
    print("Finding 02 — building figures and outputs")
    fig1_concentration_scatter()
    fig2_specialty_bars()
    fig3_dumbbell()
    table1()
    print("Done. Data vintage: SAMPLE (design preview).")
