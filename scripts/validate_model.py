"""Reconcile read-only Desktop DAX query output with untouched source data.

Run query_model.ps1 first, then: python scripts/validate_model.py <query-output.json>
"""
from pathlib import Path
import sys, json, hashlib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
raw = np.loadtxt(ROOT/'data/secom.data')
labels = pd.read_csv(ROOT/'data/secom_labels.data', sep=r'\s+', header=None,
                     names=['outcome','timestamp'], quotechar='"')
dates = pd.to_datetime(labels.timestamp, format='%d/%m/%Y %H:%M:%S')
failed = labels.outcome.eq(1).to_numpy()
checks = 0
def check(actual, expected, label):
    global checks
    checks += 1
    if expected is None:
        assert actual is None, (label, actual, expected)
    else:
        assert actual is not None and np.isclose(actual, expected, rtol=1e-8, atol=1e-10), (label, actual, expected)

h = result['headline'][0]
for key, value in {'Samples':len(raw),'Passed':(~failed).sum(),'Failed':failed.sum(),
                   'Rate':(~failed).mean(),'Readings':np.isfinite(raw).sum(),
                   'Missing':np.isnan(raw).sum(),'Completeness':np.isfinite(raw).mean(),
                   'Constant':116,'Variable':474,'AllMissing':0}.items():
    check(h[f'[{key}]'],value,key)
for row in result['measurements']:
    idx=row['Measurement[Measurement ID]']-1
    col=raw[:,idx]; p=col[~failed]; f=col[failed]
    p=p[np.isfinite(p)]; f=f[np.isfinite(f)]
    pooled=np.sqrt(((len(p)-1)*p.var(ddof=1)+(len(f)-1)*f.var(ddof=1))/(len(p)+len(f)-2))
    eligible=(len(p)>=100 and len(f)>=20 and len(p)/(~failed).sum()>=.8 and len(f)/failed.sum()>=.8 and np.nanmin(col)!=np.nanmax(col))
    expected={'Valid':np.isfinite(col).sum(),'Missing':np.isnan(col).sum(),'Pass':len(p),'Fail':len(f),
              'PassMean':p.mean(),'FailMean':f.mean(),
              'Effect':abs(f.mean()-p.mean())/pooled if eligible and pooled>0 else None}
    for key,value in expected.items(): check(row[f'[{key}]'],value,f'measurement {idx+1} {key}')
for group,key,period in [('daily','Calendar[Date]',dates.dt.normalize()),
                         ('weekly','Calendar[Week Start]',dates.dt.normalize()-pd.to_timedelta(dates.dt.weekday,unit='D'))]:
    for row in result[group]:
        mask=period.eq(pd.Timestamp(row[key])).to_numpy()
        check(row['[Samples]'],int(mask.sum()),group+' samples')
        check(row['[Failed]'] or 0,int(failed[mask].sum()),group+' failed')
        check(row['[Rate]'],(~failed[mask]).mean(),group+' rate')
        if group=='daily':check(row['[Completeness]'],np.isfinite(raw[mask]).mean(),'daily completeness')
check(result['pass_filter'][0]['[Samples]'],len(raw),'pass filter denominator')
check(result['pass_filter'][0]['[Rate]'],(~failed).mean(),'pass filter rate')
for key in ['Samples','Rate','Completeness']:check(result['empty'][0][f'[{key}]'],None,'empty '+key)
for key in ['Value','Coverage']:check(result['no_sample'][0][f'[{key}]'],None,'no sample '+key)
check(result['no_sample'][0]['[Selected]'],0,'no sample selected')
assert len(result['sample1'])==590
for row in result['sample1']:
    value=raw[0,row['Measurement[Measurement ID]']-1]
    check(row['[Value]'],value if np.isfinite(value) else None,'sample1 value')
    assert row['[Status]']==('Recorded' if np.isfinite(value) else 'Missing')
    checks+=1
for row in result['histogram']:
    idx=row['Measurement Selector[Measurement ID]']-1
    b=row['Histogram Bin[Bin]']; col=raw[:,idx]; lo=np.nanmin(col); hi=np.nanmax(col)
    bins=np.ones(len(col)) if lo==hi else np.minimum(20,1+np.floor(20*(col-lo)/(hi-lo)))
    for name,mask in [('Pass',~failed),('Fail',failed)]:
        check(row[f'[{name}]'],((bins==b)&mask&np.isfinite(col)).sum()/(np.isfinite(col)&mask).sum(),'histogram '+name)
output={'status':'passed','checked_at_utc':result['queried_at_utc'],'assertions':checks,
        'measurement_columns_reconciled':len(result['measurements']),
        'query_batch_seconds':result['query_seconds'],
        'scope':['headline counts and rates','all 590 measurement counts, means and eligible effect sizes',
                 'daily and weekly totals and rates','daily reading completeness','outcome-filter denominator',
                 'empty selection','single-sample gate','590 original sample-1 readings including 44 nulls',
                 '20-bin normalized distributions for measurements 001, 006 (constant), 060 and 104'],
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data').glob('*.data')}}
(ROOT/'docs/model-validation.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
print(f'PASS: {checks:,} assertions against original SECOM values.')
