"""Independent data anomaly screen; consumes immutable band caches and their audits.
Candidates identify patterns, never establish merger/recoding/clinical causes.
Run with project .venv311/bin/python. All outputs start anomaly_.
"""
from pathlib import Path
import json, itertools, csv
import numpy as np
import pandas as pd
from build_cache import load_cache
BASE=Path(__file__).resolve().parents[1]; OUT=BASE/'results'
SEVEN={'C_100','C_110','C_120','C_130','C_301','C_320','C_400'}
def save(df,name): df.to_csv(OUT/f'anomaly_{name}.csv',index=False)
def pct(a,q):
    n=int(sum(a)); target=n*q; previous=0
    if n==0:return np.nan
    for j,count in enumerate(a):
        if previous+count>=target:
            return np.nan if j==len(a)-1 else j+(target-previous)/count
        previous+=count

def main():
    frames=[]; caches={}; checks=[]; audit_rows=[]; reconcile=[]; names=[]
    for path in sorted((OUT/'cache').glob('*.npz')):
        c=load_cache(path); idx=c.index.copy(); a=c.audit; source=Path(a['source']['path']).name
        idx['total']=c.bands.sum(1); idx['source_file']=source
        if a['kind']=='monthly':
            frames.append(idx); caches[a['period']]=c
        keys=['provider','part','code']; dup=idx.duplicated(keys).sum()
        expected=53 if a['kind']=='baseline' else 105
        checks.append(dict(period=a['period'],kind=a['kind'],source_file=source,rows=len(idx),bands=len(c.band_names),expected_bands=expected,duplicate_pooled_keys=int(dup),negative_cells=int((c.bands<0).sum()),nonfinite_cells=int((~np.isfinite(c.bands)).sum()),fractional_cells=int((c.bands!=np.floor(c.bands)).sum()),schema_matches=c.band_names==([f'Gt {i:02d} To {i+1:02d} Weeks SUM 1' for i in range(expected-1)]+[f'Gt {expected-1} Weeks SUM 1'])))
        audit_rows.append(dict(period=a['period'],kind=a['kind'],source_file=source,retained_raw_rows=a['filters']['retained_rows'],raw_blank_cells=a['retained_band_cells']['missing_cells'],raw_rows_with_blanks=a['blank_band_resolution']['rows_with_blank_bands'],certified_blank_cells=a['blank_band_resolution']['certified_zero_cells'],unresolved_blank_rows=a['blank_band_resolution']['unresolved_rows'],raw_duplicate_keys=a['duplicate_raw_keys']['duplicate_groups'],total_unexplained=a['row_totals']['Total'].get('unexplained_mismatch_rows',0),total_all_unexplained=a['row_totals']['Total All'].get('unexplained_mismatch_rows',0),unknown_clock_positive_rows=a['unknown_clock']['positive_rows'],unknown_clock_sum=a['unknown_clock']['sum_known_counts']))
        for (provider,part),g in idx.groupby(['provider','part']):
            ids=g.index.to_numpy(); total_ids=g[g.code=='C_999'].index.to_numpy(); detail_ids=g[g.code!='C_999'].index.to_numpy()
            if len(total_ids)!=1:
                reconcile.append(dict(period=a['period'],kind=a['kind'],provider=provider,part=part,issue='missing_or_multiple_rollup',difference=np.nan))
            else:
                delta=c.bands[total_ids[0]]-c.bands[detail_ids].sum(0)
                if np.any(delta):reconcile.append(dict(period=a['period'],kind=a['kind'],provider=provider,part=part,issue='band_reconciliation',difference=int(delta.sum()),max_abs_band=int(abs(delta).max())))
    save(pd.DataFrame(checks),'cache_checks'); save(pd.DataFrame(audit_rows),'source_audit_summary'); save(pd.DataFrame(reconcile,columns=['period','kind','provider','part','issue','difference','max_abs_band']),'reconciliation_failures')
    panel=pd.concat(frames,ignore_index=True); save(panel[['period','provider','provider_name','code','total','source_file']],'provider_totals')
    months=sorted(caches); candidates=[]; events=[]; changes=[]; band_changes=[]
    for prev,now in zip(months,months[1:]):
        x=panel[panel.period==prev]; y=panel[panel.period==now]
        px=x[x.code=='C_999'].set_index('provider'); py=y[y.code=='C_999'].set_index('provider')
        for provider in sorted(set(px.index)^set(py.index)):
            appearing=provider in py.index; row=(py if appearing else px).loc[provider]
            series=panel[(panel.provider==provider)&(panel.code=='C_999')]
            later=any(series.period>now); before=any(series.period<prev)
            interpretation=('reappearance_after_gap' if before else 'first_observed_entry') if appearing else ('temporary_gap' if later else 'last_observed_exit')
            events.append(dict(period=now,previous_period=prev,provider=provider,provider_name=row.provider_name,event='appears' if appearing else 'disappears',adjacent_total=int(row.total),classification=interpretation,cause='not established from counts',disposition='caveat; preserve official monthly scope',source_file=row.source_file))
        joint=px[['total','provider_name']].join(py[['total','provider_name']],how='outer',lsuffix='_before',rsuffix='_after'); joint['total_before']=joint.total_before.fillna(0);joint['total_after']=joint.total_after.fillna(0)
        joint['difference']=joint.total_after-joint.total_before
        for provider,r in joint.iterrows():
            changes.append(dict(previous_period=prev,period=now,provider=provider,provider_name=r.provider_name_after if pd.notna(r.provider_name_after) else r.provider_name_before,before=int(r.total_before),after=int(r.total_after),difference=int(r.difference),same_provider=provider in px.index and provider in py.index))
            if provider in px.index and provider in py.index and r.provider_name_before!=r.provider_name_after:names.append(dict(previous_period=prev,period=now,provider=provider,name_before=r.provider_name_before,name_after=r.provider_name_after,cause='label changed; organisational cause not established',disposition='benign for code-based pooling'))
        table=x[x.code!='C_999'].pivot(index='provider',columns='code',values='total').fillna(0).combine_first(y[y.code!='C_999'].pivot(index='provider',columns='code',values='total')*0).fillna(0)
        after=y[y.code!='C_999'].pivot(index='provider',columns='code',values='total').reindex(index=table.index,columns=table.columns).fillna(0)
        for provider in table.index:
            if provider not in px.index or provider not in py.index:continue
            old=table.loc[provider];new=after.loc[provider];delta=new-old
            rel=abs(delta)/old.replace(0,np.nan);rel[(old==0)&(delta!=0)]=np.inf
            unusual=list(delta.index[delta!=0])
            for a,b in itertools.combinations(unusual,2):
                if not ({a,b}&SEVEN) or delta[a]*delta[b]>=0 or max(rel[a],rel[b])<=.5:continue
                ratio=min(abs(delta[a]),abs(delta[b]))/max(abs(delta[a]),abs(delta[b]))
                if ratio<.5:continue
                target=a if a in SEVEN else b
                nat_before=x[x.code==target].total.sum();nat_after=y[y.code==target].total.sum()
                candidates.append(dict(previous_period=prev,period=now,provider=provider,provider_name=py.loc[provider].provider_name,code_a=a,code_b=b,before_a=int(old[a]),after_a=int(new[a]),change_a=int(delta[a]),before_b=int(old[b]),after_b=int(new[b]),change_b=int(delta[b]),absolute_change_ratio=float(ratio),paired_net_change=int(delta[a]+delta[b]),target_code=target,target_change_share_national_pct=100*float(abs(delta[target]))/nat_after if nat_after else np.nan,classification='known RJL recoding, verified pattern' if provider=='RJL' and prev=='2024-01' and {a,b}=={'C_300','C_301'} else 'possible recoding or service mix change; cause unconfirmed',disposition='caveat; preserve reported codes'))
        for period in (prev,now):
            pass
        cb,ca=caches[prev],caches[now]; common=set(px.index)&set(py.index)
        for label,providers in [('all',set(px.index)|set(py.index)),('common',common)]:
            bb=cb.bands[cb.index.code.eq('C_999')&cb.index.provider.isin(providers)].sum(0);aa=ca.bands[ca.index.code.eq('C_999')&ca.index.provider.isin(providers)].sum(0)
            band_changes.append(dict(previous_period=prev,period=now,population=label,providers=len(providers),total_before=int(bb.sum()),total_after=int(aa.sum()),p50_before=pct(bb,.5),p50_after=pct(aa,.5),p50_change=pct(aa,.5)-pct(bb,.5),p92_before=pct(bb,.92),p92_after=pct(aa,.92),within18_change=int(aa[:18].sum()-bb[:18].sum()),middle_change=int(aa[18:52].sum()-bb[18:52].sum()),over52_change=int(aa[52:].sum()-bb[52:].sum())))
    cand=pd.DataFrame(candidates).sort_values('target_change_share_national_pct',ascending=False);save(cand,'recoding_candidates')
    save(pd.DataFrame(events),'provider_presence_events');save(pd.DataFrame(names),'provider_name_changes');save(pd.DataFrame(changes),'provider_month_changes');save(pd.DataFrame(band_changes),'common_provider_sensitivity')
    measures=pd.read_csv(OUT/'all_measures.csv'); ordered=measures[['p50','p75','p92','p95']].to_numpy();nonmono=np.any(np.diff(ordered,axis=1)<0,axis=1)
    save(measures[nonmono],'nonmonotonic_percentiles')
    nat=measures[(measures.kind=='monthly')&(measures.code=='C_999')].sort_values('period').copy()
    for col in ['p50','p92','total']:
        nat[col+'_change']=nat[col].diff(); absd=abs(nat[col+'_change'].dropna());q1,q3=absd.quantile([.25,.75]);threshold=q3+1.5*(q3-q1);nat[col+'_threshold']=threshold;nat[col+'_outlier']=abs(nat[col+'_change'])>threshold
    nat['previous_release']=nat.release.shift();nat['release_boundary']=nat.release!=nat.previous_release;nat.loc[nat.index[0],'release_boundary']=False
    save(nat,'national_discontinuities')
    summary=dict(source_count=len(checks),monthly_count=len(months),pooled_rows=sum(r['rows'] for r in checks),raw_retained_rows=sum(r['retained_raw_rows'] for r in audit_rows),nonmonotonic_percentiles=int(nonmono.sum()),recoding_candidate_pairs=len(cand),provider_presence_events=len(events),provider_name_changes=len(names),reconciliation_failures=len(reconcile),threshold_rule='Absolute 28 month-on-month changes: Q3 + 1.5 IQR; pandas linear sample quantiles. Descriptive flags, not significance tests.',national_thresholds={k:float(nat[k+'_threshold'].iloc[-1]) for k in ['p50','p92','total']},modern_min_closed_share=float(measures[measures.kind!='baseline'].closed_share.min()),baseline_min_closed_share=float(measures[measures.kind=='baseline'].closed_share.min()))
    (OUT/'anomaly_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2));print(cand.head(12).to_string(index=False));print(nat[nat.p50_outlier|nat.total_outlier][['period','p50_change','total_change','release','release_boundary']].to_string(index=False))
if __name__=='__main__':main()

# Endpoint-cohort sensitivity is separate from the declared monthly scope.
def endpoint_common_check():
    caches=[load_cache(p) for p in sorted((OUT/'cache').glob('*__monthly.npz'))]
    first,last=caches[0],caches[-1]
    common=set(first.index.loc[first.index.code.eq('C_999'),'provider'])&set(last.index.loc[last.index.code.eq('C_999'),'provider'])
    records=[]
    for c in (first,last):
        for code in sorted(SEVEN|{'C_999'}):
            b=c.bands[c.index.code.eq(code)&c.index.provider.isin(common)].sum(0);n=int(b.sum())
            records.append(dict(period=c.audit['period'],code=code,common_provider_count=len(common),total=n,p50=pct(b,.5),p92=pct(b,.92),middle_count=int(b[18:52].sum()),middle_share=float(b[18:52].sum()/n)))
    save(pd.DataFrame(records),'endpoint_common_providers')

# Independent raw check logs every blank cell via a compact 105-bit mask.
# Bit i in the mask corresponds to the zero-based weekly column i from raw header.
# A set bit means a source blank certified as zero, not an observed zero.
def raw_blank_certificates():
    import duckdb,gzip
    records=[]
    with gzip.open(OUT/'anomaly_raw_blank_certificates.csv.gz','wt',newline='') as f:
        fields=['source_file','period','kind','provider','commissioner','part','code','band_count','blank_cell_count','blank_mask_hex_little_bit_order','observed_band_sum','Total','Total All','unknown_clock','residual','certified']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for ap in sorted((OUT/'cache').glob('*.audit.json')):
            a=json.loads(ap.read_text());source=a['source']['path'];bands=a['schema']['band_columns'];parts=['Part_1A','Part_1B'] if a['kind']=='full' else ['Part_2']
            def qt(s):return '"'+s.replace('"','""')+'"'
            numeric=bands+['Total','Total All','Patients with unknown clock start date']
            cols=['Provider Org Code','Commissioner Org Code','RTT Part Type','Treatment Function Code']
            select=','.join([qt(s) for s in cols]+[f'CAST({qt(s)} AS DOUBLE) AS {qt(s)}' for s in numeric])
            with duckdb.connect() as con:
                df=con.execute('SELECT '+select+' FROM read_csv(?,all_varchar=true) WHERE "Commissioner Org Code" <> \'NONC\' AND "RTT Part Type" IN ('+','.join('?' for _ in parts)+')',[source,*parts]).df()
            values=df[bands].to_numpy();missing=np.isnan(values);obs=np.nansum(values,axis=1);unknown=df['Patients with unknown clock start date'].to_numpy();alltotal=df['Total All'].to_numpy();total=df['Total'].to_numpy()
            # Unknown is never silently imputed. Where unknown is null, an exact
            # Total All==observed sum permits no positive nonnegative residual.
            residual=alltotal-obs-np.where(np.isfinite(unknown),unknown,0)
            cert=(residual==0)&np.isfinite(alltotal)&((~np.isfinite(unknown))|(unknown>=0))
            raw_bad=(np.isinf(values)|(values<0)|(np.isfinite(values)&(values!=np.floor(values)))).sum()
            populated_total_mismatch=(np.isfinite(total)&(total!=obs)).sum()
            alltotal_mismatch=(np.isfinite(alltotal)&(residual!=0)).sum()
            rows=np.where(missing.any(1))[0]; packed=np.packbits(missing[rows],axis=1,bitorder='little')
            for at,(i,mask) in enumerate(zip(rows,packed)):
                r=df.iloc[i]
                writer.writerow(dict(source_file=Path(source).name,period=a['period'],kind=a['kind'],provider=r[cols[0]],commissioner=r[cols[1]],part=r[cols[2]],code=r[cols[3]],band_count=len(bands),blank_cell_count=int(missing[i].sum()),blank_mask_hex_little_bit_order=mask.tobytes().hex(),observed_band_sum=int(obs[i]),Total=total[i],**{'Total All':alltotal[i]},unknown_clock=unknown[i],residual=residual[i],certified=bool(cert[i] and raw_bad==0)))
            records.append(dict(period=a['period'],kind=a['kind'],source_file=Path(source).name,raw_rows=len(df),blank_rows=len(rows),blank_cells=int(missing.sum()),uncertified_blank_rows=int((~cert[rows]).sum()),invalid_populated_cells=int(raw_bad),populated_total_mismatch=int(populated_total_mismatch),total_all_less_unknown_mismatch=int(alltotal_mismatch)))
            print('raw audit',a['period'],a['kind'],flush=True)
    save(pd.DataFrame(records),'independent_raw_checks')

if __name__=='__main__':
    endpoint_common_check()
    raw_blank_certificates()


def annotate_candidates():
    """Stable row IDs and official evidence, without converting candidates to causes."""
    for filename,prefix in [('recoding_candidates','RC'),('provider_presence_events','PE'),('provider_name_changes','PN')]:
        path=OUT/f'anomaly_{filename}.csv';df=pd.read_csv(path)
        if 'candidate_id' not in df:df.insert(0,'candidate_id',[f'{prefix}{i:03d}' for i in range(1,len(df)+1)])
        if filename=='provider_presence_events':
            df['official_evidence_url']=''
            gap='https://data.england.nhs.uk/providers/acute-provider-table?info=true'
            for code,start in [('RHQ','2025-07'),('RA9','2026-04')]:
                m=df.provider.eq(code)&df.period.eq(start);df.loc[m,'cause']='officially documented non-reporting; estimates used in separate NHS dashboard';df.loc[m,'official_evidence_url']=gap
            m=df.provider.eq('RF4')&df.period.eq('2025-11');df.loc[m,'cause']='officially documented non-submission';df.loc[m,'official_evidence_url']='https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/01/Nov25-RTT-SPN-Publication-PDF-458K-1Xmjkk.pdf'
            m=df.provider.eq('RAP')&df.period.eq('2025-01');df.loc[m,'cause']='officially documented acquisition by Royal Free London on 1 January 2025';df.loc[m,'official_evidence_url']='https://www.england.nhs.uk/publication/royal-free-london-nhs-foundation-trust/'
        save(df,filename)

if __name__=='__main__':annotate_candidates()
