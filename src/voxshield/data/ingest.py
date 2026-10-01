from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from collections import Counter
from collections.abc import Iterable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from tqdm import tqdm

from .index import AUDIO_EXTENSIONS, NOISE_CATEGORIES, SPLITS


@dataclass(frozen=True)
class SourceSpec:
    path: Path
    kind: str = "auto"
    category: str | None = None


def parse_source_spec(value: str) -> SourceSpec:
    """Parse PATH, clean=PATH, noise=PATH, noise:CATEGORY=PATH, or rir=PATH."""
    if "=" not in value:
        return SourceSpec(Path(value).expanduser().resolve())
    prefix, raw_path = value.split("=", 1)
    prefix = prefix.strip().lower()
    if ":" in prefix:
        kind, category = prefix.split(":", 1)
    else:
        kind, category = prefix, None
    if kind not in {"auto", "clean", "noise", "rir"}:
        raise ValueError(f"Invalid source kind in {value!r}")
    if category and category not in NOISE_CATEGORIES:
        raise ValueError(f"Invalid noise category {category!r} in {value!r}")
    if category and kind != "noise":
        raise ValueError("A category may only be supplied for a noise source")
    return SourceSpec(Path(raw_path).expanduser().resolve(), kind, category)


def detect_adapter(root: Path) -> str:
    name = root.name.lower()
    if (root / "uav-conversion.json").exists() or "uav" in _tokens(Path(name)):
        return "uav"
    if "librispeech" in name or any((root / split).exists() for split in ("train-clean-100", "dev-clean", "test-clean")):
        return "librispeech"
    if "vctk" in name or (root / "speaker-info.txt").exists() or any(
        (root / directory).exists() for directory in ("wav48_silence_trimmed", "wav48")
    ):
        return "vctk"
    if "esc-50" in name or (root / "meta" / "esc50.csv").exists():
        return "esc50"
    if "musan" in name or ((root / "noise").exists() and (root / "music").exists()):
        return "musan"
    if "mad_dataset" in name or "military_audio" in name or (
        (root / "training.csv").exists() and (root / "test.csv").exists()
    ):
        return "mad"
    lowered_parts = {part.lower() for part in root.parts}
    if "dns-challenge" in name or "dns-challenge" in lowered_parts or any(
        (root / item).exists() for item in ("clean", "noise", "clean_fullband", "noise_fullband")
    ):
        return "dns"
    return "generic"


def _tokens(path: Path) -> set[str]:
    return {
        token
        for part in path.parts
        for token in re.split(r"[^a-z0-9]+", part.lower())
        if token
    }


STATIONARY_WORDS = {
    "aircon", "airconditioner", "ac", "fan", "hvac", "hum", "idling", "steady",
    "vacuum", "pump", "compressor", "generator", "ventilation", "white", "pink",
    "washing", "washer", "clock", "tick", "engine", "crickets", "insects",
}
NONSTATIONARY_WORDS = {
    "babble", "speech", "talking", "music", "wind", "rotor", "helicopter", "siren",
    "vehicle", "traffic", "crowd", "train", "truck", "car", "motorcycle", "rain",
    "chainsaw", "airplane", "aircraft", "waves", "birds", "chirping",
}
IMPULSIVE_WORDS = {
    "bang", "blast", "explosion", "explosive", "gun", "gunshot", "shot", "knock",
    "impact", "hammer", "slam", "firework", "fireworks", "click", "clap", "clapping",
    "burst", "crack", "breaking", "sneeze", "sneezing", "cough", "coughing",
    "footstep", "footsteps", "keyboard", "horn", "bells", "thunderstorm",
}


def classify_from_name(path: Path) -> str | None:
    tokens = _tokens(path)
    if tokens & IMPULSIVE_WORDS:
        return "impulsive"
    if tokens & STATIONARY_WORDS:
        return "stationary"
    if tokens & NONSTATIONARY_WORDS:
        return "nonstationary"
    return None


