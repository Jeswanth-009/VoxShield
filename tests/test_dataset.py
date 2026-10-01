import json
import random
from argparse import Namespace
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from voxshield.data.dataset import (
    RandomMixDataset,
    choose_speech_segment,
    entry_sampling_weight,
    sample_weighted_snr,
)


def test_weighted_snr_sampler_can_force_hard_range() -> None:
    rng = random.Random(7)
    values = [
        sample_weighted_snr(
            rng,
            (-5.0, 5.0),
            [{"min": -20.0, "max": -15.0, "weight": 1.0}],
        )
        for _ in range(20)
    ]
    assert all(-20.0 <= value <= -15.0 for value in values)


def test_weighted_snr_sampler_rejects_bad_ranges() -> None:
    with pytest.raises(ValueError):
        sample_weighted_snr(
            random.Random(0),
            (-5.0, 5.0),
            [{"min": 2.0, "max": -2.0, "weight": 1.0}],
        )
from voxshield.data.index import make_fixed


def _write_manifest(path: Path, audio_path: Path, root: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"path": audio_path.relative_to(root).as_posix()}
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")


def test_curriculum_weight_multiplies_dataset_and_label_weights() -> None:
    entry = {"dataset": "MAD_dataset", "source_label": "gunshot"}
    weight = entry_sampling_weight(
        entry,
        {"mad_dataset": 4.0},
        {"GunShot": 2.5},
    )
    assert weight == 10.0


def test_curriculum_weight_matches_specific_uav_label() -> None:
    entry = {"dataset": "small_uav_acoustics", "source_label": "drone_uav_cub"}
    assert entry_sampling_weight(entry, {}, {"drone": 2.0}) == 2.0


def test_random_mix_is_reproducible_by_index(tmp_path: Path) -> None:
    sample_rate = 16000
    t = np.arange(sample_rate, dtype=np.float32) / sample_rate
    clean_path = tmp_path / "raw" / "clean.wav"
    noise_path = tmp_path / "raw" / "noise.wav"
    clean_path.parent.mkdir(parents=True)
    sf.write(clean_path, 0.1 * np.sin(2 * np.pi * 220 * t), sample_rate)
    sf.write(noise_path, 0.05 * np.sin(2 * np.pi * 997 * t), sample_rate)
    clean_manifest = tmp_path / "manifests" / "clean.jsonl"
    _write_manifest(clean_manifest, clean_path, tmp_path)
    noise_manifests = {}
    for category in ("stationary", "nonstationary", "impulsive", "environmental"):
        path = tmp_path / "manifests" / f"{category}.jsonl"
        _write_manifest(path, noise_path, tmp_path)
        noise_manifests[category] = str(path)
    config = {
        "seed": 12,
        "audio": {"sample_rate": sample_rate, "segment_seconds": 0.25},
        "data": {
            "root": str(tmp_path),
            "train_clean_manifest": str(clean_manifest),
            "train_noise_manifests": noise_manifests,
            "train_rir_manifest": str(tmp_path / "missing.jsonl"),
            "samples_per_epoch": 10,
            "snr_db": [-5.0, 5.0],
            "clean_gain_db": [-2.0, 0.0],
            "reverb_probability": 0.0,
            "multi_noise_probability": 0.2,
            "polarity_probability": 0.5,
            "spectral_tilt_probability": 0.2,
            "clipping_probability": 0.0,
            "clipping_threshold": [0.35, 0.95],
        },
    }
    dataset = RandomMixDataset(config, "train")
    first, repeated = dataset[3], dataset[3]
    assert np.array_equal(first["mixture"].numpy(), repeated["mixture"].numpy())
    assert first["mixture"].shape == first["clean"].shape == (4000,)
    assert np.isfinite(first["mixture"].numpy()).all()


