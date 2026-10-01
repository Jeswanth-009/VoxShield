import json
import random
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from voxshield.config import load_config
from voxshield.data.dataset import RandomMixDataset, _impulsive_segment
from voxshield.hybrid_model import HybridDualChannelGTCRN
from voxshield.losses import (
    phase_consistency_loss,
    preservation_snr_loss,
    spectral_delta_loss,
    speech_retention_loss,
)
from voxshield.train import _selection_score


def _config(tmp_path: Path) -> dict:
    sample_rate = 16000
    time = np.arange(sample_rate, dtype=np.float32) / sample_rate
    clean_path = tmp_path / "clean.wav"
    noise_path = tmp_path / "noise.wav"
    sf.write(clean_path, 0.1 * np.sin(2 * np.pi * 220 * time), sample_rate)
    sf.write(noise_path, 0.1 * np.sin(2 * np.pi * 700 * time), sample_rate)
    clean_manifest = tmp_path / "clean.jsonl"
    clean_manifest.write_text(json.dumps({"path": str(clean_path)}) + "\n")
    noise_manifests = {}
    for category in ("stationary", "nonstationary", "impulsive", "environmental"):
        manifest = tmp_path / f"{category}.jsonl"
        manifest.write_text(json.dumps({"path": str(noise_path)}) + "\n")
        noise_manifests[category] = str(manifest)
    return {
        "seed": 7,
        "audio": {"sample_rate": 16000, "n_fft": 512, "hop_length": 128,
                  "segment_seconds": 0.25},
        "model": {"architecture": "hybrid_dual_gtcrn", "channels": 8,
                  "recurrent_blocks": 1, "min_mask_gain": 0.08,
                  "max_mask_gain": 1.2, "preserve_bias": 2.0},
        "data": {"root": str(tmp_path), "multichannel": True,
                 "train_clean_manifest": str(clean_manifest),
                 "train_noise_manifests": noise_manifests,
                 "samples_per_epoch": 8, "snr_db": [-5.0, 5.0],
                 "clean_gain_db": [-2.0, 0.0], "clean_probability": 0.0,
                 "near_clean_probability": 0.0, "reverb_probability": 0.0,
                 "multi_noise_probability": 0.0, "spectral_tilt_probability": 0.0,
                 "polarity_probability": 0.0, "clipping_probability": 0.0,
                 "interchannel_delay_samples": [-4, 4]},
        "runtime": {},
    }


def test_multichannel_dataset_is_deterministic(tmp_path: Path) -> None:
    dataset = RandomMixDataset(_config(tmp_path), "train")
    first, repeated = dataset[2], dataset[2]
    assert first["reference"].shape == first["mixture"].shape == first["clean"].shape
    assert torch.equal(first["reference"], repeated["reference"])
    assert not torch.equal(first["reference"], first["mixture"])


def test_impulse_is_placed_over_active_speech() -> None:
    activity = np.zeros(4000, dtype=np.float32)
    activity[1800:2200] = 1.0
    impulse = np.ones(4000, dtype=np.float32)
    result = _impulsive_segment(impulse, 4000, random.Random(3), activity)
    assert np.any(result[1300:2700] != 0)
    assert np.count_nonzero(result) < len(result)


def test_impulse_crop_does_not_select_only_silence() -> None:
    activity = np.ones(4000, dtype=np.float32)
    impulse = np.zeros(32000, dtype=np.float32)
    impulse[30000:30100] = 1.0
    result = _impulsive_segment(impulse, 4000, random.Random(11), activity)
    assert np.max(np.abs(result)) == 1.0


def test_fresh_dual_model_is_identity_and_streamable() -> None:
    torch.manual_seed(4)
    model = HybridDualChannelGTCRN(channels=8, recurrent_blocks=1).eval()
    primary = torch.randn(1, 2, 257, 7)
    reference = torch.randn_like(primary)
    state = model.initial_state(1)
    whole, whole_state = model(primary, reference, state)
    assert torch.allclose(whole, primary, atol=1e-6, rtol=1e-6)
    pieces = []
    state = model.initial_state(1)
    for primary_frame, reference_frame in zip(
        primary.split(1, dim=-1), reference.split(1, dim=-1)
    ):
        output, state = model(primary_frame, reference_frame, state)
        pieces.append(output)
    assert torch.allclose(whole, torch.cat(pieces, dim=-1), atol=2e-5, rtol=2e-5)
    assert torch.allclose(whole_state, state, atol=2e-5, rtol=2e-5)


