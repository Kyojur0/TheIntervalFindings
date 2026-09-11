#!/usr/bin/env python3
"""
The Interval — README header image
==================================

Draws the archive's header banner in light (paper) and dark (ink) variants.
The mark uses the same percentage scale as the website masthead: 65.6% of
pathways within 18 weeks in May 2026 against the 92% NHS standard. It is a
static promise-versus-reality comparison, not a time series.

    python assets/make_header.py

Outputs: assets/the-interval-header-light.png,
         assets/the-interval-header-dark.png
"""

from pathlib import Path

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
ACTUAL = 65.6
TARGET = 92.0

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
             "The NHS standard is 92% within 18 weeks.",
             fontfamily=SERIF, fontsize=13.5, color=c["muted"])
    fig.text(0.057, 0.375,
             "The latest published result sits at 65.6%.",
             fontfamily=SERIF, fontsize=13.5, color=c["muted"])
    fig.text(0.057, 0.22, "THE FINDINGS ARCHIVE · EVERY NUMBER REPRODUCIBLE",
             fontfamily=MONO, fontsize=9, color=c["muted"])

    # ——— the signature promise-versus-reality scale, right ———
    ax = fig.add_axes([0.50, 0.20, 0.455, 0.52])
    ax.set_facecolor(c["bg"])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0, colors=c["muted"], labelsize=9, pad=8)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontfamily(MONO)

    ax.set_xlim(0, 100)
    ax.set_ylim(-0.44, 0.44)
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xticklabels(["0", "20", "40", "60", "80", "100"])
    ax.set_yticks([])
    ax.xaxis.grid(True, color=c["hairline"], lw=0.8, zorder=0)

    ax.axvline(TARGET, color=c["teal"], lw=1.2, ls=(0, (5, 4)), zorder=1)
    ax.plot([0, 100], [0, 0], color=c["ink"], lw=1.5, zorder=2)
    ax.plot([ACTUAL, TARGET], [0, 0], color=c["vermilion"], lw=5,
            solid_capstyle="round", zorder=3)
    ax.scatter([ACTUAL], [0], color=c["vermilion"], s=42, zorder=4)
    ax.scatter([TARGET], [0], color=c["teal"], s=42, zorder=4)

    ax.text(ACTUAL, 0.19, f"{ACTUAL:.1f}%", fontfamily=MONO, fontsize=11,
            fontweight="bold", color=c["vermilion"], ha="center", va="bottom")
    ax.text(ACTUAL, -0.27, "MAY 2026", fontfamily=MONO, fontsize=8.5,
            color=c["muted"], ha="center", va="top")
    ax.text(TARGET, -0.27, "92% · THE STANDARD", fontfamily=MONO, fontsize=8.5,
            color=c["teal"], ha="center", va="top")
    ax.text(0, 0.36, "WITHIN 18 WEEKS", fontfamily=MONO, fontsize=8.5,
            color=c["muted"], ha="left", va="bottom")

    fig.savefig(OUT / f"the-interval-header-{name}.png", dpi=110,
                facecolor=c["bg"], bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    print(f"  wrote assets/the-interval-header-{name}.png")


if __name__ == "__main__":
    for variant, colours in VARIANTS.items():
        draw(variant, colours)
