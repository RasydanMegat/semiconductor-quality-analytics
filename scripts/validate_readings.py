"""Compare every imported value and missing position with the original SECOM file."""
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def validate(export_path):
    source = ROOT / 'data/secom.data'
    rows = [line.split() for line in source.read_text().splitlines()]
    assert rows and all(len(row) == 590 for row in rows), 'Unexpected source dimensions'
    numeric = np.array(rows, dtype=float)
    # Recompute the original shared-bin formula independently of Power Query.
    bins = np.ones(numeric.shape)
    for column in range(590):
        values = numeric[:, column]
        valid = np.isfinite(values)
        if not valid.any():
            continue
        low, high = values[valid].min(), values[valid].max()
        if low != high:
            bins[valid, column] = np.minimum(20, 1 + np.floor(20 * (values[valid]-low)/(high-low)))
    seen = set()
    with export_path.open(newline='', encoding='utf-8-sig') as stream:
        for reading in csv.DictReader(stream):
            sample = int(reading['SampleID'])
            measurement = int(reading['MeasurementID'])
            key = sample, measurement
            assert 1 <= sample <= len(rows) and 1 <= measurement <= 590, f'Invalid key: {key}'
            assert key not in seen, f'Duplicate reading: {key}'
            expected = rows[sample-1][measurement-1]
            assert expected.lower() != 'nan', f'Missing source cell imported as a value: {key}'
            assert Decimal(reading['Value']) == Decimal(expected), f'Changed value: {key}'
            assert 1 <= int(reading['Bin']) <= 20, f'Invalid histogram bin: {key}'
            assert int(reading['Bin']) == bins[sample-1, measurement-1], f'Changed histogram bin: {key}'
            seen.add(key)
    missing = 0
    for sample, row in enumerate(rows, 1):
        for measurement, token in enumerate(row, 1):
            is_missing = token.lower() == 'nan'
            assert ((sample, measurement) in seen) != is_missing, f'Presence mismatch: {(sample, measurement)}'
            missing += is_missing
    result = {
        'status': 'passed',
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'samples': len(rows),
        'measurements': 590,
        'source_positions_checked': len(rows) * 590,
        'exact_values_matched': len(seen),
        'missing_positions_preserved': missing,
        'duplicate_imported_keys': 0,
        'histogram_bins_matched': len(seen),
        'comparison': 'Decimal equality for every value; exact presence/absence for every source position',
    }
    (ROOT / 'docs/reading-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    validate(Path(sys.argv[1]))
