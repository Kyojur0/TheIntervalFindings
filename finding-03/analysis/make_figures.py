#!/usr/bin/env python3
"""Finding 03 — draw the published figures to The Interval's figure spec.

Reads the verified tables in ``outputs/`` and writes light and dark variants
into ``figures/``. Run from anywhere:

    python analysis/make_figures.py

Regenerating the underlying tables from the NHS England monthly series is a
separate step — see ``SOURCES.md`` and ``finding_03_pipeline.py``.
"""
from pathlib import Path

import pandas as pd

from figure_spec import MONO, THEMES, right_labels, save, series_colours, source, style_ax, title

PACK = Path(__file__).resolve().parents[1]
OUT, FIG = PACK / "outputs", PACK / "figures"
FIG.mkdir(exist_ok=True)

# Ordered by how much durable between-provider structure each carries, so every
# figure tells the four specialties in the same sequence.
ORDER = ["C_110", "C_301", "C_130", "C_120"]
SHORT = {"C_110": "Trauma & Orthopaedics", "C_301": "Gastroenterology",
         "C_130": "Ophthalmology", "C_120": "Ear, Nose & Throat"}
SRC = "Source: NHS England RTT, Jan 2024 - May 2026  ·  Analysis: The Interval"


def palette(c):
    return dict(zip(ORDER, series_colours(c)))


def year_ticks(ax, series):
    years = sorted({int(p[:4]) for p in series})
    ax.set_xticks([f"{y}-01" for y in years])
    ax.set_xticklabels([str(y) for y in years], fontsize=8)


def fig_spread_over_time(theme):
    import matplotlib.pyplot as plt

    c, pal = THEMES[theme], palette(THEMES[theme])
    df = pd.read_csv(OUT / "monthly_spread_floor500.csv")

    fig, ax = plt.subplots(figsize=(10, 5.4), facecolor=c["bg"])
    fig.subplots_adjust(left=0.075, right=0.755, top=0.72, bottom=0.135)
    style_ax(ax, c)

    marks = []
    for code in ORDER:
        sub = df[df["specialty_code"] == code].sort_values("period")
        ax.plot(sub["period"], sub["sd_pct"], color=pal[code], lw=2.1, zorder=3)
        marks.append((sub["sd_pct"].iloc[-1], SHORT[code], pal[code]))
    right_labels(ax, marks, min_gap=1.1, fontsize=8)

    ax.set_ylim(0, 18)
    ax.set_yticks([0, 5, 10, 15])
    year_ticks(ax, df["period"])
    ax.set_ylabel("standard deviation (pp)", family=MONO, fontsize=8,
                  color=c["muted"], labelpad=9)

    title(fig, c, "The gap between providers never closes",
          "Spread of provider performance against the 18-week standard, month by month.\n"
          "Providers with at least 500 pathways in that month.")
    source(fig, c, SRC)
    return save(fig, c, str(FIG / "fig1_spread_over_time"), theme)


def fig_rank_decay(theme):
    import matplotlib.pyplot as plt

    c, pal = THEMES[theme], palette(THEMES[theme])
    df = pd.read_csv(OUT / "rank_correlation_decay.csv")
    df = df[df["floor"] == 500]

    fig, ax = plt.subplots(figsize=(10, 5.4), facecolor=c["bg"])
    fig.subplots_adjust(left=0.075, right=0.755, top=0.72, bottom=0.135)
    style_ax(ax, c)

    marks = []
    for code in ORDER:
        sub = df[df["specialty_code"] == code].sort_values("lag_months")
        ax.plot(sub["lag_months"], sub["mean_spearman"], color=pal[code], lw=2.1, zorder=3)
        marks.append((sub["mean_spearman"].iloc[-1], SHORT[code], pal[code]))
    right_labels(ax, marks, min_gap=0.055, fontsize=8)

    ax.axhline(0, color=c["hairline"], lw=1.0, zorder=1)
    ax.set_ylim(0, 1.02)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlim(0, 29)
    ax.set_xlabel("months between the two snapshots", family=MONO, fontsize=8,
                  color=c["muted"], labelpad=9)
    ax.set_ylabel("rank correlation", family=MONO, fontsize=8, color=c["muted"], labelpad=9)

    title(fig, c, "Rankings drift, but they never reset",
          "How strongly a provider's position in one month predicts its position later.\n"
          "A value of 1 is a fixed league table; 0 is pure reshuffle.")
    source(fig, c, SRC)
    return save(fig, c, str(FIG / "fig2_rank_decay"), theme)


