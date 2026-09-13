"""Produce Finding 04 tables from cached provider matrices; no raw rereads.

Run with --cache-dir, --output-dir and --reference-dir for a portable pack.
The reference directory holds official_nhs_percentiles.csv and the unchanged
Finding 02 rtt_trajectory_national.csv. All shares are fractions, not percentages.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from build_cache import load_cache
from percentiles import summary

SPECIALTIES = {'C_100': 'General surgery', 'C_110': 'Trauma and orthopaedics',
               'C_120': 'ENT', 'C_130': 'Ophthalmology', 'C_301': 'Gastroenterology',
               'C_320': 'Cardiology', 'C_400': 'Neurology'}
NAMES = {'C_999': 'England, all specialties', **SPECIALTIES}
FIRST_RELEASE = {'2025-10','2025-11','2026-01','2026-02','2026-04','2026-05'}


def analyse(cache_dir, output_dir, reference_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    gate = pd.read_csv(reference_dir / 'validation_gate.csv')
    if not (gate.status.eq('PASS').all() and gate.difference.abs().max() <= .1):
        raise RuntimeError('Official median validation gate has not passed')
    records, sensitivity, distributions, reconciliations = [], [], [], []
    for path in sorted(cache_dir.glob('*.npz')):
        c = load_cache(path)
        index = c.index
        kind = c.audit.get('kind', c.audit.get('source_kind'))
        if kind is None:
            kind = 'full' if 'full-extract' in path.name else ('baseline' if '201902' in path.name else 'monthly')
        for (period, part), rows in index.groupby(['period','part']):
            period = str(period)
            if kind == 'full' and part not in ('Part_1A','Part_1B'):
                continue
            national = c.bands[rows.index[rows.code.eq('C_999')]].sum(axis=0)
            detailed = c.bands[rows.index[rows.code.ne('C_999')]].sum(axis=0)
            reconciliations.append(dict(period=period, part=part, kind=kind,
                national_total=int(national.sum()), detailed_total=int(detailed.sum()),
                max_band_difference=int(np.abs(national-detailed).max())))
            if not np.array_equal(national, detailed):
                raise ValueError(f'Total and detailed bands do not reconcile: {period} {part}')
            for code, name in NAMES.items():
                bands = c.bands[rows.index[rows.code.eq(code)]].sum(axis=0)
                key = dict(period=period, part=part, kind=kind, code=code, name=name,
                    release='first-release' if period in FIRST_RELEASE else 'revised-or-established')
                values = summary(bands)
                records.append({**key, **values})
                for p in (50,75,92,95):
                    j=values[f'p{p}_band_lower']; val=values[f'p{p}']
                    closed = np.isfinite(val)
                    sensitivity.append({**key, 'percentile':p, 'linear':val,
                        'lower_bound':float(j) if closed else np.nan,
                        'midpoint':j+.5 if closed else np.nan,
                        'upper_bound':j+1 if closed else np.nan,
                        'lower_minus_linear':j-val if closed else np.nan,
                        'midpoint_minus_linear':j+.5-val if closed else np.nan})
                if code=='C_999':
                    for j,count in enumerate(bands):
                        distributions.append({**key,'lower_week':j,
                            'upper_week':j+1 if j<len(bands)-1 else np.nan,
                            'open_band':j==len(bands)-1,'count':int(count),
                            'share':count/values['total'] if values['total'] else np.nan,
                            'group':'within18' if j<18 else ('middle' if j<52 else 'over52')})
    panel = pd.DataFrame(records).sort_values(['kind','period','part','code'])
    monthly = panel[panel.kind.eq('monthly')].copy()
    if len(monthly)!=29*8 or monthly.duplicated(['period','code']).any():
        raise ValueError(f'Expected 232 unique monthly series rows, got {len(monthly)}')
    if panel[['p50','p75','p92','p95']].diff(axis=1).iloc[:,1:].lt(0).any().any():
        raise ValueError('Non-monotonic percentiles')
    tables = {'all_measures':panel, 'monthly_measures':monthly,
        'national_monthly':monthly[monthly.code.eq('C_999')],
        'specialty_monthly':monthly[monthly.code.ne('C_999')],
        'completed_measures':panel[panel.kind.eq('full')],
        'baseline_measures':panel[panel.kind.eq('baseline')],
        'band_sensitivity':pd.DataFrame(sensitivity),
        'national_band_distribution':pd.DataFrame(distributions),
        'total_detail_reconciliation':pd.DataFrame(reconciliations)}
    open_check=panel[['period','part','kind','code','name','total','open_count','closed_share']].copy()
    open_check['all_below_p99_identifiable']=open_check.closed_share.ge(.99)
    open_check['published_percentile_in_open_band']=panel[['p50','p75','p92','p95']].isna().any(axis=1)
    tables['open_band_checks']=open_check

    # Re-run the gate and full precision workbook comparisons using final cache.
    official=pd.read_csv(reference_dir/'official_nhs_percentiles.csv')
    compared=[]
    for row in official.to_dict('records'):
        match=monthly[monthly.period.eq(row['period']) & monthly.code.eq('C_999')].iloc[0]
        p=int(round(row['percentile']*100)); value=match[f'p{p}']
        compared.append({**row, 'computed_value':value,'difference':value-row['official_value'],
            'press_precision_official':round(row['official_value'],1),
            'difference_from_rounded':value-round(row['official_value'],1),
            'computed_total':match.total, 'total_difference':match.total-row['total_pathways'],
            'status':'PASS' if abs(value-row['official_value'])<=.1 else 'FAIL',
            'method_note':'Linear p*N interpolation; C_999 counted once; workbook source vintage retained.'})
    tables['official_comparison']=pd.DataFrame(compared)
    if tables['official_comparison'].status.ne('PASS').any():
        raise ValueError('An official comparison fails; stop before interpreting results')

    old=pd.read_csv(reference_dir/'rtt_trajectory_national.csv')
    old['period']=old.date.str[:7]
    rec=monthly[monthly.code.ne('C_999')].merge(old,left_on=['period','code'],right_on=['period','specialty_code'],validate='one_to_one')
    rec['within18_count_difference']=rec.within18_count-rec.waiting_0_18w
    rec['middle_count_difference']=rec.middle_count-rec.waiting_18_52w
    rec['total_difference']=rec.total-rec.total_waiting
    rec['within18_pp_difference']=rec.within18_share*100-rec.pct_within_18w
    rec['status']=np.where((rec.within18_count_difference.eq(0)&rec.middle_count_difference.eq(0)&rec.total_difference.eq(0)&rec.within18_pp_difference.abs().le(.00500001)), 'PASS','FAIL')
    tables['finding02_reconciliation']=rec[['period','code','within18_count_difference','middle_count_difference','total_difference','within18_pp_difference','status']]
    prior={'2024-01':15.04,'2024-10':14.23,'2025-05':13.57,'2025-12':13.45,'2026-03':11.33,'2026-04':11.90,'2026-05':12.42}
    tables['earlier_median_crosscheck']=pd.DataFrame([dict(period=r.period, earlier_rounded=prior[r.period],computed=r.p50,difference=r.p50-prior[r.period]) for r in monthly[monthly.code.eq('C_999')].itertuples() if r.period in prior])
    endpoints=[]
    for code,rows in monthly.groupby('code'):
        rows=rows.sort_values('period'); a,b=rows.iloc[0],rows.iloc[-1]
        d=dict(code=code,name=b['name'],start_period=a.period,end_period=b.period)
        for metric in ['total','within18_count','middle_count','over52_count','within18_share','middle_share','over52_share','p50','p75','p92','p95','gap_weeks']:
            d[metric+'_start']=a[metric]; d[metric+'_end']=b[metric]; d[metric+'_change']=b[metric]-a[metric]
        endpoints.append(d)
    tables['endpoint_changes']=pd.DataFrame(endpoints)
    stress=[]
    for code,rows in monthly.groupby('code'):
        for subset, data in [('all_months',rows),('exclude_first_release',rows[~rows.period.isin(FIRST_RELEASE)])]:
            data=data.sort_values('period'); last=data.iloc[-1]
            stress.append(dict(code=code,name=last['name'],subset=subset,months=len(data),last_period=last.period,
                latest_p50=last.p50,latest_p92=last.p92,latest_gap=last.gap_weeks,
                min_p92=data.p92.min(),max_p92=data.p92.max(),
                median_improvement=data.p50.iloc[0]-last.p50,
                middle_largest_months=int((data.middle_count.gt(data.within18_count)&data.middle_count.gt(data.over52_count)).sum())))
    tables['adversarial_checks']=pd.DataFrame(stress)
    for name,df in tables.items():
        df.to_csv(output_dir/f'{name}.csv',index=False,float_format='%.12g')
    print(tables['national_monthly'][['period','total','p50','p92','gap_weeks','middle_count','middle_share']].to_string(index=False))
    print('Official comparison max absolute weeks:',tables['official_comparison'].difference.abs().max())
    print('Finding02 failures:',int(rec.status.ne('PASS').sum()))
    return tables


if __name__=='__main__':
    p=argparse.ArgumentParser(); base=Path(__file__).resolve().parent.parent
    p.add_argument('--cache-dir',type=Path,default=base/'results/cache')
    p.add_argument('--output-dir',type=Path,default=base/'results')
    p.add_argument('--reference-dir',type=Path,default=base/'results')
    args=p.parse_args(); analyse(args.cache_dir,args.output_dir,args.reference_dir)
