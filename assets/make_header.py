#!/usr/bin/env python3
"""
The Interval — README header image
==================================

Draws the archive's header banner in light (paper) and dark (ink) variants,
to The Interval's figure specification: ink within the 18-week standard,
vermilion beyond it, dashed teal where the standard lies.

    python assets/make_header.py

Outputs: assets/the-interval-header-light.png, assets/the-interval-header-dark.png
The series shown is the Finding 01 sample series; the header is a brand mark,
not a published figure.
"""

from pathlib import Path

import pandas as pd

try:
    from daimon_runtime import setup_plot

    setup_plot()
except ImportError:
    import matplotlib

    matplotlib.use("Agg")

import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
SERIF = "DejaVu Serif"
MONO = "DejaVu Sans Mono"
STANDARD = 18.0

# Finding 01 sample series (monthly median wait, weeks)
MONTHS = pd.date_range("2024-01", periods=24, freq="MS")
SERIES = [14.8, 14.6, 15.1, 15.3, 15.0, 15.6, 16.2, 16.8, 17.5, 18.2, 18.6, 19.1,
          19.8, 20.1, 20.7, 21.0, 21.4, 21.9, 22.2, 22.5, 22.8, 23.0, 23.2, 23.4]

VARIANTS = {
    "light": dict(bg="#FBFAF6", ink="#1C1B17", muted="#6E6A5E", hairline="#D8D3C6",
                  teal="#2E6F6A", vermilion="#C2492B"),
    "dark": dict(bg="#1B1915", ink="#F5F2E9", muted="#9A9484", hairline="#3A372D",
                 teal="#5FA8A0", vermilion="#D96A4A"),
}


def draw(name, c):
    fig = plt.figure(figsize=(16, 5))
    fig.patch.set_facecolor(c["bg"])

    # ——— wordmark block, left ———
    fig.text(0.055, 0.74, "THE INTERVAL", fontfamily=SERIF, fontsize=46,
             fontweight="bold", color=c["ink"])
    fig.text(0.057, 0.60, "NHS DATA, READ OUT LOUD", fontfamily=MONO,
             fontsize=12.5, color=c["vermilion"])
    fig.text(0.057, 0.455,
             "The NHS promises the wait from referral to treatment is 18 weeks.",
             fontfamily=SERIF, fontsize=13.5, color=c["muted"])
    fig.text(0.057, 0.375, "The data records what it actually is.",
             fontfamily=SERIF, fontsize=13.5, color=c["muted"])
    fig.text(0.057, 0.22, "THE FINDINGS ARCHIVE · EVERY NUMBER REPRODUCIBLE",
             fontfamily=MONO, fontsize=9, color=c["muted"])

    # ——— the signature series, right ———
    ax = fig.add_axes([0.50, 0.16, 0.455, 0.62])
    ax.set_facecolor(c["bg"])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0, colors=c["muted"], labelsize=9)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontfamily(MONO)

    ax.set_ylim(12, 25)
    ax.set_xlim(MONTHS[0], MONTHS[-1])
    ax.set_yticks([12, 15, 18, 21, 24])
    ax.set_xticks([MONTHS[0], MONTHS[12], MONTHS[-1]])
    ax.set_xticklabels(["JAN 24", "JAN 25", "DEC 25"])
    ax.yaxis.grid(True, color=c["hairline"], lw=0.8)

    ax.axhline(STANDARD, color=c["teal"], lw=1.2, ls=(0, (5, 4)), zorder=1)

    breach_start = next(i for i, v in enumerate(SERIES) if v > STANDARD)
    ax.plot(MONTHS[: breach_start + 1], SERIES[: breach_start + 1],
            color=c["ink"], lw=2, zorder=3)
    ax.plot(MONTHS[breach_start:], SERIES[breach_start:],
            color=c["vermilion"], lw=2, zorder=3)
    ax.fill_between(MONTHS[breach_start:], STANDARD, SERIES[breach_start:],
                    color=c["vermilion"], alpha=0.14, zorder=2)
    ax.scatter([MONTHS[-1]], [SERIES[-1]], color=c["vermilion"], s=30, zorder=4)
    ax.annotate(f"{SERIES[-1]:.1f}", (MONTHS[-1], SERIES[-1]),
                textcoords="offset points", xytext=(-2, 10), ha="right",
                fontfamily=MONO, fontsize=11, fontweight="bold", color=c["vermilion"])
    ax.text(MONTHS[-1], STANDARD - 1.1, "18 WKS · THE STANDARD",
            fontfamily=MONO, fontsize=8.5, color=c["teal"], ha="right")

    fig.savefig(OUT / f"the-interval-header-{name}.png", dpi=110,
                facecolor=c["bg"])
    plt.close(fig)
    print(f"  wrote assets/the-interval-header-{name}.png")


if __name__ == "__main__":
    for variant, colours in VARIANTS.items():
        draw(variant, colours)
