"""STOI envelope-correlation loss tests."""

import torch

from voxshield.losses import stoi_envelope_loss


def _signal(seconds: float = 2.0, seed: int = 0) -> torch.Tensor:
    generator = torch.Generator().manual_seed(seed)
    time = torch.arange(int(16000 * seconds), dtype=torch.float32) / 16000
    speech = 0.3 * torch.sin(2 * torch.pi * 220 * time) * (1 + 0.5 * torch.sin(2 * torch.pi * 3 * time))
    return (speech + 0.01 * torch.randn(speech.shape, generator=generator)).unsqueeze(0)


def test_identical_signal_has_zero_loss() -> None:
    audio = _signal()
    loss = stoi_envelope_loss(audio, audio.clone(), 16000)
    assert loss.item() < 0.01


def test_gain_scaled_signal_stays_low() -> None:
    """Correlation is gain-invariant, like STOI itself."""
    audio = _signal()
    loss = stoi_envelope_loss(audio * 0.5, audio, 16000)
    assert loss.item() < 0.05


def test_decorrelated_noise_scores_high() -> None:
    audio = _signal()
    generator = torch.Generator().manual_seed(99)
    noise = torch.randn(audio.shape, generator=generator) * 0.1
    loss = stoi_envelope_loss(noise, audio, 16000)
    assert loss.item() > 0.5


def test_time_shifted_signal_is_penalised() -> None:
    audio = _signal()
    shifted = torch.roll(audio, shifts=800, dims=-1)  # 50 ms lag
    loss = stoi_envelope_loss(shifted, audio, 16000)
    assert loss.item() > 0.1


def test_loss_is_differentiable_and_finite() -> None:
    audio = _signal()
    estimate = audio.clone().requires_grad_(True)
    loss = stoi_envelope_loss(estimate, audio, 16000)
    assert torch.isfinite(loss)
    loss.backward()
    assert torch.isfinite(estimate.grad).all()
    assert estimate.grad.abs().sum() > 0


def test_short_inputs_are_padded_safely() -> None:
    audio = _signal(0.1)
    loss = stoi_envelope_loss(audio, audio.clone(), 16000)
    assert torch.isfinite(loss)


def test_partly_silent_windows_have_finite_gradients() -> None:
    """Inactive zero-variance windows must not create 0 * NaN gradients."""
    target = torch.zeros(1, 32000)
    target[:, 8000:24000] = _signal(1.0)
    estimate = (target + 1e-4 * torch.randn_like(target)).requires_grad_(True)
    loss = stoi_envelope_loss(estimate, target, 16000)
    loss.backward()
    assert torch.isfinite(loss)
    assert torch.isfinite(estimate.grad).all()


def test_all_inactive_windows_return_differentiable_zero() -> None:
    estimate = torch.zeros(1, 8000, requires_grad=True)
    target = torch.zeros_like(estimate)
    loss = stoi_envelope_loss(estimate, target, 16000)
    loss.backward()
    assert loss.item() == 0.0
    assert torch.equal(estimate.grad, torch.zeros_like(estimate))
