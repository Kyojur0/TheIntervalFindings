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

def _hsl(h, s, l):
    """HSL percentages to hex, so the palette below can be written exactly as the
    site's CSS custom properties declare it."""
    import colorsys

    r, g, b = colorsys.hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


# Transcribed from TheIntervalWebsite/src/index.css. The figures sit inside the
# page, so they must use the page's own palette rather than an approximation of
# it. If the site's tokens change, change these with them.
THEMES = {
    "light": dict(                       # :root
        bg=_hsl(48, 33, 97),             # --background
        ink=_hsl(40, 9, 10),             # --foreground
        muted=_hsl(44, 9, 33),           # --muted-foreground
        hairline=_hsl(46, 14, 81),       # --hairline
        teal=_hsl(180, 68, 18),          # --teal
        vermilion=_hsl(13, 73, 45),      # --vermilion
    ),
    "dark": dict(                        # .dark
        bg=_hsl(150, 6, 6),
        ink=_hsl(48, 14, 92),
        muted=_hsl(45, 6, 58),
        hairline=_hsl(150, 5, 15),
        teal=_hsl(171, 46, 56),
        vermilion=_hsl(14, 82, 59),
    ),
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