def classify_from_audio(path: Path, info: Any, max_seconds: float = 30.0) -> tuple[str, dict[str, float]]:
    frames = min(int(info.frames), int(info.samplerate * max_seconds))
    audio, _ = sf.read(str(path), frames=frames, dtype="float32", always_2d=True)
    audio = np.nan_to_num(audio.mean(axis=1), nan=0.0, posinf=0.0, neginf=0.0)
    if len(audio) < max(64, info.samplerate // 10):
        return "environmental", {"noise_rms_cv": 0.0, "noise_peak_to_rms": 0.0, "noise_flux": 0.0}
    frame_length = max(64, int(info.samplerate * 0.05))
    hop = frame_length // 2
    count = 1 + max(0, (len(audio) - frame_length) // hop)
    sample_count = min(count, 400)
    positions = np.linspace(0, max(0, len(audio) - frame_length), sample_count, dtype=np.int64)
    frames_view = np.stack([audio[position : position + frame_length] for position in positions])
    rms = np.sqrt(np.mean(frames_view.astype(np.float64) ** 2, axis=1) + 1e-10)
    median_rms = float(np.median(rms))
    rms_cv = float(np.std(rms) / max(float(np.mean(rms)), 1e-8))
    overall_rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2) + 1e-10))
    peak_to_rms = float(np.max(np.abs(audio)) / max(overall_rms, 1e-8))
    transient_fraction = float(np.mean(rms > max(4.0 * median_rms, 1e-4)))
    window = np.hanning(frame_length).astype(np.float32)
    spectra = np.abs(np.fft.rfft(frames_view * window, axis=1))
    spectra /= np.maximum(spectra.sum(axis=1, keepdims=True), 1e-8)
    flux = float(np.mean(np.sqrt(np.sum(np.diff(spectra, axis=0) ** 2, axis=1)))) if len(spectra) > 1 else 0.0
    features = {
        "noise_rms_cv": rms_cv,
        "noise_peak_to_rms": peak_to_rms,
        "noise_flux": flux,
        "noise_transient_fraction": transient_fraction,
    }
    if peak_to_rms > 10.0 and transient_fraction < 0.20:
        return "impulsive", features
    if rms_cv < 0.30 and flux < 0.12:
        return "stationary", features
    if rms_cv > 0.65 or flux > 0.22:
        return "nonstationary", features
    return "environmental", features


def _official_split(relative: Path, adapter: str, esc_metadata: dict[str, dict[str, str]]) -> str | None:
    if adapter == "esc50" and relative.name in esc_metadata:
        fold = int(esc_metadata[relative.name]["fold"])
        return "train" if fold <= 3 else "val" if fold == 4 else "test"
    for part in relative.parts:
        normalized = part.lower().replace("_", "-")
        if normalized.startswith(("train", "training")):
            return "train"
        if normalized.startswith(("dev", "valid", "validation", "val")):
            return "val"
        if normalized.startswith(("test", "eval", "evaluation")):
            return "test"
    return None


def _load_mad_metadata(root: Path) -> dict[str, dict[str, str]]:
    """Load the official MAD path/label CSVs, keyed by normalized relative audio path."""
    metadata: dict[str, dict[str, str]] = {}
    for filename, split in (("training.csv", "train"), ("test.csv", "test")):
        path = root / filename
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                raw_path = (row.get("path") or "").strip().replace("\\", "/")
                if raw_path:
                    metadata[Path(raw_path).as_posix().casefold()] = {**row, "split": split}
    return metadata


MAD_LABELS = {
    "0": "communication",
    "1": "gunshot",
    "2": "footsteps",
    "3": "shelling",
    "4": "vehicle",
    "5": "helicopter",
    "6": "fighter",
}

MAD_NOISE_CATEGORIES = {
    "1": "impulsive",      # gunshot
    "2": "impulsive",      # footsteps: repeated short impacts
    "3": "impulsive",      # shelling
    "4": "nonstationary",  # vehicle
    "5": "nonstationary",  # helicopter
    "6": "nonstationary",  # fighter
}


def _group_key(relative: Path, adapter: str, kind: str) -> str:
    parts = relative.parts
    if adapter == "librispeech":
        for index, part in enumerate(parts[:-1]):
            if part.lower().startswith(("train", "dev", "test")) and index + 1 < len(parts):
                return parts[index + 1]
    if kind == "clean" and len(parts) > 1:
        return relative.parent.name
    if adapter == "uav":
        return relative.stem.removeprefix("uav_")
    stem = relative.stem
    return re.split(r"[-_]", stem, maxsplit=1)[0] or stem


def _hashed_split(dataset: str, group: str, seed: int, ratios: tuple[float, float, float]) -> str:
    digest = hashlib.sha1(f"{seed}|{dataset}|{group}".encode()).hexdigest()
    value = int(digest[:12], 16) / float(16**12)
    if value < ratios[0]:
        return "train"
    if value < ratios[0] + ratios[1]:
        return "val"
    return "test"


