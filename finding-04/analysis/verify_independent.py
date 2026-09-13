#!/usr/bin/env python3
"""Independent Finding 04 verification; never imports author/parser modules.

Original CSVs are aggregated afresh using DuckDB. Independent cumulative traversal
uses Python integers; no cached primary matrix is read. Bands are [0,1] then
(L,L+1] weeks; the last >52 or >104 band has no known upper boundary. The linear
grouped percentile is L+(p*N-prior)/n. An open containing band returns None.
"""
import argparse
import csv
import hashlib
import json
import math
import re
import urllib.request
from pathlib import Path

import duckdb
import pandas as pd

CODES = ['C_999', 'C_100', 'C_110', 'C_120', 'C_130', 'C_301', 'C_320', 'C_400']
FIRST = {'2025-10', '2025-11', '2026-01', '2026-02', '2026-04', '2026-05'}


def percentile(counts, p):
    """Return (linear estimate, containing lower edge), using an integer scan."""
    target = sum(counts) * p
    prior = 0
    for lower, count in enumerate(counts):
        if count and prior + count >= target:
            if lower == len(counts) - 1:
                return None, lower
            return lower + (target - prior) / count, lower
        prior += count
    return None, None


def quoted(name):
    return '"' + name.replace('"', '""') + '"'


