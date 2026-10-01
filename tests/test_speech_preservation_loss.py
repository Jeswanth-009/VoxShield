import torch

from voxshield.losses import speech_spectral_hole_loss


def test_spectral_hole_penalizes_missing_active_speech():
    target = torch.ones(2, 16, 8, dtype=torch.complex64)
    matched = speech_spectral_hole_loss(target, target)
    attenuated = speech_spectral_hole_loss(target * 0.1, target)
    assert matched.item() == 0.0
    assert attenuated.item() > 1.0


def test_spectral_hole_does_not_penalize_extra_energy():
    target = torch.ones(1, 8, 4, dtype=torch.complex64)
    assert speech_spectral_hole_loss(target * 2.0, target).item() == 0.0
