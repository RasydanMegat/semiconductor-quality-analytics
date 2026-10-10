"""Profile original SECOM files without modifying or imputing observations.

Run: python scripts/profile_secom.py
Requires numpy and pandas. Outputs docs/data-profile.json.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
raw = np.loadtxt(DATA / 'secom.data')
labels = pd.read_csv(DATA / 'secom_labels.data', sep=r'\s+', header=None,
                     names=['outcome', 'timestamp'], quotechar='"')
assert raw.shape == (len(labels), 590), 'Unexpected shape or label alignment'
assert labels.outcome.isin([-1, 1]).all(), 'Unexpected outcome code'
dates = pd.to_datetime(labels.timestamp, format='%d/%m/%Y %H:%M:%S', errors='raise')
assert np.isfinite(raw[~np.isnan(raw)]).all(), 'Nonfinite measurement other than NaN'
frame = pd.DataFrame(raw)
counts = frame.count()
unique = frame.nunique(dropna=True)
fail_mask = labels.outcome.eq(1).to_numpy()
pass_mask = ~fail_mask
measurements = []
for col in frame:
    values = frame[col]
    passed = values[pass_mask].dropna()
    failed = values[fail_mask].dropna()
    status = 'All missing' if counts[col] == 0 else 'Constant' if unique[col] == 1 else 'Variable'
    valid = values.dropna()
    q1, median, q3 = valid.quantile([.25, .5, .75]).tolist() if len(valid) else (None, None, None)
    iqr = q3 - q1 if len(valid) else 0
    outliers = int(((valid < q1 - 1.5 * iqr) | (valid > q3 + 1.5 * iqr)).sum()) if iqr > 0 else None
    eligible = (status == 'Variable' and len(passed) >= 100 and len(failed) >= 20
                and len(passed) / pass_mask.sum() >= .8 and len(failed) / fail_mask.sum() >= .8)
    pooled = np.sqrt(((len(passed)-1)*passed.var() + (len(failed)-1)*failed.var())
                     / (len(passed)+len(failed)-2)) if eligible else np.nan
    score = float(abs(failed.mean()-passed.mean()) / pooled) if eligible and pooled > 0 else None
    measurements.append(dict(measurement_id=int(col)+1, name=f'Measurement {col+1:03}',
        valid=int(counts[col]), missing=int(values.isna().sum()), distinct=int(unique[col]),
        status=status, minimum=float(valid.min()) if len(valid) else None,
        maximum=float(valid.max()) if len(valid) else None, median=median,
        iqr_outlier_flags=outliers, pass_valid=len(passed), fail_valid=len(failed),
        exploratory_absolute_standardized_mean_difference=score))
daily = pd.DataFrame({'date': dates.dt.date.astype(str), 'fail': fail_mask.astype(int)})
daily = daily.groupby('date').agg(samples=('fail','size'), failed=('fail','sum')).reset_index()
weekly = pd.DataFrame({'week': (dates.dt.normalize()-pd.to_timedelta(dates.dt.weekday,unit='D')).dt.strftime('%Y-%m-%d'), 'fail':fail_mask.astype(int)})
weekly = weekly.groupby('week').agg(samples=('fail','size'), failed=('fail','sum')).reset_index()
files = []
for name in ['secom.data','secom_labels.data','secom.names','secom.zip']:
    path = DATA / name
    if path.exists():
        files.append(dict(name=name, bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
# Keep original download checksum when re-profiling after removal of duplicate ZIP.
output = ROOT / 'docs' / 'data-profile.json'
if output.exists() and not (DATA / 'secom.zip').exists():
    previous = json.loads(output.read_text(encoding='utf-8'))
    files.extend(f for f in previous['files'] if f['name']=='secom.zip')
summary = dict(rows=len(labels), measurement_columns=raw.shape[1], passed=int(pass_mask.sum()),
    failed=int(fail_mask.sum()), observed_pass_rate=float(pass_mask.mean()),
    first_timestamp=dates.min().isoformat(), last_timestamp=dates.max().isoformat(),
    measurement_cells=int(raw.size), missing_cells=int(np.isnan(raw).sum()),
    missing_percent=float(np.isnan(raw).mean()*100),
    all_missing_measurements=int((counts==0).sum()), constant_measurements=int((unique==1).sum()),
    variable_measurements=int((unique>1).sum()),
    measurements_over_half_missing=int((frame.isna().mean()>.5).sum()),
    duplicate_measurement_rows_beyond_first=int(frame.duplicated().sum()),
    duplicate_complete_records_beyond_first=int(frame.assign(outcome=labels.outcome,timestamp=dates).duplicated().sum()),
    timestamp_duplicates_beyond_first=int(dates.duplicated().sum()), timestamps_sorted=bool(dates.is_monotonic_increasing),
    observed_dates=len(daily), calendar_dates=int((dates.max().normalize()-dates.min().normalize()).days)+1,
    daily_sample_min=int(daily.samples.min()), daily_sample_max=int(daily.samples.max()),
    daily_sample_median=float(daily.samples.median()), weekly_periods=len(weekly))
profile = dict(source='https://archive.ics.uci.edu/dataset/179/secom',
    citation='McCann, M. & Johnston, A. (2008). SECOM. UCI. https://doi.org/10.24432/C54305',
    license='CC BY 4.0', retrieved_date='2026-10-08',
    verified_at_utc=datetime.now(timezone.utc).isoformat(),
    summary=summary, files=files, daily=daily.to_dict('records'),weekly=weekly.to_dict('records'),
    measurements=measurements,
    limitations=['Original row position supplies technical key; no original equipment or lot identifiers.',
                'Timezone and physical measurement meanings unspecified.',
                'Standardized mean difference is exploratory, not causal or confirmatory; no p-values.',
                'IQR flags are profiling hints only and observations are preserved.'])
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(profile, indent=2, allow_nan=False),encoding='utf-8')
print(json.dumps(summary,indent=2))
ranked = sorted((m for m in measurements if m['exploratory_absolute_standardized_mean_difference'] is not None),
                key=lambda m:m['exploratory_absolute_standardized_mean_difference'],reverse=True)
print('Exploratory leading measurements:', [(m['name'],round(m['exploratory_absolute_standardized_mean_difference'],3)) for m in ranked[:5]])
