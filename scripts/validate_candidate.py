"""Snapshot, export, score and benchmark a candidate; never auto-deploy it.

Run from the ANC environment. Exit 2 means a quality gate failed; reports and
audio are retained for diagnosis. This is distinct from a tool/runtime error.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not args.name.replace('-', '').replace('_', '').isalnum():
        parser.error('--name must contain only letters, digits, underscores and hyphens')
    output = root / 'artifacts' / args.name
    output.mkdir(exist_ok=False)
    source = Path(args.checkpoint)
    if not source.is_absolute():
        source = root / source
    checkpoint = output / 'checkpoint.pt'
    shutil.copy2(source, checkpoint)
    model = output / 'model.onnx'
    def run(module, *arguments):
        subprocess.run([sys.executable, '-m', module, *map(str, arguments)], cwd=root, check=True)
    run('voxshield.export_onnx', '--checkpoint', checkpoint, '--output', model)
    reports = {}
    listening = ['# Candidate listening comparisons', '',
                 'Use headphones at a comfortable level. Compare the same utterance in all three files.',
                 'Do not judge naturalness from SNR or PESQ alone. These are synthetic validation recordings.', '']
    for name, manifest, categories in (
        ('broad', 'audit_broad_val', 'stationary,nonstationary,impulsive,environmental,mixed'),
        ('military', 'audit_military_val', 'impulsive,nonstationary,mixed'),
    ):
        report_path = output / f'{name}.json'
        run('voxshield.evaluate', '--checkpoint', checkpoint, '--onnx', model,
            '--manifest', f'data/mixtures/{manifest}/manifest.jsonl', '--device', 'cpu',
            '--require-pesq', '--strict-sih-gate', '--expected-noisy-categories', categories,
            '--output', report_path, '--save-audio', output / f'{name}-audio',
            '--save-audio-limit', 20)
        reports[name] = json.loads(report_path.read_text())
        rows = [json.loads(line) for line in
                (root / f'data/mixtures/{manifest}/manifest.jsonl').read_text().splitlines() if line]
        listening.extend([f'## {name.capitalize()}', ''])
        for row in rows[:20]:
            links = []
            for label, path in (
                ('Noisy input', root / 'data' / row['noisy']),
                ('Enhanced output', output / f'{name}-audio' / f"{row['id']}.wav"),
                ('Clean reference', root / 'data' / row['clean']),
            ):
                links.append(f'[{label}](<{path.as_posix()}>)')
            listening.append(f"- {row['id']} ({row.get('category', 'unknown')}): " + ' | '.join(links))
        listening.append('')
    run('voxshield.benchmark', '--checkpoint', checkpoint, '--onnx', model,
        '--frames', 1000, '--threads', 1, '--output', output / 'laptop-benchmark.json')
    accepted = all(report['quality_gate']['passed'] for report in reports.values())
    result = {
        'source_checkpoint': str(source), 'candidate_directory': str(output),
        'validation_accepted': accepted, 'deployment_accepted': False,
        'remaining_hardware_evidence': ['physical loopback latency', 'Pi 5 benchmark',
                                      'real microphone listening', 'long-duration live test'],
        'datasets': {name: {'count': report['count'], 'noisy_only': report['noisy_only_summary'],
                            'gate': report['quality_gate']} for name, report in reports.items()},
        'note': 'Validation is development evidence, not a fresh independent field test.',
    }
    (output / 'acceptance.json').write_text(json.dumps(result, indent=2))
    (output / 'listening.md').write_text('\n'.join(listening), encoding='utf-8')
    print(json.dumps({'validation_accepted': accepted, 'report': str(output / 'acceptance.json')}))
    return 0 if accepted else 2


if __name__ == '__main__':
    raise SystemExit(main())
