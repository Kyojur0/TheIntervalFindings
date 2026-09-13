# Finding 04 — A shorter median, a promise still unmet

**Status:** Verified
**Series:** RTT · Distribution
**Article:** `/findings/04` on The Interval

In May 2026 half of the reported incomplete pathways had been open for 12.4 weeks
or less, while 92% were within 38.6 weeks — 20.6 weeks beyond the standard's 18.
Both figures have fallen since January 2024. NHS England publishes both; this
finding reads them together and states the shortfall in weeks.

Start with [the report](outputs/REPORT.md), then the independent verification and
anomaly records in `outputs/`. The report corrects three premises in its original
brief: a duplicated national count, the claim that the middle is the largest group,
and the claim that NHS England does not publish p92.

## Contents

- `analysis/`: standalone ingestion, calculations, tests, figures and independent checks.
- `data/`: source inventory, hashes, official reference values and retained manifest.
- `figures/`: four charts, each in light and dark variants; direct labels throughout.
- `outputs/`: full-precision tables, report, method notes and verification records.

## Reproduce

Use Python 3.11 with numpy, pandas, duckdb and matplotlib. The supplied project's
`.venv311/bin/python` has the required packages. Keep the original source project
available with its `data/rtt_monthly_series/` and `data/source_research/` folders.
From the pack directory, for a source project available at `../source-project`:

```sh
python analysis/run_pipeline.py --source-root ../source-project --references data --output outputs --cache .cache --figures figures
python -m unittest discover -s analysis -p 'test_*.py'
```

Change only the relative source-root location for your layout. The pipeline first
recomputes January's official median gate; it stops before the other sources if
the difference exceeds the specified tolerance. Parsed provider matrices are
cached in `.cache/` and reused when source metadata and parser version match.
Rebuild from original data by choosing a new cache directory. The distinct
independent verifier reads the original CSVs without importing the primary engine.
Its command-line usage is available via `--help`.

The exact report bytes checked by the claim audit are preserved in
`outputs/verification_report_snapshot.md`. The readable `outputs/REPORT.md`
relocates only its image links to the pack's figures folder. Both checksums and
that presentation change are recorded in `data/pack_provenance.json`.

`analysis/write_report.py --results-dir outputs` rebuilds the numerical report
tables and retains any completed review appendix files. Re-running the analysis
does not claim to repeat the human-language review or approve publication.
All shares in CSVs are fractions; report/figure labels convert them to percentages.
Completed counts include only pathways with known waits.

Sources and input-vintage limitations: [data/SOURCES.md](data/SOURCES.md).
