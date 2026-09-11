"""The Interval — shared figure specification.

One visual code across the site, the banner and every pack: ink for what sits
within the standard, vermilion for what breaches it, teal where the standard
lies. No chart furniture. Direct labels, never a legend box. A mono source line
under every figure.

Each pack carries its own copy so it runs standalone.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

MONO = "DejaVu Sans Mono"
SERIF = "DejaVu Serif"

THEMES = {
    "light": dict(bg="#FBFAF6", ink="#1C1B17", muted="#6E6A5E", hairline="#D8D3C6",
                  teal="#2E6F6A", vermilion="#C2492B"),
    "dark": dict(bg="#1B1915", ink="#F5F2E9", muted="#9A9484", hairline="#3A372D",
                 teal="#5FA8A0", vermilion="#D96A4A"),
}


def style_ax(ax, c, *, grid="y"):
    """Paper ground, hairline grid, no spines, mono tick labels."""
    ax.set_facecolor(c["bg"])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0, colors=c["muted"], labelsize=8)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontfamily(MONO)
    if grid:
        ax.grid(axis=grid, color=c["hairline"], lw=0.6, zorder=0)
        ax.set_axisbelow(True)


def title(fig, c, text, sub=None, *, x=0.055, y=0.955):
    fig.text(x, y, text, family=SERIF, fontsize=15, color=c["ink"], va="top")
    if sub:
        fig.text(x, y - 0.062, sub, family=SERIF, fontsize=10.5,
                 color=c["muted"], va="top")


def source(fig, c, text, *, x=0.055, y=0.028):
    fig.text(x, y, text.upper(), family=MONO, fontsize=7, color=c["muted"])


def save(fig, c, path_stem, theme):
    out = f"{path_stem}.png" if theme == "light" else f"{path_stem}-dark.png"
    fig.savefig(out, dpi=200, facecolor=c["bg"], edgecolor="none")
    plt.close(fig)
    return out


def right_labels(ax, items, *, min_gap=7.0, x=1.012, fontsize=7.5):
    """Draw direct labels in the right margin, nudged apart where they collide.

    ``items`` is a list of ``(y_value, text, colour)`` in data coordinates.
    Labels are the spec's replacement for a legend box, so they must stay
    legible even when two series end at similar values.
    """
    placed = []
    for y, text, colour in sorted(items, key=lambda it: it[0]):
        lines = text.count("\n") + 1
        need = min_gap * lines * 0.75
        if placed and y - placed[-1][0] < need:
            y = placed[-1][0] + need
        placed.append((y, text, colour))
    for y, text, colour in placed:
        ax.text(x, y, text, transform=ax.get_yaxis_transform(), family=MONO,
                fontsize=fontsize, color=colour, va="center")
