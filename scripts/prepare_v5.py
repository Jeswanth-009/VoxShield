"""Create versioned manifests with a MAD development partition; never copy audio.

Old VoxShield checkpoints saw this pool: use new initialization for v5.
Groups use the catalog recording identifier; original acquisition-session
independence cannot be asserted without source metadata.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / 'data/manifests_v4/catalog.jsonl'
    destination = root / 'data/manifests_v5'
    if destination.exists():
        raise SystemExit('manifests_v5 already exists; refusing to replace a frozen split')
    rows = [json.loads(line) for line in source.read_text().splitlines() if line]
    moved = 0
    for row in rows:
        if row.get('adapter') == 'mad' and row['split'] == 'train':
            group = str(row.get('group') or Path(row['path']).stem)
            fraction = int(hashlib.sha256(('260925|MAD|' + group).encode()).hexdigest()[:8], 16) / 2**32
            row['original_split'] = 'train'
            row['split_method'] = 'official-train-development-group-hash'
            if fraction < 0.15:
                row['split'] = 'val'
                moved += 1
    counts = Counter((r.get('dataset'), r['split']) for r in rows)
    assert moved > 0
    destination.mkdir(parents=True)
    def write(name, selected):
        (destination / name).write_text(''.join(json.dumps(r) + '\n' for r in selected), encoding='utf-8')
    write('catalog.jsonl', rows)
    for split in ('train', 'val', 'test'):
        for kind in ('clean', 'rir'):
            write(f'{kind}_{split}.jsonl', [r for r in rows if r['kind'] == kind and r['split'] == split])
        for category in ('stationary', 'nonstationary', 'impulsive', 'environmental'):
            write(f'noise_{category}_{split}.jsonl', [r for r in rows if r['kind'] == 'noise' and r['split'] == split and r['category'] == category])
    report = {
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'mad_moved_from_training_to_validation': moved,
        'counts': {f'{dataset}/{split}': value for (dataset, split), value in sorted(counts.items())},
        'test_partition_unchanged': True,
        'warning': 'Do not initialize from old VoxShield checkpoints: they saw the new validation pool. Grouping is limited by supplied metadata.',
    }
    (destination / 'split-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
