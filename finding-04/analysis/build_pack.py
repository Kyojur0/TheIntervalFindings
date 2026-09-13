"""Assemble a review pack without copying source extracts or private paths."""
from pathlib import Path
import csv
import hashlib
import json
import shutil
from build_cache import find_project_root


def build_pack(base):
    project=find_project_root(); results=base/'results'; pack=base/'pack'
    for folder in ['analysis','data','figures','outputs']:
        (pack/folder).mkdir(parents=True,exist_ok=True)
    for script in (base/'scripts').glob('*.py'):
        shutil.copy2(script,pack/'analysis'/script.name)
    for p in results.iterdir():
        if p.is_file() and p.name.endswith('.csv.gz'):
            shutil.copy2(p,pack/'outputs'/p.name)
            continue
        if p.is_file() and p.suffix in ['.csv','.md','.json']:
            if p.name=='verification_report_snapshot.md':
                # Preserve the exact bytes whose hash is in the claim ledger.
                shutil.copy2(p,pack/'outputs'/p.name)
                continue
            content=p.read_text()
            # Audit outputs may identify original files by local absolute path.
            # The public pack replaces that root with a relative source marker.
            content=content.replace(str(project.resolve())+'/', '')
            content=content.replace('../pack/figures/', '../figures/')
            content=content.replace('../scripts/', '../analysis/')
            (pack/'outputs'/p.name).write_text(content)
    if (results/'verification_report_snapshot.md').exists():
        (pack/'data/pack_provenance.json').write_text(json.dumps({
            'audited_snapshot':'outputs/verification_report_snapshot.md',
            'audited_report_sha256':hashlib.sha256((results/'verification_report_snapshot.md').read_bytes()).hexdigest(),
            'presentation_report':'outputs/REPORT.md',
            'presentation_report_sha256':hashlib.sha256((pack/'outputs/REPORT.md').read_bytes()).hexdigest(),
            'presentation_changes':['Image links relocated from ../pack/figures/ to ../figures/; prose and numbers unchanged.'],
        },indent=2)+'\n')
    for name in ['official_nhs_percentiles.csv','rtt_trajectory_national.csv','validation_gate.csv']:
        shutil.copy2(results/name,pack/'data'/name)
    manifest=json.loads((project/'data/rtt_monthly_series/manifest.json').read_text())
    shutil.copy2(project/'data/rtt_monthly_series/manifest.json',pack/'data/manifest.json')
    source_records=[]
    for p in sorted((results/'cache').glob('*.audit.json')):
        a=json.loads(p.read_text()); src=a['source']; path=Path(src['path'])
        m=next((x for x in manifest['files'] if x['period']==a['period']),{})
        url=m.get('download_url','')
        if a['kind']=='baseline':
            landing='https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-data-2018-19/'
        else:
            year=int(a['period'][:4]); month=int(a['period'][5:7]); year=year if month>=4 else year-1
            landing=f'https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-data-{year}-{str(year+1)[2:]}/'
        source_records.append(dict(period=a['period'],kind=a['kind'],source_file=str(path.relative_to(project)),
            sha256=src['sha256'],size_bytes=src['size_bytes'],download_url=url,publication_page=landing))
    with (pack/'data/source_inventory.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(source_records[0]));w.writeheader();w.writerows(source_records)
    source_text='''# Sources and scope

The source is NHS England's monthly consultant-led Referral to Treatment waiting
times collection, acquired in the supplied project on 17 July 2026. The pack uses
the held vintages; it does not silently refresh them from today's publication.

`source_inventory.csv` identifies every held CSV by relative source path, byte
size and SHA-256. `manifest.json` preserves the original acquisition record and
available archive URLs. A blank archive URL means the supplied manifest did not
retain one; use the linked annual publication page and the file identifier. An
archive URL points to the NHS full extract, whereas the held modern monthly CSVs
contain the selected incomplete rows. Hashes describe the held CSVs, not the ZIPs.
The original extracts are intentionally omitted from this pack.

Main series: reported pathways only, with no missing-provider estimates; exact
Part_2, non-English commissioner NONC excluded, national C_999
Total counted once and reconciled against detailed specialties. Baseline: separate
53-band schema. Completed flows: exact Part_1A/Part_1B, known waits only, same
England scope; unknown clock starts are excluded from percentile denominators.

The supplied first-release months are October and November 2025, January and
February 2026, and April and May 2026. They are identifiable in the derived data
and tested separately. Other months retain their supplied revised/established
vintages; January 2024's official incomplete workbook is not labelled revised.

## Official methodology and comparisons

- [RTT statistical guidance and band definitions](https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-statistics-user-guidance/)
- [January 2024 statistical press notice](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/03/Jan24-RTT-SPN-Publication-PDF-437K.pdf)
- `official_nhs_percentiles.csv`: precise source workbook URLs, cells, values and
  publication vintages; see the corresponding comparison in `../outputs/`.
- `../outputs/method_source_research.md`: evidence identifying the current linear
  convention from NHS workbook bands/values, with limits stated explicitly.
- `rtt_trajectory_national.csv`: unchanged supplied Finding 02 output used only
  as a reconciliation target. Current measures are rebuilt from raw inputs.

The figure specification is an unchanged copy from the reviewed Finding 03 pack.
The images are newly generated from the current outputs.
'''
    (pack/'data/SOURCES.md').write_text(source_text)
    (pack/'README.md').write_text('''# Finding 04 — review pack

Start with [the report](outputs/REPORT.md), then the independent verification and
anomaly records in `outputs/`. This is a completed analytical draft for owner
review. It has not been promoted to `final-uploads/finding-04/` or published.

The report corrects the brief's duplicated national count, its assertion that the
middle is the largest group, and its claim that NHS England does not publish p92.

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
''')
    for transient in pack.rglob('__pycache__'):
        shutil.rmtree(transient)
    print(f'Pack assembled: {sum(p.is_file() for p in pack.rglob("*"))} files')


if __name__=='__main__':
    build_pack(Path(__file__).resolve().parent.parent)