def _load_esc_metadata(root: Path) -> dict[str, dict[str, str]]:
    candidates = (root / "meta" / "esc50.csv", root / "esc50.csv")
    path = next((candidate for candidate in candidates if candidate.exists()), None)
    if path is None:
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {row["filename"]: row for row in csv.DictReader(handle)}


def _infer_kind(adapter: str, relative: Path) -> str | None:
    if adapter in {"librispeech", "vctk"}:
        return "clean"
    if adapter in {"esc50", "musan", "mad", "uav"}:
        return "noise"
    tokens = _tokens(relative)
    if tokens & {"rir", "impulse", "responses", "response"} and "noise" not in tokens:
        return "rir"
    if any(token.startswith("clean") for token in tokens):
        return "clean"
    if any(token.startswith("noise") for token in tokens):
        return "noise"
    return None


def _iter_audio(root: Path, adapter: str) -> Iterable[Path]:
    scan_root = root
    if adapter == "vctk":
        # VCTK releases sometimes contain multiple rendered copies of the same
        # utterances. Prefer the silence-trimmed tree, then the regular WAV tree.
        for directory in ("wav48_silence_trimmed", "wav48"):
            candidate = root / directory
            if candidate.exists():
                scan_root = candidate
                break
    elif adapter == "esc50":
        # Some packaged ESC-50 copies contain the original 44.1 kHz files plus
        # additional 44.1/16 kHz renders. Select exactly one flat set, preferring
        # the ready-to-train 16 kHz render, instead of cataloging duplicates.
        candidates = (
            root / "audio" / "audio" / "16000",
            root / "audio" / "16000",
            root / "audio",
            root / "audio" / "audio",
        )
        for candidate in candidates:
            if candidate.exists() and any(
                path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
                for path in candidate.iterdir()
            ):
                return (
                    path
                    for path in candidate.iterdir()
                    if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
                )
    return (
        path
        for path in scan_root.rglob("*")
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    )


def _probe_audio(path: Path) -> tuple[Path, Any | None]:
    try:
        info = sf.info(str(path))
    except (RuntimeError, ValueError, OSError):
        return path, None
    if info.frames <= 0 or info.samplerate <= 0:
        return path, None
    return path, info


def _iter_probed_audio(
    paths: Iterable[Path], workers: int
) -> Iterable[tuple[Path, Any | None]]:
    """Probe headers concurrently while keeping only a bounded number of futures."""
    if workers <= 1:
        for path in paths:
            yield _probe_audio(path)
        return
    iterator = iter(paths)
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="audio-probe") as executor:
        pending: set[Future[tuple[Path, Any | None]]] = set()
        exhausted = False
        while pending or not exhausted:
            while not exhausted and len(pending) < workers * 4:
                try:
                    pending.add(executor.submit(_probe_audio, next(iterator)))
                except StopIteration:
                    exhausted = True
            if not pending:
                break
            completed, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in completed:
                yield future.result()


