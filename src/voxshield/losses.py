from __future__ import annotations

import math
from typing import Any

import torch
import torch.nn.functional as F
from torch import nn

from .audio import frame_stft


def si_snr_loss(
    estimate: torch.Tensor,
    target: torch.Tensor,
    eps: float = 1e-8,
    max_db: float = 30.0,
) -> torch.Tensor:
    estimate = estimate - estimate.mean(dim=-1, keepdim=True)
    target = target - target.mean(dim=-1, keepdim=True)
    projection = (estimate * target).sum(dim=-1, keepdim=True) * target
    projection = projection / target.square().sum(dim=-1, keepdim=True).clamp_min(eps)
    noise = estimate - projection
    ratio = projection.square().sum(dim=-1) / noise.square().sum(dim=-1).clamp_min(eps)
    ratio = ratio.clamp(min=eps, max=10.0 ** (max_db / 10.0))
    return -10.0 * torch.log10(ratio).mean()


def snr_loss(
    estimate: torch.Tensor,
    target: torch.Tensor,
    eps: float = 1e-8,
    max_db: float = 30.0,
) -> torch.Tensor:
    """Scale-sensitive SNR loss used to prevent gain-changing shortcuts."""
    signal = target.square().sum(dim=-1)
    error = (target - estimate).square().sum(dim=-1)
    ratio = ((signal + eps) / (error + eps)).clamp(
        min=eps, max=10.0 ** (max_db / 10.0)
    )
    return -10.0 * torch.log10(ratio).mean()


