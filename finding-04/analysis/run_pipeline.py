"""Rebuild Finding 04, enforcing the official median gate before the full series.

From a standalone pack:
python analysis/run_pipeline.py --source-root /path/to/original/project \
    --references data --output outputs --cache .cache --figures figures

Raw sources are never modified. Source discovery uses the supplied manifest.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
from build_cache import build_source, source_inventory, find_project_root
from percentiles import percentile
from analyse import analyse


def run(source_root, references, output, cache, figures=None):
    output.mkdir(parents=True, exist_ok=True)
    inventory=source_inventory(source_root)
    jan=next(s for s in inventory if s['period']=='2024-01' and s['kind']=='monthly')
    parsed=build_source(jan['path'],jan['period'],jan['kind'],cache)
    counts=parsed.bands[parsed.index.code.eq('C_999')].sum(axis=0)
    value=percentile(counts,.5)
    official=pd.read_csv(references/'official_nhs_percentiles.csv')
    source=official[(official.period=='2024-01') & (official.percentile==.5)].iloc[0]
    published=round(source.official_value,1)
    gate=pd.DataFrame([dict(month='2024-01',official_value=published,computed_value=value,
        difference=value-published,official_unrounded_value=source.official_value,
        unrounded_difference=value-source.official_value,
        status='PASS' if abs(value-published)<=.1 else 'FAIL',
        source_url=source.workbook_url,
        method_note='Linear p*N within one-week band; published precision one decimal; C_999 once.')])
    gate.to_csv(output/'validation_gate.csv',index=False)
    passed=bool(gate.status.eq('PASS').all())
    (output/'validation_gate.json').write_text(json.dumps({'passed':passed,'period':'2024-01',
        'official':published,'computed':value,'difference':value-published},indent=2)+'\n')
    if not passed:
        raise RuntimeError('Median differs from official publication by more than 0.1 weeks; full analysis stopped')
    for item in inventory:
        result=build_source(item['path'],item['period'],item['kind'],cache)
        print(item['period'],item['kind'],'cache' if result.cache_hit else 'parsed',flush=True)
    # Inputs are copied beside outputs for analyse's explicit provenance reads.
    for filename in ['official_nhs_percentiles.csv','rtt_trajectory_national.csv']:
        target=output/filename
        if (references/filename).resolve()!=target.resolve():
            target.write_bytes((references/filename).read_bytes())
    analyse(cache,output,output)
    if figures:
        from make_figures import make_figures
        make_figures(output,figures)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    base=Path(__file__).resolve().parent.parent
    p.add_argument('--source-root',type=Path)
    p.add_argument('--references',type=Path,default=base/'results')
    p.add_argument('--output',type=Path,default=base/'results')
    p.add_argument('--cache',type=Path,default=base/'results/cache')
    p.add_argument('--figures',type=Path)
    a=p.parse_args()
    run(a.source_root or find_project_root(),a.references,a.output,a.cache,a.figures)
