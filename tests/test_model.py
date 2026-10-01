import torch

from voxshield.losses import EnhancementLoss
from voxshield.model import CausalComplexMaskNet


def _config() -> dict:
    return {
        "audio": {"n_fft": 512, "hop_length": 128, "sample_rate": 16000},
        "model": {
            "channels": 8,
            "recurrent_blocks": 1,
            "min_mask_gain": 0.05,
            "max_mask_gain": 1.25,
        },
        "loss": {
            "si_snr": 1.0,
            "snr": 0.5,
            "multi_resolution_stft": 0.5,
            "complex_l1": 0.25,
            "waveform_l1": 0.5,
            "stft_resolutions": [[256, 64], [512, 128]],
        },
    }


def test_fresh_model_is_identity_like() -> None:
    model = CausalComplexMaskNet.from_config(_config()).eval()
    value = torch.randn(2, 2, 257, 7)
    state = model.initial_state(2)
    output, _ = model(value, state)
    assert torch.allclose(output, value, atol=1e-6, rtol=1e-6)


def test_full_sequence_equals_stateful_frames() -> None:
    torch.manual_seed(4)
    model = CausalComplexMaskNet.from_config(_config()).eval()
    with torch.no_grad():
        model.decoder_last.weight.normal_(0.0, 0.02)
        model.decoder_last.bias.normal_(0.0, 0.02)
    value = torch.randn(1, 2, 257, 9)
    whole, whole_state = model(value, model.initial_state(1))
    state = model.initial_state(1)
    pieces = []
    for frame in value.split(1, dim=-1):
        output, state = model(frame, state)
        pieces.append(output)
    assert torch.allclose(whole, torch.cat(pieces, dim=-1), atol=2e-5, rtol=2e-5)
    assert torch.allclose(whole_state, state, atol=2e-5, rtol=2e-5)


def test_training_objective_backpropagates() -> None:
    torch.manual_seed(2)
    config = _config()
    model = CausalComplexMaskNet.from_config(config)
    criterion = EnhancementLoss(config)
    noisy = torch.randn(2, 2048) * 0.1
    clean = noisy * 0.8
    estimate, spectrum = model.forward_audio(noisy, 128)
    loss, components = criterion(estimate, clean, spectrum)
    loss.backward()
    assert torch.isfinite(loss)
    assert all(torch.isfinite(value) for value in components.values())
    assert model.decoder_last.weight.grad is not None
    assert torch.isfinite(model.decoder_last.weight.grad).all()