def test_validation_curriculum_is_explicitly_opt_in(tmp_path: Path) -> None:
    sample_rate = 16000
    audio = np.zeros(sample_rate, dtype=np.float32)
    clean_path = tmp_path / "clean.wav"
    noise_path = tmp_path / "noise.wav"
    sf.write(clean_path, audio, sample_rate)
    sf.write(noise_path, audio, sample_rate)
    clean_manifest = tmp_path / "clean.jsonl"
    _write_manifest(clean_manifest, clean_path, tmp_path)
    noise_manifests = {}
    for category in ("stationary", "nonstationary", "impulsive", "environmental"):
        path = tmp_path / f"{category}.jsonl"
        path.write_text(
            json.dumps(
                {
                    "path": noise_path.relative_to(tmp_path).as_posix(),
                    "dataset": "MAD_dataset",
                    "source_label": "gunshot",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        noise_manifests[category] = str(path)
    config = {
        "seed": 1,
        "audio": {"sample_rate": sample_rate, "segment_seconds": 0.1},
        "data": {
            "root": str(tmp_path),
            "val_clean_manifest": str(clean_manifest),
            "val_noise_manifests": noise_manifests,
            "samples_per_epoch": 10,
            "validation_curriculum": True,
            "category_weights": {"impulsive": 2.5},
            "noise_dataset_weights": {"MAD_dataset": 4.0},
            "noise_label_weights": {"gunshot": 2.0},
        },
    }
    dataset = RandomMixDataset(config, "val")
    assert dataset.category_weights["impulsive"] == 2.5
    assert dataset.noise_sampling_weights["impulsive"] == [8.0]

    config["data"]["validation_curriculum"] = False
    unweighted = RandomMixDataset(config, "val")
    assert unweighted.category_weights == {}
    assert unweighted.noise_sampling_weights == {}


def test_short_speech_is_padded_once_not_tiled() -> None:
    source = np.arange(1, 9, dtype=np.float32)
    result = choose_speech_segment(source, 32, random.Random(3))
    assert result.shape == (32,)
    assert np.count_nonzero(result) <= len(source)
    assert np.max(result) <= np.max(source)


def test_clean_examples_teach_identity(tmp_path: Path) -> None:
    sample_rate = 16000
    source = (
        np.sin(2 * np.pi * 220 * np.arange(1000) / sample_rate).astype(np.float32) * 0.1
    )
    clean_path = tmp_path / "clean.wav"
    noise_path = tmp_path / "noise.wav"
    sf.write(clean_path, source, sample_rate)
    sf.write(noise_path, source, sample_rate)
    clean_manifest = tmp_path / "clean.jsonl"
    _write_manifest(clean_manifest, clean_path, tmp_path)
    noise_manifests = {}
    for category in ("stationary", "nonstationary", "impulsive", "environmental"):
        path = tmp_path / f"{category}.jsonl"
        _write_manifest(path, noise_path, tmp_path)
        noise_manifests[category] = str(path)
    config = {
        "seed": 1,
        "audio": {"sample_rate": sample_rate, "segment_seconds": 0.1},
        "data": {
            "root": str(tmp_path),
            "train_clean_manifest": str(clean_manifest),
            "train_noise_manifests": noise_manifests,
            "train_rir_manifest": str(tmp_path / "missing.jsonl"),
            "samples_per_epoch": 2,
            "clean_gain_db": [0.0, 0.0],
            "clean_probability": 1.0,
            "near_clean_probability": 0.0,
            "reverb_probability": 0.0,
        },
    }
    item = RandomMixDataset(config, "train")[0]
    assert item["category"] == "clean"
    assert np.array_equal(item["mixture"].numpy(), item["clean"].numpy())


def test_make_fixed_can_isolate_one_noise_dataset(tmp_path: Path) -> None:
    sample_rate = 16000
    time = np.arange(sample_rate, dtype=np.float32) / sample_rate
    clean_path = tmp_path / "clean.wav"
    mad_path = tmp_path / "mad.wav"
    other_path = tmp_path / "other.wav"
    sf.write(clean_path, 0.1 * np.sin(2 * np.pi * 220 * time), sample_rate)
    sf.write(mad_path, 0.1 * np.sin(2 * np.pi * 700 * time), sample_rate)
    sf.write(other_path, 0.1 * np.sin(2 * np.pi * 900 * time), sample_rate)
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    (manifests / "clean_test.jsonl").write_text(
        json.dumps({"path": str(clean_path)}) + "\n", encoding="utf-8"
    )
    for category in ("stationary", "nonstationary", "impulsive", "environmental"):
        rows = [
            {
                "path": str(other_path),
                "dataset": "other",
                "source_label": "other",
            }
        ]
        if category == "impulsive":
            rows.append(
                {
                    "path": str(mad_path),
                    "dataset": "MAD_dataset",
                    "source_label": "gunshot",
                }
            )
        (manifests / f"noise_{category}_test.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
    make_fixed(
        Namespace(
            data_root=str(tmp_path), split="test", noise_dataset="mad_dataset",
            output_dir=str(tmp_path / "mixtures" / "mad"), seed=9, count=6,
            seconds=0.1, sample_rate=sample_rate, clean_fraction=1 / 6,
            near_clean_fraction=1 / 6, snr_min=-5.0, snr_max=5.0,
            near_clean_snr_min=25.0, near_clean_snr_max=30.0,
        )
    )
    rows = [
        json.loads(line)
        for line in (tmp_path / "mixtures" / "mad" / "manifest.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    noisy = [row for row in rows if row["category"] != "clean"]
    assert noisy
    assert {row["noise_dataset"] for row in noisy} == {"MAD_dataset"}
    assert {row["noise_source_label"] for row in noisy} == {"gunshot"}
    assert all("other.wav" not in str(row["noise_source_path"]) for row in noisy)