def ingest_sources(
    sources: list[SourceSpec],
    data_root: Path,
    *,
    seed: int = 1337,
    split_ratios: tuple[float, float, float] = (0.90, 0.05, 0.05),
    analyze_unknown_noise: bool = False,
    scan_workers: int = min(8, os.cpu_count() or 1),
    dry_run: bool = False,
    manifest_dir: str = "manifests",
) -> dict[str, int]:
    if not np.isclose(sum(split_ratios), 1.0):
        raise ValueError("Split ratios must sum to one")
    if scan_workers < 1:
        raise ValueError("scan_workers must be at least one")
    rows: list[dict[str, Any]] = []
    skipped = 0
    seen: set[str] = set()
    for source in sources:
        if not source.path.exists():
            raise FileNotFoundError(f"Dataset source does not exist: {source.path}")
        adapter = detect_adapter(source.path)
        dataset = source.path.name
        esc_metadata = _load_esc_metadata(source.path)
        mad_metadata = _load_mad_metadata(source.path) if adapter == "mad" else {}
        # Keep this streaming: a very large corpus should not require a complete
        # in-memory file listing before metadata collection can begin.
        print(f"{dataset}: adapter={adapter}, mode=reference (audio is not copied)")
        probed = _iter_probed_audio(_iter_audio(source.path, adapter), scan_workers)
        for path, info in tqdm(probed, desc=f"scan {dataset}", unit="file"):
            canonical = str(path.resolve()).casefold()
            if canonical in seen:
                continue
            relative = path.relative_to(source.path)
            kind = source.kind if source.kind != "auto" else _infer_kind(adapter, relative)
            if kind is None:
                skipped += 1
                continue
            if info is None:
                skipped += 1
                continue
            group = _group_key(relative, adapter, kind)
            mad_row = mad_metadata.get(relative.as_posix().casefold())
            split = mad_row["split"] if mad_row else _official_split(relative, adapter, esc_metadata)
            split_method = "official/path" if split else "deterministic-group-hash"
            split = split or _hashed_split(dataset, group, seed, split_ratios)
            category = None
            category_method = None
            features: dict[str, float] = {}
            source_label = None
            source_label_id = None
            if kind == "noise":
                if adapter == "uav":
                    vehicle = relative.stem.removeprefix("uav_").split("_", 1)[0]
                    source_label = f"drone_uav_{vehicle}"
                    category = source.category or "nonstationary"
                    category_method = (
                        "user-source-spec" if source.category else "uav-adapter"
                    )
                elif source.category:
                    category, category_method = source.category, "user-source-spec"
                elif adapter == "mad" and mad_row:
                    source_label_id = (mad_row.get("label") or "").strip()
                    source_label = MAD_LABELS.get(source_label_id, f"unknown-{source_label_id}")
                    # The target is speech enhancement. Automatically using MAD's
                    # communication class as "noise" creates an ambiguous speech-on-
                    # speech target and may train the network to remove wanted speech.
                    if source_label_id == "0":
                        skipped += 1
                        continue
                    category = MAD_NOISE_CATEGORIES.get(source_label_id)
                    category_method = "mad-csv-label" if category else None
                elif adapter == "musan" and _tokens(relative) & {"music", "speech"}:
                    category, category_method = "nonstationary", "musan-layout"
                elif adapter == "esc50" and relative.name in esc_metadata:
                    source_label = esc_metadata[relative.name]["category"].strip()
                    source_label_id = esc_metadata[relative.name].get("target")
                    category = classify_from_name(Path(source_label))
                    category_method = "esc50-metadata" if category else None
                if category is None:
                    category = classify_from_name(relative)
                    category_method = "path-keyword" if category else None
                if category is None and analyze_unknown_noise:
                    category, features = classify_from_audio(path, info)
                    category_method = "acoustic-heuristic"
                if category is None:
                    category, category_method = "environmental", "unknown-default"
            row = {
                "path": str(path.resolve()),
                "frames": int(info.frames),
                "sample_rate": int(info.samplerate),
                "channels": int(info.channels),
                "duration": float(info.duration),
                "dataset": dataset,
                "adapter": adapter,
                "kind": kind,
                "category": category,
                "category_method": category_method,
                "source_label": source_label,
                "source_label_id": source_label_id,
                "split": split,
                "split_method": split_method,
                "group": group,
                **features,
            }
            rows.append(row)
            seen.add(canonical)
    counts = Counter(
        f"{row['kind']}/{row['category'] + '/' if row['category'] else ''}{row['split']}"
        for row in rows
    )
    counts["skipped"] = skipped
    if dry_run:
        print(json.dumps(dict(sorted(counts.items())), indent=2))
        return dict(counts)
    manifests = data_root / manifest_dir
    try:
        manifests.resolve().relative_to(data_root.resolve())
    except ValueError as exc:
        raise ValueError("manifest_dir must stay inside data_root") from exc
    manifests.mkdir(parents=True, exist_ok=True)
    catalog = manifests / "catalog.jsonl"
    with catalog.open("w", encoding="utf-8") as handle:
        for row in sorted(rows, key=lambda item: item["path"].casefold()):
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    for split in SPLITS:
        clean_rows = [row for row in rows if row["kind"] == "clean" and row["split"] == split]
        _write_rows(manifests / f"clean_{split}.jsonl", clean_rows)
        rir_rows = [row for row in rows if row["kind"] == "rir" and row["split"] == split]
        _write_rows(manifests / f"rir_{split}.jsonl", rir_rows)
        for category in NOISE_CATEGORIES:
            noise_rows = [
                row
                for row in rows
                if row["kind"] == "noise"
                and row["category"] == category
                and row["split"] == split
            ]
            _write_rows(manifests / f"noise_{category}_{split}.jsonl", noise_rows)
    summary = manifests / "ingest-summary.json"
    summary.write_text(json.dumps(dict(sorted(counts.items())), indent=2), encoding="utf-8")
    print(json.dumps(dict(sorted(counts.items())), indent=2))
    print(f"Referenced {len(rows)} files without copying audio. Catalog: {catalog}")
    return dict(counts)


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