def spectral_convergence(estimate: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    difference = torch.linalg.vector_norm(target.abs() - estimate.abs(), dim=(-2, -1))
    reference = torch.linalg.vector_norm(target.abs(), dim=(-2, -1)).clamp_min(1e-8)
    return (difference / reference).mean()


def clean_identity_loss(
    estimate: torch.Tensor,
    mixture: torch.Tensor,
    preservation_mask: torch.Tensor | None,
) -> torch.Tensor:
    """Penalize modifying clean/near-clean examples.

    The mask is supplied by the dataset category, so genuinely noisy examples
    are not encouraged to copy their input.
    """
    if preservation_mask is None or not bool(preservation_mask.any()):
        return estimate.new_zeros(())
    difference = (estimate - mixture).abs().mean(dim=-1)
    reference = mixture.abs().mean(dim=-1).clamp_min(1e-4)
    return (difference[preservation_mask] / reference[preservation_mask]).mean()


def preservation_snr_loss(
    estimate: torch.Tensor,
    mixture: torch.Tensor,
    preservation_mask: torch.Tensor | None,
) -> torch.Tensor:
    """Maximize fidelity to the input only for clean and near-clean examples."""
    if preservation_mask is None or not bool(preservation_mask.any()):
        return estimate.new_zeros(())
    return snr_loss(
        estimate[preservation_mask],
        mixture[preservation_mask],
        max_db=40.0,
    )


def spectral_delta_loss(
    estimate: torch.Tensor,
    target: torch.Tensor,
) -> torch.Tensor:
    """Preserve spectral motion and formant-envelope changes.

    Matching first differences discourages isolated time-frequency holes and
    the slowly varying comb-like coloration commonly perceived as robotic.
    """
    estimate_log = torch.log1p(estimate.abs())
    target_log = torch.log1p(target.abs())
    terms: list[torch.Tensor] = []
    if estimate_log.shape[-1] > 1:
        terms.append(
            (
                torch.diff(estimate_log, dim=-1)
                - torch.diff(target_log, dim=-1)
            ).abs().mean()
        )
    if estimate_log.shape[-2] > 1:
        terms.append(
            (
                torch.diff(estimate_log, dim=-2)
                - torch.diff(target_log, dim=-2)
            ).abs().mean()
        )
    return torch.stack(terms).mean() if terms else estimate_log.new_zeros(())


def speech_spectral_hole_loss(
    estimate: torch.Tensor,
    target: torch.Tensor,
    tolerance_db: float = 3.0,
    active_fraction: float = 0.05,
) -> torch.Tensor:
    """Penalize missing target-speech energy without rewarding residual noise.

    A symmetric spectral distance can be reduced by attenuating uncertain bins,
    which sounds like holes or robotic speech at very low SNR.  This asymmetric
    term acts only on speech-active target frames and only when the estimate is
    below the clean target by more than ``tolerance_db``.
    """
    estimate_mag = estimate.abs().clamp_min(1e-7)
    target_mag = target.abs().clamp_min(1e-7)
    frame_rms = target_mag.square().mean(dim=-2).sqrt()
    active = frame_rms >= (
        frame_rms.amax(dim=-1, keepdim=True) * float(active_fraction)
    ).clamp_min(1e-5)
    log_tolerance = float(tolerance_db) * torch.log(target_mag.new_tensor(10.0)) / 20.0
    missing = torch.relu(torch.log(target_mag) - torch.log(estimate_mag) - log_tolerance)
    weights = target_mag.pow(0.3)
    weights = weights / weights.mean(dim=(-2, -1), keepdim=True).clamp_min(1e-6)
    active_bins = active.unsqueeze(-2).expand_as(missing)
    return (missing * weights * active_bins).sum() / (
        (weights * active_bins).sum().clamp_min(1.0)
    )


def phase_consistency_loss(
    estimate: torch.Tensor,
    target: torch.Tensor,
    eps: float = 1e-8,
) -> torch.Tensor:
    """Magnitude-weighted circular phase error without unstable angle wrapping."""
    estimate_mag = estimate.abs()
    target_mag = target.abs()
    cosine = (
        estimate.real * target.real + estimate.imag * target.imag
    ) / (estimate_mag * target_mag).clamp_min(eps)
    weights = target_mag / target_mag.mean(dim=(-2, -1), keepdim=True).clamp_min(eps)
    weights = weights.clamp(max=5.0)
    return ((1.0 - cosine.clamp(-1.0, 1.0)) * weights).mean()


def clean_spectral_identity_loss(
    estimate: torch.Tensor,
    mixture: torch.Tensor,
    preservation_mask: torch.Tensor | None,
) -> torch.Tensor:
    """Penalize magnitude and phase coloration on clean/near-clean inputs."""
    if preservation_mask is None or not bool(preservation_mask.any()):
        return estimate.real.new_zeros(())
    estimate = estimate[preservation_mask]
    mixture = mixture[preservation_mask]
    log_magnitude = (
        torch.log1p(estimate.abs()) - torch.log1p(mixture.abs())
    ).abs().mean()
    phase = phase_consistency_loss(estimate, mixture)
    return log_magnitude + 0.25 * phase


def speech_retention_loss(
    estimate: torch.Tensor,
    target: torch.Tensor,
    sample_rate: int,
    frame_ms: float = 20.0,
    max_attenuation_db: float = 12.0,
) -> torch.Tensor:
    """Penalize catastrophic short-time attenuation during active speech."""
    frame = max(16, round(sample_rate * frame_ms / 1000.0))
    hop = max(8, frame // 2)
    if estimate.shape[-1] < frame:
        pad = frame - estimate.shape[-1]
        estimate = torch.nn.functional.pad(estimate, (0, pad))
        target = torch.nn.functional.pad(target, (0, pad))
    estimate_frames = estimate.unfold(-1, frame, hop)
    target_frames = target.unfold(-1, frame, hop)
    estimate_rms = estimate_frames.square().mean(dim=-1).add(1e-8).sqrt()
    target_rms = target_frames.square().mean(dim=-1).add(1e-8).sqrt()
    active_threshold = torch.maximum(
        target_rms.amax(dim=-1, keepdim=True) * 0.05,
        target_rms.new_tensor(1e-4),
    )
    active = target_rms >= active_threshold
    attenuation_db = 20.0 * torch.log10(target_rms / estimate_rms.clamp_min(1e-6))
    excess = torch.relu(attenuation_db - float(max_attenuation_db))
    return (excess * active).sum() / active.sum().clamp_min(1)


def stoi_envelope_loss(
    estimate: torch.Tensor,
    target: torch.Tensor,
    sample_rate: int,
    n_fft: int = 512,
    hop_length: int = 256,
    bands: int = 8,
    window_ms: float = 384.0,
    low_hz: float = 150.0,
    high_hz: float = 8000.0,
    eps: float = 1e-8,
) -> torch.Tensor:
    """Differentiable STOI-style envelope-correlation loss.

    STOI measures intelligibility as the short-time correlation between
    third-octave temporal envelopes of clean and processed speech.  This term
    mirrors that structure: log-spaced band envelopes are compared by Pearson
    correlation over ~384 ms windows, and the loss is ``1 - correlation``.
    Unlike the magnitude losses, it is explicitly insensitive to per-band gain
    and directly targets the intelligibility metric used by the quality gate.
    Windows whose target envelope is near-silent are excluded so silence does
    not dilute the term.

    Computed in fp32 with autocast disabled: squaring STFT magnitudes
    overflows fp16 for loud clips (65504 ceiling), which otherwise produces
    inf/NaN under mixed-precision training.
    """
    with torch.autocast(device_type=estimate.device.type, enabled=False):
        estimate = estimate.float()
        target = target.float()
        estimate_spec = frame_stft(estimate, n_fft, hop_length).abs()
        target_spec = frame_stft(target, n_fft, hop_length).abs()
    n_freq = estimate_spec.shape[-2]
    freqs = torch.linspace(0.0, sample_rate / 2.0, n_freq, device=estimate_spec.device)
    edges = torch.logspace(
        math.log10(low_hz), math.log10(high_hz), bands + 1, device=estimate_spec.device
    )
    estimate_bands = []
    target_bands = []
    for index in range(bands):
        mask = (freqs >= edges[index]) & (freqs < edges[index + 1])
        if not bool(mask.any()):
            continue
        # Clamp band energy before sqrt for the same reason as the correlation
        # denominator below: sqrt has an infinite derivative at exactly zero.
        estimate_energy = estimate_spec[..., mask, :].square().mean(dim=-2).clamp_min(eps)
        target_energy = target_spec[..., mask, :].square().mean(dim=-2).clamp_min(eps)
        estimate_bands.append(estimate_energy.sqrt())
        target_bands.append(target_energy.sqrt())
    estimate_env = torch.stack(estimate_bands, dim=1)  # (B, bands, T)
    target_env = torch.stack(target_bands, dim=1)

    window = max(4, round(sample_rate * window_ms / 1000.0 / hop_length))
    stride = max(1, window // 2)
    if estimate_env.shape[-1] < window:
        pad = window - estimate_env.shape[-1]
        estimate_env = F.pad(estimate_env, (0, pad))
        target_env = F.pad(target_env, (0, pad))
    estimate_windows = estimate_env.unfold(-1, window, stride)  # (B, bands, W, window)
    target_windows = target_env.unfold(-1, window, stride)

    active = target_windows.std(dim=-1) > 1e-5
    active = active & (estimate_windows.std(dim=-1) > 1e-7)
    if not bool(active.any()):
        # Keep a zero-gradient connection to the estimate so this loss remains
        # safe when it is used alone in diagnostics or future recipes.
        return estimate_env.sum() * 0.0

    estimate_centred = estimate_windows - estimate_windows.mean(dim=-1, keepdim=True)
    target_centred = target_windows - target_windows.mean(dim=-1, keepdim=True)
    numerator = (estimate_centred * target_centred).sum(dim=-1)
    # Clamp each energy before sqrt.  Clamping only after sqrt leaves an
    # infinite derivative at zero-variance (inactive) windows; multiplying
    # those entries by a false mask later can then produce 0 * NaN gradients.
    estimate_energy = estimate_centred.square().sum(dim=-1).clamp_min(eps)
    target_energy = target_centred.square().sum(dim=-1).clamp_min(eps)
    denominator = torch.sqrt(estimate_energy * target_energy)
    correlation = (numerator / denominator).clamp(-1.0, 1.0)
    loss = (1.0 - correlation) * active
    return loss.sum() / active.sum().clamp_min(1)


class EnhancementLoss(nn.Module):
    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__()
        self.weights = config["loss"]
        self.n_fft = config["audio"]["n_fft"]
        self.hop = config["audio"]["hop_length"]
        self.sample_rate = int(config["audio"]["sample_rate"])
        self.kind = self.weights.get("type", "legacy")

    def _target_spectrum(self, target: torch.Tensor) -> torch.Tensor:
        if self.kind != "gtcrn_hybrid":
            return frame_stft(target, self.n_fft, self.hop)
        window = torch.hann_window(
            self.n_fft, periodic=True, device=target.device, dtype=target.dtype
        ).sqrt()
        return torch.stft(
            target,
            self.n_fft,
            self.hop,
            self.n_fft,
            window,
            return_complex=True,
            center=True,
        )

    def forward(
        self,
        estimate_audio: torch.Tensor,
        target_audio: torch.Tensor,
        estimate_spectrum: torch.Tensor,
        *,
        mixture_audio: torch.Tensor | None = None,
        preservation_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        target_spectrum = self._target_spectrum(target_audio)
        if self.kind == "gtcrn_hybrid":
            return self._gtcrn_hybrid(
                estimate_audio,
                target_audio,
                estimate_spectrum,
                target_spectrum,
                mixture_audio,
                preservation_mask,
            )
        complex_l1 = (
            (estimate_spectrum.real - target_spectrum.real).abs().mean()
            + (estimate_spectrum.imag - target_spectrum.imag).abs().mean()
        )
        multi_stft = estimate_audio.new_zeros(())
        for n_fft, hop in self.weights["stft_resolutions"]:
            est = frame_stft(estimate_audio, int(n_fft), int(hop))
            ref = frame_stft(target_audio, int(n_fft), int(hop))
            log_mag = (torch.log1p(est.abs()) - torch.log1p(ref.abs())).abs().mean()
            multi_stft = multi_stft + log_mag + spectral_convergence(est, ref)
        multi_stft = multi_stft / len(self.weights["stft_resolutions"])
        sisnr = si_snr_loss(estimate_audio, target_audio)
        scale_snr = snr_loss(estimate_audio, target_audio)
        waveform_l1 = (
            (estimate_audio - target_audio).abs().mean(dim=-1)
            / target_audio.abs().mean(dim=-1).clamp_min(1e-4)
        ).mean()
        identity = clean_identity_loss(
            estimate_audio,
            estimate_audio if mixture_audio is None else mixture_audio,
            preservation_mask,
        )
        retention = speech_retention_loss(
            estimate_audio,
            target_audio,
            self.sample_rate,
            float(self.weights.get("retention_frame_ms", 20.0)),
            float(self.weights.get("retention_max_attenuation_db", 12.0)),
        )
        preservation_snr = estimate_audio.new_zeros(())
        clean_spectral_identity = estimate_audio.new_zeros(())
        mixture_spectrum = None
        if mixture_audio is not None and (
            self.weights.get("preservation_snr", 0.0)
            or self.weights.get("clean_spectral_identity", 0.0)
        ):
            preservation_snr = preservation_snr_loss(
                estimate_audio, mixture_audio, preservation_mask
            )
            mixture_spectrum = self._target_spectrum(mixture_audio)
            clean_spectral_identity = clean_spectral_identity_loss(
                estimate_spectrum, mixture_spectrum, preservation_mask
            )
        spectral_delta = spectral_delta_loss(estimate_spectrum, target_spectrum)
        phase_consistency = phase_consistency_loss(estimate_spectrum, target_spectrum)
        spectral_hole = speech_spectral_hole_loss(
            estimate_spectrum,
            target_spectrum,
            float(self.weights.get("spectral_hole_tolerance_db", 3.0)),
        )
        stoi_envelope = stoi_envelope_loss(estimate_audio, target_audio, self.sample_rate)
        total = (
            self.weights["si_snr"] * sisnr
            + self.weights.get("snr", 0.0) * scale_snr
            + self.weights["multi_resolution_stft"] * multi_stft
            + self.weights["complex_l1"] * complex_l1
            + self.weights.get("waveform_l1", 0.0) * waveform_l1
            + self.weights.get("clean_identity", 0.0) * identity
            + self.weights.get("speech_retention", 0.0) * retention
            + self.weights.get("preservation_snr", 0.0) * preservation_snr
            + self.weights.get("clean_spectral_identity", 0.0)
            * clean_spectral_identity
            + self.weights.get("spectral_delta", 0.0) * spectral_delta
            + self.weights.get("phase_consistency", 0.0) * phase_consistency
            + self.weights.get("spectral_hole", 0.0) * spectral_hole
            + self.weights.get("stoi_envelope", 0.0) * stoi_envelope
        )
        return total, {
            "total": total,
            "si_snr": sisnr,
            "snr": scale_snr,
            "mrstft": multi_stft,
            "complex": complex_l1,
            "waveform_l1": waveform_l1,
            "clean_identity": identity,
            "speech_retention": retention,
            "preservation_snr": preservation_snr,
            "clean_spectral_identity": clean_spectral_identity,
            "spectral_delta": spectral_delta,
            "phase_consistency": phase_consistency,
            "spectral_hole": spectral_hole,
            "stoi_envelope": stoi_envelope,
        }

    def _gtcrn_hybrid(
        self,
        estimate_audio: torch.Tensor,
        target_audio: torch.Tensor,
        estimate_spectrum: torch.Tensor,
        target_spectrum: torch.Tensor,
        mixture_audio: torch.Tensor | None,
        preservation_mask: torch.Tensor | None,
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        """Power-compressed complex/magnitude objective from the official GTCRN recipe."""
        eps = 1e-12
        power = float(self.weights.get("compression_power", 0.3))
        estimate_mag = estimate_spectrum.abs().clamp_min(eps)
        target_mag = target_spectrum.abs().clamp_min(eps)
        # z / |z|^(1-p) preserves phase while compressing magnitude to |z|^p.
        estimate_compressed = estimate_spectrum / estimate_mag.pow(1.0 - power)
        target_compressed = target_spectrum / target_mag.pow(1.0 - power)
        compressed_complex = (
            (estimate_compressed.real - target_compressed.real).square().mean()
            + (estimate_compressed.imag - target_compressed.imag).square().mean()
        )
        compressed_magnitude = (
            estimate_mag.pow(power) - target_mag.pow(power)
        ).square().mean()
        sisnr = si_snr_loss(estimate_audio, target_audio)
        scale_snr = snr_loss(estimate_audio, target_audio)
        waveform_l1 = (
            (estimate_audio - target_audio).abs().mean(dim=-1)
            / target_audio.abs().mean(dim=-1).clamp_min(1e-4)
        ).mean()
        identity = clean_identity_loss(
            estimate_audio,
            estimate_audio if mixture_audio is None else mixture_audio,
            preservation_mask,
        )
        retention = speech_retention_loss(
            estimate_audio,
            target_audio,
            self.sample_rate,
            float(self.weights.get("retention_frame_ms", 20.0)),
            float(self.weights.get("retention_max_attenuation_db", 12.0)),
        )
        preservation_snr = estimate_audio.new_zeros(())
        clean_spectral_identity = estimate_audio.new_zeros(())
        if mixture_audio is not None and (
            self.weights.get("preservation_snr", 0.0)
            or self.weights.get("clean_spectral_identity", 0.0)
        ):
            preservation_snr = preservation_snr_loss(
                estimate_audio, mixture_audio, preservation_mask
            )
            mixture_spectrum = self._target_spectrum(mixture_audio)
            clean_spectral_identity = clean_spectral_identity_loss(
                estimate_spectrum, mixture_spectrum, preservation_mask
            )
        spectral_delta = spectral_delta_loss(estimate_spectrum, target_spectrum)
        phase_consistency = phase_consistency_loss(estimate_spectrum, target_spectrum)
        spectral_hole = speech_spectral_hole_loss(
            estimate_spectrum,
            target_spectrum,
            float(self.weights.get("spectral_hole_tolerance_db", 3.0)),
        )
        stoi_envelope = stoi_envelope_loss(estimate_audio, target_audio, self.sample_rate)
        total = (
            float(self.weights.get("compressed_complex", 30.0)) * compressed_complex
            + float(self.weights.get("compressed_magnitude", 70.0)) * compressed_magnitude
            + float(self.weights.get("si_snr", 0.1)) * sisnr
            + float(self.weights.get("snr", 0.1)) * scale_snr
            + float(self.weights.get("waveform_l1", 0.2)) * waveform_l1
            + float(self.weights.get("clean_identity", 0.0)) * identity
            + float(self.weights.get("speech_retention", 0.0)) * retention
            + float(self.weights.get("preservation_snr", 0.0)) * preservation_snr
            + float(self.weights.get("clean_spectral_identity", 0.0))
            * clean_spectral_identity
            + float(self.weights.get("spectral_delta", 0.0)) * spectral_delta
            + float(self.weights.get("phase_consistency", 0.0)) * phase_consistency
            + float(self.weights.get("spectral_hole", 0.0)) * spectral_hole
            + float(self.weights.get("stoi_envelope", 0.0)) * stoi_envelope
        )
        return total, {
            "total": total,
            "compressed_complex": compressed_complex,
            "compressed_magnitude": compressed_magnitude,
            "si_snr": sisnr,
            "snr": scale_snr,
            "waveform_l1": waveform_l1,
            "clean_identity": identity,
            "speech_retention": retention,
            "preservation_snr": preservation_snr,
            "clean_spectral_identity": clean_spectral_identity,
            "spectral_delta": spectral_delta,
            "phase_consistency": phase_consistency,
            "spectral_hole": spectral_hole,
            "stoi_envelope": stoi_envelope,
        }
