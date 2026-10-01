"""Convert NASA small-UAS MATLAB pressure recordings into training WAV files."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.io import loadmat
from scipy.signal import resample_poly
from tqdm import tqdm

# The dataset's supplied gps_audio_playback.m and groundtrack_playback.m select
# microphone 1 for AP Hill (cub/hex) and microphone 3 for Pungo (edge/phantom/y6).
PLAYBACK_CHANNEL = {"cub": 0, "hex": 0, "edge": 2, "phantom": 2, "y6": 2}


def _ranked_splits(files: list[Path], seed: int) -> dict[Path, str]:
    ranked = sorted(
        files,
        key=lambda path: hashlib.sha1(f"{seed}|{path.stem}".encode()).hexdigest(),
    )
    train_end = round(0.80 * len(ranked))
    val_end = train_end + round(0.10 * len(ranked))
    return {
        path: "train" if index < train_end else "val" if index < val_end else "test"
        for index, path in enumerate(ranked)
    }


def convert_recording(source: Path, output: Path, target_sample_rate: int) -> dict[str, object]:
    vehicle = source.stem.split("_", 1)[0].lower()
    if vehicle not in PLAYBACK_CHANNEL:
        raise ValueError(f"Unknown small-UAS vehicle prefix in {source.name}")
    loaded = loadmat(source, simplify_cells=True, variable_names=("acoustics",))
    acoustics = loaded.get("acoustics")
    if not isinstance(acoustics, dict):
        raise TypeError(f"Missing acoustics structure in {source}")
    pressure = np.asarray(acoustics.get("incident_pascals"), dtype=np.float64)
    utc_time = np.asarray(acoustics.get("utc_time"), dtype=np.float64).reshape(-1)
    if pressure.ndim != 2 or len(pressure) != len(utc_time) or len(utc_time) < 2:
        raise ValueError(f"Invalid acoustic arrays in {source}")
    channel = PLAYBACK_CHANNEL[vehicle]
    if channel >= pressure.shape[1]:
        raise ValueError(f"Required microphone {channel + 1} is absent in {source}")
    intervals = np.diff(utc_time)
    if not np.all(np.isfinite(intervals)) or np.any(intervals <= 0):
        raise ValueError(f"Non-monotonic acoustic clock in {source}")
    original_rate = round(1.0 / float(np.median(intervals)))
    if original_rate <= 0:
        raise ValueError(f"Invalid sample rate in {source}")
    audio = np.nan_to_num(
        pressure[:, channel], nan=0.0, posinf=0.0, neginf=0.0
    )
    original_peak = float(np.max(np.abs(audio)))
    original_rms = float(np.sqrt(np.mean(audio**2)))
    if original_peak <= 1e-12:
        raise ValueError(f"Silent selected microphone in {source}")
    scale = 0.95 / original_peak
    audio = audio * scale
    if original_rate != target_sample_rate:
        divisor = math.gcd(original_rate, target_sample_rate)
        audio = resample_poly(
            audio,
            target_sample_rate // divisor,
            original_rate // divisor,
        )
    audio = np.clip(audio, -0.999, 0.999).astype(np.float32)
    output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output, audio, target_sample_rate, subtype="PCM_16")
    return {
        "source_mat": str(source.resolve()),
        "output_wav": str(output.resolve()),
        "vehicle": vehicle,
        "recording": source.stem,
        "selected_microphone_one_based": channel + 1,
        "original_sample_rate_hz": original_rate,
        "output_sample_rate_hz": target_sample_rate,
        "original_peak_pascals": original_peak,
        "original_rms_pascals": original_rms,
        "normalization_scale": scale,
        "output_samples": len(audio),
        "duration_seconds": len(audio) / target_sample_rate,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert NASA small-UAS .mat acoustic recordings to 16 kHz WAV"
    )
    parser.add_argument("--input", required=True, help="Extracted small_uav_acoustics root")
    parser.add_argument("--output", required=True, help="Derived WAV dataset root")
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    source_root = Path(args.input).resolve()
    data_root = source_root / "data" if (source_root / "data").is_dir() else source_root
    files = sorted(data_root.glob("*.mat"))
    if not files:
        raise SystemExit(f"No .mat recordings found in {data_root}")
    if args.sample_rate <= 0:
        parser.error("--sample-rate must be positive")
    output_root = Path(args.output).resolve()
    splits = _ranked_splits(files, args.seed)
    records: list[dict[str, object]] = []
    for source in tqdm(files, desc="convert small-UAS", unit="recording"):
        split = splits[source]
        target = output_root / split / f"uav_{source.stem}.wav"
        if target.exists() and not args.overwrite:
            info = sf.info(target)
            records.append(
                {
                    "source_mat": str(source.resolve()),
                    "output_wav": str(target.resolve()),
                    "vehicle": source.stem.split("_", 1)[0].lower(),
                    "recording": source.stem,
                    "split": split,
                    "output_sample_rate_hz": int(info.samplerate),
                    "output_samples": int(info.frames),
                    "duration_seconds": float(info.duration),
                    "conversion_skipped_existing": True,
                }
            )
            continue
        record = convert_recording(source, target, args.sample_rate)
        record["split"] = split
        records.append(record)
    output_root.mkdir(parents=True, exist_ok=True)
    metadata = output_root / "uav-conversion.jsonl"
    with metadata.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    summary = {
        "source_root": str(source_root),
        "output_root": str(output_root),
        "recordings": len(records),
        "sample_rate_hz": args.sample_rate,
        "splits": {
            split: sum(record["split"] == split for record in records)
            for split in ("train", "val", "test")
        },
        "metadata": str(metadata),
        "note": "WAV amplitude is normalized for PCM storage; original pressure metadata is retained.",
    }
    (output_root / "uav-conversion.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
