"""Diagnostics for synchronized primary/reference microphone recordings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from scipy.signal import coherence, correlate, correlation_lags, resample_poly

from .audio import sanitize_audio


def _dbfs(value: float, eps: float = 1e-12) -> float:
    return float(20.0 * np.log10(max(float(value), eps)))


def _channel_stats(audio: np.ndarray) -> dict[str, float]:
    audio64 = np.asarray(audio, dtype=np.float64)
    return {
        "rms_dbfs": _dbfs(np.sqrt(np.mean(audio64**2))),
        "peak_dbfs": _dbfs(np.max(np.abs(audio64))),
        "dc_offset": float(np.mean(audio64)),
        "clipping_fraction": float(np.mean(np.abs(audio64) >= 0.995)),
    }


def _lag_and_correlation(
    primary: np.ndarray,
    reference: np.ndarray,
    sample_rate: int,
    maximum_lag_ms: float,
) -> tuple[int, float]:
    limit = min(len(primary), len(reference), sample_rate * 30)
    if limit < 32:
        return 0, 0.0
    primary64 = np.asarray(primary[:limit], dtype=np.float64)
    reference64 = np.asarray(reference[:limit], dtype=np.float64)
    primary64 -= np.mean(primary64)
    reference64 -= np.mean(reference64)
    denominator = np.linalg.norm(primary64) * np.linalg.norm(reference64)
    if denominator < 1e-12:
        return 0, 0.0
    maximum_lag = max(1, round(sample_rate * maximum_lag_ms / 1000.0))
    values = correlate(primary64, reference64, mode="full", method="fft")
    lags = correlation_lags(len(primary64), len(reference64), mode="full")
    allowed = np.abs(lags) <= maximum_lag
    local_values = values[allowed]
    local_lags = lags[allowed]
    index = int(np.argmax(np.abs(local_values)))
    return int(local_lags[index]), float(local_values[index] / denominator)


def dual_channel_diagnostics(
    primary: np.ndarray,
    reference: np.ndarray,
    sample_rate: int,
    maximum_lag_ms: float = 20.0,
) -> dict[str, Any]:
    """Return bounded engineering diagnostics without claiming ground-truth quality."""
    primary = sanitize_audio(np.asarray(primary, dtype=np.float32).reshape(-1))
    reference = sanitize_audio(np.asarray(reference, dtype=np.float32).reshape(-1))
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if len(primary) != len(reference) or not len(primary):
        raise ValueError("primary and reference must be equal-length, non-empty arrays")
    lag_samples, peak_correlation = _lag_and_correlation(
        primary, reference, sample_rate, maximum_lag_ms
    )
    segment_length = min(len(primary), sample_rate * 60)
    nperseg = min(1024, segment_length)
    speech_band_coherence: float | None = None
    if nperseg >= 64:
        frequencies, coherence_values = coherence(
            primary[:segment_length],
            reference[:segment_length],
            fs=sample_rate,
            nperseg=nperseg,
        )
        speech_band = (frequencies >= 300.0) & (frequencies <= 3400.0)
        if np.any(speech_band):
            speech_band_coherence = float(np.nanmean(coherence_values[speech_band]))
    primary_stats = _channel_stats(primary)
    reference_stats = _channel_stats(reference)
    warnings: list[str] = []
    if primary_stats["rms_dbfs"] < -60.0:
        warnings.append("primary channel is nearly silent")
    if reference_stats["rms_dbfs"] < -60.0:
        warnings.append("reference channel is nearly silent")
    if primary_stats["clipping_fraction"] > 1e-4:
        warnings.append("primary channel contains clipped samples")
    if reference_stats["clipping_fraction"] > 1e-4:
        warnings.append("reference channel contains clipped samples")
    if abs(peak_correlation) >= 0.995:
        warnings.append("channels are effectively identical; verify channel routing")
    possible_leakage = bool(
        speech_band_coherence is not None
        and speech_band_coherence >= 0.85
        and abs(peak_correlation) >= 0.75
    )
    if possible_leakage:
        warnings.append(
            "high speech-band similarity may indicate target-speech leakage; verify with a "
            "speech-only calibration recording"
        )
    sync_evidence = (
        "correlated"
        if abs(peak_correlation) >= 0.10
        else "inconclusive_from_audio_content"
    )
    return {
        "sample_rate": int(sample_rate),
        "samples": len(primary),
        "duration_seconds": float(len(primary) / sample_rate),
        "primary": primary_stats,
        "reference": reference_stats,
        "estimated_relative_lag_samples": lag_samples,
        "estimated_relative_lag_ms": float(1000.0 * lag_samples / sample_rate),
        "peak_signed_correlation": peak_correlation,
        "speech_band_coherence": speech_band_coherence,
        "possible_target_speech_leakage": possible_leakage,
        "synchronization_evidence": sync_evidence,
        "warnings": warnings,
        "note": (
            "Correlation cannot prove a shared hardware clock. Long recordings and device "
            "metadata are required to assess drift."
        ),
    }


def read_dual_channel_file(
    path: str | Path,
    primary_channel: int = 0,
    reference_channel: int = 1,
    target_sample_rate: int | None = None,
) -> tuple[np.ndarray, np.ndarray, int]:
    audio, sample_rate = sf.read(str(path), dtype="float32", always_2d=True)
    if primary_channel < 0 or reference_channel < 0:
        raise ValueError("channel indices cannot be negative")
    if primary_channel == reference_channel:
        raise ValueError("primary and reference channels must be different")
    required_channels = max(primary_channel, reference_channel) + 1
    if audio.shape[1] < required_channels:
        raise ValueError(
            f"file has {audio.shape[1]} channels but channel {required_channels - 1} was requested"
        )
    primary = audio[:, primary_channel]
    reference = audio[:, reference_channel]
    if target_sample_rate is not None and sample_rate != target_sample_rate:
        divisor = np.gcd(sample_rate, target_sample_rate)
        primary = resample_poly(primary, target_sample_rate // divisor, sample_rate // divisor)
        reference = resample_poly(reference, target_sample_rate // divisor, sample_rate // divisor)
        sample_rate = target_sample_rate
    return sanitize_audio(primary), sanitize_audio(reference), int(sample_rate)
