#!/usr/bin/env python3
"""Finding 04: four source-backed figures, each in the supplied two themes."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter

from figure_spec import MONO, SERIF, THEMES, save, source, style_ax, title

SOURCE = "NHS England RTT | Reported England pathways; NONC excluded | waits so far"


def _frame(colours, heading, subtitle, *, right=0.79, bottom=0.235):
    figure = plt.figure(figsize=(10.5, 6.35), facecolor=colours["bg"])
    axis = figure.add_axes([0.085, bottom, right - 0.085, 0.56])
    style_ax(axis, colours)
    title(figure, colours, heading, subtitle, y=0.965)
    source(figure, colours, SOURCE, y=0.035)
    source(figure, colours, "Submitted data; no estimates for missing providers", y=0.013)
    return figure, axis


def _time_axis(axis, dates, colours):
    periods = pd.DatetimeIndex(dates)
    selected = [periods[0]]
    selected.extend(date for date in periods[1:-1] if date.month in (1, 7))
    selected.append(periods[-1])
    axis.set_xticks(selected, [date.strftime("%b\n%Y") for date in selected])
    axis.set_xlim(periods[0], periods[-1] + pd.Timedelta(days=25))
    axis.tick_params(axis="x", pad=10)
    for label in axis.get_xticklabels():
        label.set_fontfamily(MONO)
        label.set_color(colours["muted"])


def _label(axis, y, text, colour, *, x=1.04, fontsize=9.5):
    axis.text(x, y, text, transform=axis.get_yaxis_transform(),
              family=MONO, fontsize=fontsize, color=colour,
              ha="left", va="center", linespacing=1.5)


def _note(figure, colours, text, *, y=0.12):
    figure.text(0.085, y, text, family=SERIF, fontsize=9,
                color=colours["muted"], va="top", linespacing=1.4)


def _median(frame, colours, output, theme):
    dates = pd.to_datetime(frame["period"])
    latest = frame.iloc[-1]
    figure, axis = _frame(
        colours, "The median wait so far has fallen",
        "Reported England pathways, all specialties · January 2024–May 2026",
    )
    axis.plot(dates, frame["p50"], color=colours["ink"], lw=2.3, zorder=3)
    axis.scatter([dates.iloc[0], dates.iloc[-1]],
                 [frame.iloc[0]["p50"], latest["p50"]],
                 color=colours["ink"], s=24, zorder=4)
    axis.axhline(18, color=colours["teal"], lw=1.2, ls=(0, (5, 4)))
    axis.set_ylim(0, 21)
    axis.set_yticks([0, 6, 12, 18])
    axis.text(0, 1.025, "Wait so far (weeks)", transform=axis.transAxes,
              family=MONO, fontsize=8.5, color=colours["muted"])
    axis.annotate(f"{frame.iloc[0]['p50']:.1f} weeks", xy=(dates.iloc[0], frame.iloc[0]["p50"]),
                  xytext=(8, 13), textcoords="offset points", family=MONO,
                  fontsize=9, color=colours["ink"])
    _label(axis, latest["p50"], f"Median\n{latest['p50']:.1f} weeks", colours["ink"])
    _label(axis, 18, "18 weeks\nreference", colours["teal"])
    _time_axis(axis, dates, colours)
    _note(figure, colours,
          "The median covers half of the waiting list. The 18-week standard applies to 92%, not 50%.\n"
          "These are waits so far; six months use first-release data.")
    return save(figure, colours, output / "figure-01-median", theme)


def _promise(frame, colours, output, theme):
    dates = pd.to_datetime(frame["period"])
    latest = frame.iloc[-1]
    figure, axis = _frame(
        colours, "A shorter median; the standard remains unmet",
        "p92 is the estimated wait so far covering 92% of the reported list",
    )
    axis.fill_between(dates, 18, frame["p92"], color=colours["vermilion"], alpha=0.075)
    for key, colour in (("p50", colours["ink"]), ("p92", colours["vermilion"])):
        axis.plot(dates, frame[key], color=colour, lw=2.3, zorder=3)
        axis.scatter([dates.iloc[-1]], [latest[key]], s=24, color=colour, zorder=4)
    axis.axhline(18, color=colours["teal"], lw=1.2, ls=(0, (5, 4)))
    axis.set_ylim(0, 53)
    axis.set_yticks([0, 10, 20, 30, 40, 50])
    axis.text(0, 1.025, "Wait so far (weeks)", transform=axis.transAxes,
              family=MONO, fontsize=8.5, color=colours["muted"])
    _label(axis, latest["p92"], f"p92\n{latest['p92']:.1f} weeks", colours["vermilion"])
    _label(axis, latest["p50"], f"Median\n{latest['p50']:.1f} weeks", colours["ink"])
    _label(axis, 18.5, "18-week standard", colours["teal"], fontsize=8)
    bracket_x = dates.iloc[-1] + pd.Timedelta(days=17)
    axis.annotate("", xy=(bracket_x, latest["p92"]), xytext=(bracket_x, 18),
                  arrowprops={"arrowstyle": "<->", "color": colours["vermilion"], "lw": 1.1})
    _label(axis, (latest["p92"] + 18) / 2,
           f"{latest['gap_weeks']:.1f}-week\ngap", colours["vermilion"])
    _time_axis(axis, dates, colours)
    _note(figure, colours,
          f"May 2026: half of pathways had been waiting for up to {latest['p50']:.1f} weeks; "
          f"92% for up to {latest['p92']:.1f} weeks.\n"
          "Percentiles are estimates from weekly bands. Six months use first-release data.")
    return save(figure, colours, output / "figure-02-promise", theme)


def _middle(frame, colours, output, theme):
    dates = pd.to_datetime(frame["period"])
    latest = frame.iloc[-1]
    within = frame["within18_count"].to_numpy() / 1_000_000
    middle = frame["middle_count"].to_numpy() / 1_000_000
    tail = frame["over52_count"].to_numpy() / 1_000_000
    figure, axis = _frame(
        colours, "The middle has shrunk; shorter waits remain largest",
        "Reported pathways waiting at month end · latest total: " + f"{latest['total'] / 1_000_000:.3f} million",
    )
    axis.fill_between(dates, 0, within, color=colours["ink"], alpha=0.22, lw=0)
    axis.plot(dates, within, color=colours["ink"], lw=1.1)
    axis.fill_between(dates, within, within + middle, color=colours["vermilion"], alpha=0.70, lw=0)
    axis.fill_between(dates, within + middle, within + middle + tail,
                      color=colours["vermilion"], alpha=1, lw=0, hatch="////",
                      edgecolor=colours["bg"])
    axis.plot(dates, within + middle + tail, color=colours["vermilion"], lw=0.8)
    axis.set_ylim(0, 8.7)
    axis.set_yticks([0, 2, 4, 6, 8])
    axis.text(0, 1.025, "Pathways (millions)", transform=axis.transAxes,
              family=MONO, fontsize=8.5, color=colours["muted"])
    _label(axis, within[-1] / 2,
           f"Within 18 weeks\n{within[-1]:.3f}m · {latest['within18_share']:.1%}", colours["ink"], fontsize=9)
    _label(axis, within[-1] + middle[-1] / 2,
           f"18–52 weeks\n{middle[-1]:.3f}m · {latest['middle_share']:.1%}", colours["vermilion"], fontsize=9)
    tail_centre = within[-1] + middle[-1] + tail[-1] / 2
    _label(axis, 7.75,
           f"Over 52 weeks\n{tail[-1]:.3f}m · {latest['over52_share']:.1%}", colours["vermilion"], fontsize=9)
    axis.annotate("", xy=(dates.iloc[-1], tail_centre), xycoords="data",
                  xytext=(1.025, 7.55), textcoords=axis.get_yaxis_transform(),
                  arrowprops={"arrowstyle": "-", "color": colours["vermilion"], "lw": 0.8})
    _time_axis(axis, dates, colours)
    _note(figure, colours,
          "The middle means more than 18 and no more than 52 weeks. Counts refer to pathways, not unique people.\n"
          "Community reporting changed in February 2024. Six months use first-release data.")
    return save(figure, colours, output / "figure-03-middle", theme)


def _shape(frame, bands, colours, output, theme):
    latest = frame.iloc[-1]
    period = str(latest["period"])
    selected = bands[(bands["period"] == period) & (bands["part"] == "Part_2")]
    closed = selected[selected["upper_week"].notna()].sort_values("lower_week")
    opened = selected[selected["upper_week"].isna()]
    if len(closed) != 104 or len(opened) != 1:
        raise ValueError("Latest-month distribution must contain 104 closed bands and one open band")
    if int(selected["count"].sum()) != int(latest["total"]):
        raise ValueError("Histogram bands do not reconcile to the headline cohort")
    open_count = int(opened.iloc[0]["count"])
    figure, axis = _frame(
        colours, "The shape of the waiting list in May 2026",
        "All 105 reporting bands · the final, open-ended band is shown separately",
        right=0.765, bottom=0.235,
    )
    colours_by_band = np.where(closed["upper_week"] <= 18, colours["ink"], colours["vermilion"])
    axis.bar(closed["lower_week"], closed["count"], width=0.96, align="edge",
             color=colours_by_band, lw=0, zorder=2)
    axis.set_xlim(0, 104)
    axis.set_ylim(0, 510_000)
    axis.set_xticks([0, 18, 26, 52, 78, 104])
    axis.tick_params(axis="x", pad=8)
    axis.set_yticks([0, 100_000, 200_000, 300_000, 400_000, 500_000])
    axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: "0" if value == 0 else f"{value / 1000:.0f}k"))
    axis.set_xlabel("Wait so far (weeks)", family=MONO, fontsize=8.5,
                    color=colours["muted"], labelpad=12)
    axis.text(0, 1.025, "Pathways per band", transform=axis.transAxes,
              family=MONO, fontsize=8.5, color=colours["muted"])
    annotations = (
        (float(latest["p50"]), colours["ink"], f"Median\n{latest['p50']:.1f} weeks", (5, 445_000)),
        (18, colours["teal"], "18 weeks", (26, 385_000)),
        (float(latest["p92"]), colours["vermilion"], f"p92\n{latest['p92']:.1f} weeks", (45, 320_000)),
    )
    for value, colour, text, position in annotations:
        axis.axvline(value, color=colour, lw=1.1, ls=(0, (4, 3)), zorder=4)
        axis.annotate(text, xy=(value, position[1] - 32_000), xytext=position,
                      family=MONO, fontsize=9, color=colour, ha="center", va="bottom",
                      linespacing=1.3, bbox={"facecolor": colours["bg"], "edgecolor": "none", "pad": 2},
                      arrowprops={"arrowstyle": "-", "color": colour, "lw": 0.8})
    figure.text(0.815, 0.79, "Over 104 weeks", family=SERIF, fontsize=10.5, color=colours["ink"])
    figure.text(0.815, 0.745, f"{open_count:,} pathways", family=MONO, fontsize=10, color=colours["vermilion"])
    figure.text(0.815, 0.701, "Open-ended band", family=SERIF, fontsize=9, color=colours["muted"])
    inset = figure.add_axes([0.85, 0.29, 0.095, 0.295])
    style_ax(inset, colours)
    inset.bar([0], [open_count], width=0.5, color=colours["vermilion"], zorder=2)
    inset.set_xlim(-0.65, 0.65)
    inset.set_ylim(0, max(210, open_count * 1.15))
    inset.set_yticks([0, 100, 200])
    inset.set_xticks([0], ["104+"])
    inset.tick_params(axis="x", pad=8)
    inset.text(0.5, 1.08, "Pathways", transform=inset.transAxes, family=MONO,
                fontsize=8, color=colours["muted"], ha="center")
    figure.text(0.83, 0.21, "Separate count scale", family=SERIF, fontsize=8, color=colours["muted"])
    _note(figure, colours,
          "The median and p92 are interpolated estimates. The 104+ band has no upper limit and no finite width.\n"
          "May 2026 is first-release data; this distribution describes time waited so far.", y=0.115)
    return save(figure, colours, output / "figure-04-shape", theme)


def make_figures(results_dir: Path, figures_dir: Path):
    """Render all requested PNGs using validated result CSVs and shared themes."""
    results_dir, figures_dir = Path(results_dir), Path(figures_dir)
    frame = pd.read_csv(results_dir / "national_monthly.csv").sort_values("period")
    bands = pd.read_csv(results_dir / "national_band_distribution.csv")
    if len(frame) != 29 or frame["period"].duplicated().any():
        raise ValueError("Expected one England result for each of the 29 brief months")
    if not ((frame["p50"] <= frame["p92"]) & (frame["p92"] < 104)).all():
        raise ValueError("Invalid percentile order or open-ended national percentile")
    figures_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for theme, colours in THEMES.items():
        for render in (_median, _promise, _middle):
            written.append(render(frame, colours, figures_dir, theme))
        written.append(_shape(frame, bands, colours, figures_dir, theme))
    return written


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=root / "results")
    parser.add_argument("--output-dir", type=Path, default=root / "pack" / "figures")
    arguments = parser.parse_args()
    for path in make_figures(arguments.results_dir, arguments.output_dir):
        print(path)
