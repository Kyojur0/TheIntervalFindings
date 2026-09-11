#!/usr/bin/env python3
"""Independent recomputation of NHS RTT "Finding A" from the raw April 2026 CSV.

This script deliberately does not import or consume any prior analyst code or output.
It uses only Python's standard library and prints a JSON audit record to stdout.

The output reports both the raw-full-extract result and the official England-scope
result excluding commissioner code NONC. The publication uses the latter.

Usage:
    python3 audit_nhs_rtt_finding_a.py \
      "data/source_research/20260430-RTT-April-2026-full-extract.csv"
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable


INTERVAL_RE = re.compile(r"^Gt (\d{2,3}) To (\d{2,3}) Weeks SUM 1$")
CATCH_ALL = "Gt 104 Weeks SUM 1"
GASTRO = "C_301"
PART_2 = "Part_2"


def parse_count(raw: str | None) -> int | None:
    """Parse an NHS count, preserving blank as None rather than assuming zero."""
    if raw is None or raw.strip() == "":
        return None
    try:
        value = Decimal(raw.strip().replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError(f"Non-numeric count: {raw!r}") from exc
    if value != value.to_integral_value():
        raise ValueError(f"Expected an integer count, got: {raw!r}")
    return int(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_band_columns(fieldnames: list[str]) -> list[str]:
    """Return the 105 bands in chronological order and reject schema drift."""
    intervals: dict[int, str] = {}
    for name in fieldnames:
        match = INTERVAL_RE.match(name)
        if not match:
            continue
        left, right = map(int, match.groups())
        if right != left + 1:
            raise AssertionError(f"Non-unit waiting band: {name}")
        if left in intervals:
            raise AssertionError(f"Duplicate waiting band start: {left}")
        intervals[left] = name

    expected_starts = list(range(104))
    if sorted(intervals) != expected_starts:
        missing = sorted(set(expected_starts) - set(intervals))
        extra = sorted(set(intervals) - set(expected_starts))
        raise AssertionError(f"Band schema mismatch; missing={missing}, extra={extra}")
    if CATCH_ALL not in fieldnames:
        raise AssertionError(f"Missing catch-all band {CATCH_ALL!r}")

    columns = [intervals[i] for i in expected_starts] + [CATCH_ALL]
    if len(columns) != 105:
        raise AssertionError(f"Expected 105 waiting bands, found {len(columns)}")
    return columns


@dataclass
class ProviderAggregate:
    code: str
    names: set[str] = field(default_factory=set)
    parent_codes: set[str] = field(default_factory=set)
    parent_names: set[str] = field(default_factory=set)
    commissioners: set[tuple[str, str]] = field(default_factory=set)
    bands: list[int] = field(default_factory=lambda: [0] * 105)
    row_bands: list[list[int]] = field(default_factory=list)

    def add(self, row: dict[str, str], counts: list[int]) -> None:
        self.names.add(row["Provider Org Name"].strip())
        self.parent_codes.add(row["Provider Parent Org Code"].strip())
        self.parent_names.add(row["Provider Parent Name"].strip())
        self.commissioners.add(
            (row["Commissioner Org Code"].strip(), row["Commissioner Org Name"].strip())
        )
        self.bands = [left + right for left, right in zip(self.bands, counts)]
        self.row_bands.append(counts)

    @property
    def within_18(self) -> int:
        return sum(self.bands[:18])

    @property
    def weeks_18_to_52(self) -> int:
        return sum(self.bands[18:52])

    @property
    def weeks_52_plus(self) -> int:
        return sum(self.bands[52:])

    @property
    def total(self) -> int:
        return sum(self.bands)

    @property
    def pct_within_18(self) -> float | None:
        return 100.0 * self.within_18 / self.total if self.total else None


def round_or_none(value: float | None, digits: int = 6) -> float | None:
    return None if value is None else round(value, digits)


def provider_record(provider: ProviderAggregate) -> dict[str, object]:
    row_totals = [sum(bands) for bands in provider.row_bands]
    return {
        "provider_code": provider.code,
        "provider_names": sorted(provider.names),
        "parent_codes": sorted(provider.parent_codes),
        "parent_names": sorted(provider.parent_names),
        "source_rows": len(provider.row_bands),
        "distinct_commissioners": len(provider.commissioners),
        "within_18": provider.within_18,
        "weeks_18_to_52": provider.weeks_18_to_52,
        "weeks_52_plus": provider.weeks_52_plus,
        "total": provider.total,
        "pct_within_18": round_or_none(provider.pct_within_18),
        "first_source_row_total": row_totals[0] if row_totals else 0,
        "largest_source_row_total": max(row_totals, default=0),
        "partition_identity_holds": (
            provider.within_18 + provider.weeks_18_to_52 + provider.weeks_52_plus
            == provider.total
        ),
    }


def distribution(
    providers: Iterable[ProviderAggregate], floor: int
) -> dict[str, object]:
    eligible = [p for p in providers if p.total >= floor and p.total > 0]
    percentages = [p.pct_within_18 for p in eligible]
    percentages = [p for p in percentages if p is not None]
    if percentages:
        minimum = min(percentages)
        maximum = max(percentages)
        pop_sd = statistics.pstdev(percentages)
        sample_sd = statistics.stdev(percentages) if len(percentages) > 1 else None
    else:
        minimum = maximum = pop_sd = sample_sd = None
    return {
        "floor": floor,
        "providers": len(eligible),
        "total_waiting": sum(p.total for p in eligible),
        "min_pct": round_or_none(minimum),
        "max_pct": round_or_none(maximum),
        "range_pp": round_or_none(
            maximum - minimum if minimum is not None and maximum is not None else None
        ),
        "population_sd_pp": round_or_none(pop_sd),
        "sample_sd_pp": round_or_none(sample_sd),
        "min_provider_codes": sorted(
            p.code for p in eligible if p.pct_within_18 == minimum
        ),
        "max_provider_codes": sorted(
            p.code for p in eligible if p.pct_within_18 == maximum
        ),
    }


def pooled(providers: Iterable[ProviderAggregate]) -> dict[str, object]:
    provider_list = list(providers)
    within = sum(p.within_18 for p in provider_list)
    total = sum(p.total for p in provider_list)
    return {
        "within_18": within,
        "total": total,
        "pct_within_18": round_or_none(100.0 * within / total if total else None),
    }


def audit(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header")
        fieldnames = reader.fieldnames
        required = {
            "Period",
            "Provider Parent Org Code",
            "Provider Parent Name",
            "Provider Org Code",
            "Provider Org Name",
            "Commissioner Org Code",
            "Commissioner Org Name",
            "RTT Part Type",
            "RTT Part Description",
            "Treatment Function Code",
            "Treatment Function Name",
            "Total",
        }
        missing_required = sorted(required - set(fieldnames))
        if missing_required:
            raise AssertionError(f"Missing required columns: {missing_required}")
        bands = discover_band_columns(fieldnames)

        provider_by_part_specialty: dict[
            tuple[str, str], dict[str, ProviderAggregate]
        ] = defaultdict(dict)
        provider_by_part_specialty_excluding_nonc: dict[
            tuple[str, str], dict[str, ProviderAggregate]
        ] = defaultdict(dict)
        file_rows = 0
        periods: set[str] = set()
        part_descriptions: dict[str, set[str]] = defaultdict(set)
        specialty_names: dict[str, set[str]] = defaultdict(set)
        part_profile: dict[str, Counter[str]] = defaultdict(Counter)
        gastro_part_rows: Counter[str] = Counter()
        relevant_rows: list[dict[str, object]] = []
        selected_null_band_cells = 0
        selected_rows_any_band_null = 0
        selected_rows_all_band_null = 0
        selected_strict_row_total = 0
        selected_coalesced_total = 0
        selected_bandwise_nonnull_sums = [0] * 105
        selected_bandwise_nonnull_counts = [0] * 105
        selected_total_column_values: list[int | None] = []

        for row_number, row in enumerate(reader, start=2):
            file_rows += 1
            periods.add(row["Period"].strip())
            part = row["RTT Part Type"].strip()
            specialty = row["Treatment Function Code"].strip()
            part_descriptions[part].add(row["RTT Part Description"].strip())
            specialty_names[specialty].add(row["Treatment Function Name"].strip())
            part_profile[part]["rows"] += 1
            total_value = parse_count(row["Total"])
            if total_value is None:
                part_profile[part]["total_column_blank"] += 1
            else:
                part_profile[part]["total_column_nonblank"] += 1
                part_profile[part]["total_column_sum"] += total_value

            parsed = [parse_count(row[column]) for column in bands]
            counts = [value if value is not None else 0 for value in parsed]
            row_band_total = sum(counts)
            part_profile[part]["band_derived_total"] += row_band_total

            if specialty == GASTRO:
                gastro_part_rows[part] += 1

            if specialty in {GASTRO, "C_130", "C_120", "C_110"} and part in {
                PART_2,
                "Part_2A",
            }:
                key = (part, specialty)
                code = row["Provider Org Code"].strip()
                if not code:
                    raise AssertionError(f"Blank provider code on source row {row_number}")
                aggregate = provider_by_part_specialty[key].setdefault(
                    code, ProviderAggregate(code=code)
                )
                aggregate.add(row, counts)
                if row["Commissioner Org Code"].strip() != "NONC":
                    english_aggregate = provider_by_part_specialty_excluding_nonc[
                        key
                    ].setdefault(code, ProviderAggregate(code=code))
                    english_aggregate.add(row, counts)

            if part == PART_2 and specialty == GASTRO:
                blanks = sum(value is None for value in parsed)
                selected_null_band_cells += blanks
                selected_rows_any_band_null += int(blanks > 0)
                selected_rows_all_band_null += int(blanks == len(bands))
                selected_coalesced_total += row_band_total
                if blanks == 0:
                    selected_strict_row_total += sum(value for value in parsed if value is not None)
                for index, value in enumerate(parsed):
                    if value is not None:
                        selected_bandwise_nonnull_sums[index] += value
                        selected_bandwise_nonnull_counts[index] += 1
                selected_total_column_values.append(total_value)
                if len(relevant_rows) < 8:
                    relevant_rows.append(
                        {
                            "source_row": row_number,
                            "provider_code": row["Provider Org Code"].strip(),
                            "commissioner_code": row["Commissioner Org Code"].strip(),
                            "within_18": sum(counts[:18]),
                            "weeks_18_to_52": sum(counts[18:52]),
                            "weeks_52_plus": sum(counts[52:]),
                            "total": row_band_total,
                            "partition_identity_holds": (
                                sum(counts[:18])
                                + sum(counts[18:52])
                                + sum(counts[52:])
                                == row_band_total
                            ),
                        }
                    )

    gastro = provider_by_part_specialty[(PART_2, GASTRO)]
    gastro_providers = list(gastro.values())
    gastro_excluding_nonc = provider_by_part_specialty_excluding_nonc[(PART_2, GASTRO)]
    gastro_providers_excluding_nonc = list(gastro_excluding_nonc.values())
    positive_gastro = [provider for provider in gastro_providers if provider.total > 0]
    large = [provider for provider in positive_gastro if provider.total >= 500]
    national = pooled(gastro_providers)

    if not all(
        provider.within_18 + provider.weeks_18_to_52 + provider.weeks_52_plus
        == provider.total
        for provider in gastro_providers
    ):
        raise AssertionError("Waiting-band partitions do not add to provider totals")

    large_percentages = [provider.pct_within_18 for provider in large]
    large_percentages = [value for value in large_percentages if value is not None]

    large_excluding_nonc = [
        provider
        for provider in gastro_providers_excluding_nonc
        if provider.total >= 500 and provider.total > 0
    ]
    large_excluding_nonc_percentages = [
        provider.pct_within_18 for provider in large_excluding_nonc
    ]
    large_excluding_nonc_percentages = [
        value for value in large_excluding_nonc_percentages if value is not None
    ]

    part2a_map = provider_by_part_specialty[("Part_2A", GASTRO)]
    all_codes_for_subset_check = set(gastro) | set(part2a_map)
    subset_total_violations = []
    subset_band_violations = []
    for code in sorted(all_codes_for_subset_check):
        full = gastro.get(code, ProviderAggregate(code=code))
        admitted = part2a_map.get(code, ProviderAggregate(code=code))
        if admitted.total > full.total:
            subset_total_violations.append(code)
        if any(a > f for a, f in zip(admitted.bands, full.bands)):
            subset_band_violations.append(code)

    combined_part2_part2a_within = sum(p.within_18 for p in gastro.values()) + sum(
        p.within_18 for p in part2a_map.values()
    )
    combined_part2_part2a_total = sum(p.total for p in gastro.values()) + sum(
        p.total for p in part2a_map.values()
    )

    parent_groups: dict[str, set[str]] = defaultdict(set)
    for provider in large:
        for parent_code in provider.parent_codes:
            if parent_code:
                parent_groups[parent_code].add(provider.code)
    shared_parent_groups = {
        parent: sorted(codes)
        for parent, codes in sorted(parent_groups.items())
        if len(codes) > 1
    }
    provider_name_changes = {
        provider.code: sorted(provider.names)
        for provider in gastro_providers
        if len(provider.names) > 1
    }
    exact_name_to_codes: dict[str, set[str]] = defaultdict(set)
    for provider in gastro_providers:
        for name in provider.names:
            exact_name_to_codes[name].add(provider.code)
    exact_names_with_multiple_codes = {
        name: sorted(codes)
        for name, codes in sorted(exact_name_to_codes.items())
        if len(codes) > 1
    }
    large_non_trust_name_proxy = [
        {
            "provider_code": provider.code,
            "provider_names": sorted(provider.names),
            "total": provider.total,
            "pct_within_18": round_or_none(provider.pct_within_18),
        }
        for provider in sorted(large, key=lambda item: item.code)
        if not any("NHS TRUST" in name or "NHS FOUNDATION TRUST" in name for name in provider.names)
    ]
    large_nhs_trust_name_proxy = [
        provider
        for provider in large
        if any("NHS TRUST" in name or "NHS FOUNDATION TRUST" in name for name in provider.names)
    ]
    large_nhs_trust_name_proxy_excluding_nonc = [
        provider
        for provider in large_excluding_nonc
        if any("NHS TRUST" in name or "NHS FOUNDATION TRUST" in name for name in provider.names)
    ]

    specialty_checks = {}
    for code in ["C_130", "C_120", "C_110"]:
        specialty_providers = list(provider_by_part_specialty[(PART_2, code)].values())
        specialty_checks[code] = {
            "names": sorted(specialty_names[code]),
            "large_floor_500": distribution(specialty_providers, 500),
        }

    zero_total_providers = sorted(p.code for p in gastro_providers if p.total == 0)
    row_counts = [len(provider.row_bands) for provider in gastro_providers]
    bandwise_skip_null_total = sum(selected_bandwise_nonnull_sums)

    return {
        "source": {
            "path": str(path.resolve()),
            "sha256": sha256_file(path),
            "file_rows": file_rows,
            "columns": len(fieldnames),
            "period_values": sorted(periods),
            "band_count": len(bands),
            "first_band": bands[0],
            "within_18_last_included_band": bands[17],
            "first_excluded_band": bands[18],
            "last_finite_band": bands[-2],
            "catch_all_band": bands[-1],
        },
        "definitions_in_source": {
            "part_descriptions": {
                key: sorted(value) for key, value in sorted(part_descriptions.items())
            },
            "gastro_specialty_names": sorted(specialty_names[GASTRO]),
        },
        "part_profile": {key: dict(value) for key, value in sorted(part_profile.items())},
        "gastro_part_row_counts": dict(sorted(gastro_part_rows.items())),
        "gastro_part2": {
            "source_rows": sum(row_counts),
            "provider_codes_including_zero": len(gastro_providers),
            "positive_provider_codes": len(positive_gastro),
            "zero_total_provider_codes": zero_total_providers,
            "providers_with_multiple_rows": sum(count > 1 for count in row_counts),
            "maximum_rows_per_provider": max(row_counts, default=0),
            "national_pooled": national,
            "RTF": provider_record(gastro["RTF"]),
            "RJL": provider_record(gastro["RJL"]),
            "large_floor_500": {
                **distribution(gastro_providers, 500),
                "at_least_90_pct": sum(value >= 90 for value in large_percentages),
                "provider_codes_at_least_90_pct": sorted(
                    provider.code
                    for provider in large
                    if provider.pct_within_18 is not None and provider.pct_within_18 >= 90
                ),
                "below_50_pct": sum(value < 50 for value in large_percentages),
                "below_92_pct": sum(value < 92 for value in large_percentages),
                "below_92_share_pct": round_or_none(
                    100.0 * sum(value < 92 for value in large_percentages)
                    / len(large_percentages)
                    if large_percentages
                    else None
                ),
                "below_65_pct": sum(value < 65 for value in large_percentages),
                "below_65_share_pct": round_or_none(
                    100.0 * sum(value < 65 for value in large_percentages)
                    / len(large_percentages)
                    if large_percentages
                    else None
                ),
            },
            "size_control": {
                label: distribution(gastro_providers, floor)
                for label, floor in [
                    ("any_positive", 1),
                    ("at_least_50", 50),
                    ("at_least_300", 300),
                    ("at_least_500", 500),
                    ("at_least_750", 750),
                    ("at_least_1000", 1000),
                ]
            },
        },
        "methodology_checks": {
            "band_boundary": {
                "within_18_band_indexes_zero_based": [0, 17],
                "within_18_band_count": 18,
                "last_included": bands[17],
                "first_excluded": bands[18],
            },
            "partition_identity": {
                "all_aggregated_providers_hold": True,
                "sample_source_rows": relevant_rows,
            },
            "total_column_trap": {
                "selected_rows": len(selected_total_column_values),
                "blank": sum(value is None for value in selected_total_column_values),
                "nonblank": sum(value is not None for value in selected_total_column_values),
                "sum_of_nonblank": sum(
                    value for value in selected_total_column_values if value is not None
                ),
                "band_derived_total": selected_coalesced_total,
            },
            "band_null_handling": {
                "selected_band_cells": len(selected_total_column_values) * len(bands),
                "blank_band_cells": selected_null_band_cells,
                "rows_with_any_blank_band": selected_rows_any_band_null,
                "rows_with_all_bands_blank": selected_rows_all_band_null,
                "sum_coalescing_blanks_to_zero": selected_coalesced_total,
                "sum_each_band_ignoring_nulls_then_add": bandwise_skip_null_total,
                "difference_coalesce_vs_bandwise_skip_null": (
                    selected_coalesced_total - bandwise_skip_null_total
                ),
                "sum_only_rows_with_no_blank_bands": selected_strict_row_total,
                "bands_with_no_nonblank_values": [
                    bands[index]
                    for index, count in enumerate(selected_bandwise_nonnull_counts)
                    if count == 0
                ],
            },
            "aggregation": {
                "providers_with_multiple_source_rows": sum(count > 1 for count in row_counts),
                "maximum_rows_per_provider": max(row_counts, default=0),
                "RTF": provider_record(gastro["RTF"]),
                "RJL": provider_record(gastro["RJL"]),
            },
            "part_2a": {
                "description": sorted(part_descriptions["Part_2A"]),
                "pooled": pooled(part2a_map.values()),
                "part2a_total_exceeds_part2_provider_violations": subset_total_violations,
                "part2a_band_exceeds_part2_provider_violations": subset_band_violations,
                "incorrect_part2_plus_part2a": {
                    "within_18": combined_part2_part2a_within,
                    "total": combined_part2_part2a_total,
                    "pct_within_18": round_or_none(
                        100.0 * combined_part2_part2a_within / combined_part2_part2a_total
                        if combined_part2_part2a_total
                        else None
                    ),
                },
            },
        },
        "adversarial_checks": {
            "exclude_non_english_commissioned_nonc": {
                "national_pooled": pooled(gastro_providers_excluding_nonc),
                "RTF": provider_record(gastro_excluding_nonc["RTF"]),
                "RJL": provider_record(gastro_excluding_nonc["RJL"]),
                "large_floor_500": {
                    **distribution(gastro_providers_excluding_nonc, 500),
                    "at_least_90_pct": sum(
                        value >= 90 for value in large_excluding_nonc_percentages
                    ),
                    "below_50_pct": sum(
                        value < 50 for value in large_excluding_nonc_percentages
                    ),
                    "below_92_pct": sum(
                        value < 92 for value in large_excluding_nonc_percentages
                    ),
                    "below_65_pct": sum(
                        value < 65 for value in large_excluding_nonc_percentages
                    ),
                    "provider_codes_at_least_90_pct": sorted(
                        provider.code
                        for provider in large_excluding_nonc
                        if provider.pct_within_18 is not None
                        and provider.pct_within_18 >= 90
                    ),
                },
                "size_control": {
                    label: distribution(gastro_providers_excluding_nonc, floor)
                    for label, floor in [
                        ("any_positive", 1),
                        ("at_least_50", 50),
                        ("at_least_300", 300),
                        ("at_least_500", 500),
                        ("at_least_750", 750),
                        ("at_least_1000", 1000),
                    ]
                },
            },
            "provider_identity": {
                "large_providers_sharing_a_nonblank_parent_code": shared_parent_groups,
                "provider_codes_with_multiple_names_in_month": provider_name_changes,
                "exact_provider_names_used_by_multiple_codes": exact_names_with_multiple_codes,
                "large_provider_codes": len(large),
                "large_provider_codes_without_nhs_trust_in_name": (
                    len(large_non_trust_name_proxy)
                ),
                "large_non_trust_name_proxy": large_non_trust_name_proxy,
                "nhs_trust_name_proxy_raw_full_csv": {
                    **distribution(large_nhs_trust_name_proxy, 500),
                    "at_least_90_pct": sum(
                        provider.pct_within_18 is not None
                        and provider.pct_within_18 >= 90
                        for provider in large_nhs_trust_name_proxy
                    ),
                    "below_50_pct": sum(
                        provider.pct_within_18 is not None
                        and provider.pct_within_18 < 50
                        for provider in large_nhs_trust_name_proxy
                    ),
                    "below_92_pct": sum(
                        provider.pct_within_18 is not None
                        and provider.pct_within_18 < 92
                        for provider in large_nhs_trust_name_proxy
                    ),
                    "below_65_pct": sum(
                        provider.pct_within_18 is not None
                        and provider.pct_within_18 < 65
                        for provider in large_nhs_trust_name_proxy
                    ),
                },
                "nhs_trust_name_proxy_excluding_nonc": {
                    **distribution(large_nhs_trust_name_proxy_excluding_nonc, 500),
                    "at_least_90_pct": sum(
                        provider.pct_within_18 is not None
                        and provider.pct_within_18 >= 90
                        for provider in large_nhs_trust_name_proxy_excluding_nonc
                    ),
                    "below_50_pct": sum(
                        provider.pct_within_18 is not None
                        and provider.pct_within_18 < 50
                        for provider in large_nhs_trust_name_proxy_excluding_nonc
                    ),
                    "below_92_pct": sum(
                        provider.pct_within_18 is not None
                        and provider.pct_within_18 < 92
                        for provider in large_nhs_trust_name_proxy_excluding_nonc
                    ),
                    "below_65_pct": sum(
                        provider.pct_within_18 is not None
                        and provider.pct_within_18 < 65
                        for provider in large_nhs_trust_name_proxy_excluding_nonc
                    ),
                },
                "RTF_identity": provider_record(gastro["RTF"]),
                "RJL_identity": provider_record(gastro["RJL"]),
            },
            "alternate_gastro_size_floors": {
                "at_least_300": distribution(gastro_providers, 300),
                "at_least_750": distribution(gastro_providers, 750),
            },
            "other_specialties": specialty_checks,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path, help="Raw NHS RTT full-extract CSV")
    args = parser.parse_args()
    if not args.csv_path.is_file():
        parser.error(f"File not found: {args.csv_path}")
    result = audit(args.csv_path)
    json.dump(result, fp=__import__("sys").stdout, indent=2, sort_keys=True)
    print()


if __name__ == "__main__":
    main()
