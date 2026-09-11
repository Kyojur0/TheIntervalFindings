#!/usr/bin/env python3
"""Finding 01 — draw the published figures to The Interval's figure spec.

Reads the verified tables in ``outputs/`` and writes light and dark variants
into ``figures/``. Run from anywhere:

    python analysis/make_figures.py

Regenerating the underlying tables from the NHS England extracts is a separate
step — see ``SOURCES.md`` and the numbered analysis scripts.
"""
from pathlib import Path

import pandas as pd

from figure_spec import MONO, THEMES, save, source, style_ax, title

PACK = Path(__file__).resolve().parents[1]
OUT, FIG = PACK / "outputs", PACK / "figures"
FIG.mkdir(exist_ok=True)

STANDARD, INTERIM, FLOOR = 92.0, 65.0, 500
SRC = "Source: NHS England RTT, April 2026  ·  Analysis: The Interval"


def fig_provider_distribution(theme):
    import matplotlib.pyplot as plt

    c = THEMES[theme]
    df = pd.read_csv(OUT / "rtt_gastro_trust_variation_apr26.csv")
    df = df[df["total_waiting"] >= FLOOR]
    v = df["pct_within_18w"]

    fig, ax = plt.subplots(figsize=(9, 5.1), facecolor=c["bg"])
    fig.subplots_adjust(left=0.075, right=0.965, top=0.74, bottom=0.135)
    style_ax(ax, c)

    bins = range(32, 103, 5)   # a bin edge lands exactly on the 92% standard
    n, edges, patches = ax.hist(v, bins=bins, zorder=2)
    for count, left, patch in zip(n, edges[:-1], patches):
        patch.set_facecolor(c["ink"] if left >= STANDARD else c["vermilion"])
        patch.set_edgecolor(c["bg"])
        patch.set_linewidth(1.2)

    # Headroom above the tallest bar so the threshold labels never sit on one.
    ax.set_ylim(0, max(n) * 1.24)
    label_y = max(n) * 1.11

    ax.axvline(STANDARD, color=c["teal"], lw=1.2, ls=(0, (5, 4)), zorder=3)
    ax.text(STANDARD - 1.2, label_y, "92%  THE STANDARD",
            family=MONO, fontsize=7.5, color=c["teal"], ha="right", va="center")
    ax.axvline(INTERIM, color=c["muted"], lw=0.9, ls=(0, (2, 3)), zorder=3)
    ax.text(INTERIM - 1.2, label_y, "65%  INTERIM TARGET",
            family=MONO, fontsize=7.5, color=c["muted"], ha="right", va="center")

    lo, hi = df.loc[v.idxmin()], df.loc[v.idxmax()]
    ax.annotate(f"{lo.pct_within_18w:.1f}%  {lo.provider_code}", xy=(lo.pct_within_18w, 0.6),
                xytext=(lo.pct_within_18w, max(n) * 0.42), family=MONO, fontsize=7.5,
                color=c["vermilion"], ha="center",
                arrowprops=dict(arrowstyle="-", color=c["vermilion"], lw=0.8))
    ax.annotate(f"{hi.pct_within_18w:.1f}%  {hi.provider_code}", xy=(hi.pct_within_18w, 0.6),
                xytext=(hi.pct_within_18w, max(n) * 0.42), family=MONO, fontsize=7.5,
                color=c["ink"], ha="center",
                arrowprops=dict(arrowstyle="-", color=c["ink"], lw=0.8))

    ax.set_xlim(31, 103)
    ax.set_xticks([30, 40, 50, 60, 70, 80, 90, 100])
    ax.set_xlabel("% of gastroenterology pathways within 18 weeks",
                  family=MONO, fontsize=8, color=c["muted"], labelpad=9)
    ax.set_ylabel("providers", family=MONO, fontsize=8, color=c["muted"], labelpad=9)

    title(fig, c, "Sixty points within one specialty",
          f"Each of {len(df)} providers reported at least {FLOOR} incomplete gastroenterology\n"
          f"pathways in April 2026. Vermilion marks the providers below the 92% standard.")
    source(fig, c, SRC)
    return save(fig, c, str(FIG / "chart2_gastro_trust_variation"), theme)


def fig_specialty_shift(theme):
    import matplotlib.pyplot as plt

    c = THEMES[theme]
    df = pd.read_csv(OUT / "rtt_endpoint_distribution_comparison.csv")
    # C_999 is the England total and the X0* codes are residual buckets, not
    # treatment functions. A specialty comparison must exclude both.
    df = df[df["specialty_code"].str.startswith("C_") & (df["specialty_code"] != "C_999")]
    df = df.nlargest(9, "total_apr26").sort_values("pct_18w_apr26")
    names = [n.replace(" Service", "") for n in df["specialty_name"]]
    y = range(len(df))

    fig, ax = plt.subplots(figsize=(9, 5.3), facecolor=c["bg"])
    fig.subplots_adjust(left=0.245, right=0.945, top=0.755, bottom=0.135)
    style_ax(ax, c, grid="x")

    for i, (_, r) in enumerate(df.iterrows()):
        ax.plot([r.pct_18w_feb25, r.pct_18w_apr26], [i, i],
                color=c["hairline"], lw=2.4, zorder=2, solid_capstyle="round")
        ax.scatter(r.pct_18w_feb25, i, s=34, color=c["muted"], zorder=3)
        ax.scatter(r.pct_18w_apr26, i, s=46, color=c["ink"], zorder=4)

    ax.axvline(STANDARD, color=c["teal"], lw=1.2, ls=(0, (5, 4)), zorder=1)
    ax.text(STANDARD - 0.6, len(df) - 0.35, "92%  THE STANDARD", family=MONO,
            fontsize=7.5, color=c["teal"], ha="right", va="center")

    top = df.iloc[-1]
    ax.text(top.pct_18w_feb25, len(df) - 1 + 0.42, "FEB 2025", family=MONO,
            fontsize=7, color=c["muted"], ha="center")
    ax.text(top.pct_18w_apr26, len(df) - 1 + 0.42, "APR 2026", family=MONO,
            fontsize=7, color=c["ink"], ha="center")

    ax.set_yticks(list(y))
    ax.set_yticklabels(names, fontsize=8.5)
    ax.set_xlim(45, 96)
    ax.set_xlabel("% within 18 weeks", family=MONO, fontsize=8,
                  color=c["muted"], labelpad=9)
    ax.set_ylim(-0.7, len(df) - 0.05)

    title(fig, c, "Every large specialty improved, none reached the standard",
          "The nine largest treatment functions by April 2026 waiting list,\n"
          "February 2025 to April 2026.")
    source(fig, c, "Source: NHS England RTT, Feb 2025 and Apr 2026  ·  Analysis: The Interval")
    return save(fig, c, str(FIG / "chart1_distribution_shift_by_specialty"), theme)


def main():
    for theme in ("light", "dark"):
        print(" ", fig_provider_distribution(theme))
        print(" ", fig_specialty_shift(theme))


if __name__ == "__main__":
    main()