def test_retention_loss_detects_speech_deletion() -> None:
    target = torch.ones(2, 1600) * 0.1
    preserved = speech_retention_loss(target, target, 16000)
    deleted = speech_retention_loss(torch.zeros_like(target), target, 16000)
    assert preserved == 0
    assert deleted > 20


def test_preservation_and_spectral_losses_reward_identity() -> None:
    torch.manual_seed(9)
    waveform = torch.randn(2, 1600) * 0.1
    mask = torch.tensor([True, False])
    preserved = preservation_snr_loss(waveform, waveform, mask)
    distorted = preservation_snr_loss(waveform * 0.5, waveform, mask)
    assert preserved < distorted

    spectrum = torch.stft(
        waveform,
        256,
        64,
        window=torch.hann_window(256),
        return_complex=True,
    )
    assert spectral_delta_loss(spectrum, spectrum) < 1e-7
    assert phase_consistency_loss(spectrum, spectrum) < 1e-6
    assert phase_consistency_loss(-spectrum, spectrum) > 0.1


def test_preservation_aware_selection_score() -> None:
    metrics = {
        "total": -20.0,
        "clean_identity": 0.04,
        "preservation_snr": -22.0,
    }
    config = {
        "train": {
            "selection_weights": {
                "total": 1.0,
                "clean_identity": 2.0,
                "preservation_snr": 0.1,
            }
        }
    }
    assert _selection_score(metrics, config) == -22.12


def test_v4_config_loads() -> None:
    config = load_config(Path(__file__).parents[1] / "configs" / "hybrid_v4.yaml")
    assert config["model"]["architecture"] == "hybrid_dual_gtcrn"
    assert config["data"]["multichannel"] is True


def test_v4_staged_curriculum_configs_load() -> None:
    root = Path(__file__).parents[1] / "configs"
    stage1 = load_config(root / "hybrid_v4_stage1_broad.yaml")
    preserve = load_config(root / "hybrid_v4_stage1_preserve.yaml")
    preserve_smoke = load_config(root / "hybrid_v4_preserve_smoke.yaml")
    stage2 = load_config(root / "hybrid_v4_stage2_defence.yaml")
    stage2_gate = load_config(root / "hybrid_v4_stage2_gate.yaml")
    stage2_continue = load_config(root / "hybrid_v4_stage2_continue.yaml")
    stage2b_gate = load_config(root / "hybrid_v4_stage2b_gate.yaml")
    stage2b_continue = load_config(root / "hybrid_v4_stage2b_continue.yaml")
    stage3 = load_config(root / "hybrid_v4_stage3_target.yaml")
    assert stage1["model"].get("initialize_from") is None
    assert preserve["model"]["initialize_from"] == "checkpoints_v4_stage1/best.pt"
    assert preserve["runtime"]["wet_mix"] == 0.9
    assert preserve_smoke["data"]["samples_per_epoch"] == 16
    HybridDualChannelGTCRN.from_config(preserve)
    assert stage2["model"]["initialize_from"] == "checkpoints_v4_preserve/best.pt"
    assert stage2["data"]["noise_dataset_weights"]["MAD_dataset"] == 4.0
    assert stage2["data"]["clean_probability"] == 0.25
    assert stage2["data"]["near_clean_probability"] == 0.20
    assert stage2["data"]["validation_curriculum"] is True
    assert stage2["loss"]["preservation_snr"] > 0.0
    assert stage2["loss"]["clean_spectral_identity"] > 0.0
    assert stage2["runtime"]["wet_mix"] == 0.9
    assert stage2_gate["train"]["epochs"] == 3
    assert stage2_gate["train"]["checkpoint_dir"] == "checkpoints_v4_stage2"
    assert stage2_continue["model"].get("initialize_from") is None
    assert stage2_continue["train"]["epochs"] == 25
    assert stage2b_gate["model"]["initialize_from"] == "checkpoints_v4_stage2/best.pt"
    assert stage2b_gate["data"]["clean_probability"] == 0.20
    assert stage2b_gate["data"]["near_clean_probability"] == 0.15
    assert stage2b_gate["train"]["checkpoint_dir"] == "checkpoints_v4_stage2b"
    assert stage2b_continue["model"].get("initialize_from") is None
    assert stage2b_continue["train"]["epochs"] == 25
    assert stage3["model"]["initialize_from"] == "checkpoints_v4_stage2b/best.pt"
