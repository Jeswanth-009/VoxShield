from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve
from tqdm import tqdm

from ..audio import peak_normalize_pair, read_audio, write_audio
from .dataset import (
    _impulsive_segment,
    choose_noise_segment,
    choose_speech_segment,
    load_manifest,
    mix_at_snr,
)

AUDIO_EXTENSIONS = {".wav", ".flac", ".ogg"}
SPLITS = ("train", "val", "test")
NOISE_CATEGORIES = ("stationary", "nonstationary", "impulsive", "environmental")


def _delay(audio: np.ndarray, samples: int) -> np.ndarray:
    output = np.zeros_like(audio)
    if samples >= 0:
        if samples < len(audio):
            output[samples:] = audio[: len(audio) - samples]
    elif -samples < len(audio):
        output[:samples] = audio[-samples:]
    return output


def _scan(directory: Path, data_root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not directory.exists():
        return rows
    for path in sorted(item for item in directory.rglob("*") if item.suffix.lower() in AUDIO_EXTENSIONS):
        try:
            info = sf.info(str(path))
            if info.frames <= 0 or info.samplerate <= 0:
                continue
            rows.append(
                {
                    "path": path.relative_to(data_root).as_posix(),
                    "frames": int(info.frames),
                    "sample_rate": int(info.samplerate),
                    "channels": int(info.channels),
                    "duration": float(info.duration),
                }
            )
        except (RuntimeError, ValueError):
            print(f"warning: skipped unreadable audio: {path}")
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def index_data(data_root: Path) -> None:
    raw = data_root / "raw"
    manifests = data_root / "manifests"
    total = 0
    for split in SPLITS:
        rows = _scan(raw / "clean" / split, data_root)
        _write_jsonl(manifests / f"clean_{split}.jsonl", rows)
        print(f"clean/{split}: {len(rows)} files")
        total += len(rows)
        for category in NOISE_CATEGORIES:
            rows = _scan(raw / "noise" / category / split, data_root)
            _write_jsonl(manifests / f"noise_{category}_{split}.jsonl", rows)
            print(f"noise/{category}/{split}: {len(rows)} files")
            total += len(rows)
        rows = _scan(raw / "rir" / split, data_root)
        _write_jsonl(manifests / f"rir_{split}.jsonl", rows)
        print(f"rir/{split}: {len(rows)} files (optional)")
    if total == 0:
        raise SystemExit(f"No audio found under {raw}. See data/README.md for the required layout.")


def make_fixed(args: argparse.Namespace) -> None:
    root = Path(args.data_root)
    manifests = root / getattr(args, "manifest_dir", "manifests")
    reverb_fraction = float(getattr(args, "reverb_fraction", 0.0))
    clean_rows = load_manifest(manifests / f"clean_{args.split}.jsonl")
    noises = {
        category: load_manifest(manifests / f"noise_{category}_{args.split}.jsonl")
        for category in NOISE_CATEGORIES
    }
    rirs = load_manifest(manifests / f"rir_{args.split}.jsonl", required=False)
    if reverb_fraction > 0.0 and not rirs:
        raise ValueError(
            f"--reverb-fraction is {reverb_fraction}, but no {args.split} RIRs exist"
        )
    noise_dataset = getattr(args, "noise_dataset", None)
    if noise_dataset:
        wanted = noise_dataset.casefold()
        noises = {
            category: [
                row for row in rows
                if str(row.get("dataset", "")).casefold() == wanted
            ]
            for category, rows in noises.items()
        }
    eligible_categories = tuple(category for category, rows in noises.items() if rows)
    if not eligible_categories:
        suffix = f" for dataset {noise_dataset!r}" if noise_dataset else ""
        raise ValueError(f"No {args.split} noise rows are available{suffix}")
    output = Path(args.output_dir) if args.output_dir else root / "mixtures" / args.split
    if (output / "manifest.jsonl").exists():
        raise FileExistsError("Frozen mixtures already exist; choose a new --output-dir")
    try:
        output.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("--output-dir must stay inside --data-root") from exc
    manifest: list[dict[str, object]] = []
    rng = random.Random(args.seed)
    length = int(args.seconds * args.sample_rate)
    clean_count = round(args.count * args.clean_fraction)
    near_clean_count = round(args.count * args.near_clean_fraction)
    noisy_count = args.count - clean_count - near_clean_count
    if noisy_count < 1:
        raise ValueError("clean and near-clean fractions leave no noisy evaluation pairs")
    categories = [
        eligible_categories[index % len(eligible_categories)] for index in range(noisy_count)
    ]
    categories[::5] = ["mixed"] * len(categories[::5])
    categories.extend(["clean"] * clean_count)
    categories.extend(["near_clean"] * near_clean_count)
    rng.shuffle(categories)
    clean_rows = list(clean_rows)
    rng.shuffle(clean_rows)
    for index in tqdm(range(args.count), desc="fixed mixtures"):
        clean_row = clean_rows[index % len(clean_rows)]
        category = categories[index]
        clean = choose_speech_segment(
            read_audio(root / clean_row["path"], args.sample_rate), length, rng
        )
        rir_row = None
        if rirs and rng.random() < reverb_fraction:
            rir_row = rng.choice(rirs)
            rir_path = Path(str(rir_row["path"]))
            if not rir_path.is_absolute():
                rir_path = root / rir_path
            rir = read_audio(rir_path, args.sample_rate)
            rir = rir[: min(len(rir), args.sample_rate)]
            rir = rir / max(
                np.sqrt(np.sum(rir.astype(np.float64) ** 2)), 1e-8
            )
            clean = fftconvolve(clean, rir, mode="full")[:length].astype(np.float32)
        source_category = None
        if category == "clean":
            clean, mixture = peak_normalize_pair(clean, clean.copy())
            snr_db = 60.0
        else:
            source_category = (
                rng.choice(eligible_categories)
                if category in ("mixed", "near_clean")
                else category
            )
            noise_row = rng.choice(noises[source_category])
            source_noise = read_audio(root / noise_row["path"], args.sample_rate)
            noise = (
                _impulsive_segment(source_noise, length, rng, clean)
                if source_category == "impulsive"
                else choose_noise_segment(source_noise, length, rng)
            )
        if category == "mixed":
            alternatives = [item for item in eligible_categories if item != source_category]
            second_category = rng.choice(alternatives or list(eligible_categories))
            second_row = rng.choice(noises[second_category])
            second = choose_noise_segment(
                read_audio(root / second_row["path"], args.sample_rate), length, rng
            )
            noise = noise + rng.uniform(0.2, 0.8) * second
        if category != "clean":
            snr_db = (
                rng.uniform(args.near_clean_snr_min, args.near_clean_snr_max)
                if category == "near_clean"
                else rng.uniform(args.snr_min, args.snr_max)
            )
            clean, mixture = mix_at_snr(clean, noise, snr_db)
        reference = None
        if getattr(args, "multichannel", False):
            primary_noise = mixture - clean
            delay = rng.randint(
                getattr(args, "reference_delay_min", -16),
                getattr(args, "reference_delay_max", 16),
            )
            noise_gain = 10.0 ** (
                rng.uniform(
                    getattr(args, "reference_noise_gain_min", -6.0),
                    getattr(args, "reference_noise_gain_max", 6.0),
                ) / 20.0
            )
            speech_leak = 10.0 ** (
                rng.uniform(
                    getattr(args, "reference_speech_leak_min", -35.0),
                    getattr(args, "reference_speech_leak_max", -12.0),
                ) / 20.0
            )
            reference = (
                noise_gain * _delay(primary_noise, delay)
                + speech_leak * _delay(clean, delay)
            ).astype(np.float32)
            peak = max(
                float(np.max(np.abs(clean))),
                float(np.max(np.abs(mixture))),
                float(np.max(np.abs(reference))),
                0.95,
            )
            scale = 0.95 / peak
            clean = (clean * scale).astype(np.float32)
            mixture = (mixture * scale).astype(np.float32)
            reference = (reference * scale).astype(np.float32)
        stem = f"{index:06d}"
        clean_path = output / "clean" / f"{stem}.wav"
        noisy_path = output / "noisy" / f"{stem}.wav"
        write_audio(clean_path, clean, args.sample_rate)
        write_audio(noisy_path, mixture, args.sample_rate)
        reference_path = output / "reference" / f"{stem}.wav"
        if reference is not None:
            write_audio(reference_path, reference, args.sample_rate)
        manifest.append(
            {
                "id": stem,
                "clean_source_path": clean_row.get("path"),
                "generator_revision": "2026-09-worker-runtime-audit",
                "clean": clean_path.relative_to(root).as_posix(),
                "noisy": noisy_path.relative_to(root).as_posix(),
                "reference": (
                    reference_path.relative_to(root).as_posix()
                    if reference is not None
                    else None
                ),
                "category": category,
                "source_category": source_category,
                "noise_dataset": None if category == "clean" else noise_row.get("dataset"),
                "noise_source_label": (
                    None if category == "clean" else noise_row.get("source_label")
                ),
                "noise_source_path": None if category == "clean" else noise_row.get("path"),
                "second_noise_dataset": (
                    second_row.get("dataset") if category == "mixed" else None
                ),
                "second_noise_source_label": (
                    second_row.get("source_label") if category == "mixed" else None
                ),
                "second_noise_source_path": (
                    second_row.get("path") if category == "mixed" else None
                ),
                "snr_db": snr_db,
                "sample_rate": args.sample_rate,
                "rir_source_path": rir_row.get("path") if rir_row else None,
            }
        )
    _write_jsonl(output / "manifest.jsonl", manifest)
    print(f"wrote {len(manifest)} pairs to {output}")


def audit_catalog(args: argparse.Namespace) -> None:
    """Report coverage and reject group leakage before expensive training."""
    root = Path(args.data_root)
    catalog_path = root / getattr(args, "manifest_dir", "manifests") / "catalog.jsonl"
    rows = load_manifest(catalog_path)
    counts: Counter[str] = Counter()
    durations: defaultdict[str, float] = defaultdict(float)
    groups: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    labels: Counter[str] = Counter()
    missing: list[str] = []
    for row in rows:
        key = f"{row.get('kind', 'unknown')}/{row.get('category') or 'none'}/{row.get('split')}"
        counts[key] += 1
        durations[key] += float(row.get("duration", 0.0))
        if row.get("split_method") != "official/path":
            dataset_group = (str(row.get("dataset", "unknown")), str(row.get("group", "")))
            groups[dataset_group].add(str(row.get("split", "unknown")))
        if row.get("source_label"):
            labels[str(row["source_label"]).casefold()] += 1
        path = Path(str(row["path"]))
        if not path.is_absolute():
            path = root / path
        if not path.exists() and len(missing) < 100:
            missing.append(str(path))
    leakage = [
        {"dataset": dataset, "group": group, "splits": sorted(splits)}
        for (dataset, group), splits in groups.items()
        if group and len(splits) > 1
    ]
    required_defence = {
        "gunshot": ("gunshot", "gun", "rifle"),
        "artillery_or_shelling": ("artillery", "shelling", "explosion"),
        "vehicle_or_tank": ("vehicle", "tank", "armored", "armoured"),
        "helicopter_or_rotor": ("helicopter", "rotor"),
        "aircraft": ("fighter", "aircraft", "airplane"),
        "drone": ("drone", "uav", "quadcopter"),
        "wind": ("wind",),
        "siren": ("siren",),
    }
    coverage = {
        name: sum(
            count
            for label, count in labels.items()
            if any(token in label for token in tokens)
        )
        for name, tokens in required_defence.items()
    }
    missing_requirements = [
        f"defence_label:{name}" for name, count in coverage.items() if count == 0
    ]
    rir_rows = sum(1 for row in rows if row.get("kind") == "rir")
    if rir_rows == 0:
        missing_requirements.append("rir")
    report = {
        "catalog": str(catalog_path),
        "rows": len(rows),
        "counts": dict(sorted(counts.items())),
        "duration_hours": {
            key: value / 3600.0 for key, value in sorted(durations.items())
        },
        "defence_label_coverage": coverage,
        "rir_rows": rir_rows,
        "missing_requirements": missing_requirements,
        "group_split_leakage": leakage,
        "missing_file_count_capped": len(missing),
        "missing_files_first_100": missing,
        "ready": not leakage and not missing and not missing_requirements,
        "note": "Coverage is label-based; manually verify licences and acoustic relevance.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if args.fail_on_leakage and (leakage or missing):
        raise SystemExit("Dataset audit failed: split leakage or missing source files")


def main() -> None:
    parser = argparse.ArgumentParser(description="Index VoxShield data or create fixed mixtures")
    subparsers = parser.add_subparsers(dest="command", required=True)
    index_parser = subparsers.add_parser("index")
    index_parser.add_argument("--data-root", default="data")
    mix_parser = subparsers.add_parser("make-fixed")
    mix_parser.add_argument("--data-root", default="data")
    mix_parser.add_argument("--manifest-dir", default="manifests")
    mix_parser.add_argument("--split", choices=("val", "test"), default="test")
    mix_parser.add_argument("--count", type=int, default=500)
    mix_parser.add_argument("--seconds", type=float, default=4.0)
    mix_parser.add_argument("--sample-rate", type=int, default=16000)
    mix_parser.add_argument("--snr-min", type=float, default=-10.0)
    mix_parser.add_argument("--snr-max", type=float, default=20.0)
    mix_parser.add_argument("--near-clean-snr-min", type=float, default=25.0)
    mix_parser.add_argument("--near-clean-snr-max", type=float, default=40.0)
    mix_parser.add_argument("--clean-fraction", type=float, default=0.10)
    mix_parser.add_argument("--near-clean-fraction", type=float, default=0.10)
    mix_parser.add_argument(
        "--reverb-fraction",
        type=float,
        default=0.0,
        help="Fraction of pairs convolved with a split-disjoint RIR",
    )
    mix_parser.add_argument(
        "--multichannel",
        action="store_true",
        help="Also write a deterministic synchronized reference-microphone channel",
    )
    mix_parser.add_argument("--reference-delay-min", type=int, default=-16)
    mix_parser.add_argument("--reference-delay-max", type=int, default=16)
    mix_parser.add_argument("--reference-noise-gain-min", type=float, default=-6.0)
    mix_parser.add_argument("--reference-noise-gain-max", type=float, default=6.0)
    mix_parser.add_argument("--reference-speech-leak-min", type=float, default=-35.0)
    mix_parser.add_argument("--reference-speech-leak-max", type=float, default=-12.0)
    mix_parser.add_argument(
        "--noise-dataset",
        default=None,
        help="Use noise only from this manifest dataset name (case-insensitive)",
    )
    mix_parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional directory inside data root; preserves an older fixed evaluation set",
    )
    mix_parser.add_argument("--seed", type=int, default=2025)
    ingest_parser = subparsers.add_parser(
        "ingest", help="Reference large extracted datasets in place and build all manifests"
    )
    ingest_parser.add_argument(
        "--source",
        action="append",
        required=True,
        help="PATH, clean=PATH, noise=PATH, noise:CATEGORY=PATH, or rir=PATH; repeat as needed",
    )
    ingest_parser.add_argument("--data-root", default="data")
    ingest_parser.add_argument(
        "--manifest-dir",
        default="manifests",
        help="Versioned manifest folder inside data root, for example manifests_v4",
    )
    ingest_parser.add_argument("--seed", type=int, default=1337)
    ingest_parser.add_argument("--train-ratio", type=float, default=0.90)
    ingest_parser.add_argument("--val-ratio", type=float, default=0.05)
    ingest_parser.add_argument("--test-ratio", type=float, default=0.05)
    ingest_parser.add_argument("--analyze-unknown-noise", action="store_true")
    ingest_parser.add_argument(
        "--scan-workers",
        type=int,
        default=8,
        help="Concurrent audio-header readers; reduce for a slow HDD or network drive",
    )
    ingest_parser.add_argument("--dry-run", action="store_true")
    audit_parser = subparsers.add_parser(
        "audit", help="Summarize coverage and detect group leakage/missing source files"
    )
    audit_parser.add_argument("--data-root", default="data")
    audit_parser.add_argument("--manifest-dir", default="manifests")
    audit_parser.add_argument("--output", default="artifacts/data-audit.json")
    audit_parser.add_argument("--fail-on-leakage", action="store_true")
    args = parser.parse_args()
    if args.command == "make-fixed" and not 0.0 <= args.reverb_fraction <= 1.0:
        parser.error("--reverb-fraction must be between 0 and 1")
    if args.command == "index":
        index_data(Path(args.data_root))
    elif args.command == "make-fixed":
        make_fixed(args)
    elif args.command == "ingest":
        from .ingest import ingest_sources, parse_source_spec

        ingest_sources(
            [parse_source_spec(value) for value in args.source],
            Path(args.data_root),
            seed=args.seed,
            split_ratios=(args.train_ratio, args.val_ratio, args.test_ratio),
            analyze_unknown_noise=args.analyze_unknown_noise,
            scan_workers=args.scan_workers,
            dry_run=args.dry_run,
            manifest_dir=args.manifest_dir,
        )
    else:
        audit_catalog(args)


if __name__ == "__main__":
    main()
