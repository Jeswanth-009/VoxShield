"""Download a small, targeted AudioSet subset from Hugging Face.

This intentionally avoids downloading the full AudioSet. It streams rows from
agkphysics/AudioSet, keeps only defense/demo-relevant non-speech noise labels,
and writes capped 16 kHz mono WAV files under data/external_audioset_targeted.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np
import soundfile as sf
from datasets import Audio, load_dataset

try:
    from scipy.signal import resample_poly
except Exception:  # pragma: no cover - optional fallback
    resample_poly = None


TARGETS: dict[str, tuple[str, ...]] = {
    "gunshot": ("gunshot", "gunfire", "cap gun"),
    "explosion": ("explosion", "bang", "blast", "fireworks"),
    "engine": ("engine", "idling", "motor"),
    "vehicle": ("vehicle", "car", "truck", "bus", "air brake"),
    "helicopter": ("helicopter", "rotor"),
    "aircraft": ("aircraft", "airplane", "jet", "fighter"),
    "siren": ("siren", "alarm"),
    "footsteps": ("footsteps", "walk"),
}

SKIP_LABELS = {
    "speech",
    "music",
    "singing",
    "conversation",
    "narration",
    "inside, small room",
}


def slug(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9._-]+", "_", text).strip("_")
    return text[:120] or "clip"


def match_target(human_labels: list[str], allow_speech: bool) -> str | None:
    lowered = [label.lower() for label in human_labels]
    if not allow_speech and any(label in SKIP_LABELS for label in lowered):
        return None
    joined = " | ".join(lowered)
    for target, needles in TARGETS.items():
        if any(needle in joined for needle in needles):
            return target
    return None


def to_mono(audio: np.ndarray) -> np.ndarray:
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if audio.size == 0:
        return audio
    peak = float(np.max(np.abs(audio)))
    if math.isfinite(peak) and peak > 1.0:
        audio = audio / peak
    return audio


def resample(audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate == target_rate:
        return audio
    if resample_poly is None:
        raise RuntimeError("scipy is required for resampling. Install scipy or set --sample-rate to source rate.")
    gcd = math.gcd(source_rate, target_rate)
    return resample_poly(audio, target_rate // gcd, source_rate // gcd).astype(np.float32)


def _decode_with_ffmpeg(input_path: Path, output_path: Path, target_rate: int) -> tuple[np.ndarray, int]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError(
            "Could not decode AudioSet clip with soundfile, and ffmpeg was not found on PATH. "
            "Install ffmpeg or add it to PATH."
        )
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(input_path),
            "-ac",
            "1",
            "-ar",
            str(target_rate),
            str(output_path),
        ],
        check=True,
    )
    audio, sample_rate = sf.read(output_path, dtype="float32", always_2d=False)
    return to_mono(audio), int(sample_rate)


def decode_audio(audio_info: dict, target_rate: int) -> tuple[np.ndarray, int]:
    """Decode a Hugging Face Audio(decode=False) record without torchcodec.

    Newer versions of datasets route normal audio decoding through torchcodec.
    On this Windows environment torchcodec can install but fail to load its DLLs,
    so we request raw bytes and decode them with libsndfile/soundfile first, then
    ffmpeg as a fallback.
    """

    raw = audio_info.get("bytes")
    path = audio_info.get("path")

    if raw:
        try:
            audio, sample_rate = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
            audio = to_mono(audio)
            return resample(audio, int(sample_rate), target_rate), target_rate
        except Exception:
            with tempfile.TemporaryDirectory(prefix="voxshield_audioset_") as tmp:
                tmpdir = Path(tmp)
                input_path = tmpdir / (Path(str(path)).name if path else "clip.audio")
                converted_path = tmpdir / "converted.wav"
                input_path.write_bytes(raw)
                audio, sample_rate = _decode_with_ffmpeg(input_path, converted_path, target_rate)
                return audio, sample_rate

    if path:
        input_path = Path(path)
        if input_path.exists():
            try:
                audio, sample_rate = sf.read(input_path, dtype="float32", always_2d=False)
                audio = to_mono(audio)
                return resample(audio, int(sample_rate), target_rate), target_rate
            except Exception:
                with tempfile.TemporaryDirectory(prefix="voxshield_audioset_") as tmp:
                    converted_path = Path(tmp) / "converted.wav"
                    audio, sample_rate = _decode_with_ffmpeg(input_path, converted_path, target_rate)
                    return audio, sample_rate

    raise RuntimeError("AudioSet row did not contain decodable audio bytes or a local audio path.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/external_audioset_targeted")
    parser.add_argument("--dataset", default="agkphysics/AudioSet")
    parser.add_argument("--subset", default="balanced")
    parser.add_argument("--split", default="train")
    parser.add_argument("--max-per-label", type=int, default=100)
    parser.add_argument("--max-total", type=int, default=800)
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--allow-speech", action="store_true")
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.jsonl"

    print(
        f"Streaming {args.dataset}/{args.subset}:{args.split}; "
        f"max_per_label={args.max_per_label}, max_total={args.max_total}"
    )
    dataset = load_dataset(args.dataset, args.subset, split=args.split, streaming=True)
    dataset = dataset.cast_column("audio", Audio(decode=False))

    counts: Counter[str] = Counter()
    total = 0
    with manifest_path.open("w", encoding="utf-8") as manifest:
        for row in dataset:
            human_labels = list(row.get("human_labels") or [])
            target = match_target(human_labels, args.allow_speech)
            if target is None or counts[target] >= args.max_per_label:
                continue

            audio_info = row["audio"]
            audio, sample_rate = decode_audio(audio_info, args.sample_rate)
            if audio.size == 0:
                continue

            video_id = slug(str(row.get("video_id") or f"{target}_{counts[target]:04d}"))
            out_path = output / target / f"{video_id}.wav"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(out_path, audio, sample_rate, subtype="PCM_16")

            record = {
                "path": str(out_path.as_posix()),
                "target": target,
                "video_id": row.get("video_id"),
                "human_labels": human_labels,
                "sample_rate": sample_rate,
                "seconds": round(float(len(audio) / sample_rate), 3),
            }
            manifest.write(json.dumps(record, ensure_ascii=False) + "\n")
            counts[target] += 1
            total += 1
            print(f"{total:04d} {target:10s} {out_path.name} {human_labels}")

            if total >= args.max_total:
                break
            if all(counts[target] >= args.max_per_label for target in TARGETS):
                break

    print(f"downloaded={total} counts={dict(counts)} manifest={manifest_path}")


if __name__ == "__main__":
    main()
