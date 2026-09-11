"""Reproducible Finding 03 provider-persistence analysis.

The default invocation discovers the project root from the script location,
reads the 29 local RTT monthly files through DuckDB, and writes derived
outputs under ``Codex's Workspace/Codex's Verifications/finding-03/results``.
No raw source files are copied or modified.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({"font.family": "DejaVu Sans Mono", "axes.titleweight": "normal"})


FOCUS_CODES = {
    "C_301": "Gastroenterology",
    "C_130": "Ophthalmology",
    "C_120": "Ear, Nose and Throat",
    "C_110": "Trauma and Orthopaedics",
}
RECODE_CODES = {**FOCUS_CODES, "C_300": "General Medicine"}
FIRST_RELEASE = {"2025-10", "2025-11", "2026-01", "2026-02", "2026-04", "2026-05"}
SOURCE_LINE = "Source: NHS England RTT Incomplete Pathways, Part_2, NONC excluded; provider-month aggregates calculated from the local 29-file series."
PAPER = "#FBFAF6"
INK = "#1C1B17"
MUTED = "#6E6A5E"
HAIRLINE = "#D8D3C6"
TEAL = "#2E6F6A"
VERMILION = "#C2492B"
BLUE = "#386FA4"
GOLD = "#B8871A"

F01 = {
    "n_providers": 119,
    "total_pathways": 361_130,
    "mean": 71.50,
    "sd": 13.01,
    "min_code": "RJL",
    "min_pct": 37.29,
    "max_code": "RTF",
    "max_pct": 97.70,
    "n_ge1000": 108,
    "sd_ge1000": 12.72,
}


def band_name(i: int) -> str:
    return "Gt 104 Weeks SUM 1" if i == 104 else f"Gt {i:02d} To {i + 1:02d} Weeks SUM 1"


def all_band_columns() -> list[str]:
    return [band_name(i) for i in range(105)]


def _sum_expr(columns: Iterable[str]) -> str:
    return " + ".join(f'COALESCE("{c}", 0)' for c in columns)


def find_project_root(start: Path | None = None) -> Path:
    start = (start or Path(__file__)).resolve()
    if start.is_file():
        start = start.parent
    for candidate in [start, *start.parents]:
        if (candidate / "data" / "rtt_monthly_series" / "manifest.json").exists():
            return candidate
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "data" / "rtt_monthly_series" / "manifest.json").exists():
            return candidate
    raise FileNotFoundError("Could not find project root containing data/rtt_monthly_series/manifest.json")


def load_manifest(project_root: Path) -> dict:
    return json.loads((project_root / "data" / "rtt_monthly_series" / "manifest.json").read_text())


def manifest_periods(manifest: dict) -> list[str]:
    return [entry["period"] for entry in manifest["files"]]


MONTHS = [f"{year:04d}-{month:02d}" for year in (2024, 2025, 2026) for month in range(1, 13)]
MONTHS = [p for p in MONTHS if "2024-01" <= p <= "2026-05"]


def split_half_periods(periods: list[str]) -> tuple[list[str], list[str]]:
    if len(periods) != 29:
        raise ValueError(f"Expected 29 periods, got {len(periods)}")
    middle = len(periods) // 2
    return periods[:middle], periods[middle + 1 :]


def spearman(x: pd.Series, y: pd.Series) -> float:
    x = pd.Series(x, dtype=float)
    y = pd.Series(y, dtype=float)
    if len(x) < 3:
        return float("nan")
    rx = x.rank(method="average").to_numpy()
    ry = y.rank(method="average").to_numpy()
    if np.std(rx) == 0 or np.std(ry) == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def ols_slope(values: pd.Series | np.ndarray) -> tuple[float, float]:
    y = np.asarray(values, dtype=float)
    x = np.arange(len(y), dtype=float)
    if len(y) < 2 or np.allclose(y, y[0]):
        return 0.0, float("nan")
    slope, intercept = np.polyfit(x, y, 1)
    r = float(np.corrcoef(x, y)[0, 1])
    return float(slope), r


@dataclass
class GateResult:
    ok: bool
    lines: list[str]


def validate_reproduction(april: pd.DataFrame) -> GateResult:
    lines: list[str] = []
    ok = True

    def check(label: str, got, expected, tol: float | None = None) -> None:
        nonlocal ok
        if tol is None:
            passed = got == expected
        else:
            passed = math.isfinite(float(got)) and abs(float(got) - float(expected)) <= tol
        ok = ok and passed
        lines.append(f"{'PASS' if passed else 'FAIL'}  {label}: got {got!r}; expected {expected!r}")

    cohort = april[april["total_waiting"] >= 500].copy()
    cohort["pct_within_18w"] = 100 * cohort["within_18w"] / cohort["total_waiting"]
    check("provider count", len(cohort), F01["n_providers"])
    check("total pathways", int(cohort["total_waiting"].sum()), F01["total_pathways"])
    check("unweighted mean %", cohort["pct_within_18w"].mean(), F01["mean"], 0.005)
    check("sample SD (ddof=1)", cohort["pct_within_18w"].std(ddof=1), F01["sd"], 0.005)
    lo = cohort.loc[cohort["pct_within_18w"].idxmin()]
    hi = cohort.loc[cohort["pct_within_18w"].idxmax()]
    check("minimum provider", lo["provider_code"], F01["min_code"])
    check("minimum waiting", int(lo["total_waiting"]), 3_966)
    check("minimum %", lo["pct_within_18w"], F01["min_pct"], 0.005)
    check("maximum provider", hi["provider_code"], F01["max_code"])
    check("maximum waiting", int(hi["total_waiting"]), 1_478)
    check("maximum %", hi["pct_within_18w"], F01["max_pct"], 0.005)
    big = april[april["total_waiting"] >= 1000].copy()
    big["pct_within_18w"] = 100 * big["within_18w"] / big["total_waiting"]
    check("provider count >=1000", len(big), F01["n_ge1000"])
    check("SD >=1000", big["pct_within_18w"].std(ddof=1), F01["sd_ge1000"], 0.005)
    return GateResult(ok, lines)


def extract_panel(project_root: Path, cache_path: Path, force: bool = False) -> pd.DataFrame:
    if cache_path.exists() and not force:
        panel = pd.read_csv(cache_path)
        return add_derived_columns(panel)

    monthly_dir = project_root / "data" / "rtt_monthly_series"
    manifest = load_manifest(project_root)
    all_expr = _sum_expr(all_band_columns())
    w18_expr = _sum_expr([band_name(i) for i in range(18)])
    w52_expr = _sum_expr([band_name(i) for i in range(52, 105)])
    con = duckdb.connect()
    frames: list[pd.DataFrame] = []
    for entry in manifest["files"]:
        period = entry["period"]
        csv_path = monthly_dir / entry["filename"]
        if not csv_path.exists():
            raise FileNotFoundError(csv_path)
        csv_sql = str(csv_path).replace("'", "''")
        sql = f"""
        SELECT
          '{period}' AS period,
          '{entry['label']}' AS label,
          "Treatment Function Code" AS specialty_code,
          "Provider Org Code" AS provider_code,
          MIN("Provider Org Name") AS provider_name,
          SUM({all_expr}) AS total_waiting,
          SUM({w18_expr}) AS within_18w,
          SUM({w52_expr}) AS over_52w,
          COUNT(*) AS n_source_rows
        FROM read_csv_auto('{csv_sql}', header=true, sample_size=-1)
        WHERE "RTT Part Type" = 'Part_2'
          AND COALESCE("Commissioner Org Code", '') <> 'NONC'
          AND "Treatment Function Code" <> 'C_999'
        GROUP BY 1, 2, 3, 4
        HAVING SUM({all_expr}) > 0
        ORDER BY specialty_code, provider_code
        """
        frame = con.execute(sql).df()
        frames.append(frame)
        print(f"  {period}: {len(frame):,} provider-specialty rows")
    panel = pd.concat(frames, ignore_index=True)
    panel.to_csv(cache_path, index=False)
    return add_derived_columns(panel)


def add_derived_columns(panel: pd.DataFrame) -> pd.DataFrame:
    panel = panel.copy()
    for col in ["total_waiting", "within_18w", "over_52w"]:
        panel[col] = pd.to_numeric(panel[col], errors="coerce").fillna(0)
    panel["pct_within_18w"] = np.where(
        panel["total_waiting"] > 0,
        100 * panel["within_18w"] / panel["total_waiting"],
        np.nan,
    )
    panel["pct_over_52w"] = np.where(
        panel["total_waiting"] > 0,
        100 * panel["over_52w"] / panel["total_waiting"],
        np.nan,
    )
    panel["first_release"] = panel["period"].isin(FIRST_RELEASE)
    latest = panel.sort_values("period").groupby("provider_code")["provider_name"].last()
    panel["provider_name"] = panel["provider_code"].map(latest).fillna(panel["provider_name"])
    return panel.sort_values(["specialty_code", "period", "provider_code"]).reset_index(drop=True)


def cohort_stats(frame: pd.DataFrame, floor: int) -> dict:
    cohort = frame[frame["total_waiting"] >= floor].copy()
    if cohort.empty:
        return {"n": 0, "pathways": 0, "mean_pct": np.nan, "sd_pct": np.nan}
    if "pct_within_18w" not in cohort:
        cohort["pct_within_18w"] = np.where(
            cohort["total_waiting"] > 0,
            100 * cohort["within_18w"] / cohort["total_waiting"],
            np.nan,
        )
    v = cohort["pct_within_18w"]
    lo = cohort.loc[v.idxmin()]
    hi = cohort.loc[v.idxmax()]
    q1, med, q3 = np.percentile(v, [25, 50, 75])
    return {
        "n": int(len(cohort)),
        "pathways": int(cohort["total_waiting"].sum()),
        "mean_pct": float(v.mean()),
        "sd_pct": float(v.std(ddof=1)),
        "min_pct": float(v.min()),
        "min_provider": lo["provider_code"],
        "min_provider_name": lo["provider_name"],
        "q1_pct": float(q1),
        "median_pct": float(med),
        "q3_pct": float(q3),
        "iqr_pp": float(q3 - q1),
        "max_pct": float(v.max()),
        "max_provider": hi["provider_code"],
        "max_provider_name": hi["provider_name"],
        "range_pp": float(v.max() - v.min()),
    }


def monthly_spread(panel: pd.DataFrame, floor: int) -> pd.DataFrame:
    rows: list[dict] = []
    for specialty_code, specialty in FOCUS_CODES.items():
        sub = panel[panel["specialty_code"] == specialty_code]
        for period in sorted(sub["period"].unique()):
            g = sub[sub["period"] == period]
            row = cohort_stats(g, floor)
            row.update({
                "specialty_code": specialty_code,
                "specialty": specialty,
                "period": period,
                "label": g["label"].iloc[0],
                "first_release": bool(g["first_release"].iloc[0]),
            })
            rows.append(row)
    return pd.DataFrame(rows)


def cohorts_by_period(panel: pd.DataFrame, specialty_code: str, periods: list[str], floor: int,
                      restrict: set[str] | None = None) -> dict[str, pd.Series]:
    sub = panel[panel["specialty_code"] == specialty_code]
    out: dict[str, pd.Series] = {}
    for period in periods:
        g = sub[(sub["period"] == period) & (sub["total_waiting"] >= floor)]
        if restrict is not None:
            g = g[g["provider_code"].isin(restrict)]
        out[period] = g.set_index("provider_code")["pct_within_18w"]
    return out


def rank_persistence(panel: pd.DataFrame, specialty_code: str, periods: list[str], floor: int,
                     restrict: set[str] | None = None) -> tuple[pd.DataFrame, dict]:
    cohorts = cohorts_by_period(panel, specialty_code, periods, floor, restrict)
    rows: list[dict] = []
    for a, b in zip(periods[:-1], periods[1:]):
        shared = cohorts[a].index.intersection(cohorts[b].index)
        rows.append({
            "specialty_code": specialty_code,
            "specialty": FOCUS_CODES[specialty_code],
            "floor": floor,
            "from_period": a,
            "to_period": b,
            "n_in_both": int(len(shared)),
            "n_only_from": int(len(cohorts[a].index.difference(cohorts[b].index))),
            "n_only_to": int(len(cohorts[b].index.difference(cohorts[a].index))),
            "spearman": spearman(cohorts[a].loc[shared], cohorts[b].loc[shared]),
        })
    consecutive = pd.DataFrame(rows)
    first, last = cohorts[periods[0]], cohorts[periods[-1]]
    shared = first.index.intersection(last.index)
    summary = {
        "specialty_code": specialty_code,
        "specialty": FOCUS_CODES[specialty_code],
        "floor": floor,
        "n_first": int(len(first)),
        "n_last": int(len(last)),
        "n_first_last": int(len(shared)),
        "first_last_spearman": spearman(first.loc[shared], last.loc[shared]),
        "consecutive_mean_spearman": float(consecutive["spearman"].mean()),
        "consecutive_min_spearman": float(consecutive["spearman"].min()),
        "consecutive_max_spearman": float(consecutive["spearman"].max()),
    }
    for which, ascending in (("bottom", True), ("top", False)):
        start_n = max(1, int(math.ceil(len(first) / 10)))
        end_n = max(1, int(math.ceil(len(last) / 10)))
        start = set(first.sort_values(ascending=ascending).head(start_n).index)
        end = set(last.sort_values(ascending=ascending).head(end_n).index)
        still = start & set(last.index)
        summary[f"{which}_decile_start_n"] = len(start)
        summary[f"{which}_decile_survivors"] = len(start & end)
        summary[f"{which}_decile_expected_random"] = len(still) * len(end) / len(shared) if len(shared) else np.nan
        summary[f"{which}_decile_survivor_codes"] = "|".join(sorted(start & end))
    return consecutive, summary


def rank_decay(panel: pd.DataFrame, specialty_code: str, periods: list[str], floor: int,
               restrict: set[str] | None = None) -> pd.DataFrame:
    cohorts = cohorts_by_period(panel, specialty_code, periods, floor, restrict)
    rows: list[dict] = []
    for lag in range(1, len(periods)):
        values: list[float] = []
        ns: list[int] = []
        for i in range(len(periods) - lag):
            a, b = cohorts[periods[i]], cohorts[periods[i + lag]]
            shared = a.index.intersection(b.index)
            if len(shared) >= 3:
                values.append(spearman(a.loc[shared], b.loc[shared]))
                ns.append(len(shared))
        rows.append({
            "specialty_code": specialty_code,
            "specialty": FOCUS_CODES[specialty_code],
            "floor": floor,
            "lag_months": lag,
            "n_pairs": len(values),
            "mean_spearman": float(np.mean(values)),
            "min_spearman": float(np.min(values)),
            "max_spearman": float(np.max(values)),
            "mean_n_providers": float(np.mean(ns)),
        })
    return pd.DataFrame(rows)


def balanced_codes(panel: pd.DataFrame, specialty_code: str, periods: list[str], floor: int) -> set[str]:
    sub = panel[(panel["specialty_code"] == specialty_code) & (panel["total_waiting"] >= floor)]
    counts = sub.groupby("provider_code")["period"].nunique()
    return set(counts[counts == len(periods)].index)


def split_half_summary(panel: pd.DataFrame, specialty_code: str, periods: list[str], floor: int,
                       codes: set[str]) -> dict:
    first, second = split_half_periods(periods)
    sub = panel[(panel["specialty_code"] == specialty_code) & panel["provider_code"].isin(codes)]
    h1 = sub[sub["period"].isin(first)].groupby("provider_code")["pct_within_18w"].mean()
    h2 = sub[sub["period"].isin(second)].groupby("provider_code")["pct_within_18w"].mean()
    shared = h1.index.intersection(h2.index)
    h1, h2 = h1.loc[shared], h2.loc[shared]
    k = max(1, int(math.ceil(len(shared) / 4)))
    worst1, worst2 = set(h1.nsmallest(k).index), set(h2.nsmallest(k).index)
    best1, best2 = set(h1.nlargest(k).index), set(h2.nlargest(k).index)
    return {
        "specialty_code": specialty_code,
        "specialty": FOCUS_CODES[specialty_code],
        "floor": floor,
        "n_providers": int(len(shared)),
        "first_half": f"{first[0]}..{first[-1]}",
        "second_half": f"{second[0]}..{second[-1]}",
        "spearman": spearman(h1, h2),
        "quartile_size": k,
        "worst_quartile_retained": len(worst1 & worst2),
        "best_quartile_retained": len(best1 & best2),
        "quartile_expected_random": k * k / len(shared) if len(shared) else np.nan,
    }


def split_half_moving_summary(panel: pd.DataFrame, specialty_code: str, periods: list[str], floor: int) -> dict:
    """Split-half persistence for the moving, within-month floor cohort.

    A provider needs at least one floor-qualifying month in each half. Its half
    score is the unweighted average of only the months in which it qualified;
    the all-29-month balanced calculation is reported separately.
    """
    first, second = split_half_periods(periods)
    sub = panel[(panel["specialty_code"] == specialty_code) & (panel["total_waiting"] >= floor)]
    h1 = sub[sub["period"].isin(first)].groupby("provider_code")["pct_within_18w"].mean()
    h2 = sub[sub["period"].isin(second)].groupby("provider_code")["pct_within_18w"].mean()
    shared = h1.index.intersection(h2.index)
    h1, h2 = h1.loc[shared], h2.loc[shared]
    k = max(1, int(math.ceil(len(shared) / 4)))
    worst1, worst2 = set(h1.nsmallest(k).index), set(h2.nsmallest(k).index)
    best1, best2 = set(h1.nlargest(k).index), set(h2.nlargest(k).index)
    return {
        "specialty_code": specialty_code,
        "specialty": FOCUS_CODES[specialty_code],
        "floor": floor,
        "n_providers": int(len(shared)),
        "first_half": f"{first[0]}..{first[-1]}",
        "second_half": f"{second[0]}..{second[-1]}",
        "spearman": spearman(h1, h2),
        "quartile_size": k,
        "worst_quartile_retained": len(worst1 & worst2),
        "best_quartile_retained": len(best1 & best2),
        "quartile_expected_random": k * k / len(shared) if len(shared) else np.nan,
        "panel": "moving",
    }


def occupancy(panel: pd.DataFrame, specialty_code: str, periods: list[str], floor: int,
              restrict: set[str] | None = None) -> tuple[pd.DataFrame, dict]:
    sub = panel[panel["specialty_code"] == specialty_code]
    if restrict is not None:
        sub = sub[sub["provider_code"].isin(restrict)]
    counts: dict[str, dict[str, int]] = {}
    slots_bottom = slots_top = 0
    for period in periods:
        g = sub[(sub["period"] == period) & (sub["total_waiting"] >= floor)]
        if g.empty:
            continue
        k = max(1, int(math.ceil(len(g) / 10)))
        bottom = g.nsmallest(k, "pct_within_18w")
        top = g.nlargest(k, "pct_within_18w")
        slots_bottom += k
        slots_top += k
        for which, selected in (("bottom", bottom), ("top", top)):
            for _, row in selected.iterrows():
                key = row["provider_code"]
                counts.setdefault(key, {"bottom": 0, "top": 0})
                counts[key][which] += 1
    rows: list[dict] = []
    names = sub.groupby("provider_code")["provider_name"].last().to_dict()
    means = sub.groupby("provider_code")["pct_within_18w"].mean().to_dict()
    for code, counts_for_code in counts.items():
        rows.append({
            "specialty_code": specialty_code,
            "specialty": FOCUS_CODES[specialty_code],
            "floor": floor,
            "provider_code": code,
            "provider_name": names.get(code, ""),
            "months_in_bottom_decile": counts_for_code["bottom"],
            "months_in_top_decile": counts_for_code["top"],
            "mean_pct": means.get(code, np.nan),
            "panel": "moving",
        })
    profile = pd.DataFrame(rows)
    summary = {
        "specialty_code": specialty_code,
        "specialty": FOCUS_CODES[specialty_code],
        "floor": floor,
        "panel": "moving",
        "distinct_bottom_decile_providers": int((profile["months_in_bottom_decile"] > 0).sum()) if not profile.empty else 0,
        "distinct_top_decile_providers": int((profile["months_in_top_decile"] > 0).sum()) if not profile.empty else 0,
        "bottom_decile_slots": slots_bottom,
        "top_decile_slots": slots_top,
        "fully_fixed_bottom_slots": int(profile["months_in_bottom_decile"].max()) if not profile.empty else 0,
        "fully_fixed_top_slots": int(profile["months_in_top_decile"].max()) if not profile.empty else 0,
        "eligible_provider_universe": int(sub[sub["total_waiting"] >= floor]["provider_code"].nunique()),
        "max_possible_distinct_bottom": min(slots_bottom, int(sub[sub["total_waiting"] >= floor]["provider_code"].nunique())),
        "max_possible_distinct_top": min(slots_top, int(sub[sub["total_waiting"] >= floor]["provider_code"].nunique())),
    }
    return profile, summary


def variance_decomposition(balanced: pd.DataFrame, specialty_code: str, floor: int) -> dict:
    grand = balanced["pct_within_18w"].mean()
    means = balanced.groupby("provider_code")["pct_within_18w"].mean()
    n_months = balanced["period"].nunique()
    n_providers = balanced["provider_code"].nunique()
    ss_between = float(n_months * ((means - grand) ** 2).sum())
    joined = balanced.join(means.rename("provider_mean"), on="provider_code")
    ss_within = float(((joined["pct_within_18w"] - joined["provider_mean"]) ** 2).sum())
    total = ss_between + ss_within
    df_between = max(1, n_providers - 1)
    df_within = max(1, n_providers * (n_months - 1))
    ms_between, ms_within = ss_between / df_between, ss_within / df_within
    var_provider = max(0.0, (ms_between - ms_within) / n_months)
    icc = var_provider / (var_provider + ms_within) if var_provider + ms_within else np.nan
    return {
        "specialty_code": specialty_code,
        "specialty": FOCUS_CODES[specialty_code],
        "floor": floor,
        "n_providers": n_providers,
        "n_months": n_months,
        "share_variance_between_providers": ss_between / total if total else np.nan,
        "share_variance_within_provider": ss_within / total if total else np.nan,
        "icc1": icc,
        "sd_provider_means_pp": float(means.std(ddof=1)),
        "mean_within_provider_sd_pp": float(balanced.groupby("provider_code")["pct_within_18w"].std(ddof=1).mean()),
    }


def recode_flags(panel: pd.DataFrame, periods: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    all_codes = sorted(c for c in panel["specialty_code"].dropna().unique() if c != "C_999")
    totals = (panel.pivot_table(index=["provider_code", "specialty_code"], columns="period",
                                values="total_waiting", aggfunc="sum", fill_value=0)
              .reindex(columns=periods, fill_value=0))
    for specialty_code in FOCUS_CODES:
        for (provider_code, current_code), pivot in totals.loc[totals.index.get_level_values("specialty_code") == specialty_code].iterrows():
            for before, after in zip(periods[:-1], periods[1:]):
                old, new = float(pivot.loc[before]), float(pivot.loc[after])
                relative = (new - old) / old if old else (math.inf if new else 0.0)
                flagged = (old == 0 and new > 0) or (old > 0 and new == 0) or abs(relative) > 0.5
                if not flagged:
                    continue
                siblings: list[dict] = []
                for sibling in all_codes:
                    if sibling == specialty_code:
                        continue
                    if (provider_code, sibling) in totals.index:
                        sp = totals.loc[(provider_code, sibling)]
                    else:
                        sp = pd.Series(0.0, index=periods)
                    sold, snew = float(sp.loc[before]), float(sp.loc[after])
                    srel = (snew - sold) / sold if sold else (math.inf if snew else 0.0)
                    opposite = (relative > 0 and srel < 0) or (relative < 0 and srel > 0)
                    if opposite:
                        siblings.append({"code": sibling, "from": sold, "to": snew, "relative": srel})
                rows.append({
                    "specialty_code": specialty_code,
                    "specialty": FOCUS_CODES[specialty_code],
                    "provider_code": provider_code,
                    "from_period": before,
                    "to_period": after,
                    "from_total": old,
                    "to_total": new,
                    "relative_change": relative,
                    "material_event": max(old, new) >= 500,
                    "opposite_siblings": "|".join(s["code"] for s in siblings),
                    "sibling_details": "; ".join(f"{s['code']} {s['from']:.0f}->{s['to']:.0f} ({s['relative']:+.1%})" for s in siblings),
                    "opposite_material_sibling": any(abs(s["to"] - s["from"]) >= 500 for s in siblings),
                })
    return pd.DataFrame(rows)


def recode_sensitivity(panel: pd.DataFrame, recodes: pd.DataFrame, periods: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    material = recodes[recodes["material_event"]].copy() if not recodes.empty else recodes
    for code in FOCUS_CODES:
        for floor in (500, 1000):
            base_codes = balanced_codes(panel, code, periods, floor)
            flagged = set(material.loc[material["specialty_code"] == code, "provider_code"]) if not material.empty else set()
            kept_codes = base_codes - flagged
            base_bal = panel[(panel["specialty_code"] == code) & panel["provider_code"].isin(base_codes) & (panel["total_waiting"] >= floor)]
            kept_bal = panel[(panel["specialty_code"] == code) & panel["provider_code"].isin(kept_codes) & (panel["total_waiting"] >= floor)]
            base_var = variance_decomposition(base_bal, code, floor)
            kept_var = variance_decomposition(kept_bal, code, floor) if len(kept_codes) >= 3 else {"icc1": np.nan, "share_variance_between_providers": np.nan}
            base_split = split_half_summary(panel, code, periods, floor, base_codes)
            kept_split = split_half_summary(panel, code, periods, floor, kept_codes) if len(kept_codes) >= 3 else {"spearman": np.nan}
            rows.append({
                "specialty_code": code,
                "specialty": FOCUS_CODES[code],
                "floor": floor,
                "material_flagged_provider_specialties": len(flagged),
                "balanced_n_baseline": len(base_codes),
                "balanced_n_excluding_material_flags": len(kept_codes),
                "icc_baseline": base_var["icc1"],
                "icc_excluding_material_flags": kept_var["icc1"],
                "split_half_baseline": base_split["spearman"],
                "split_half_excluding_material_flags": kept_split["spearman"],
            })
    return pd.DataFrame(rows)


def configure_axes(ax):
    ax.set_facecolor(PAPER)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(False)
    ax.set_axisbelow(True)


def finish_figure(fig, path: Path) -> None:
    fig.patch.set_facecolor(PAPER)
    fig.text(0.01, 0.012, SOURCE_LINE, color=MUTED, fontsize=7, family="DejaVu Sans Mono")
    fig.savefig(path, dpi=180, facecolor=PAPER, bbox_inches="tight")
    plt.close(fig)


def make_figures(monthly500: pd.DataFrame, decay500: pd.DataFrame, panel: pd.DataFrame,
                 periods: list[str], balanced_sets: dict[tuple[str, int], set[str]], figures_dir: Path) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    colors = {"C_301": TEAL, "C_130": BLUE, "C_120": GOLD, "C_110": VERMILION}
    labels = {c: FOCUS_CODES[c] for c in FOCUS_CODES}

    # Figure 1: provider SD spread over time, all four specialties.
    fig, ax = plt.subplots(figsize=(11, 5.2))
    configure_axes(ax)
    for code in FOCUS_CODES:
        g = monthly500[monthly500["specialty_code"] == code].sort_values("period")
        ax.plot(g["period"], g["sd_pct"], color=colors[code], lw=2, label=labels[code])
        ax.fill_between(g["period"], g["sd_pct"], alpha=0.06, color=colors[code])
    ax.set_ylabel("Sample SD of provider % within 18 weeks (pp)", color=MUTED)
    ax.set_title("Provider spread stays visible across four treatment functions", loc="left", color=INK, fontsize=15, pad=14)
    ax.legend(frameon=False, ncol=2, loc="upper right", fontsize=8)
    ax.tick_params(axis="x", rotation=45)
    finish_figure(fig, figures_dir / "figure1_spread_over_time.png")

    # Figure 2: mean rank-correlation decay.
    fig, ax = plt.subplots(figsize=(11, 5.2))
    configure_axes(ax)
    for code in FOCUS_CODES:
        g = decay500[decay500["specialty_code"] == code].sort_values("lag_months")
        ax.plot(g["lag_months"], g["mean_spearman"], color=colors[code], lw=2, label=labels[code])
    ax.set_xlabel("Months apart", color=MUTED)
    ax.set_ylabel("Mean Spearman rank correlation", color=MUTED)
    ax.set_ylim(0, 1.02)
    ax.set_title("Rank persistence decays gradually rather than collapsing", loc="left", color=INK, fontsize=15, pad=14)
    ax.legend(frameon=False, ncol=2, loc="lower left", fontsize=8)
    finish_figure(fig, figures_dir / "figure2_rank_correlation_decay.png")

    # Figure 3: balanced-panel quartile trajectories.
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True, sharey=True)
    x = np.arange(len(periods))
    for ax, code in zip(axes.flat, FOCUS_CODES):
        codes = balanced_sets[(code, 500)]
        sub = panel[(panel["specialty_code"] == code) & panel["provider_code"].isin(codes)].copy()
        base = sub[sub["period"] == periods[0]].set_index("provider_code")["pct_within_18w"]
        quartiles = pd.qcut(base, 4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")
        for q, color in zip(["Q1", "Q2", "Q3", "Q4"], [VERMILION, GOLD, TEAL, BLUE]):
            members = set(quartiles[quartiles == q].index)
            if not members:
                continue
            line = sub[sub["provider_code"].isin(members)].groupby("period")["pct_within_18w"].mean().reindex(periods)
            ax.plot(x, line, color=color, lw=1.8, label=q)
        configure_axes(ax)
        ax.set_title(labels[code], loc="left", color=INK, fontsize=11)
        ax.set_ylim(0, 100)
        ax.set_xticks(x[::6], [periods[i] for i in x[::6]], rotation=45)
    axes[0, 0].legend(frameon=False, ncol=4, fontsize=7, loc="upper left")
    fig.suptitle("Balanced-panel quartile means retain separation over 29 months", x=0.01, ha="left", color=INK, fontsize=15)
    fig.supxlabel("Month", color=MUTED)
    fig.supylabel("% within 18 weeks", color=MUTED)
    finish_figure(fig, figures_dir / "figure3_balanced_panel_quartiles.png")

    # Figure 4: gastroenterology trajectory detail, with the recoding sibling.
    code = "C_301"
    g = panel[(panel["specialty_code"] == code) & (panel["provider_code"] == "RJL")].set_index("period").reindex(periods)
    cohort = monthly500[monthly500["specialty_code"] == code].set_index("period").reindex(periods)
    sibling = panel[(panel["specialty_code"] == "C_300") & (panel["provider_code"] == "RJL")].set_index("period").reindex(periods)
    fig, ax = plt.subplots(figsize=(11, 5.2))
    configure_axes(ax)
    ax.plot(x, cohort["mean_pct"], color=TEAL, lw=2, label="Gastro cohort mean")
    ax.plot(x, g["pct_within_18w"], color=VERMILION, lw=2.4, marker="o", ms=3, label="RJL gastroenterology")
    if sibling["pct_within_18w"].notna().any():
        ax.plot(x, sibling["pct_within_18w"], color=MUTED, lw=1.4, ls="--", label="RJL general medicine (C_300)")
    ax.set_ylim(0, 100)
    ax.set_ylabel("% within 18 weeks", color=MUTED)
    ax.set_xticks(x[::3], [periods[i] for i in x[::3]], rotation=45)
    ax.set_title("RJL shows the gastro trajectory and its January 2024 recoding context", loc="left", color=INK, fontsize=14, pad=14)
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    finish_figure(fig, figures_dir / "figure4_provider_trajectory_detail.png")


def write_sources(manifest: dict, path: Path) -> None:
    lines = [
        "# Data Sources",
        "",
        "NHS England RTT Waiting Times: https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/",
        "",
        f"The analysis uses the local manifest-listed RTT Incomplete Pathways CSVs. The local manifest records acquisition on {manifest.get('acquisition_date', 'an unspecified date')}. No files were downloaded by this pipeline.",
        "Vintages are classified from the local manifest: the six specified months are first release; the remaining months are revised unless the manifest notes otherwise.",
        "",
        "| Period | Local filename | Manifest download URL | Vintage |",
        "|---|---|---|---|",
    ]
    for entry in manifest["files"]:
        url = entry.get("download_url") or "(blank in local manifest; see NHS England base URL above)"
        note = entry.get("notes", "") or ""
        vintage = "First release" if entry["period"] in FIRST_RELEASE else "Revised"
        if note:
            vintage = f"{vintage}; {note}"
        lines.append(f"| {entry['period']} | `{entry['filename']}` | {url} | {vintage} |")
    path.write_text("\n".join(lines) + "\n")


def fmt(value, digits=2):
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "NA"
    return f"{float(value):.{digits}f}"


def build_report(results_dir: Path, report_path: Path, gate: GateResult, comparison: pd.DataFrame,
                 monthly500: pd.DataFrame, persistence: pd.DataFrame, split: pd.DataFrame,
                 occupancy_summary: pd.DataFrame, recodes: pd.DataFrame, variance: pd.DataFrame,
                 balanced: pd.DataFrame, recode_sensitivity_df: pd.DataFrame | None = None,
                 occupancy_profile: pd.DataFrame | None = None) -> None:
    lines = [
        "# Finding 03 — provider persistence across four treatment functions",
        "",
        "## Reproduction gate",
        "",
        f"**{'PASS' if gate.ok else 'FAIL'}** — April 2026 gastroenterology (`C_301`), `Part_2`, `NONC` excluded, with a >=500 pathway floor.",
        "",
    ]
    lines += [f"- {line}" for line in gate.lines]
    if not gate.ok:
        lines += ["", "The gate failed, so no cross-specialty conclusion is accepted.", ""]
        report_path.write_text("\n".join(lines))
        return

    lines += [
        "",
        "## What the four-specialty comparison shows",
        "",
        "The comparison table uses the >=1,000 pathway floor so it lines up with Finding 01's cross-specialty size-control convention. The monthly and balanced-panel outputs also include the >=500 floor requested in the brief.",
        "",
        "| Specialty | SD range (pp) | SD trend (pp/year) | ICC(1) | Split-half rho | Jan 2024 vs May 2026 rho (n) | Balanced N |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in comparison.iterrows():
        lines.append(
            f"| {row['specialty']} | {fmt(row['sd_min'])}–{fmt(row['sd_max'])} | {fmt(row['sd_trend_pp_year'])} | {fmt(row['icc1'], 3)} | {fmt(row['split_half_spearman'], 3)} | {fmt(row['first_last_spearman'], 3)} ({int(row['first_last_n'])}) | {int(row['balanced_n'])} |"
        )
    lines += ["", "### Plain-language verdict", ""]
    other = comparison[comparison["specialty_code"] != "C_301"]
    g = comparison[comparison["specialty_code"] == "C_301"].iloc[0]
    if (other["split_half_spearman"] >= g["split_half_spearman"] * 0.8).all() and (other["icc1"] >= 0.5).all():
        lines.append("Provider persistence is not confined to gastroenterology. Ophthalmology, ENT, and Trauma and Orthopaedics all retain substantial between-provider structure and multi-month rank persistence, although the strength differs by specialty. The evidence supports persistence as a broad property of English elective care within these four functions, not an identical effect everywhere.")
    else:
        lines.append("The gastroenterology result is stronger than at least one of the other treatment functions. The data therefore supports provider persistence as a real gastroenterology finding and a graded cross-specialty pattern, rather than a claim that persistence is equally structural across all English elective care.")

    lines += ["", "## Persistence details", "", "The full machine-readable tables are in `results/` and `pack/outputs/`. Rank decay is the unweighted mean of all month-pair Spearman correlations at each lag, using the provider intersection for that pair; all 28 lag rows are retained, including the noisy one-pair lag 28 endpoint. The terminal correlations remain positive rather than reaching zero, so the pattern is gradual decay with persistent structure, not rank reset. The split-half calculation uses January 2024–February 2025 and April 2025–May 2026 and deliberately leaves March 2025 out as the middle month, matching the gastro control. The headline patterns are:", ""]
    for _, row in persistence[persistence["floor"] == 500].iterrows():
        lines.append(
            f"- **{row['specialty']}**: consecutive-month Spearman mean {fmt(row['consecutive_mean_spearman'], 3)}; first-versus-last {fmt(row['first_last_spearman'], 3)} (n={int(row['n_first_last'])}); bottom-decile survivors {row['bottom_decile_survivors']} versus {fmt(row['bottom_decile_expected_random'], 1)} expected at random."
        )
    lines += ["", "## Balanced-panel controls", ""]
    lines.append("The balanced panel requires every provider to clear the floor in all 29 months. Its pathway-month share, variance decomposition, split-half result, and rank-decay outputs are reported in the corresponding CSVs.")
    for _, row in balanced[balanced["floor"] == 500].iterrows():
        lines.append(f"- **{row['specialty']}**: {int(row['balanced_n'])} providers, carrying {fmt(100 * row['pathway_month_share'], 1)}% of cohort pathway-months; SD range {fmt(row['sd_min'])}–{fmt(row['sd_max'])}pp; balanced consecutive rho {fmt(row['balanced_consecutive_mean_spearman'], 3)} and first-last rho {fmt(row['balanced_first_last_spearman'], 3)} (n={int(row['balanced_first_last_n'])}).")
    lines += ["", "Variance decomposition is the one-way equal-month provider ANOVA on the complete balanced panel. The between and within shares are sums-of-squares fractions; ICC(1) is the corresponding reliability estimate.", ""]
    for _, row in variance[variance["floor"] == 500].iterrows():
        lines.append(f"- **{row['specialty']}**: between-provider {fmt(100 * row['share_variance_between_providers'], 1)}%, within-provider {fmt(100 * row['share_variance_within_provider'], 1)}%, ICC(1) {fmt(row['icc1'], 3)}, SD of provider means {fmt(row['sd_provider_means_pp'])}pp, mean within-provider SD {fmt(row['mean_within_provider_sd_pp'])}pp.")
    lines += ["", "## Decile occupancy", "", "Decile size is `ceil(N/10)` per month with deterministic code order after sorting by percentage. The occupancy CSVs report distinct providers ever entering each tail, total slot assignments, the eligible provider universe, the no-reuse ceiling, and the highest occupancy providers for both the moving cohort and the balanced panel. Slot assignments are not a claim that every slot would be a distinct provider under rotation.", ""]
    for _, row in occupancy_summary[occupancy_summary["floor"] == 500].head(8).iterrows():
        panel_label = row.get("panel", "moving cohort")
        if pd.isna(panel_label) or not panel_label:
            panel_label = "moving"
        lines.append(f"- **{row['specialty']} ({panel_label})**: bottom distinct {int(row['distinct_bottom_decile_providers'])} of {int(row['bottom_decile_slots'])} slots and {int(row['eligible_provider_universe'])} eligible providers; top distinct {int(row['distinct_top_decile_providers'])} of {int(row['top_decile_slots'])} slots.")
    if occupancy_profile is not None and not occupancy_profile.empty:
        lines.append("")
        for code, specialty in FOCUS_CODES.items():
            top = occupancy_profile[(occupancy_profile["specialty_code"] == code) & (occupancy_profile["floor"] == 500) & (occupancy_profile["panel"] == "moving")].nlargest(2, "months_in_top_decile")
            bottom = occupancy_profile[(occupancy_profile["specialty_code"] == code) & (occupancy_profile["floor"] == 500) & (occupancy_profile["panel"] == "moving")].nlargest(2, "months_in_bottom_decile")
            if not top.empty and not bottom.empty:
                lines.append(f"- **{specialty} highest occupancy:** bottom {', '.join(f'{r.provider_code} ({int(r.months_in_bottom_decile)}/29)' for r in bottom.itertuples())}; top {', '.join(f'{r.provider_code} ({int(r.months_in_top_decile)}/29)' for r in top.itertuples())}.")
    lines += ["", "## Recoding checks", ""]
    if recodes.empty:
        lines.append("No provider-month changes above the 50% flag threshold were found in the four target functions.")
    else:
        material = recodes[recodes["material_event"]]
        opposite = material[material["opposite_material_sibling"]]
        lines.append(f"The complete audit flags {len(recodes)} provider-month changes above 50%; {len(material)} have at least 500 pathways on one side of the transition. These are flags for review, not automatic exclusions. The material subset contains {len(opposite)} transitions with an opposite-direction sibling movement of at least 500 pathways; those are recoding candidates rather than proven reallocations. Full details are in `recode_flags.csv`, with a sensitivity rerun in `recode_sensitivity.csv`.")
        for _, row in material[material["opposite_material_sibling"]].head(12).iterrows():
            sibling = row["sibling_details"] or "no opposite-direction sibling in the checked codes"
            change = "infinite from zero" if math.isinf(float(row["relative_change"])) else f"{float(row['relative_change']):+.1%}"
            lines.append(f"- `{row['provider_code']}` {row['specialty']} {row['from_period']}→{row['to_period']}: {float(row['from_total']):.0f}→{float(row['to_total']):.0f} ({change}); {sibling}.")
        if len(opposite) > 12:
            lines.append(f"- {len(opposite) - 12} additional material sibling-opposite flags are in the CSV.")
        if recode_sensitivity_df is not None and not recode_sensitivity_df.empty:
            lines.append("")
            lines.append("Conservative sensitivity: excluding every provider-specialty with a material flag from the balanced panel leaves the core ICC and split-half conclusions in the following ranges:")
            for _, row in recode_sensitivity_df[recode_sensitivity_df["floor"] == 500].iterrows():
                lines.append(f"- {row['specialty']}: ICC {fmt(row['icc_baseline'], 3)} → {fmt(row['icc_excluding_material_flags'], 3)}; split-half rho {fmt(row['split_half_baseline'], 3)} → {fmt(row['split_half_excluding_material_flags'], 3)}; retained N {int(row['balanced_n_excluding_material_flags'])}.")
    lines += ["", "## Limitations", "", "- Six months are first-release rather than revised: October 2025, November 2025, January 2026, February 2026, April 2026, and May 2026. All are in the final eight months, so recent trend endpoints are least settled.", "- Treatment-function code is not a complete case-mix adjustment. The analysis describes provider persistence in the observed RTT distribution; it does not identify causes.", "- Provider codes are used for continuity because names change mid-series. A code can still represent an organisation whose structure or catchment changes.", "- The monthly >=500 and >=1,000 cohorts can change as providers cross the floor. The balanced-panel analysis is the control for cohort churn.", "- The RJL gastro trajectory has a January 2024 recoding context: its gastro pathways appear under `C_300` before moving into `C_301`. The flagged transition is retained and shown rather than silently discarded.", "", "## Reproducibility", "", "From the Finding 03 workspace, run `cd ../../.. && ./.venv311/bin/python \"Codex's Workspace/Codex's Verifications/finding-03/scripts/finding_03_pipeline.py\" --force`. The script uses only local files under `data/rtt_monthly_series/`, caches provider-month aggregates, and writes all derived tables and figures under `results/`."]
    report_path.write_text("\n".join(lines) + "\n")


def run_analysis(project_root: Path, work_dir: Path, force: bool = False) -> int:
    results_dir = work_dir / "results"
    figures_dir = results_dir / "figures"
    pack_dir = work_dir / "pack"
    results_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(project_root)
    periods = manifest_periods(manifest)
    if periods != MONTHS:
        raise ValueError(f"Manifest periods differ from expected Jan 2024-May 2026 series: {periods}")
    cache_path = results_dir / "provider_month_panel.csv"
    print(f"Loading {len(periods)} monthly files and all treatment-function codes for sibling checks...")
    panel = extract_panel(project_root, cache_path, force=force)

    april = panel[(panel["period"] == "2026-04") & (panel["specialty_code"] == "C_301")]
    gate = validate_reproduction(april)
    (results_dir / "reproduction_check.txt").write_text("\n".join(gate.lines) + f"\nRESULT: {'PASS' if gate.ok else 'FAIL'}\n")
    print("Reproduction gate:", "PASS" if gate.ok else "FAIL")
    if not gate.ok:
        build_report(results_dir, work_dir / "REPORT.md", gate, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
        return 1

    monthly500 = monthly_spread(panel, 500)
    monthly1000 = monthly_spread(panel, 1000)
    monthly500.to_csv(results_dir / "monthly_spread_floor500.csv", index=False)
    monthly1000.to_csv(results_dir / "monthly_spread_floor1000.csv", index=False)

    persistence_rows: list[dict] = []
    decay_frames: list[pd.DataFrame] = []
    consecutive_frames: list[pd.DataFrame] = []
    split_rows: list[dict] = []
    balanced_persistence_rows: list[dict] = []
    balanced_decay_frames: list[pd.DataFrame] = []
    balanced_consecutive_frames: list[pd.DataFrame] = []
    variance_rows: list[dict] = []
    balanced_rows: list[dict] = []
    balanced_monthly_rows: list[dict] = []
    occupancy_rows: list[pd.DataFrame] = []
    occupancy_balanced_rows: list[pd.DataFrame] = []
    occupancy_summary_rows: list[dict] = []
    balanced_sets: dict[tuple[str, int], set[str]] = {}
    for floor in (500, 1000):
        for code in FOCUS_CODES:
            consecutive, summary = rank_persistence(panel, code, periods, floor)
            consecutive_frames.append(consecutive)
            persistence_rows.append(summary)
            decay_frames.append(rank_decay(panel, code, periods, floor))
            codes = balanced_codes(panel, code, periods, floor)
            balanced_sets[(code, floor)] = codes
            balanced_panel = panel[(panel["specialty_code"] == code) & panel["provider_code"].isin(codes) & (panel["total_waiting"] >= floor)].copy()
            balanced_consecutive, balanced_summary = rank_persistence(panel, code, periods, floor, restrict=codes)
            balanced_consecutive_frames.append(balanced_consecutive.assign(panel="balanced"))
            balanced_decay_frames.append(rank_decay(panel, code, periods, floor, restrict=codes).assign(panel="balanced"))
            balanced_summary["panel"] = "balanced"
            balanced_persistence_rows.append(balanced_summary)
            split_rows.append(split_half_moving_summary(panel, code, periods, floor))
            variance_rows.append(variance_decomposition(balanced_panel, code, floor))
            all_monthly_pathways = monthly500 if floor == 500 else monthly1000
            all_pathways = all_monthly_pathways[all_monthly_pathways["specialty_code"] == code]["pathways"].sum()
            balanced_pathways = balanced_panel["total_waiting"].sum()
            sd = all_monthly_pathways[all_monthly_pathways["specialty_code"] == code]["sd_pct"]
            bs = monthly_spread(balanced_panel.assign(specialty_code=code), floor) if False else None
            for period in periods:
                bg = balanced_panel[balanced_panel["period"] == period]
                if period == periods[0]:
                    first_balanced_stats = cohort_stats(bg, floor)
                if period == periods[-1]:
                    last_balanced_stats = cohort_stats(bg, floor)
            # balanced per-month stats are computed directly to avoid mixing the moving cohort.
            bspread = []
            for period in periods:
                row = cohort_stats(balanced_panel[balanced_panel["period"] == period], floor)
                row.update({"specialty_code": code, "specialty": FOCUS_CODES[code], "floor": floor, "period": period, "panel": "balanced"})
                bspread.append(row)
                balanced_monthly_rows.append(row)
            bsd = pd.Series([r.get("sd_pct", np.nan) for r in bspread])
            slope, _ = ols_slope(bsd)
            balanced_rows.append({
                "specialty_code": code,
                "specialty": FOCUS_CODES[code],
                "floor": floor,
                "balanced_n": len(codes),
                "pathway_month_share": float(balanced_pathways / all_pathways) if all_pathways else np.nan,
                "sd_min": float(bsd.min()),
                "sd_max": float(bsd.max()),
                "sd_mean": float(bsd.mean()),
                "sd_trend_pp_year": float(slope * 12),
                "first_mean_pct": float(bspread[0].get("mean_pct", np.nan)),
                "last_mean_pct": float(bspread[-1].get("mean_pct", np.nan)),
            })
            profile, occ_summary = occupancy(panel, code, periods, floor)
            occupancy_rows.append(profile)
            occupancy_summary_rows.append(occ_summary)
            balanced_profile, balanced_occ_summary = occupancy(panel, code, periods, floor, restrict=codes)
            if not balanced_profile.empty:
                balanced_profile["panel"] = "balanced"
                occupancy_balanced_rows.append(balanced_profile)
            balanced_occ_summary["panel"] = "balanced"
            occupancy_summary_rows.append(balanced_occ_summary)

    persistence = pd.DataFrame(persistence_rows).merge(pd.DataFrame(split_rows), on=["specialty_code", "specialty", "floor"], how="left")
    decay = pd.concat(decay_frames, ignore_index=True)
    consecutive = pd.concat(consecutive_frames, ignore_index=True)
    balanced_consecutive = pd.concat(balanced_consecutive_frames, ignore_index=True)
    balanced_decay = pd.concat(balanced_decay_frames, ignore_index=True)
    variance = pd.DataFrame(variance_rows)
    balanced = pd.DataFrame(balanced_rows).merge(variance, on=["specialty_code", "specialty", "floor"], how="left")
    balanced_split = pd.DataFrame([dict(row, panel="balanced") for row in split_rows])
    # Replace moving split values with the explicitly computed balanced values.
    balanced_split_rows = []
    for code in FOCUS_CODES:
        for floor in (500, 1000):
            bal_codes = balanced_sets[(code, floor)]
            row = split_half_summary(panel, code, periods, floor, bal_codes)
            row["panel"] = "balanced"
            balanced_split_rows.append(row)
    balanced_split = pd.DataFrame(balanced_split_rows)
    balanced = balanced.merge(balanced_split[["specialty_code", "specialty", "floor", "spearman", "worst_quartile_retained", "best_quartile_retained"]].rename(columns={
        "spearman": "balanced_split_half_spearman",
        "worst_quartile_retained": "balanced_worst_quartile_retained",
        "best_quartile_retained": "balanced_best_quartile_retained",
    }), on=["specialty_code", "specialty", "floor"], how="left")
    balanced_rank = pd.DataFrame(balanced_persistence_rows)[["specialty_code", "specialty", "floor", "n_first_last", "first_last_spearman", "consecutive_mean_spearman"]]
    balanced = balanced.merge(balanced_rank.rename(columns={
        "n_first_last": "balanced_first_last_n",
        "first_last_spearman": "balanced_first_last_spearman",
        "consecutive_mean_spearman": "balanced_consecutive_mean_spearman",
    }), on=["specialty_code", "specialty", "floor"], how="left")
    occupancy_profile = pd.concat([p for p in occupancy_rows if not p.empty], ignore_index=True)
    occupancy_balanced_profile = pd.concat([p for p in occupancy_balanced_rows if not p.empty], ignore_index=True)
    occupancy_summary = pd.DataFrame(occupancy_summary_rows)
    recodes = recode_flags(panel, periods)
    recode_sensitivity_df = recode_sensitivity(panel, recodes, periods)

    persistence.to_csv(results_dir / "persistence_summary.csv", index=False)
    decay.to_csv(results_dir / "rank_correlation_decay.csv", index=False)
    consecutive.to_csv(results_dir / "rank_stability_consecutive.csv", index=False)
    balanced_consecutive.to_csv(results_dir / "rank_stability_consecutive_balanced.csv", index=False)
    balanced_decay.to_csv(results_dir / "rank_correlation_decay_balanced.csv", index=False)
    balanced_persistence_output = pd.DataFrame(balanced_persistence_rows).drop(columns=["panel"], errors="ignore").merge(
        balanced_split.drop(columns=["panel"], errors="ignore"),
        on=["specialty_code", "specialty", "floor"], how="left",
    )
    balanced_persistence_output["panel"] = "balanced"
    balanced_persistence_output.to_csv(results_dir / "persistence_summary_balanced.csv", index=False)
    variance.to_csv(results_dir / "variance_decomposition.csv", index=False)
    balanced.to_csv(results_dir / "balanced_panel_summary.csv", index=False)
    pd.DataFrame(balanced_monthly_rows).to_csv(results_dir / "balanced_panel_monthly_spread.csv", index=False)
    occupancy_profile.to_csv(results_dir / "decile_occupancy_provider.csv", index=False)
    occupancy_balanced_profile.to_csv(results_dir / "decile_occupancy_provider_balanced.csv", index=False)
    occupancy_summary.to_csv(results_dir / "decile_occupancy_summary.csv", index=False)
    recodes.to_csv(results_dir / "recode_flags.csv", index=False)
    recode_sensitivity_df.to_csv(results_dir / "recode_sensitivity.csv", index=False)

    # Cross-specialty comparison deliberately uses the >=1000 floor.
    comparison_rows: list[dict] = []
    for code in FOCUS_CODES:
        m = monthly1000[monthly1000["specialty_code"] == code].sort_values("period")
        p = persistence[(persistence["specialty_code"] == code) & (persistence["floor"] == 1000)].iloc[0]
        v = variance[(variance["specialty_code"] == code) & (variance["floor"] == 1000)].iloc[0]
        b = balanced[(balanced["specialty_code"] == code) & (balanced["floor"] == 1000)].iloc[0]
        slope, _ = ols_slope(m["sd_pct"])
        comparison_rows.append({
            "specialty_code": code,
            "specialty": FOCUS_CODES[code],
            "floor": 1000,
            "sd_min": float(m["sd_pct"].min()),
            "sd_max": float(m["sd_pct"].max()),
            "sd_trend_pp_year": float(slope * 12),
            "icc1": float(v["icc1"]),
            "split_half_spearman": float(p["spearman"]),
            "first_last_spearman": float(p["first_last_spearman"]),
            "first_last_n": int(p["n_first_last"]),
            "balanced_n": int(b["balanced_n"]),
        })
    comparison = pd.DataFrame(comparison_rows)
    comparison.to_csv(results_dir / "comparison_floor1000.csv", index=False)

    make_figures(monthly500, decay[decay["floor"] == 500], panel, periods, balanced_sets, figures_dir)
    report_path = work_dir / "REPORT.md"
    build_report(results_dir, report_path, gate, comparison, monthly500, persistence, pd.DataFrame(split_rows), occupancy_summary, recodes, variance, balanced, recode_sensitivity_df, occupancy_profile)
    (results_dir / "analysis_report.txt").write_text(report_path.read_text())

    # Clean reproducibility pack mirrors the published Finding 01/02 layout.
    if pack_dir.exists():
        shutil.rmtree(pack_dir)
    for directory in [pack_dir / "analysis", pack_dir / "data", pack_dir / "figures", pack_dir / "outputs"]:
        directory.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__), pack_dir / "analysis" / "finding_03_pipeline.py")
    (pack_dir / "analysis" / "README.md").write_text("From the project root, run `./.venv311/bin/python pack/analysis/finding_03_pipeline.py --project-root . --work-dir \"Codex's Workspace/Codex's Verifications/finding-03\" --force`. The pack script uses relative project and output paths.\n")
    write_sources(manifest, pack_dir / "data" / "SOURCES.md")
    for csv_path in results_dir.glob("*.csv"):
        shutil.copy2(csv_path, pack_dir / "outputs" / csv_path.name)
    for figure_path in figures_dir.glob("*.png"):
        shutil.copy2(figure_path, pack_dir / "figures" / figure_path.name)
    (pack_dir / "README.md").write_text(
        "# Finding 03 reproducibility pack\n\n"
        "Status: analysis complete; April 2026 gastroenterology reproduction gate passed.\n\n"
        "Series: NHS England RTT Incomplete Pathways, January 2024 to May 2026; exact Part_2, NONC excluded; four treatment functions C_301, C_130, C_120, and C_110.\n\n"
        "Claim: provider-level variation and rank persistence are compared across four treatment functions, with moving-cohort and balanced-panel controls. The report states the cross-specialty verdict and limitations.\n"
    )
    print(f"Wrote report: {report_path}")
    print(f"Wrote pack: {pack_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--work-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--force", action="store_true", help="reparse raw monthly CSVs instead of using the cache")
    args = parser.parse_args()
    project_root = find_project_root(args.project_root)
    return run_analysis(project_root, args.work_dir.resolve(), force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
