"""Parse RTT band matrices once, retaining an inspectable provider-level cache.

No percentiles are computed here. A cache row pools commissioner-level records
for one provider, part and treatment function. National consumers must select
C_999 ONLY: it already totals all treatment functions, so summing it alongside
the specialty rows doubles the list. Raw source files are never modified.

The source is parsed with DuckDB; SHA-256 is a separate byte-level provenance
pass. Cache reuse checks source path, size, mtime_ns, parser version and scope,
and performs no source content read when those are unchanged.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

import duckdb
import numpy as np
import pandas as pd

PARSER_VERSION = "finding04-cache-v2"
BASE = Path(__file__).resolve().parents[1]
DEFAULT_CACHE = BASE / "results" / "cache"
KEY_MAP = {"Provider Org Code":"provider", "Provider Org Name":"provider_name",
           "Commissioner Org Code":"commissioner", "RTT Part Type":"part",
           "Treatment Function Code":"code", "Treatment Function Name":"specialty_name"}
TOTAL_COLUMNS = ["Total", "Patients with unknown clock start date", "Total All"]
RAW_KEYS = ["provider", "commissioner", "part", "code"]


class DataQualityError(ValueError):
    """A source cannot safely be represented as nonnegative integer bands."""


@dataclass
class CacheData:
    index: pd.DataFrame
    bands: np.ndarray
    band_names: list[str]
    audit: dict
    paths: dict[str, Path]
    cache_hit: bool = False


def expected_bands(kind: str) -> list[str]:
    last = 52 if kind == "baseline" else 104
    return [f"Gt {i:02d} To {i+1:02d} Weeks SUM 1" for i in range(last)] + [f"Gt {last} Weeks SUM 1"]


def find_project_root(start: Path | None = None) -> Path:
    here = (start or Path(__file__)).resolve()
    for p in [here, *here.parents, Path.cwd(), *Path.cwd().parents]:
        if (p / "data/rtt_monthly_series/manifest.json").is_file():
            return p
    raise FileNotFoundError("Cannot find data/rtt_monthly_series/manifest.json")


def cache_paths(source: Path, kind: str, cache_dir: Path) -> dict[str, Path]:
    stem = source.stem + "__" + kind
    return {key: cache_dir / (stem + suffix) for key, suffix in
            {"npz":".npz", "index":".index.csv", "audit":".audit.json"}.items()}


def load_cache(npz_path: Path | str) -> CacheData:
    npz_path = Path(npz_path)
    stem = npz_path.with_suffix("")
    paths = {"npz":npz_path,"index":Path(str(stem)+".index.csv"),"audit":Path(str(stem)+".audit.json")}
    audit = json.loads(paths["audit"].read_text())
    if audit.get("status") != "ok":
        raise DataQualityError(f"Cache audit is not successful: {paths['audit']}")
    with np.load(npz_path, allow_pickle=False) as z:
        bands, band_names = z["bands"], z["band_names"].tolist()
    index = pd.read_csv(paths["index"], dtype={c:"str" for c in ["provider","provider_name","part","code","specialty_name","period"]})
    if len(index) != len(bands):
        raise DataQualityError("Cache matrix/index row count mismatch")
    return CacheData(index, bands, band_names, audit, paths, True)


def _json(path: Path, value: dict):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _examples(frame: pd.DataFrame, mask, limit=20) -> list[dict]:
    return json.loads(frame.loc[mask].head(limit).to_json(orient="records"))


def _count_audit(values: np.ndarray) -> dict:
    finite = np.isfinite(values)
    return {"missing_cells":int(np.isnan(values).sum()), "nonfinite_cells":int((~finite).sum()),
            "negative_cells":int((values < 0).sum()),
            "fractional_cells":int((finite & (values != np.floor(values))).sum()),
            "rows_with_missing":int(np.isnan(values).any(axis=1).sum())}


def build_source(source_path: Path | str, period: str, kind: str = "monthly",
                 cache_dir: Path | str = DEFAULT_CACHE, force: bool = False) -> CacheData:
    if kind not in {"monthly", "baseline", "full"}:
        raise ValueError(f"Unknown source kind {kind}")
    source, cache_dir = Path(source_path).resolve(), Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = cache_paths(source, kind, cache_dir)
    stat = source.stat()
    parts = ["Part_1A", "Part_1B"] if kind == "full" else ["Part_2"]
    fingerprint = {"path":str(source), "size_bytes":stat.st_size, "mtime_ns":stat.st_mtime_ns,
                   "parser_version":PARSER_VERSION, "period":period,"kind":kind,"parts":parts}
    if not force and all(p.is_file() for p in paths.values()):
        previous = json.loads(paths["audit"].read_text())
        if previous.get("fingerprint") == fingerprint and previous.get("status") == "ok":
            return load_cache(paths["npz"])

    digest = hashlib.sha256()
    with source.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            digest.update(chunk)
    with source.open(encoding="utf-8-sig", newline="") as f:
        headers = next(csv.reader(f))
    bands = expected_bands(kind)
    observed_bands = [c for c in headers if re.fullmatch(r"Gt \d+(?: To \d+)? Weeks SUM 1", c)]
    audit = {"status":"building", "kind":kind, "period":period, "fingerprint":fingerprint,
             "source":{**fingerprint,"sha256":digest.hexdigest()},
             "created_utc":datetime.now(timezone.utc).isoformat(),
             "schema":{"columns":headers,"band_columns":observed_bands,"expected_band_count":len(bands),
                       "missing_bands":sorted(set(bands)-set(observed_bands)),
                       "unexpected_bands":sorted(set(observed_bands)-set(bands))}}
    def reject(message):
        audit.update(status="failed",error=message)
        _json(paths["audit"],audit)
        raise DataQualityError(message)
    if len(headers) != len(set(headers)):
        reject("Duplicate source column names")
    if audit["schema"]["missing_bands"] or audit["schema"]["unexpected_bands"]:
        reject("Band schema differs from expected modern/baseline schema")
    if any(c not in headers for c in KEY_MAP):
        reject("Missing required identifier column")
    def quote(s):
        return '"'+s.replace('"','""')+'"'
    select = [f"{quote(src)} AS {quote(dst)}" for src,dst in KEY_MAP.items()]
    numeric_columns = bands + [c for c in TOTAL_COLUMNS if c in headers]
    select += [f"CAST({quote(c)} AS DOUBLE) AS {quote(c)}" for c in numeric_columns]
    try:
        with duckdb.connect() as con:
            frame = con.execute("SELECT " + ",".join(select) +
                " FROM read_csv(?, header=true, all_varchar=true)",[str(source)]).df()
    except Exception as exc:
        reject(f"DuckDB could not parse a numeric field: {exc}")
    audit["raw_band_cells_by_part"] = {str(part):_count_audit(g[bands].to_numpy(float))
                                       for part,g in frame.groupby("part",dropna=False)}
    selected = frame.part.isin(parts)
    nonc = frame.commissioner.eq("NONC")
    audit["filters"] = {"raw_rows":len(frame),"raw_rows_by_part":frame.part.value_counts(dropna=False).to_dict(),
                        "selected_part_rows":int(selected.sum()),
                        "excluded_other_part_rows":int((~selected).sum()),
                        "excluded_NONC_rows_in_selected_parts":int((selected & nonc).sum()),
                        "retained_rows":int((selected & ~nonc).sum())}
    frame = frame.loc[selected & ~nonc].copy().reset_index(drop=True)
    if frame.empty:
        reject("No rows survived exact part and commissioner filters")
    if frame[RAW_KEYS].isna().any().any():
        reject("Missing retained provider/commissioner/part/treatment-function identifier")
    raw_values = frame[bands].to_numpy(float, copy=True)
    audit["retained_band_cells"] = _count_audit(raw_values)
    bad = np.isinf(raw_values) | (raw_values<0) | (np.isfinite(raw_values) & (raw_values != np.floor(raw_values)))
    audit["retained_band_cells"]["examples"] = [
        {**frame.loc[int(r),RAW_KEYS].to_dict(),"column":bands[int(c)],
         "value":None if not np.isfinite(raw_values[r,c]) else float(raw_values[r,c])}
        for r,c in np.argwhere(bad)[:20]]
    if bad.any():
        reject("Retained band counts contain infinite, negative or fractional cells")
    # A blank is NOT assumed to be zero. Since valid counts are nonnegative,
    # an independently reported total already exhausted by observed bands
    # mathematically certifies that the remaining blank bands contain zero.
    missing = np.isnan(raw_values)
    missing_rows = missing.any(axis=1)
    observed_sum = np.nansum(raw_values,axis=1)
    unknown = frame.get("Patients with unknown clock start date", pd.Series(np.nan,index=frame.index)).to_numpy(float)
    certified = np.zeros(len(frame),bool)
    for column in ["Total", "Total All"]:
        if column not in frame:
            continue
        independent = frame[column].to_numpy(float)
        certified |= np.isfinite(independent) & (independent == observed_sum)
        if column == "Total All":
            certified |= np.isfinite(independent) & np.isfinite(unknown) & (unknown >= 0) & (independent-unknown == observed_sum)
    unresolved = missing_rows & ~certified
    audit["blank_band_resolution"] = {"rows_with_blank_bands":int(missing_rows.sum()),
        "certified_zero_rows":int((missing_rows & certified).sum()),
        "certified_zero_cells":int(missing[certified].sum()),"unresolved_rows":int(unresolved.sum()),
        "rule":"Blank bands become zero only when a nonnull independent Total or Total All (minus known clock-unknown count where available) equals the observed-band sum; valid counts are nonnegative, so no positive residual can be hidden in blanks.",
        "unresolved_examples":_examples(frame[RAW_KEYS].assign(observed_band_sum=observed_sum),unresolved)}
    if unresolved.any():
        reject("Missing retained bands cannot be certified zero from available independent totals")
    frame["certified_blank_band_cells"] = missing.sum(axis=1)
    raw_values[missing] = 0
    frame[bands] = raw_values
    duplicates = frame.groupby(RAW_KEYS,dropna=False).size().reset_index(name="raw_rows")
    dup = duplicates.raw_rows.gt(1)
    audit["duplicate_raw_keys"] = {"duplicate_groups":int(dup.sum()),
        "excess_rows":int((duplicates.loc[dup,"raw_rows"]-1).sum()),
        "examples":_examples(duplicates,dup)}
    totals = raw_values.sum(axis=1)
    unknown = frame.get("Patients with unknown clock start date", pd.Series(np.nan,index=frame.index)).to_numpy(float)
    audit["unknown_clock"] = {"missing_rows":int(np.isnan(unknown).sum()),
        "nonnull_rows":int(np.isfinite(unknown).sum()),"positive_rows":int((unknown>0).sum()),
        "sum_known_counts":float(np.nansum(unknown)),
        "note":"Missing unknown-clock values are not imputed. Total All residuals are compared to known clock counts only."}
    audit["row_totals"] = {}
    for column in ["Total","Total All"]:
        if column not in frame:
            audit["row_totals"][column] = {"available":False}
            continue
        other = frame[column].to_numpy(float)
        available = np.isfinite(other)
        delta = other-totals
        mismatch = available & (delta != 0)
        explained = mismatch & np.isfinite(unknown) & (delta == unknown) if column == "Total All" else np.zeros(len(frame),bool)
        detail = frame[RAW_KEYS].assign(band_sum=totals,published_total=other,unknown_clock=unknown,difference=delta)
        audit["row_totals"][column] = {"available":True,"nonnull_rows":int(available.sum()),
            "equal_band_sum_rows":int((available & ~mismatch).sum()),
            "different_from_band_sum_rows":int(mismatch.sum()),
            "explained_by_known_unknown_clock_rows":int(explained.sum()),
            "unexplained_mismatch_rows":int((mismatch & ~explained).sum()),
            "max_absolute_difference":float(np.abs(delta[available]).max()) if available.any() else None,
            "unexplained_examples":_examples(detail,mismatch & ~explained)}
    keys = ["provider","part","code"]
    grouped = frame.groupby(keys,sort=True,dropna=False)
    matrix = grouped[bands].sum().astype("int64")
    index = matrix.index.to_frame(index=False)
    labels = grouped[["provider_name","specialty_name"]].first().reset_index()
    index = index.merge(labels,on=keys,validate="one_to_one",sort=False)
    index["period"] = period
    index["kind"] = kind
    index["raw_rows_pooled"] = grouped.size().to_numpy()
    index["certified_blank_band_cells"] = grouped["certified_blank_band_cells"].sum().to_numpy()
    values = matrix.to_numpy(np.int64)
    checks = []
    for (provider,part), group in index.groupby(["provider","part"],sort=True):
        ids = group.index.to_numpy()
        all_ids = ids[group.code.eq("C_999").to_numpy()]
        child_ids = ids[~group.code.eq("C_999").to_numpy()]
        if len(all_ids) != 1:
            checks.append({"provider":provider,"part":part,"issue":"missing_C_999","max_abs_band_difference":None})
            continue
        difference = values[all_ids[0]] - values[child_ids].sum(axis=0)
        if (difference != 0).any():
            checks.append({"provider":provider,"part":part,"issue":"C_999_differs_from_other_codes", 
                "total_difference":int(difference.sum()),"mismatched_bands":int((difference!=0).sum()),
                "max_abs_band_difference":int(np.abs(difference).max())})
    audit["specialty_total_reconciliation"] = {"provider_parts_checked":int(index.groupby(["provider","part"]).ngroups),
        "mismatched_provider_parts":len(checks),"details":checks,
        "note":"C_999 is a total row, retained separately; never add to its component specialty rows."}
    audit["filters"].update(pooled_provider_part_specialty_rows=len(index),
        pooled_unique_providers=int(index.provider.nunique()), pooled_specialty_codes=sorted(index.code.unique().tolist()))
    audit["national_C_999_band_sum_by_part"] = {part:int(values[index.part.eq(part).to_numpy() & index.code.eq("C_999").to_numpy()].sum()) for part in parts}
    audit["status"] = "ok"
    np.savez_compressed(paths["npz"],bands=values,band_names=np.asarray(bands,dtype=str))
    index.to_csv(paths["index"],index=False)
    _json(paths["audit"],audit)
    return CacheData(index,values,bands,audit,paths,False)


def source_inventory(project: Path) -> list[dict]:
    monthly = project / "data/rtt_monthly_series"
    manifest = json.loads((monthly/"manifest.json").read_text())
    sources = [{"path":monthly/e["filename"],"period":e["period"],"kind":"monthly"} for e in manifest["files"]]
    sources.append({"path":monthly/"201902-RTT-February2019-incomplete-pathways.csv","period":"2019-02","kind":"baseline"})
    for filename,period in [("20250228-RTT-February-2025-full-extract-revised.csv","2025-02"),
                            ("20260430-RTT-April-2026-full-extract.csv","2026-04")]:
        sources.append({"path":project/"data/source_research"/filename,"period":period,"kind":"full"})
    return sources


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--period",default="2024-01",help="One source period (defaults to gate month)")
    parser.add_argument("--kind",choices=["monthly","full","baseline"],default="monthly")
    parser.add_argument("--all",action="store_true",help="Process entire inventory; only after validation gate has passed")
    parser.add_argument("--gate-file",type=Path,help="Required with --all: JSON containing passed:true")
    parser.add_argument("--cache-dir",type=Path,default=DEFAULT_CACHE)
    parser.add_argument("--project-root",type=Path)
    parser.add_argument("--force",action="store_true")
    args=parser.parse_args()
    if args.all and (not args.gate_file or not json.loads(args.gate_file.read_text()).get("passed")):
        parser.error("--all requires --gate-file with passed:true after official median validation")
    project=args.project_root or find_project_root()
    sources=source_inventory(project)
    if not args.all:
        sources=[s for s in sources if s["period"]==args.period and s["kind"]==args.kind]
    if not sources:
        parser.error("No source matches period and kind")
    for item in sources:
        got=build_source(item["path"],item["period"],item["kind"],args.cache_dir,args.force)
        print(json.dumps({"period":item["period"],"kind":item["kind"],"cache_hit":got.cache_hit,
            "shape":list(got.bands.shape),"national":got.audit["national_C_999_band_sum_by_part"],
            "npz":str(got.paths["npz"])}),flush=True)


if __name__ == "__main__":
    main()
