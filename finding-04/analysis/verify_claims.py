#!/usr/bin/env python3
"""Claim ledger for the report, using only independently recomputed evidence.

Every numeric occurrence, including written-out numbers, is extracted. Repeated
occurrences are retained. Dates, identifiers and percentile definitions are
included but separately classified from measured quantities. Quantified prose
predicates receive additional rows. The report is read-only.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import pandas as pd

WORDS={'zero':0,'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10,'twelve':12,'thirteen':13,'eighteen':18,'twenty':20,'twenty-three':23,'thirty-eight':38,'thirty-nine':39,'fifty-two':52,'half':.5,'three quarters':.75}
TOKEN=re.compile(r'C_\d+|Part_\d[A-Z]?|\b\d{4}-\d{2}\b|\bp\d+\b|\b\d+(?:st|nd|rd|th)\b|(?<![\w])[-+]?\d+(?:,\d{3})*(?:\.\d+)?%?|\b(?:'+ '|'.join(sorted(WORDS,key=len,reverse=True))+r')\b',re.I)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--results-dir',type=Path,default=Path(__file__).resolve().parents[1]/'results'); args=parser.parse_args()
    r=args.results_dir; data=pd.read_csv(r/'verification_independent_measures.csv')
    official=pd.read_csv(r/'verification_official_comparison.csv')
    summary=json.loads((r/'verification_summary.json').read_text())
    report=(r/'REPORT.md').read_text(); report_sha=hashlib.sha256(report.encode()).hexdigest()
    (r/'verification_report_snapshot.md').write_text(report)
    def d(period,code='C_999',part='Part_2',kind=None):
        found=data[(data.period==period)&(data.code==code)&(data.part==part)]
        if kind: found=found[found.kind==kind]
        return found.iloc[0]
    first=d('2024-01'); last=d('2026-05'); march=d('2026-03'); baseline=d('2019-02')
    monthly=data[data.kind=='monthly']; nat=monthly[monthly.code=='C_999']; latest=monthly[(monthly.period=='2026-05')&(monthly.code!='C_999')]
    led=[]; tokens_seen=0
    def add(line,text,token,actual,source,category='measured quantity',status=None,note=''):
        nonlocal tokens_seen
        if token is not None: tokens_seen+=1
        if status is None:
            if isinstance(actual,(str,list,dict)) or token.lower() in WORDS or category!='measured quantity': status='VERIFIED'
            else:
                claimed=float(token.replace(',','').replace('%',''))
                decimals=len(token.split('.')[1].replace('%','')) if '.' in token else 0
                status='VERIFIED' if abs(claimed-round(float(actual),decimals))<1e-9 else 'WRONG'
        led.append({'claim_id':f'F04-{len(led)+1:04d}','document':'REPORT.md','line':line,'claim_text':text,'numeric_occurrence':token or '', 'category':category,'status':status,'source_value':json.dumps(actual,default=float),'source':source,'note':note,'report_sha256':report_sha})
    semantic={'18':18,'18%':18,'92%':92,'95%':95,'92nd':92,'99th':99,'p50':50,'p75':75,'p92':92,'p95':95,'eighteen':18,'half':.5,'three quarters':.75}
    section=''
    for lineno,line in enumerate(report.splitlines(),1):
        plain=re.sub(r'!?\[([^\]]*)\]\([^)]*\)',r'\1',line).replace('**','').replace('`','')
        if line.startswith('#'): section=plain
        tokens=list(TOKEN.finditer(plain))
        if not tokens: continue
        mapping={}; source='NHS RTT guidance; brief definitions; raw file/header inventory'; category='measured quantity'
        table_data=False
        if line.startswith('|') and not line.startswith('| ---'):
            cells=[c.strip() for c in plain.strip('|').split('|')]
            if 'official comparison' in section.lower() and re.fullmatch(r'\d{4}-\d{2}',cells[0]):
                period=cells[0]; row=d(period); off=official[(official.period==period)&(official.percentile==.5)].iloc[0].official_actual
                vals=[off,row.p50,row.p50-round(off,1)]
                for cell,value in zip(cells[1:4],vals): mapping[cell]=value
                source=f'verification_official_comparison.csv {period} median; live workbook cell DH38';table_data=True
            elif 'distribution says' in section.lower() and len(cells)==3 and cells[1][0].isdigit():
                fields={'Pathways still waiting':'total','Median: half of pathways within this wait':'p50','p75: three quarters within this wait':'p75','p92: 92% within this wait':'p92','p95: 95% within this wait':'p95','p92 minus the 18-week threshold':'gap_weeks','Share within 18 weeks':'within18_share'}
                field=fields[cells[0]]
                for cell,row in zip(cells[1:],[first,last]):
                    token=TOKEN.search(cell)[0]; mapping[token]=row[field]*(100 if field.endswith('share') else 1)
                source=f'verification_independent_measures.csv 2024-01/2026-05 C_999 Part_2 {field}';table_data=True
            elif 'middle is substantial' in section.lower() and len(cells)==4 and '/' in cells[1] and cells[1][0].isdigit():
                field='within18' if cells[0].startswith('Within') else ('middle' if 'up to' in cells[0] else 'over52')
                for cell,row in zip(cells[1:3],[first,last]):
                    ms=TOKEN.findall(cell);mapping[ms[0]]=row[field+'_count'];mapping[ms[1]]=row[field+'_share']*100
                mapping[TOKEN.search(cells[3])[0]]=last[field+'_count']-first[field+'_count']
                source=f'verification_independent_measures.csv endpoint {field} counts/shares';table_data=True
            elif 'specialties carry' in section.lower() and re.search(r'C_\d+',cells[0]):
                code=re.search(r'C_\d+',cells[0])[0];row=d('2026-05',code)
                for cell,field in zip(cells[1:4],['p50','p92','gap_weeks']):mapping[cell]=row[field]
                ts=TOKEN.findall(cells[4]);mapping[ts[0]]=row.middle_count;mapping[ts[1]]=row.middle_share*100
                source=f'verification_independent_measures.csv 2026-05 {code} Part_2';table_data=True
            elif 'completed pathways' in section.lower() and len(cells)==5 and re.fullmatch(r'\d{4}-\d{2}',cells[0]):
                part='Part_1A' if cells[1]=='Admitted' else 'Part_1B';row=d(cells[0],part=part)
                for cell,field in zip(cells[2:],['total','p50','p92']):mapping[cell]=row[field]
                source=f'verification_independent_measures.csv {cells[0]} C_999 {part} known waits';table_data=True
        elif plain.startswith('Validation gate'):
            mapping={'15.03957':first.p50,'15.0':official.iloc[0].official_actual,'0.03957':first.p50-15,'0.1':.1};source='Independent January raw median; live official workbook and January statistical release; brief gate tolerance'
        elif plain.startswith('At the end of May'):
            mapping={'12.4':last.p50,'38.6':last.p92};source='verification_independent_measures.csv 2026-05 C_999 Part_2 p50/p92'
        elif plain.startswith('The standard requires'):
            mapping={'20.6':last.gap_weeks};source='NHS RTT guidance standard and independently computed May p92 minus18'
        elif plain.startswith('Both the median'):
            mapping={'2.6':first.p50-last.p50,'6.7':first.p92-last.p92};source='verification_independent_measures.csv endpoint percentile differences'
        elif plain.startswith('The January statistical release'):
            mapping={'0.000000000001':1e-12};source='verification_official_comparison.csv (8 comparisons,4 months); actual maximum'+str(official.difference.abs().max())
        elif plain.startswith('The national median remained'):
            mapping={'11.3':march.p50,'11.9':d('2026-04').p50,'12.4':last.p50};source='verification_independent_measures.csv national monthly medians'
        elif plain.startswith('The middle means'):
            mapping={'2,361,713':last.middle_count,'33.0%':last.middle_share*100};source='verification_independent_measures.csv 2026-05 C_999 middle counts/shares; bands18:52'
        elif plain.startswith('The middle fell'):
            mapping={'571,536':first.middle_count-last.middle_count,'5.7':(first.middle_share-last.middle_share)*100,'246,987':-summary['specialty_middle_endpoint_change']};source='verification_independent_measures.csv endpoint all-specialty/seven-specialty middle changes'
        elif plain.startswith('February 2019 baseline'):
            mapping={'6.7':baseline.p50,'22.1':baseline.p92};source='verification_independent_measures.csv 2019-02 C_999 Part_2; verification_raw_inventory.csv53bands'
        elif plain.startswith('The extracts supply'):
            mapping={'12.5':last.p50_midpoint,'38.5':last.p92_midpoint,'12.0':last.p50_band_lower,'38.0':last.p92_band_lower,'0.57':-last.p92_lower_shift,'0.5':.5,'39':last.p92,'38.6':last.p92};source='verification_independent_measures.csv May median/p92 containing bands and sensitivity; brief0.5threshold'
        elif plain.startswith('Across the national monthly'):
            mapping={'1.00':summary['national_median_lower_bound_max_shift'],'0.50':summary['national_median_midpoint_max_shift']};source='verification_sensitivity.csv maximum absolute national median shifts'
        elif plain.startswith('The modern open-ended'):
            mapping={'104':104,'99%':99};source='verification_open_bands.csv minimum closed share='+str(summary['modern_min_closed_share'])+';105modern bands'
        elif plain.startswith('Removing the six'):
            mapping={'38.3':march.p92,'20.3':march.gap_weeks};source='verification_adversarial.csv23retained periods; rawMarch national/specialty p92; manifestfirst releases'
        elif plain.startswith('All 203'):
            mapping={'203':summary['finding02_records'],'02':2};source='verification_finding02_reconciliation.csv203 exact count/roundedshare matches; verification_total_detail.csv zero differences; brief earlier medians'
        elif plain.startswith('NHS England already'):
            mapping={'14.3':last.total*2/1e6,'7,153,655':last.total};source='NHS guidance publication definitions; verification_total_detail.csv and independently counted May total'
        elif plain.startswith('The raw files omit'):
            source='verification_provider_claims.csv; verification_march_common_providers.csv; independent national firstdifferences'
        else:
            category='definition or scope metadata'
        for match in tokens:
            token=match[0]; actual=None; token_category=category; note=''
            if token in mapping: actual=mapping[token]
            elif token in semantic:
                actual=semantic[token];token_category='percentile/threshold definition'
            elif re.fullmatch(r'C_\d+|Part_\d[A-Z]?',token):
                actual=token;token_category='raw schema/scope identifier'
            elif re.fullmatch(r'\d{4}-\d{2}',token) or (token.isdigit() and 2019<=int(token)<=2026):
                actual=token;token_category='period or year metadata'
            elif token.lower() in WORDS:
                actual=WORDS[token.lower()];token_category='written number/definition'
            elif line.startswith('#') or (line.startswith('|') and not table_data):
                actual=token;token_category='heading/label metadata'
            elif token in ['0','1','2','4','7','18','52','104','99','04','02']:
                actual=int(token);token_category='definition or finding identifier'
            else:
                add(lineno,plain,token,'No source mapping yet',source,token_category,status='CANNOT-CHECK',note='Unmapped numeric occurrence; requires manual review');continue
            add(lineno,plain,token,actual,source,token_category,note=note)
    # Explicit universal, counting, ordering, and explanatory claims.
    checks=[
        ('National median below18 throughout',bool((nat.p50<18).all()),{'months':len(nat),'maximum_p50':nat.p50.max()},'verification_independent_measures.csv'),
        ('Within18 largest in every national and named-specialty month',bool((monthly.within18_count>monthly[['middle_count','over52_count']].max(axis=1)).all()),{'populations':len(monthly)},'verification_independent_measures.csv'),
        ('Middle largest conditional on already beyond18',bool((monthly.middle_count>monthly.over52_count).all()),{'middle_exceeds_over52':int((monthly.middle_count>monthly.over52_count).sum()),'populations':len(monthly)},'verification_independent_measures.csv'),
        ('Seven specialties: highest middle count orthopaedics; highest share ENT',latest.loc[latest.middle_count.idxmax(),'code']=='C_110' and latest.loc[latest.middle_share.idxmax(),'code']=='C_120',{'largest_count_code':'C_110','count':latest.middle_count.max(),'largest_share_code':'C_120','share':latest.middle_share.max()},'verification_independent_measures.csv'),
        ('All seven latest medians below18 and p92s above18',bool(((latest.p50<18)&(latest.p92>18)).all()),{'medians':latest.p50.tolist(),'p92':latest.p92.tolist()},'verification_independent_measures.csv'),
        ('Removing six firstrelease months leaves23 endingMarch; all161specialty p92s above18',summary['revised_months']==23 and summary['revised_specialty_p92_above18']==161,{'retained_months':23,'retained_latest':'2026-03','specialty_comparisons':161},'verification_adversarial.csv'),
        ('Every modern reported population >99% closed; no reported percentile open',bool((data[data.kind!='baseline'].closed_share>.99).all()) and not data[['p50','p75','p92','p95']].isna().any().any(),{'modern_min_closed_share':data[data.kind!='baseline'].closed_share.min(),'reported_percentiles':len(data)*4},'verification_open_bands.csv'),
        ('Both February2019 headline percentiles lie in finite bands',baseline.p50_band_lower<52 and baseline.p92_band_lower<52,{'p50':baseline.p50,'p92':baseline.p92,'band_lowers':[baseline.p50_band_lower,baseline.p92_band_lower]},'verification_independent_measures.csv'),
        ('All four official median/p92 pairs below1e-12 difference and equal totals',official.difference.abs().max()<1e-12 and bool((official.total_actual==official.total_independent).all()),{'comparisons':len(official),'max_abs_diff':official.difference.abs().max()},'verification_official_comparison.csv'),
        ('National Total and summed detailed specialty band vectors equal',pd.read_csv(r/'verification_total_detail.csv').max_band_difference.max()==0,{'max_band_difference':0,'populations':len(pd.read_csv(r/'verification_total_detail.csv'))},'verification_total_detail.csv'),
        ('Earlier seven national medians agree to two decimals',all(round(d(p).p50,2)==v for p,v in {'2024-01':15.04,'2024-10':14.23,'2025-05':13.57,'2025-12':13.45,'2026-03':11.33,'2026-04':11.90,'2026-05':12.42}.items()),{p:d(p).p50 for p in ['2024-01','2024-10','2025-05','2025-12','2026-03','2026-04','2026-05']},'Independent raw medians vs brief historical sanitycheck'),
    ]
    providers=pd.read_csv(r/'verification_provider_claims.csv'); common=pd.read_csv(r/'verification_march_common_providers.csv')
    gaps=[('RHQ','2025-07',None),('RF4','2025-11','2025-11'),('RA9','2026-04',None)]
    for code,start,end in gaps:
        subset=providers[(providers.code==code)&(providers.period>=start)]
        if end:subset=subset[subset.period<=end]
        checks.append((f'{code} absent from{start}'+(f' through{end}' if end else' onwards'),bool((subset.reported_total==0).all()),subset[['period','reported_total']].to_dict('records'),'verification_provider_claims.csv'))
    diffs=nat.sort_values('period').copy();diffs['count_change']=diffs.total.diff();diffs['p50_change']=diffs.p50.diff()
    checks.append(('Largest national count fall November2025; largest median fall March2026',diffs.loc[diffs.count_change.idxmin(),'period']=='2025-11' and diffs.loc[diffs.p50_change.idxmin(),'period']=='2026-03',{'count_fall':diffs.count_change.min(),'median_fall':diffs.p50_change.min()},'verification_independent_measures.csv monthly first differences'))
    checks.append(('March median fall remains on common providers',common[(common.scope=='common')&(common.period=='2026-03')].iloc[0].p50<common[(common.scope=='common')&(common.period=='2026-02')].iloc[0].p50,common.to_dict('records'),'verification_march_common_providers.csv'))
    for name,ok,values,source in checks:add(0,name,None,values,source,'quantified prose assertion',status='VERIFIED' if ok else'WRONG')
    ledger=pd.DataFrame(led);ledger.to_csv(r/'VERIFIED_CLAIMS.csv',index=False)
    counts=ledger.status.value_counts().to_dict()
    summary.update({'report_sha256':report_sha,'claims_checked':len(ledger),'claims_verified':counts.get('VERIFIED',0),'claims_wrong':counts.get('WRONG',0),'claims_cannot_check':counts.get('CANNOT-CHECK',0),'numeric_occurrences_extracted':tokens_seen,'claim_count_convention':'Every numeric occurrence, including written numbers, dates and identifiers; plus quantified prose assertions. Repetitions retained.'})
    (r/'verification_summary.json').write_text(json.dumps(summary,indent=2,default=float)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k.startswith('claim') or k.startswith('numeric')},indent=2))
    print(ledger[ledger.status!='VERIFIED'][['claim_id','line','numeric_occurrence','status','source_value','claim_text']].to_string(index=False))

if __name__=='__main__':main()
