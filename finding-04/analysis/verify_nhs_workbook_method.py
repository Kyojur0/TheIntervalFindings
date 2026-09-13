#!/usr/bin/env python3
"""Identify finite-band interpolation against official NHS workbook values.

Read-only remote sources; writes two provenance/comparison CSVs to ../results.
Uses Python's standard library, so runs with the project's .venv311 Python.
This is source-method research, not the raw-file validation gate.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path
import posixpath
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
URLS = {
    "2024-01": "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/03/Incomplete-Commissioner-Jan24-XLSX-4254K-55749.xlsx",
    "2025-02": "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/07/Incomplete-Commissioner-Feb25-XLSX-4M-revised.xlsx",
    "2026-04": "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/06/Incomplete-Commissioner-Apr26-XLSX-4M-X7gGnn.xlsx",
    "2026-05": "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/07/Incomplete-Commissioner-May26-XLSX-4M-3jBgba.xlsx",
}


def column_number(coordinate: str) -> int:
    result = 0
    for character in re.match(r"[A-Z]+", coordinate)[0]:
        result = result * 26 + ord(character) - ord("A") + 1
    return result


def column_name(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


def rows(archive: zipfile.ZipFile, sheet_path: str, strings: list[str]):
    """Yield sparse numeric-column dictionaries without an Excel dependency."""
    with archive.open(sheet_path) as source:
        for _, element in ET.iterparse(source, events=("end",)):
            if element.tag != f"{{{NS['s']}}}row":
                continue
            values = {}
            for cell in element.findall("s:c", NS):
                value = cell.find("s:v", NS)
                if value is None or value.text is None:
                    continue
                if cell.get("t") == "s":
                    parsed = strings[int(value.text)]
                elif cell.get("t") in {"str", "e"}:
                    parsed = value.text
                else:
                    parsed = float(value.text)
                    if parsed.is_integer():
                        parsed = int(parsed)
                values[column_number(cell.get("r"))] = parsed
            yield int(element.get("r")), values
            element.clear()


def source_comparison(period: str, url: str):
    with urllib.request.urlopen(url, timeout=60) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    strings = [
        "".join(element.itertext())
        for element in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("s:si", NS)
    ]
    relationships = {
        element.get("Id"): posixpath.normpath(posixpath.join("xl", element.get("Target")))
        for element in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    }
    sheets = {
        element.get("name"): relationships[element.get(RID)]
        for element in ET.fromstring(archive.read("xl/workbook.xml")).findall("s:sheets/s:sheet", NS)
    }
    gates, comparisons = [], []
    published = revised = None
    for sheet in ("National", "Sub-ICB"):
        for row_number, cells in rows(archive, sheets[sheet], strings):
            if sheet == "National" and row_number in (8, 9):
                if row_number == 8:
                    published = cells.get(3)
                else:
                    revised = cells.get(3)
            code_column = 2 if sheet == "National" else 5
            code = cells.get(code_column)
            if not str(code).startswith("C_"):
                continue
            first_band_column = code_column + 2
            bands = [cells.get(column) for column in range(first_band_column, first_band_column + 105)]
            if not all(isinstance(value, (int, float)) for value in bands):
                continue
            total = sum(bands)
            if total <= 0:
                continue
            for percentile, offset in ((0.5, 108), (0.92, 109)):
                official_column = first_band_column + offset
                official = cells.get(official_column)
                # Suppressed/undefined values '-' do not provide a numeric comparison.
                if not isinstance(official, (int, float)):
                    continue
                target, before = percentile * total, 0
                for band, count in enumerate(bands):
                    if before + count >= target:
                        break
                    before += count
                # For band=104 this deliberately illustrates why interpolation is
                # invalid. NHS stores 104 with a number format displaying '104+'.
                estimate = band + (target - before) / count
                comparisons.append({
                    "period": period, "sheet": sheet, "row": row_number,
                    "code": code, "p": percentile, "n": total, "band": band,
                    "official": official, "linear_pN": estimate,
                    "difference": estimate - official,
                })
                if sheet == "National" and code == "C_999":
                    gates.append({
                        "period": period, "part": "Part_2",
                        "scope": "England; NONC excluded; C_999 Total",
                        "percentile": percentile, "official_value": official,
                        "workbook_url": url, "sheet": sheet,
                        "cell": column_name(official_column) + str(row_number),
                        "total_pathways": total,
                        "total_cell": column_name(first_band_column + 105) + str(row_number),
                        "published": published, "revised": revised,
                    })
    archive.close()
    return gates, comparisons


def main():
    official, comparisons = [], []
    for period, url in URLS.items():
        gate, comparison = source_comparison(period, url)
        official.extend(gate)
        comparisons.extend(comparison)
        print(f"{period}: read official source; {len(comparison):,} numeric comparisons", flush=True)
    output = ROOT / "results"
    output.mkdir(parents=True, exist_ok=True)
    for name, records in (
        ("official_nhs_percentiles.csv", official),
        ("method_identification_workbook_comparison.csv", comparisons),
    ):
        with (output / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=records[0])
            writer.writeheader()
            writer.writerows(records)
    finite = [record for record in comparisons if record["band"] < 104]
    censored = [record for record in comparisons if record["band"] == 104]
    maximum = max(abs(record["difference"]) for record in finite)
    print(f"Finite-band values: {len(finite):,}; maximum difference: {maximum:.17g} weeks")
    print(f"Censored 104+ values: {len(censored)} (excluded from finite-band error)")
    assert maximum < 1e-10, "NHS finite-band numerical identification no longer matches"
    assert all(record["official"] == 104 for record in censored)


if __name__ == "__main__":
    main()
