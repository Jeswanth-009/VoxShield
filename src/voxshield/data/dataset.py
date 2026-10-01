from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

import numpy as np
import torch
from scipy.signal import fftconvolve, lfilter
from torch.utils.data import Dataset

from ..audio import peak_normalize_pair, read_audio


def load_manifest(path: str | Path, *, required: bool = True) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Manifest not found: {path}. Run `voxshield-data index` first.")
        return []
    with path.open("r", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    if required and not rows:
        raise ValueError(f"Manifest is empty: {path}")
    return rows


def _resolve(data_root: Path, entry: dict[str, Any]) -> Path:
    path = Path(entry["path"])
    return path if path.is_absolute() else data_root / path


def _resolve_mixture_path(data_root: Path, entry: dict[str, Any], key: str) -> Path:
    path = Path(entry[key])
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == "mixtures":
        return data_root / path
    return data_root / "mixtures" / path


def _fit_length(audio: np.ndarray, length: int, rng: random.Random) -> np.ndarray:
    audio = np.asarray(audio, dtype=np.float32)
    if len(audio) == length:
        return audio.copy()
    if len(audio) < length:
        output = np.zeros(length, dtype=np.float32)
        offset = rng.randint(0, length - len(audio))
        output[offset : offset + len(audio)] = audio
        return output
    start = rng.randint(0, len(audio) - length)
    return audio[start : start + length].copy()


def choose_noise_segment(audio: np.ndarray, length: int, rng: random.Random) -> np.ndarray:
    if len(audio) == 0:
        raise ValueError("Encountered an empty audio file")
    if len(audio) < length:
        audio = np.tile(audio, math.ceil(length / len(audio)))
    start = rng.randint(0, max(0, len(audio) - length))
    if np.max(np.abs(audio[start : start + length])) <= 1e-8:
        peak = int(np.argmax(np.abs(audio)))
        start = min(max(0, peak - length // 2), max(0, len(audio) - length))
    return audio[start : start + length].copy()


def choose_speech_segment(
    audio: np.ndarray,
    length: int,
    rng: random.Random,
    candidates: int = 8,
) -> np.ndarray:
    """Choose an active speech crop without ever repeating an utterance."""
    audio = np.asarray(audio, dtype=np.float32)
    if len(audio) == 0:
        raise ValueError("Encountered an empty audio file")
    if len(audio) <= length:
        output = np.zeros(length, dtype=np.float32)
        offset = rng.randint(0, length - len(audio))
        source = audio.copy()
        # Fade joins that touch synthetic silence so non-zero corpus edges do
        # not create clicks. Unlike tiling, the utterance appears exactly once.
        fade = min(max(1, length // 400), len(source) // 4)
        if fade:
            ramp = np.linspace(0.0, 1.0, fade, endpoint=False, dtype=np.float32)
            source[:fade] *= ramp
            source[-fade:] *= ramp[::-1]
        output[offset : offset + len(source)] = source
        return output

    best: np.ndarray | None = None
    best_score = -1.0
    for _ in range(max(1, candidates)):
        start = rng.randint(0, len(audio) - length)
        candidate = audio[start : start + length]
        # Prefer speech-active regions without letting one transient dominate.
        score = float(np.mean(np.sqrt(np.abs(candidate).astype(np.float64))))
        if score > best_score:
            best, best_score = candidate, score
    assert best is not None
    return best.copy()


def _delay_signal(audio: np.ndarray, samples: int) -> np.ndarray:
    """Delay (or advance) a signal without wrapping samples around the edges."""
    output = np.zeros_like(audio)
    if samples >= 0:
        if samples < len(audio):
            output[samples:] = audio[: len(audio) - samples]
    elif -samples < len(audio):
        output[:samples] = audio[-samples:]
    return output


def _impulsive_segment(
    audio: np.ndarray,
    length: int,
    rng: random.Random,
    activity: np.ndarray | None = None,
) -> np.ndarray:
    """Place isolated events, preferentially overlapping active speech.

    Copying an entire long gunshot/shelling recording into every segment turns
    an impulsive class into stationary noise.  Restrict each event to at most a
    quarter of the training segment and place it near speech whenever possible.
    """
    output = np.zeros(length, dtype=np.float32)
    event_length = min(len(audio), max(256, length // 4))
    if event_length == 0:
        raise ValueError("Encountered an empty impulsive-noise file")
    active_positions = np.empty(0, dtype=np.int64)
    if activity is not None and len(activity):
        threshold = max(float(np.max(np.abs(activity))) * 0.08, 1e-4)
        active_positions = np.flatnonzero(np.abs(activity) >= threshold)
    for _ in range(rng.randint(1, 3)):
        # Long event recordings often contain seconds of silence. Select the
        # most active of several deterministic candidate crops so a nominal
        # gunshot/shelling example cannot silently become a clean example.
        best_source_start = 0
        best_source_score = -1.0
        for _candidate in range(8):
            candidate_start = rng.randint(0, max(0, len(audio) - event_length))
            candidate = audio[candidate_start : candidate_start + event_length]
            candidate_score = float(
                np.mean(np.sqrt(np.abs(candidate).astype(np.float64)))
            )
            if candidate_score > best_source_score:
                best_source_start = candidate_start
                best_source_score = candidate_score
        if best_source_score <= 1e-8:
            peak = int(np.argmax(np.abs(audio)))
            best_source_start = min(
                max(0, peak - event_length // 2),
                max(0, len(audio) - event_length),
            )
        if len(active_positions):
            centre = int(active_positions[rng.randrange(len(active_positions))])
            jitter = rng.randint(-event_length // 4, event_length // 4)
            target_start = min(
                max(0, centre + jitter - event_length // 2),
                max(0, length - event_length),
            )
        else:
            target_start = rng.randint(0, max(0, length - event_length))
        output[target_start : target_start + event_length] += audio[
            best_source_start : best_source_start + event_length
        ]
    return output


def _active_rms(audio: np.ndarray, eps: float = 1e-7) -> float:
    threshold = max(float(np.max(np.abs(audio))) * 0.05, 1e-4)
    active = audio[np.abs(audio) >= threshold]
    source = active if len(active) else audio
    return float(np.sqrt(np.mean(source.astype(np.float64) ** 2) + eps))


def _spectral_tilt(audio: np.ndarray, rng: random.Random) -> np.ndarray:
    coefficient = rng.uniform(-0.65, 0.65)
    return lfilter([1.0, -coefficient], [1.0], audio).astype(np.float32)


def mix_at_snr(clean: np.ndarray, noise: np.ndarray, snr_db: float) -> tuple[np.ndarray, np.ndarray]:
    if not np.isfinite(clean).all() or not np.isfinite(noise).all():
        raise ValueError("Non-finite mixture source; inspect the dataset")
    if np.max(np.abs(noise)) <= 1e-8:
        raise ValueError("Silent noise source cannot create a labelled noisy example")
    if np.max(np.abs(clean)) <= 1e-8:
        raise ValueError("Silent speech source cannot create a speech-enhancement pair")
    clean_rms = _active_rms(clean)
    noise_rms = _active_rms(noise)
    scaled_noise = noise * (clean_rms / (noise_rms * (10.0 ** (snr_db / 20.0))))
    mixture = clean + scaled_noise
    clean, mixture = peak_normalize_pair(clean, mixture)
    return clean, mixture


def entry_sampling_weight(
    entry: dict[str, Any],
    dataset_weights: dict[str, float] | None = None,
    label_weights: dict[str, float] | None = None,
) -> float:
    """Return a transparent curriculum weight for one manifest row."""
    dataset_weights = {str(key).lower(): float(value) for key, value in (dataset_weights or {}).items()}
    label_weights = {str(key).lower(): float(value) for key, value in (label_weights or {}).items()}
    dataset = str(entry.get("dataset") or "").lower()
    label = str(entry.get("source_label") or "").lower()
    label_weight = label_weights.get(label)
    if label_weight is None:
        matching = [value for key, value in label_weights.items() if key and key in label]
        label_weight = max(matching, default=1.0)
    weight = dataset_weights.get(dataset, 1.0) * label_weight
    if not np.isfinite(weight) or weight <= 0.0:
        raise ValueError("noise curriculum weights must be finite and positive")
    return weight


def sample_weighted_snr(
    rng: random.Random,
    default_range: tuple[float, float] | list[float],
    weighted_ranges: list[dict[str, Any]] | None = None,
) -> float:
    """Sample SNR from an explicit mixture of ranges.

    A single uniform range under-samples the extremely-low-SNR tail that
    dominates the defence failures.  Recipes may therefore provide entries
    such as ``{min: -20, max: -8, weight: 3}`` without duplicating audio.
    """
    if not weighted_ranges:
        return rng.uniform(float(default_range[0]), float(default_range[1]))
    weights: list[float] = []
    for item in weighted_ranges:
        low, high = float(item["min"]), float(item["max"])
        weight = float(item.get("weight", 1.0))
        if not np.isfinite(low) or not np.isfinite(high) or low > high:
            raise ValueError("each snr_sampling_ranges entry needs finite min <= max")
        if not np.isfinite(weight) or weight <= 0.0:
            raise ValueError("each snr_sampling_ranges weight must be finite and positive")
        weights.append(weight)
    selected = rng.choices(weighted_ranges, weights=weights, k=1)[0]
    return rng.uniform(float(selected["min"]), float(selected["max"]))


class RandomMixDataset(Dataset[dict[str, Any]]):
    """Deterministic-by-index, on-the-fly clean/noise mixture generator."""

    def __init__(self, config: dict[str, Any], split: str = "train") -> None:
        self.config = config
        self.split = split
        self.data_root = Path(config["data"]["root"])
        clean_key = f"{split}_clean_manifest"
        noise_key = f"{split}_noise_manifests"
        self.clean = load_manifest(config["data"][clean_key])
        self.noise = {
            category: load_manifest(path)
            for category, path in config["data"][noise_key].items()
        }
        if split == 'val':
            present = {str(row.get('dataset', '')).casefold()
                       for entries in self.noise.values() for row in entries}
            required = {str(name).casefold() for name in
                        config['data'].get('required_validation_datasets', [])}
            if required - present:
                raise ValueError(f"Missing required validation datasets: {sorted(required - present)}")
        rir_path = config["data"].get(f"{split}_rir_manifest")
        self.rirs = load_manifest(rir_path, required=False) if rir_path else []
        hard_path = config["data"].get(f"{split}_hard_mix_manifest")
        self.hard_mixes = load_manifest(hard_path, required=False) if hard_path else []
        self.hard_mix_probability = (
            float(config["data"].get("hard_mix_probability", 0.0))
            if split == "train"
            else 0.0
        )
        self.sample_rate = int(config["audio"]["sample_rate"])
        self.length = round(config["audio"]["segment_seconds"] * self.sample_rate)
        self.size = int(config["data"]["samples_per_epoch"])
        self.seed = int(config.get("seed", 0)) + (0 if split == "train" else 10_000_000)
        self.multichannel = bool(config["data"].get("multichannel", False))
        # Training always follows the configured sampling curriculum.  A
        # defence fine-tune may opt its deterministic validation distribution
        # into the same weights so checkpoint selection measures the domain
        # the stage is intended to improve.  Test/frozen-pair evaluation is
        # never affected by this option.
        curriculum_enabled = split == "train" or (
            split == "val"
            and bool(config["data"].get("validation_curriculum", False))
        )
        self.category_weights = (
            {
                str(key): float(value)
                for key, value in config["data"].get("category_weights", {}).items()
            }
            if curriculum_enabled
            else {}
        )
        self.noise_dataset_weights = (
            config["data"].get("noise_dataset_weights", {}) if curriculum_enabled else {}
        )
        self.noise_label_weights = (
            config["data"].get("noise_label_weights", {}) if curriculum_enabled else {}
        )
        self.noise_sampling_weights = {
            category: [
                entry_sampling_weight(
                    entry,
                    self.noise_dataset_weights,
                    self.noise_label_weights,
                )
                for entry in entries
            ]
            for category, entries in self.noise.items()
        } if (self.noise_dataset_weights or self.noise_label_weights) else {}
        # Workers retain Dataset copies when persistent_workers=True. Shared
        # storage makes set_epoch visible to Windows spawn workers as well.
        self._epoch = torch.zeros((), dtype=torch.int64).share_memory_()

    @property
    def epoch(self) -> int:
        return int(self._epoch.item())

    def set_epoch(self, epoch: int) -> None:
        self._epoch.fill_(int(epoch))

    def __len__(self) -> int:
        return self.size if self.split == "train" else min(self.size // 10, 2000)

    def _load(
        self,
        entries: list[dict[str, Any]],
        rng: random.Random,
        *,
        curriculum: bool = False,
        sampling_weights: list[float] | None = None,
    ) -> np.ndarray:
        if curriculum and (self.noise_dataset_weights or self.noise_label_weights):
            if sampling_weights is None or len(sampling_weights) != len(entries):
                raise ValueError("cached curriculum weights do not match manifest entries")
            entry = rng.choices(entries, weights=sampling_weights, k=1)[0]
        else:
            entry = entries[rng.randrange(len(entries))]
        return read_audio(_resolve(self.data_root, entry), self.sample_rate)

    def _choose_category(self, rng: random.Random) -> str:
        categories = sorted(self.noise)
        weights = [self.category_weights.get(category, 1.0) for category in categories]
        if any(not np.isfinite(weight) or weight <= 0.0 for weight in weights):
            raise ValueError("category_weights must be finite and positive")
        return rng.choices(categories, weights=weights, k=1)[0]

    def _reference_channel(
        self,
        clean: np.ndarray,
        primary_noise: np.ndarray,
        rng: random.Random,
    ) -> np.ndarray:
        """Simulate an external reference microphone from known components.

        This is deliberately conservative: the reference mostly contains the
        environmental noise but includes realistic speech leakage, gain error,
        delay, response mismatch and microphone self-noise.  Recorded,
        synchronized target-domain channels can later replace this simulation
        without changing the model interface.
        """
        data = self.config["data"]
        delay_min, delay_max = data.get("interchannel_delay_samples", (-16, 16))
        delay = rng.randint(int(delay_min), int(delay_max))
        noise_gain_db = rng.uniform(*data.get("reference_noise_gain_db", (-6.0, 6.0)))
        speech_leak_db = rng.uniform(*data.get("reference_speech_leak_db", (-35.0, -12.0)))
        reference_noise = _delay_signal(primary_noise, delay)
        if rng.random() < data.get("reference_tilt_probability", 0.5):
            reference_noise = _spectral_tilt(reference_noise, rng)
        reference = (
            reference_noise * (10.0 ** (noise_gain_db / 20.0))
            + _delay_signal(clean, delay) * (10.0 ** (speech_leak_db / 20.0))
        )
        self_noise_db = rng.uniform(*data.get("reference_self_noise_snr_db", (35.0, 55.0)))
        reference_rms = max(_active_rms(reference), 1e-5)
        self_noise = np.random.default_rng(rng.getrandbits(64)).standard_normal(
            len(reference), dtype=np.float32
        )
        self_noise *= reference_rms / (
            max(_active_rms(self_noise), 1e-7) * (10.0 ** (self_noise_db / 20.0))
        )
        return (reference + self_noise).astype(np.float32)

    @staticmethod
    def _joint_peak_normalize(
        clean: np.ndarray,
        primary: np.ndarray,
        reference: np.ndarray,
        peak: float = 0.95,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        maximum = max(
            float(np.max(np.abs(clean))),
            float(np.max(np.abs(primary))),
            float(np.max(np.abs(reference))),
            peak,
        )
        scale = peak / maximum
        return tuple(
            np.asarray(value * scale, dtype=np.float32)
            for value in (clean, primary, reference)
        )

    def _hard_mix_item(self, rng: random.Random) -> dict[str, Any]:
        row = self.hard_mixes[rng.randrange(len(self.hard_mixes))]
        clean = _fit_length(
            read_audio(_resolve_mixture_path(self.data_root, row, "clean"), self.sample_rate),
            self.length,
            rng,
        )
        mixture = _fit_length(
            read_audio(_resolve_mixture_path(self.data_root, row, "noisy"), self.sample_rate),
            self.length,
            rng,
        )
        clean, mixture = peak_normalize_pair(clean, mixture)
        item = {
            "mixture": torch.from_numpy(mixture),
            "clean": torch.from_numpy(clean),
            "snr_db": torch.tensor(float(row.get("snr_db", 0.0)), dtype=torch.float32),
            "category": str(row.get("category", "hard")),
            "clipped": False,
        }
        if self.multichannel:
            if row.get("reference"):
                reference = _fit_length(
                    read_audio(
                        _resolve_mixture_path(self.data_root, row, "reference"),
                        self.sample_rate,
                    ),
                    self.length,
                    rng,
                )
                clean, mixture, reference = self._joint_peak_normalize(
                    clean, mixture, reference
                )
                item["mixture"] = torch.from_numpy(mixture)
                item["clean"] = torch.from_numpy(clean)
                item["reference"] = torch.from_numpy(reference)
                item["primary_noise"] = torch.from_numpy(
                    (mixture - clean).astype(np.float32)
                )
            else:
                primary_noise = (mixture - clean).astype(np.float32)
                reference = self._reference_channel(clean, primary_noise, rng)
                clean, mixture, reference = self._joint_peak_normalize(
                    clean, mixture, reference
                )
                item["mixture"] = torch.from_numpy(mixture)
                item["clean"] = torch.from_numpy(clean)
                item["reference"] = torch.from_numpy(reference)
                item["primary_noise"] = torch.from_numpy(primary_noise)
        return item

    def __getitem__(self, index: int) -> dict[str, Any]:
        rng = random.Random(self.seed + self.epoch * self.size + index)
        if (
            self.hard_mixes
            and self.hard_mix_probability > 0.0
            and rng.random() < self.hard_mix_probability
        ):
            return self._hard_mix_item(rng)
        clean = choose_speech_segment(self._load(self.clean, rng), self.length, rng)
        gain_db = rng.uniform(*self.config["data"]["clean_gain_db"])
        clean *= 10.0 ** (gain_db / 20.0)
        if self.rirs and rng.random() < self.config["data"]["reverb_probability"]:
            rir = self._load(self.rirs, rng)
            rir = rir[: min(len(rir), self.sample_rate)]
            rir = rir / max(np.sqrt(np.sum(rir.astype(np.float64) ** 2)), 1e-8)
            clean = fftconvolve(clean, rir, mode="full")[: self.length].astype(np.float32)
        clean_probability = float(self.config["data"].get("clean_probability", 0.0))
        near_clean_probability = float(
            self.config["data"].get("near_clean_probability", 0.0)
        )
        mode = rng.random()
        if mode < clean_probability:
            clean, mixture = peak_normalize_pair(clean, clean.copy())
            item = {
                "mixture": torch.from_numpy(mixture),
                "clean": torch.from_numpy(clean),
                "snr_db": torch.tensor(60.0, dtype=torch.float32),
                "category": "clean",
                "clipped": False,
            }
            if self.multichannel:
                reference = self._reference_channel(clean, np.zeros_like(clean), rng)
                clean, mixture, reference = self._joint_peak_normalize(
                    clean, mixture, reference
                )
                item["mixture"] = torch.from_numpy(mixture)
                item["clean"] = torch.from_numpy(clean)
                item["reference"] = torch.from_numpy(reference)
                item["primary_noise"] = torch.zeros_like(item["clean"])
            return item

        last_mix_error: ValueError | None = None
        for _attempt in range(16):
            category = self._choose_category(rng)
            source_noise = self._load(
                self.noise[category],
                rng,
                curriculum=True,
                sampling_weights=self.noise_sampling_weights.get(category),
            )
            noise = (
                _impulsive_segment(source_noise, self.length, rng, clean)
                if category == "impulsive"
                else choose_noise_segment(source_noise, self.length, rng)
            )
            if rng.random() < self.config["data"]["multi_noise_probability"]:
                second_category = self._choose_category(rng)
                second = choose_noise_segment(
                    self._load(
                        self.noise[second_category],
                        rng,
                        curriculum=True,
                        sampling_weights=self.noise_sampling_weights.get(second_category),
                    ),
                    self.length,
                    rng,
                )
                noise = noise + rng.uniform(0.1, 0.7) * second
                category = f"{category}+{second_category}"
            if rng.random() < self.config["data"]["spectral_tilt_probability"]:
                noise = _spectral_tilt(noise, rng)
            if rng.random() < self.config["data"]["polarity_probability"]:
                noise = -noise
            near_clean = mode < clean_probability + near_clean_probability
            snr_range = (
                self.config["data"].get("near_clean_snr_db", (25.0, 40.0))
                if near_clean
                else self.config["data"]["snr_db"]
            )
            snr_db = sample_weighted_snr(
                rng,
                snr_range,
                None if near_clean else self.config["data"].get("snr_sampling_ranges"),
            )
            output_category = f"near_clean:{category}" if near_clean else category
            try:
                clean, mixture = mix_at_snr(clean, noise, snr_db)
                category = output_category
                break
            except ValueError as exc:
                message = str(exc).lower()
                if "silent noise" not in message and "non-finite" not in message:
                    raise
                last_mix_error = exc
        else:
            raise ValueError(
                "Could not draw a valid noisy training example after 16 attempts"
            ) from last_mix_error
        primary_noise = (mixture - clean).astype(np.float32)
        reference = None
        if self.multichannel:
            reference = self._reference_channel(clean, primary_noise, rng)
            clean, mixture, reference = self._joint_peak_normalize(
                clean, mixture, reference
            )
            primary_noise = (mixture - clean).astype(np.float32)
        clipped = False
        if rng.random() < self.config["data"].get("clipping_probability", 0.0):
            threshold = rng.uniform(*self.config["data"].get("clipping_threshold", (0.35, 0.95)))
            mixture = np.clip(mixture, -threshold, threshold).astype(np.float32)
            if reference is not None:
                reference = np.clip(reference, -threshold, threshold).astype(np.float32)
            clipped = True
        item = {
            "mixture": torch.from_numpy(mixture),
            "clean": torch.from_numpy(clean),
            "snr_db": torch.tensor(snr_db, dtype=torch.float32),
            "category": category,
            "clipped": clipped,
        }
        if reference is not None:
            item["reference"] = torch.from_numpy(reference)
            item["primary_noise"] = torch.from_numpy(primary_noise)
        return item
