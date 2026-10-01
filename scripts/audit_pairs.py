"""Read-only integrity audit of frozen noisy/clean WAV pairs."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import soundfile as sf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--data-root', default='data')
    args = parser.parse_args()
    path = Path(args.manifest)
    rows = [json.loads(line) for line in path.read_text().splitlines() if line]
    issues = []
    for row in rows:
        clean, fs = sf.read(Path(args.data_root) / row['clean'], dtype='float32')
        noisy, ns = sf.read(Path(args.data_root) / row['noisy'], dtype='float32')
        if clean.shape != noisy.shape or fs != ns:
            issues.append({'id': row['id'], 'problem': 'unaligned pair'})
            continue
        if not np.isfinite(clean).all() or not np.isfinite(noisy).all():
            issues.append({'id': row['id'], 'problem': 'nonfinite samples'})
        if np.max(np.abs(clean)) < 1e-7:
            issues.append({'id': row['id'], 'problem': 'silent target speech'})
        if row['category'] not in ('clean', 'near_clean') and np.array_equal(clean, noisy):
            issues.append({'id': row['id'], 'problem': 'labelled noisy but identical to clean'})
    result = {'manifest': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'count': len(rows), 'counts': dict(Counter(r['category'] for r in rows)),
              'issues': issues, 'passed': not issues}
    Path(args.output).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
