#!/usr/bin/env python3
"""Regenerate the verified Finding 01 package outputs.

The canonical analysis scripts read the NHS England extracts documented in
``SOURCES.md`` and write the derived CSVs and PNGs into this pack.  The raw
extracts are intentionally kept outside the upload package because of their
size; this wrapper runs only the verified analysis inputs.
"""
from pathlib import Path
import subprocess
import sys

PACK = Path(__file__).resolve().parents[1]
SCRIPTS = [
    PACK / "analysis" / "01_rtt_distribution_analysis.py",
    PACK / "analysis" / "02_pressure_test.py",
    PACK / "analysis" / "04_trust_size_control.py",
]


def main() -> None:
    for script in SCRIPTS:
        print(f"Running {script.name} ...")
        subprocess.run([sys.executable, str(script)], check=True)
    print("Done. Data vintage: NHS England April 2026 (with February 2025 comparison).")


if __name__ == "__main__":
    main()
