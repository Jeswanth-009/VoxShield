import json
import random
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf
import torch
from torch.utils.data import DataLoader

from voxshield.data.dataset import RandomMixDataset, choose_noise_segment, mix_at_snr
from voxshield.hybrid_model import HybridDualChannelGTCRN
from voxshield.official_gtcrn import OfficialGTCRN
from voxshield.runtime import OutputConditioner, StreamingEnhancer
from voxshield.train import _initialize_fresh_model, _valid_amp_scaler_state


class IdentityRunner:
    def reset(self):
        pass

    def enhance(self, value):
        return value


def test_invalid_amp_scaler_state_is_not_silently_usable():
    """A zero scaler is exhausted and must never be treated as resumable."""
    assert not _valid_amp_scaler_state(None)
    assert not _valid_amp_scaler_state({"scale": 0.0})
    assert not _valid_amp_scaler_state({"scale": float("nan")})
    assert _valid_amp_scaler_state({"scale": 512.0})


def test_nonidentity_neural_outputs_match_frame_stream():
    torch.manual_seed(42)
    model = HybridDualChannelGTCRN(channels=8, recurrent_blocks=1).eval()
    with torch.no_grad():
        model.decoder_last.weight.normal_(0, 0.1)
        primary = torch.randn(1, 2, 257, 9)
        reference = torch.randn_like(primary)
        whole, final = model(primary, reference, model.initial_state(1))
        state = model.initial_state(1)
        frames = []
        for i in range(9):
            frame, state = model(primary[..., i:i+1], reference[..., i:i+1], state)
            frames.append(frame)
        assert not torch.allclose(whole, primary)
        torch.testing.assert_close(whole, torch.cat(frames, dim=-1), atol=2e-5, rtol=2e-5)
        torch.testing.assert_close(final, state, atol=2e-5, rtol=2e-5)


def test_silent_noise_is_not_accepted_as_noisy_training_data():
    with pytest.raises(ValueError, match='Silent noise'):
        mix_at_snr(np.ones(100, dtype=np.float32), np.zeros(100), -15)


def test_noise_crop_recovers_sparse_event():
    source = np.zeros(10000, dtype=np.float32)
    source[9990] = 0.5
    for seed in range(10):
        crop = choose_noise_segment(source, 200, random.Random(seed))
        assert len(crop) == 200
        assert crop.max() == 0.5


def test_required_military_validation_cannot_be_silently_absent(tmp_path):
    manifest = tmp_path / 'manifest.jsonl'
    manifest.write_text(json.dumps({'path': 'unused.wav', 'dataset': 'musan'}) + '\n')
    config = {'data': {
        'root': str(tmp_path), 'val_clean_manifest': str(manifest),
        'val_noise_manifests': {'stationary': str(manifest)},
        'required_validation_datasets': ['MAD_dataset'],
    }}
    with pytest.raises(ValueError, match='Missing required validation datasets'):
        RandomMixDataset(config, 'val')


def test_explicit_initialization_is_not_overwritten_by_pretrained(tmp_path):
    source = OfficialGTCRN()
    with torch.no_grad():
        next(source.parameters()).fill_(0.123)
    checkpoint = tmp_path / 'source.pt'
    torch.save({
        'config': {'model': {'architecture': 'official_gtcrn'}},
        'model': source.state_dict(),
    }, checkpoint)
    target = OfficialGTCRN()
    config = {
        'model': {
            'architecture': 'official_gtcrn',
            'initialize_from': str(checkpoint),
            'pretrained': 'must-not-be-loaded.pt',
        }
    }
    with patch('voxshield.train.load_official_weights') as pretrained_loader:
        _initialize_fresh_model(target, config, torch.device('cpu'))
    pretrained_loader.assert_not_called()
    torch.testing.assert_close(next(target.parameters()), next(source.parameters()))


def test_stream_reset_clears_conditioner_and_health():
    audio = np.random.default_rng(9).normal(0, 0.05, 4097).astype(np.float32)
    stream = StreamingEnhancer(IdentityRunner(), dc_blocker=True, deadline_fraction=float('inf'))
    first = np.concatenate([stream.process(audio), stream.flush()])
    stream.monitor.observe(0, False)
    stream.reset()
    second = np.concatenate([stream.process(audio), stream.flush()])
    np.testing.assert_array_equal(first, second)
    assert stream.monitor.status.failures == 0


def test_default_dry_roundtrip_preserves_low_frequency_voice():
    time = np.arange(16000) / 16000
    audio = (0.1 * np.sin(2 * np.pi * 90 * time)).astype(np.float32)
    stream = StreamingEnhancer(IdentityRunner(), wet_mix=0, deadline_fraction=float('inf'))
    output = np.concatenate([stream.process(audio), stream.flush()])
    np.testing.assert_allclose(output, audio, atol=1e-6)
    assert np.max(np.abs(OutputConditioner().process(np.array([2.0, np.nan])))) <= 0.98


def test_spawn_persistent_workers_observe_epoch_and_reproduce(tmp_path):
    path = tmp_path / 'speech.wav'
    sf.write(path, np.sin(np.arange(8000) * 0.08) * 0.1, 16000)
    manifest = tmp_path / 'manifest.jsonl'
    manifest.write_text(json.dumps({'path': str(path)}) + '\n')
    config = {
        'seed': 42,
        'audio': {'sample_rate': 16000, 'segment_seconds': 0.05},
        'data': {
            'root': str(tmp_path), 'train_clean_manifest': str(manifest),
            'train_noise_manifests': {'stationary': str(manifest)},
            'samples_per_epoch': 2, 'multichannel': False,
            'clean_probability': 1.0, 'clean_gain_db': [-12, 0],
        },
    }
    dataset = RandomMixDataset(config)
    loader = DataLoader(dataset, batch_size=2, num_workers=1,
                        persistent_workers=True, multiprocessing_context='spawn')
    first = next(iter(loader))['mixture'].clone()
    dataset.set_epoch(1)
    second = next(iter(loader))['mixture'].clone()
    assert not torch.equal(first, second)
    dataset.set_epoch(0)
    assert torch.equal(first, next(iter(loader))['mixture'])