def fig_variance(theme):
    import matplotlib.pyplot as plt

    c, pal = THEMES[theme], palette(THEMES[theme])
    df = pd.read_csv(OUT / "variance_decomposition.csv")
    df = df[df["floor"] == 500].set_index("specialty_code")

    fig, ax = plt.subplots(figsize=(10, 4.3), facecolor=c["bg"])
    fig.subplots_adjust(left=0.235, right=0.93, top=0.665, bottom=0.17)
    style_ax(ax, c, grid="x")

    ys = range(len(ORDER))
    for i, code in enumerate(ORDER):
        r = df.loc[code]
        between = r["share_variance_between_providers"] * 100
        ax.barh(i, between, height=0.5, color=pal[code], zorder=3)
        ax.barh(i, 100 - between, left=between, height=0.5, color=c["hairline"], zorder=3)
        ax.text(between - 1.5, i, f"{between:.0f}%", family=MONO, fontsize=8.5,
                color=c["bg"], ha="right", va="center", zorder=4)

    ax.set_yticks(list(ys))
    ax.set_yticklabels([SHORT[c_] for c_ in ORDER], fontsize=9)
    ax.set_ylim(-0.6, len(ORDER) - 0.4)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("share of all variation (%)", family=MONO, fontsize=8,
                  color=c["muted"], labelpad=9)
    ax.text(0, len(ORDER) - 0.32, "BETWEEN PROVIDERS", family=MONO, fontsize=7.5, color=c["muted"])
    ax.text(100, len(ORDER) - 0.32, "MONTH TO MONTH", family=MONO, fontsize=7.5,
            color=c["muted"], ha="right")

    title(fig, c, "Most of the variation is the provider, not the month",
          "Splitting all the variation in performance into the part that separates providers\n"
          "from one another, and the part that is a provider moving around its own average.",
          y=0.945)
    source(fig, c, SRC, y=0.035)
    return save(fig, c, str(FIG / "fig3_variance_decomposition"), theme)


def fig_decile_survivors(theme):
    import matplotlib.pyplot as plt

    c, pal = THEMES[theme], palette(THEMES[theme])
    df = pd.read_csv(OUT / "persistence_summary.csv")
    df = df[(df["floor"] == 500) & (df["panel"] == "moving")].set_index("specialty_code")

    fig, ax = plt.subplots(figsize=(10, 4.5), facecolor=c["bg"])
    fig.subplots_adjust(left=0.235, right=0.93, top=0.655, bottom=0.165)
    style_ax(ax, c, grid="x")

    for i, code in enumerate(ORDER):
        r = df.loc[code]
        ax.barh(i, r["bottom_decile_survivors"], height=0.44, color=pal[code], zorder=3)
        ax.scatter(r["bottom_decile_expected_random"], i, s=52, color=c["bg"],
                   edgecolor=c["muted"], linewidth=1.4, zorder=5)
        ax.text(r["bottom_decile_survivors"] + 0.12, i,
                f"{int(r['bottom_decile_survivors'])} of {int(r['bottom_decile_start_n'])}",
                family=MONO, fontsize=8.5, color=c["ink"], va="center")

    ax.set_yticks(list(range(len(ORDER))))
    ax.set_yticklabels([SHORT[c_] for c_ in ORDER], fontsize=9)
    ax.set_ylim(-0.6, len(ORDER) - 0.3)
    ax.set_xlim(0, 8)
    ax.set_xticks([0, 2, 4, 6, 8])
    ax.set_xlabel("providers still in the bottom tenth, 28 months later",
                  family=MONO, fontsize=8, color=c["muted"], labelpad=9)
    ax.text(df["bottom_decile_expected_random"].mean(), len(ORDER) - 0.28,
            "○ EXPECTED BY CHANCE", family=MONO, fontsize=7.5, color=c["muted"], ha="center")

    title(fig, c, "The worst providers in 2024 are mostly still there",
          "Of the providers in the bottom tenth in January 2024, how many were still in the\n"
          "bottom tenth in May 2026 — against how many chance alone would leave.",
          y=0.945)
    source(fig, c, SRC, y=0.032)
    return save(fig, c, str(FIG / "fig4_decile_survivors"), theme)


def main():
    for theme in ("light", "dark"):
        for fn in (fig_spread_over_time, fig_rank_decay, fig_variance, fig_decile_survivors):
            print(" ", fn(theme))


if __name__ == "__main__":
    main()
