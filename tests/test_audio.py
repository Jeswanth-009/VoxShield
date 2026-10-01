import numpy as np
import torch

from voxshield.audio import frame_istft, frame_stft, sanitize_audio


def test_wola_round_trip() -> None:
    torch.manual_seed(0)
    audio = torch.randn(2, 16037) * 0.1
    spectrum = frame_stft(audio, 512, 128)
    reconstructed = frame_istft(spectrum, 512, 128, audio.shape[-1])
    assert reconstructed.shape == audio.shape
    assert torch.max(torch.abs(reconstructed - audio)).item() < 2e-5


def test_sanitize_non_finite_and_clip() -> None:
    value = sanitize_audio(np.array([np.nan, np.inf, -np.inf, 2.0, -2.0], np.float32))
    assert np.isfinite(value).all()
    assert np.max(np.abs(value)) <= 0.999