def raw_aggregate(source_root, results):
    con = duckdb.connect()
    con.execute('SET threads=4')
    files = sorted((source_root / 'data/rtt_monthly_series').glob('*.csv'))
    files += sorted((source_root / 'data/source_research').glob('*full-extract*.csv'))
    rows, comparisons, inventory, aggregates = [], [], [], []
    assert len(files) == 32, len(files)
    for source in files:
        period = source.name[:4] + '-' + source.name[4:6]
        kind = 'full' if 'full-extract' in source.name else ('baseline' if period == '2019-02' else 'monthly')
        with source.open(encoding='utf-8-sig', newline='') as f:
            headers = next(csv.reader(f))
        bands = [h for h in headers if re.fullmatch(r'Gt \d+ (?:To \d+ )?Weeks SUM 1', h)]
        bands.sort(key=lambda h: int(h.split()[1]))
        assert len(bands) == (53 if kind == 'baseline' else 105), (source, len(bands))
        assert [int(h.split()[1]) for h in bands] == list(range(len(bands)))
        parts = ['Part_1A', 'Part_1B'] if kind == 'full' else ['Part_2']
        exprs = ', '.join('SUM(COALESCE(TRY_CAST(' + quoted(h) + ' AS DOUBLE), 0)) AS b' + str(i) for i,h in enumerate(bands))
        sql = f'''SELECT "RTT Part Type", "Treatment Function Code", {exprs}
            FROM read_csv(?, header=true, all_varchar=true)
            WHERE "Commissioner Org Code" <> 'NONC'
              AND "RTT Part Type" IN ({','.join(repr(p) for p in parts)})
            GROUP BY "RTT Part Type", "Treatment Function Code"'''
        grouped = con.execute(sql, [str(source)]).fetchall()
        vectors = {(part, code): [int(v) for v in vals] for part,code,*vals in grouped}
        inventory.append({'source':str(source.relative_to(source_root)), 'period':period, 'kind':kind, 'band_count':len(bands), 'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
        for part in parts:
            nat = vectors[part, 'C_999']
            detail = [sum(v[i] for (p,c),v in vectors.items() if p == part and c != 'C_999') for i in range(len(bands))]
            comparisons.append({'period':period, 'kind':kind, 'part':part, 'max_band_difference':max(abs(a-b) for a,b in zip(nat, detail)), 'national_total':sum(nat), 'detail_total':sum(detail)})
            for code in CODES:
                counts = vectors[part, code]
                aggregates.append({'period':period, 'kind':kind, 'part':part, 'code':code, 'counts':counts})
                n = sum(counts)
                within = sum(counts[:18]); middle = sum(counts[18:52]); tail = sum(counts[52:])
                row = {'period':period, 'kind':kind, 'part':part, 'code':code, 'total':n,
                    'within18_count':within, 'middle_count':middle, 'over52_count':tail,
                    'within18_share':within/n, 'middle_share':middle/n, 'over52_share':tail/n,
                    'open_count':counts[-1], 'closed_share':1-counts[-1]/n,
                    'band_count':len(bands), 'first_release':period in FIRST}
                for p in (.5,.75,.92,.95):
                    estimate, lower = percentile(counts,p)
                    key = 'p'+str(round(p*100))
                    row[key] = estimate; row[key+'_band_lower'] = lower
                    row[key+'_midpoint'] = lower+.5 if estimate is not None else None
                    row[key+'_lower_shift'] = lower-estimate if estimate is not None else None
                    row[key+'_midpoint_shift'] = lower+.5-estimate if estimate is not None else None
                row['gap_weeks'] = row['p92']-18 if row['p92'] is not None else None
                rows.append(row)
        print('Independently aggregated', source.name, flush=True)
    data = pd.DataFrame(rows)
    data.to_csv(results / 'verification_independent_measures.csv', index=False)
    pd.DataFrame(inventory).to_csv(results / 'verification_raw_inventory.csv', index=False)
    pd.DataFrame(comparisons).to_csv(results / 'verification_total_detail.csv', index=False)
    (results / 'verification_raw_aggregates.json').write_text(json.dumps(aggregates))
    return data


def compare_outputs(data, results, source_root):
    primary = pd.read_csv(results / 'all_measures.csv')
    # Output files only are read after the independent raw engine has run.
    primary['kind'] = primary['kind'].replace({'completed':'full'})
    joined = data.merge(primary, on=['period','kind','part','code'], suffixes=('_independent','_primary'), validate='one_to_one', how='outer', indicator=True)
    assert (joined['_merge'] == 'both').all(), joined.loc[joined['_merge'] != 'both'].to_string()
    percentile_rows, count_rows = [], []
    for _,r in joined.iterrows():
        for key in ['p50','p75','p92','p95']:
            left,right = r[key+'_independent'],r[key+'_primary']
            same_null = pd.isna(left) and pd.isna(right)
            d = left-right
            percentile_rows.append({**{k:r[k] for k in ['period','kind','part','code']}, 'measure':key, 'independent':left, 'primary':right, 'difference':d,'status':'VERIFIED' if same_null or abs(d)<=.01 else 'WRONG'})
        for key in ['total','within18_count','middle_count','over52_count','open_count','within18_share','middle_share','over52_share','closed_share','gap_weeks']:
            left,right = r[key+'_independent'],r[key+'_primary']
            count_rows.append({**{k:r[k] for k in ['period','kind','part','code']}, 'measure':key,'independent':left,'primary':right,'difference':left-right,'status':'VERIFIED' if abs(left-right) <= (1e-8 if 'count' in key or key=='total' else 1e-8) else 'WRONG'})
    pd.DataFrame(percentile_rows).to_csv(results / 'verification_percentile_comparison.csv',index=False)
    pd.DataFrame(count_rows).to_csv(results / 'verification_measure_comparison.csv',index=False)
    old = pd.read_csv(source_root / 'findings/finding-02-tail-trajectory/outputs/rtt_trajectory_national.csv')
    old['period'] = old.date.str[:7]
    rec = data.query("kind == 'monthly' and code != 'C_999'").merge(old, left_on=['period','code'], right_on=['period','specialty_code'], validate='one_to_one')
    rec['count_difference'] = rec.within18_count - rec.waiting_0_18w
    rec['percentage_difference_after_rounding'] = (rec.within18_share*100).round(2)-rec.pct_within_18w
    rec['middle_count_difference'] = rec.middle_count - rec.waiting_18_52w
    rec.to_csv(results / 'verification_finding02_reconciliation.csv',index=False)
    return {'populations':len(joined), 'percentiles_compared':len(percentile_rows), 'percentile_max_abs_difference':max(abs(x['difference']) for x in percentile_rows),
        'percentile_failures':sum(x['status']=='WRONG' for x in percentile_rows), 'other_measures_compared':len(count_rows),
        'other_measure_failures':sum(x['status']=='WRONG' for x in count_rows), 'finding02_records':len(rec),
        'finding02_max_count_difference':float(rec.count_difference.abs().max()),
        'finding02_max_percentage_difference':float(rec.percentage_difference_after_rounding.abs().max())}


def workbook_check(data, results):
    """Live HTTP GET, new workbook decode, and new band traversal."""
    import io
    import zipfile
    import xml.etree.ElementTree as ET
    def decode_workbook(raw):
        ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        relns='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
        def colindex(address):
            value=0
            for letter in re.match(r'[A-Z]+',address)[0]: value=value*26+ord(letter)-64
            return value-1
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            shared=[]
            if 'xl/sharedStrings.xml' in z.namelist():
                shared=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns)]
            rels={x.attrib['Id']:x.attrib['Target'] for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
            sheets=ET.fromstring(z.read('xl/workbook.xml')).findall('m:sheets/m:sheet',ns)
            result={}
            for sheet in sheets:
                if sheet.attrib['name'] not in ['National','Sub-ICB']: continue
                target=rels[sheet.attrib[relns]]
                target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
                cells={}; rows=[]
                for row in ET.fromstring(z.read(target)).findall('m:sheetData/m:row',ns):
                    rn=int(row.attrib['r'])
                    while len(rows)<rn: rows.append([])
                    for c in row.findall('m:c',ns):
                        v=c.find('m:v',ns); value=None
                        if v is not None:
                            if c.attrib.get('t')=='s': value=shared[int(v.text)]
                            else:
                                try: value=float(v.text)
                                except (TypeError,ValueError): value=v.text
                        elif c.attrib.get('t')=='inlineStr': value=''.join(c.find('m:is',ns).itertext())
                        ci=colindex(c.attrib['r'])
                        while len(rows[rn-1])<=ci: rows[rn-1].append(None)
                        rows[rn-1][ci]=value; cells[c.attrib['r']]=value
                result[sheet.attrib['name']]={'cells':cells,'rows':rows}
            return result
    sources = pd.read_csv(results / 'official_nhs_percentiles.csv')
    checks, retrievals, band_checks = [], [], []
    for url, group in sources.groupby('workbook_url'):
        request = urllib.request.Request(url, headers={'User-Agent':'Finding04-independent-verification/1.0'})
        with urllib.request.urlopen(request,timeout=45) as response:
            raw = response.read()
            retrievals.append({'url':url,'status':response.status,'resolved_url':response.url,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        book = decode_workbook(raw)
        period = group.iloc[0].period
        for _,source in group.iterrows():
            sheet = book[source['sheet']]
            official = sheet['cells'][source.cell]
            total = sheet['cells'][source.total_cell]
            candidate = data.query("period == @period and kind == 'monthly' and code == 'C_999'").iloc[0]
            independent = candidate['p'+str(round(source.percentile*100))]
            checks.append({'period':period,'percentile':source.percentile,'cell':source.cell,'url':url,'official_actual':official,'official_claimed':source.official_value,'independent':independent,'difference':independent-official,'total_actual':total,'total_independent':candidate.total,'status':'VERIFIED' if abs(independent-official)<.01 and abs(official-source.official_value)<1e-10 and total==candidate.total else 'WRONG'})
        # Independently locate columns by workbook headers rather than hardcode
        # primary-engine positions. National header rows identify weekly bands.
        for sheet_name in ['National','Sub-ICB']:
            if sheet_name not in book: continue
            sheet=book[sheet_name]
            sheet_rows=sheet['rows']
            candidates=[]
            for row in sheet_rows[:15]:
                for index,value in enumerate(row):
                    if isinstance(value,str) and re.fullmatch(r'>?\s*0\s*-\s*1',value.strip()):
                        candidates.append(index)
            if not candidates: continue
            start=candidates[0]
            pcols={}
            for header in sheet_rows[:15]:
                for col,value in enumerate(header):
                    if isinstance(value,str) and 'Average (median)' in value: pcols[.5]=col
                    if isinstance(value,str) and '92nd percentile' in value: pcols[.92]=col
            # Column runs are verified against the national published total.
            for rn,row in enumerate(sheet_rows,1):
                if len(row)<start+105: continue
                values=row[start:start+105]
                if len(values)!=105 or not all(isinstance(v,(int,float)) and not isinstance(v,bool) and v>=0 for v in values) or sum(values)==0: continue
                for p,column in pcols.items():
                    if column>=len(row) or not isinstance(row[column],(int,float)): continue
                    est,lower=percentile(values,p)
                    band_checks.append({'period':period,'sheet':sheet_name,'row':rn,'percentile':p,'official':row[column],'computed':est,'lower':lower,'difference':est-row[column] if est is not None else None})
        print('Independently downloaded and checked', period, flush=True)
    pd.DataFrame(checks).to_csv(results / 'verification_official_comparison.csv',index=False)
    pd.DataFrame(retrievals).to_csv(results / 'verification_live_sources.csv',index=False)
    pd.DataFrame(band_checks).to_csv(results / 'verification_workbook_band_comparison.csv',index=False)
    return {'official_comparisons':len(checks),'official_failures':sum(c['status']=='WRONG' for c in checks),'official_max_abs_difference':max(abs(c['difference']) for c in checks), 'workbook_band_comparisons':len(band_checks)}


def adversarial(data, results):
    monthly=data.query("kind == 'monthly'")
    national=monthly.query("code == 'C_999'").sort_values('period')
    latest=monthly.query("period == '2026-05'")
    stable=monthly[~monthly.first_release]
    rows=[
        {'check':'national_middle_largest_months','value':int((national.middle_count>national[['within18_count','over52_count']].max(axis=1)).sum()),'denominator':len(national)},
        {'check':'specialty_middle_largest_months','value':int((monthly.query("code != 'C_999'").middle_count>monthly.query("code != 'C_999'")[['within18_count','over52_count']].max(axis=1)).sum()),'denominator':len(monthly.query("code != 'C_999'"))},
        {'check':'revised_months','value':stable.period.nunique(),'denominator':national.period.nunique()},
        {'check':'all_revised_national_p92_above18','value':int((stable.query("code == 'C_999'").p92>18).all()),'denominator':1},
        {'check':'revised_specialty_p92_above18','value':int((stable.query("code != 'C_999'").p92>18).sum()),'denominator':len(stable.query("code != 'C_999'"))},
        {'check':'latest_specialty_p50_below18','value':int((latest.query("code != 'C_999'").p50<18).sum()),'denominator':7},
        {'check':'latest_specialty_p92_above18','value':int((latest.query("code != 'C_999'").p92>18).sum()),'denominator':7},
        {'check':'national_median_lower_bound_max_shift','value':national.p50_lower_shift.abs().max(),'denominator':29},
        {'check':'national_median_midpoint_max_shift','value':national.p50_midpoint_shift.abs().max(),'denominator':29},
        {'check':'modern_min_closed_share','value':data.query("kind != 'baseline'").closed_share.min(),'denominator':len(data.query("kind != 'baseline'"))},
        {'check':'national_median_endpoint_change','value':national.iloc[-1].p50-national.iloc[0].p50,'denominator':29},
        {'check':'national_p92_endpoint_change','value':national.iloc[-1].p92-national.iloc[0].p92,'denominator':29},
        {'check':'national_middle_endpoint_change','value':national.iloc[-1].middle_count-national.iloc[0].middle_count,'denominator':29},
        {'check':'specialty_middle_endpoint_change','value':int(latest.query("code != 'C_999'").middle_count.sum()-monthly.query("period == '2024-01' and code != 'C_999'").middle_count.sum()),'denominator':7},
    ]
    pd.DataFrame(rows).to_csv(results / 'verification_adversarial.csv',index=False)
    data[[c for c in data.columns if 'shift' in c or c in ['period','kind','part','code','p50','p92']]].to_csv(results / 'verification_sensitivity.csv',index=False)
    data[['period','kind','part','code','total','open_count','closed_share','p50_band_lower','p75_band_lower','p92_band_lower','p95_band_lower','band_count']].to_csv(results / 'verification_open_bands.csv',index=False)
    return {row['check']:row['value'] for row in rows}


def provider_claim_checks(root, results):
    """Narrow extra raw checks for the later report's missing-provider caveats."""
    files=sorted((root/'data/rtt_monthly_series').glob('202*.csv'))
    con=duckdb.connect(); con.execute('SET threads=4')
    with files[0].open(newline='') as f: headers=next(csv.reader(f))
    bands=[h for h in headers if re.fullmatch(r'Gt \d+ (?:To \d+ )?Weeks SUM 1',h)]
    band_sum='+'.join('COALESCE(TRY_CAST('+quoted(h)+' AS DOUBLE),0)' for h in bands)
    raw=con.execute(f'''SELECT filename, "Provider Org Code" code, SUM({band_sum}) total
        FROM read_csv(?, header=true, all_varchar=true, filename=true)
        WHERE "RTT Part Type"='Part_2' AND "Commissioner Org Code"<>'NONC'
        AND "Treatment Function Code"='C_999' AND "Provider Org Code" IN ('RHQ','RF4','RA9')
        GROUP BY filename, code''',[list(map(str,files))]).fetchall()
    values={(Path(f).name[:6],c):v for f,c,v in raw}
    records=[{'period':f.name[:4]+'-'+f.name[4:6],'code':c,'reported_total':values.get((f.name[:6],c),0)} for f in files for c in ['RHQ','RF4','RA9']]
    pd.DataFrame(records).to_csv(results/'verification_provider_claims.csv',index=False)
    vectors={}
    sums=','.join('SUM(COALESCE(TRY_CAST('+quoted(h)+' AS DOUBLE),0))' for h in bands)
    for prefix in ['202602','202603']:
        f=next(f for f in files if f.name.startswith(prefix))
        rows=con.execute(f'''SELECT "Provider Org Code", {sums} FROM read_csv(?,header=true,all_varchar=true)
            WHERE "RTT Part Type"='Part_2' AND "Commissioner Org Code"<>'NONC' AND "Treatment Function Code"='C_999'
            GROUP BY "Provider Org Code"''',[str(f)]).fetchall()
        vectors[prefix]={c:[int(v) for v in values] for c,*values in rows}
    common=set(vectors['202602']) & set(vectors['202603'])
    comparison=[]
    for period,providers in vectors.items():
        for scope,allowed in [('all',set(providers)),('common',common)]:
            counts=[sum(providers[c][i] for c in allowed) for i in range(105)]
            comparison.append({'period':period[:4]+'-'+period[4:],'scope':scope,'providers':len(allowed),'total':sum(counts),'p50':percentile(counts,.5)[0]})
    pd.DataFrame(comparison).to_csv(results/'verification_march_common_providers.csv',index=False)
    print('Independent provider caveat checks completed',flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path)
    parser.add_argument('--results-dir', type=Path, default=Path(__file__).resolve().parents[1]/'results')
    parser.add_argument('--reuse-independent', action='store_true', help='Reuse only this verifier\'s saved raw results for claim/report checks')
    parser.add_argument('--skip-live', action='store_true')
    parser.add_argument('--provider-checks', action='store_true')
    args=parser.parse_args()
    root=args.source_root or next(p for p in Path(__file__).resolve().parents if (p/'data/rtt_monthly_series').is_dir())
    results=args.results_dir.resolve(); results.mkdir(parents=True,exist_ok=True)
    data=pd.read_csv(results/'verification_independent_measures.csv') if args.reuse_independent else raw_aggregate(root,results)
    summary=compare_outputs(data,results,root)
    summary.update(adversarial(data,results))
    if not args.skip_live: summary.update(workbook_check(data,results))
    if args.provider_checks: provider_claim_checks(root,results)
    (results/'verification_summary.json').write_text(json.dumps(summary,indent=2,default=float)+'\n')
    print(json.dumps(summary,indent=2,default=float))


if __name__=='__main__': main()
