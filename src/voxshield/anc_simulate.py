"""Offline-only physical ANC simulation and safety report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .adaptive import simulate_filtered_x_nlms
from .audio import read_audio, write_audio


def _attenuation_db(before: np.ndarray, after: np.ndarray, eps: float = 1e-12) -> float:
    return float(
        10.0
        * np.log10(
            (float(np.mean(np.asarray(before, dtype=np.float64) ** 2)) + eps)
            / (float(np.mean(np.asarray(after, dtype=np.float64) ** 2)) + eps)
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run an offline FxNLMS simulation; this never drives audio hardware"
    )
    parser.add_argument("--reference", required=True)
    parser.add_argument(
        "--disturbance",
        required=True,
        help="Error-microphone recording made with the control loudspeaker muted",
    )
    parser.add_argument("--secondary-path", required=True)
    parser.add_argument("--output-dir", default="artifacts/anc-simulation")
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--taps", type=int, default=128)
    parser.add_argument("--step-size", type=float, default=0.01)
    parser.add_argument("--output-limit", type=float, default=0.25)
    parser.add_argument("--warmup-seconds", type=float, default=2.0)
    parser.add_argument(
        "--adaptation-gate",
        default=None,
        help="Optional audio file: values above 0.5 enable adaptation",
    )
    args = parser.parse_args()
    if args.sample_rate <= 0 or args.taps <= 0 or args.warmup_seconds < 0:
        parser.error("sample rate/taps must be positive and warmup cannot be negative")
    reference = read_audio(args.reference, args.sample_rate)
    disturbance = read_audio(args.disturbance, args.sample_rate)
    length = min(len(reference), len(disturbance))
    if not length:
        parser.error("reference and disturbance must contain audio")
    reference = reference[:length]
    disturbance = disturbance[:length]
    secondary_path = read_audio(args.secondary_path, args.sample_rate)
    gate = None
    if args.adaptation_gate:
        gate = read_audio(args.adaptation_gate, args.sample_rate)
        if len(gate) < length:
            parser.error("adaptation gate is shorter than the input signals")
        gate = gate[:length]
    residual, control, weights = simulate_filtered_x_nlms(
        reference,
        disturbance,
        secondary_path,
        taps=args.taps,
        step_size=args.step_size,
        output_limit=args.output_limit,
        adaptation_gate=gate,
    )
    warmup = min(length, round(args.warmup_seconds * args.sample_rate))
    evaluated = slice(warmup, None)
    report = {
        "mode": "offline_simulation_only",
        "sample_rate": args.sample_rate,
        "samples": length,
        "warmup_samples_excluded": warmup,
        "attenuation_db_after_warmup": _attenuation_db(
            disturbance[evaluated], residual[evaluated]
        ),
        "control_peak": float(np.max(np.abs(control))),
        "residual_peak": float(np.max(np.abs(residual))),
        "coefficient_peak": float(np.max(np.abs(weights))),
        "warning": (
            "A stable offline result does not authorize headphone playback. Real ANC requires "
            "low-level secondary-path identification, polarity checks, an error microphone, "
            "output limiting, and hardware fail-safe validation."
        ),
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_audio(output_dir / "simulated-error.wav", residual, args.sample_rate)
    write_audio(output_dir / "controller-output.wav", control, args.sample_rate)
    (output_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
