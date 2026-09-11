#!/usr/bin/env python3
"""Regenerate the verified Finding 02 package outputs.

The canonical analysis scripts read the 29 NHS England monthly extracts and
February 2019 baseline documented in ``SOURCES.md``.  They write the derived
CSVs and PNGs into this pack.  This wrapper runs only the verified analysis inputs.
"""
from pathlib import Path
import subprocess
import sys

PACK = Path(__file__).resolve().parents[1]
SCRIPTS = [
    PACK / "analysis" / "05_trajectory_analysis.py",
    PACK / "analysis" / "03_completed_pathways_flow.py",
]


def main() -> None:
    for script in SCRIPTS:
        print(f"Running {script.name} ...")
        subprocess.run([sys.executable, str(script)], check=True)
    print("Done. Data vintage: NHS England monthly extracts, January 2024 to May 2026, plus February 2019 baseline.")


if __name__ == "__main__":
    main()
