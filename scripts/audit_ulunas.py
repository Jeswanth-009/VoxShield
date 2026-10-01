"""Evaluate the pinned upstream UL-UNAS checkpoint on VoxShield frozen pairs.

This is a model-comparison tool, not a deployment path.  It uses the upstream
Hann STFT/ISTFT exactly and runs the released stateful ONNX one frame at a time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
from tqdm import tqdm
from voxshield.audio import read_audio, write_audio
from voxshield.metrics import (
    active_level_error_db,
    optional_metrics,
    pause_noise_attenuation,
    si_snr,
    snr,
    speech_deletion_rate,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


class ULUNAS:
    def __init__(self, model: Path, threads: int = 1) -> None:
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(model), sess_options=options, providers=['CPUExecutionProvider']
        )
        self.window = torch.hann_window(512)

    def enhance(self, audio: np.ndarray) -> tuple[np.ndarray, list[float]]:
        value = torch.from_numpy(audio)[None]
        spectrum = torch.view_as_real(torch.stft(
            value, n_fft=512, hop_length=256, win_length=512,
            window=self.window, return_complex=True,
        )).numpy()
        caches = [
            np.zeros((1, 5358), dtype=np.float32),
            np.zeros((1, 402), dtype=np.float32),
            np.zeros((1, 1056), dtype=np.float32),
        ]
        outputs: list[np.ndarray] = []
        timings: list[float] = []
        for index in range(spectrum.shape[2]):
            started = time.perf_counter()
            output, *caches = self.session.run(None, {
                'mix': spectrum[:, :, index:index + 1, :],
                'conv_cache': caches[0], 'tfa_cache': caches[1],
                'inter_cache': caches[2],
            })
            timings.append(time.perf_counter() - started)
            outputs.append(output)
        enhanced_spectrum = torch.from_numpy(np.concatenate(outputs, axis=2))
        enhanced_complex = torch.complex(
            enhanced_spectrum[..., 0], enhanced_spectrum[..., 1]
        )
        enhanced = torch.istft(
            enhanced_complex[0], n_fft=512, hop_length=256, win_length=512,
            window=self.window, onesided=True, length=len(audio),
        ).numpy()
        return np.nan_to_num(enhanced).astype(np.float32), timings


def mean(records: list[dict], name: str) -> float | None:
    values = [row[name] for row in records if row.get(name) is not None]
    return float(np.mean(values)) if values else None


def evaluate(name: str, manifest: Path, engine: ULUNAS, output: Path, data_root: Path) -> dict:
    rows = [json.loads(line) for line in manifest.read_text().splitlines() if line]
    records: list[dict] = []
    timing: list[float] = []
    audio_dir = output / f'{name}-audio'
    audio_dir.mkdir(parents=True)
    for index, row in enumerate(tqdm(rows, desc=f'UL-UNAS {name}')):
        clean = read_audio(data_root / row['clean'], 16000)
        noisy = read_audio(data_root / row['noisy'], 16000)
        enhanced, elapsed = engine.enhance(noisy)
        timing.extend(elapsed)
        if index < 20:
            write_audio(audio_dir / f"{row['id']}.wav", enhanced, 16000)
        noisy_p = optional_metrics(clean, noisy, 16000)
        enhanced_p = optional_metrics(clean, enhanced, 16000)
        record = {
            'id': row['id'], 'category': row['category'],
            'noise_dataset': row.get('noise_dataset'),
            'input_snr_db': float(row['snr_db']),
            'snr_noisy': snr(clean, noisy), 'snr_enhanced': snr(clean, enhanced),
            'si_snr_noisy': si_snr(clean, noisy),
            'si_snr_enhanced': si_snr(clean, enhanced),
            'stoi_noisy': noisy_p['stoi'], 'stoi_enhanced': enhanced_p['stoi'],
            'pesq_noisy': noisy_p['pesq'], 'pesq_enhanced': enhanced_p['pesq'],
            'pause_noise_attenuation_db': pause_noise_attenuation(clean, noisy, enhanced),
            'speech_deletion_rate': speech_deletion_rate(clean, enhanced),
            'active_level_error_db': active_level_error_db(clean, enhanced),
        }
        for metric in ('snr', 'si_snr', 'stoi', 'pesq'):
            record[f'{metric}_improvement'] = (
                record[f'{metric}_enhanced'] - record[f'{metric}_noisy']
            )
        records.append(record)
    noisy_records = [r for r in records if r['category'] not in {'clean', 'near_clean'}]
    preservation = [r for r in records if r['category'] in {'clean', 'near_clean'}]
    metric_names = [key for key in records[0] if key not in {'id', 'category', 'noise_dataset'}]
    summarize = lambda selected: {key: mean(selected, key) for key in metric_names}
    result = {
        'count': len(records), 'summary': summarize(records),
        'noisy_only_summary': summarize(noisy_records),
        'clean_and_near_clean_summary': summarize(preservation),
        'by_category': {
            category: summarize([r for r in records if r['category'] == category])
            for category in sorted({r['category'] for r in records})
        },
        'model_frame_mean_ms': 1000 * float(np.mean(timing)),
        'model_frame_p99_ms': 1000 * float(np.quantile(timing, 0.99)),
        'records': records,
    }
    (output / f'{name}.json').write_text(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='artifacts/ulunas-upstream-audit')
    parser.add_argument('--project-root', default=None,
                        help='VoxShield project root (default: auto-detect from script location)')
    args = parser.parse_args()

    # Resolve project root so all relative paths work from any cwd
    if args.project_root:
        project_root = Path(args.project_root).resolve()
    else:
        project_root = Path(__file__).resolve().parents[1]

    model = project_root / 'external' / 'ul-unas' / 'ulunas_onnx' / 'onnx_models' / 'ulunas_stream_simple.onnx'
    output = project_root / args.output
    output.mkdir(exist_ok=False, parents=True)
    data_root = project_root / 'data'
    engine = ULUNAS(model)
    reports = {
        'broad': evaluate('broad', project_root / 'data' / 'mixtures' / 'audit_broad_val' / 'manifest.jsonl', engine, output, data_root),
        'military': evaluate('military', project_root / 'data' / 'mixtures' / 'audit_military_val' / 'manifest.jsonl', engine, output, data_root),
    }
    summary = {
        'architecture': 'upstream_ul_unas', 'onnx_sha256': sha256(model),
        'source': 'https://github.com/Xiaobin-Rong/ul-unas',
        'reports': {name: report['noisy_only_summary'] for name, report in reports.items()},
        'warning': 'Model comparison only; live frontend and Pi deployment are not yet validated.',
    }
    (output / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
