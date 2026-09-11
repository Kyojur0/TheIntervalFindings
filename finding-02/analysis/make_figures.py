#!/usr/bin/env python3
"""Finding 02 — draw the published figures to The Interval's figure spec.

Reads the verified tables in ``outputs/`` and writes light and dark variants
into ``figures/``. Run from anywhere:

    python analysis/make_figures.py
"""
from pathlib import Path

import pandas as pd

from figure_spec import MONO, THEMES, right_labels, save, source, style_ax, title

PACK = Path(__file__).resolve().parents[1]
OUT, FIG = PACK / "outputs", PACK / "figures"
FIG.mkdir(exist_ok=True)

STANDARD, INTERIM = 92.0, 65.0
MODERN_START = "2023-12-01"
SRC = "Source: NHS England RTT, Jan 2024 - May 2026  ·  Analysis: The Interval"

SPECIALTIES = [
    ("C_130", "Ophthalmology"), ("C_320", "Cardiology"), ("C_301", "Gastroenterology"),
    ("C_400", "Neurology"), ("C_120", "Ear, Nose & Throat"), ("C_100", "General Surgery"),
    ("C_110", "Trauma & Orthopaedics"),
]


def load():
    df = pd.read_csv(OUT / "rtt_trajectory_national.csv", parse_dates=["date"])
    return df[df["specialty_code"].isin([c for c, _ in SPECIALTIES])]


def year_ticks(ax, c, series):
    years = sorted({d.year for d in series})
    ax.set_xticks([pd.Timestamp(f"{y}-01-01") for y in years if y >= 2024])
    ax.set_xticklabels([str(y) for y in years if y >= 2024], fontsize=7.5)


def fig_trajectory_grid(theme):
    import matplotlib.pyplot as plt

    c = THEMES[theme]
    df = load()
    df = df[df["date"] >= MODERN_START]

    fig, axes = plt.subplots(2, 4, figsize=(11.5, 6.1), facecolor=c["bg"], sharey=True)
    fig.subplots_adjust(left=0.055, right=0.985, top=0.70, bottom=0.11,
                        wspace=0.16, hspace=0.42)

    for ax, (code, name) in zip(axes.ravel(), SPECIALTIES):
        sub = df[df["specialty_code"] == code].sort_values("date")
        style_ax(ax, c)
        ax.axhline(STANDARD, color=c["teal"], lw=1.0, ls=(0, (5, 4)), zorder=1)
        ax.axhline(INTERIM, color=c["muted"], lw=0.8, ls=(0, (2, 3)), zorder=1)
        ax.plot(sub["date"], sub["pct_within_18w"], color=c["ink"], lw=1.9, zorder=3)
        ax.plot(sub["date"], sub["pct_over_52w"], color=c["vermilion"], lw=1.9, zorder=3)
        ax.set_title(name, family=MONO, fontsize=8.5, color=c["ink"], pad=8)
        ax.set_ylim(-3, 100)
        ax.set_yticks([0, 25, 50, 75, 100])
        year_ticks(ax, c, sub["date"])

    first = axes[0][0]
    sub = df[df["specialty_code"] == SPECIALTIES[0][0]].sort_values("date")
    first.text(sub["date"].iloc[1], sub["pct_within_18w"].iloc[0] + 7, "WITHIN 18W",
               family=MONO, fontsize=7, color=c["ink"])
    first.text(sub["date"].iloc[1], sub["pct_over_52w"].iloc[0] + 7, "OVER 52W",
               family=MONO, fontsize=7, color=c["vermilion"])
    first.text(sub["date"].iloc[1], STANDARD + 2.5, "92% STANDARD",
               family=MONO, fontsize=7, color=c["teal"])

    axes[1][3].set_visible(False)

    title(fig, c, "Both ends of the queue moved, and the short end moved further",
          "Share of incomplete pathways within 18 weeks and over 52 weeks,\n"
          "seven treatment functions, January 2024 to May 2026.",
          x=0.048, y=0.965)
    source(fig, c, SRC, x=0.048, y=0.022)
    return save(fig, c, str(FIG / "chart3_trajectory_by_specialty"), theme)


def fig_gastro_detail(theme):
    import matplotlib.pyplot as plt

    c = THEMES[theme]
    df = load()
    gastro = df[df["specialty_code"] == "C_301"].sort_values("date")
    base = gastro[gastro["date"] < "2020-01-01"]
    modern = gastro[gastro["date"] >= MODERN_START]

    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=c["bg"])
    fig.subplots_adjust(left=0.075, right=0.775, top=0.735, bottom=0.135)
    style_ax(ax, c)

    # The February 2019 baseline is five years before the series starts. Drawing
    # it on the shared axis would leave most of the chart empty, so it is shown
    # as a reference level instead of a plotted point.
    marks = []
    if len(base):
        b = base.iloc[0]
        for value, colour in ((b.pct_within_18w, c["ink"]), (b.pct_over_52w, c["vermilion"])):
            ax.axhline(value, color=colour, lw=0.9, ls=(0, (1, 3)), zorder=1, alpha=0.8)
        marks.append((b.pct_within_18w, f"FEB 2019  {b.pct_within_18w:.1f}%", c["ink"]))

    ax.axhline(STANDARD, color=c["teal"], lw=1.1, ls=(0, (5, 4)), zorder=1)
    ax.axhline(INTERIM, color=c["muted"], lw=0.8, ls=(0, (2, 3)), zorder=1)
    marks += [(STANDARD, "92%  STANDARD", c["teal"]), (INTERIM, "65%  INTERIM", c["muted"])]

    ax.plot(modern["date"], modern["pct_within_18w"], color=c["ink"], lw=2.2, zorder=3)
    ax.plot(modern["date"], modern["pct_over_52w"], color=c["vermilion"], lw=2.2, zorder=3)

    last = modern.iloc[-1]
    marks += [(last.pct_within_18w, f"WITHIN 18W  {last.pct_within_18w:.1f}%", c["ink"]),
              (last.pct_over_52w, f"OVER 52W  {last.pct_over_52w:.1f}%", c["vermilion"])]
    right_labels(ax, marks)

    ax.set_ylim(-3, 100)
    ax.set_yticks([0, 25, 50, 75, 100])
    year_ticks(ax, c, modern["date"])
    ax.set_ylabel("% of incomplete pathways", family=MONO, fontsize=8,
                  color=c["muted"], labelpad=9)

    gap = base.iloc[0].pct_within_18w - last.pct_within_18w if len(base) else 0
    title(fig, c, "Gastroenterology is still short of where it started",
          f"National aggregate. The within-18-week share remains {gap:.1f} points below\n"
          f"the February 2019 baseline, five years after it was set.")
    source(fig, c, "Source: NHS England RTT, Feb 2019 and Jan 2024 - May 2026  ·  Analysis: The Interval")
    return save(fig, c, str(FIG / "chart4_gastro_trajectory_detail"), theme)


def main():
    for theme in ("light", "dark"):
        print(" ", fig_trajectory_grid(theme))
        print(" ", fig_gastro_detail(theme))


if __name__ == "__main__":
    main()
