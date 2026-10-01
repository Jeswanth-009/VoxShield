from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torch.nn.functional as F
from scipy.signal import resample_poly


def read_audio(path: str | Path, sample_rate: int) -> np.ndarray:
    audio, source_rate = sf.read(str(path), dtype="float32", always_2d=True)
    audio = audio.mean(axis=1)
    if source_rate != sample_rate:
        divisor = math.gcd(source_rate, sample_rate)
        audio = resample_poly(audio, sample_rate // divisor, source_rate // divisor).astype(
            np.float32
        )
    return sanitize_audio(audio)


def write_audio(path: str | Path, audio: np.ndarray, sample_rate: int) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), sanitize_audio(audio), sample_rate, subtype="PCM_16")


def sanitize_audio(audio: np.ndarray, limit: float = 0.999) -> np.ndarray:
    result = np.nan_to_num(np.asarray(audio, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    return np.clip(result, -limit, limit)


def sqrt_hann(n_fft: int, *, device: torch.device | None = None) -> torch.Tensor:
    return torch.hann_window(n_fft, periodic=True, device=device).clamp_min(0).sqrt()


def frame_stft(waveform: torch.Tensor, n_fft: int, hop_length: int) -> torch.Tensor:
    """Causal, left-aligned WOLA analysis. Returns [batch, frequency, frames]."""
    if waveform.ndim == 1:
        waveform = waveform.unsqueeze(0)
    if waveform.ndim != 2:
        raise ValueError("waveform must have shape [samples] or [batch, samples]")
    left = n_fft - hop_length
    right = left
    total = waveform.shape[-1] + left + right
    extra = (hop_length - (total - n_fft) % hop_length) % hop_length
    padded = F.pad(waveform, (left, right + extra))
    frames = padded.unfold(-1, n_fft, hop_length)
    window = sqrt_hann(n_fft, device=waveform.device).to(waveform.dtype)
    return torch.fft.rfft(frames * window, n=n_fft, dim=-1).transpose(1, 2)


def frame_istft(
    spectrum: torch.Tensor, n_fft: int, hop_length: int, length: int
) -> torch.Tensor:
    """Weighted overlap-add inverse matching :func:`frame_stft`."""
    if spectrum.ndim != 3:
        raise ValueError("spectrum must have shape [batch, frequency, frames]")
    frames = torch.fft.irfft(spectrum.transpose(1, 2), n=n_fft, dim=-1)
    window = sqrt_hann(n_fft, device=spectrum.device).to(frames.dtype)
    weighted = (frames * window).transpose(1, 2)
    output_length = (frames.shape[1] - 1) * hop_length + n_fft
    output = F.fold(
        weighted,
        output_size=(1, output_length),
        kernel_size=(1, n_fft),
        stride=(1, hop_length),
    ).squeeze(1).squeeze(1)
    weights = window.square().view(1, n_fft, 1).expand(spectrum.shape[0], -1, frames.shape[1])
    denominator = F.fold(
        weights,
        output_size=(1, output_length),
        kernel_size=(1, n_fft),
        stride=(1, hop_length),
    ).squeeze(1).squeeze(1)
    output = output / denominator.clamp_min(1e-8)
    left = n_fft - hop_length
    return output[..., left : left + length]


def peak_normalize_pair(clean: np.ndarray, mixture: np.ndarray, peak: float = 0.95) -> tuple[np.ndarray, np.ndarray]:
    scale = peak / max(float(np.max(np.abs(clean))), float(np.max(np.abs(mixture))), peak)
    return (clean * scale).astype(np.float32), (mixture * scale).astype(np.float32)

