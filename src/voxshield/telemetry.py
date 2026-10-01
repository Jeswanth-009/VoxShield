"""Small, atomic telemetry snapshots for the local engineering dashboard."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np


def _level(audio: np.ndarray, eps: float = 1e-12) -> dict[str, float]:
    value = np.asarray(audio, dtype=np.float64)
    return {
        "rms_dbfs": float(20.0 * np.log10(max(float(np.sqrt(np.mean(value**2))), eps))),
        "peak_dbfs": float(20.0 * np.log10(max(float(np.max(np.abs(value))), eps))),
    }


def _signal_analysis(
    primary: np.ndarray,
    reference: np.ndarray,
    enhanced: np.ndarray,
    *,
    sample_rate: int,
    n_fft: int,
) -> dict[str, Any]:
    primary64 = np.asarray(primary, dtype=np.float64).reshape(-1)
    enhanced64 = np.asarray(enhanced, dtype=np.float64).reshape(-1)
    peak = float(np.max(np.abs(primary64))) if len(primary64) else 0.0
    rms = float(np.sqrt(np.mean(primary64**2))) if len(primary64) else 0.0
    spectrum = np.abs(np.fft.rfft(np.pad(enhanced64[-n_fft:], (max(0, n_fft-len(enhanced64)), 0))))
    frequencies = np.fft.rfftfreq(n_fft, 1.0 / sample_rate)
    total = float(np.sum(spectrum))
    centroid = float(np.sum(frequencies * spectrum) / max(total, 1e-12))
    dominant = float(frequencies[int(np.argmax(spectrum))]) if len(spectrum) else 0.0
    power = spectrum**2
    total_power = float(np.sum(power))
    bands = {
        "sub_bass": (0, 250), "speech_low": (250, 800), "speech_core": (800, 2000),
        "speech_high": (2000, 4000), "presence": (4000, 6000), "air": (6000, 8000),
    }
    band_energy = {
        name: float(100.0 * np.sum(power[(frequencies >= lo) & (frequencies < hi)]) / max(total_power, 1e-12))
        for name, (lo, hi) in bands.items()
    }
    relation = _channel_relationship(primary, reference)
    correlation = abs(float(relation["zero_lag_correlation"]))
    leakage = "HIGH" if correlation >= 0.90 else "MODERATE" if correlation >= 0.65 else "LOW"
    return {
        "dominant_frequency_hz": dominant,
        "spectral_centroid_hz": centroid,
        "primary_crest_factor_db": float(20.0 * np.log10(max(peak, 1e-12) / max(rms, 1e-12))),
        "clipped_samples": int(np.count_nonzero(np.abs(primary64) >= 0.98)),
        "speech_activity": bool(rms >= 10 ** (-48.0 / 20.0)),
        "reference_leakage_risk": leakage,
        "band_energy_percent": band_energy,
    }


def _spectrum(audio: np.ndarray, n_fft: int) -> list[float]:
    value = np.asarray(audio, dtype=np.float32).reshape(-1)
    frame = np.zeros(n_fft, dtype=np.float32)
    copied = min(len(value), n_fft)
    frame[-copied:] = value[-copied:]
    magnitude = np.abs(np.fft.rfft(frame * np.hanning(n_fft))) / max(n_fft / 2.0, 1.0)
    return np.maximum(20.0 * np.log10(np.maximum(magnitude, 1e-8)), -120.0).tolist()


def _waveform(audio: np.ndarray, points: int = 192) -> list[float]:
    value = np.asarray(audio, dtype=np.float32).reshape(-1)
    if not len(value):
        return [0.0] * points
    indices = np.linspace(0, len(value) - 1, points).astype(np.int64)
    return value[indices].astype(float).tolist()


def _channel_relationship(primary: np.ndarray, reference: np.ndarray) -> dict[str, Any]:
    primary64 = np.asarray(primary, dtype=np.float64).reshape(-1)
    reference64 = np.asarray(reference, dtype=np.float64).reshape(-1)
    primary64 = primary64 - np.mean(primary64)
    reference64 = reference64 - np.mean(reference64)
    primary_rms = float(np.sqrt(np.mean(primary64**2)))
    reference_rms = float(np.sqrt(np.mean(reference64**2)))
    denominator = float(np.linalg.norm(primary64) * np.linalg.norm(reference64))
    correlation = (
        float(np.dot(primary64, reference64) / denominator)
        if denominator > 1e-12
        else 0.0
    )
    normalized_difference = float(
        np.sqrt(np.mean((primary64 - reference64) ** 2))
        / max(primary_rms + reference_rms, 1e-12)
    )
    level_delta_db = float(
        abs(20.0 * np.log10(max(primary_rms, 1e-12) / max(reference_rms, 1e-12)))
    )
    if max(primary_rms, reference_rms) < 1e-5:
        status = "inactive"
        message = "Channels are currently near silence."
    elif abs(correlation) >= 0.995 and normalized_difference <= 0.05:
        status = "duplicated"
        message = (
            "Primary and reference are effectively identical; use a true synchronized "
            "outward reference microphone. Safe bypass may activate."
        )
    elif abs(correlation) >= 0.90:
        status = "high_similarity"
        message = (
            "Channels are highly similar. Check microphone placement and target-speech leakage."
        )
    else:
        status = "distinct"
        message = "Primary and reference contain useful channel differences."
    return {
        "status": status,
        "zero_lag_correlation": correlation,
        "normalized_difference": normalized_difference,
        "level_delta_db": level_delta_db,
        "message": message,
    }


def build_live_telemetry(
    primary: np.ndarray,
    reference: np.ndarray | None,
    enhanced: np.ndarray,
    *,
    sample_rate: int,
    n_fft: int,
    runtime_status: dict[str, Any],
    engine_stats: dict[str, int],
    wet_mix: float | None = None,
    hop_length: int | None = None,
    playout_latency_ms: float | None = None,
    session_elapsed_seconds: float | None = None,
    operator_control: dict[str, Any] | None = None,
    model_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    has_reference = reference is not None
    reference_audio = (
        np.asarray(reference, dtype=np.float32)
        if has_reference
        else np.zeros_like(primary, dtype=np.float32)
    )
    frequencies = np.fft.rfftfreq(n_fft, 1.0 / sample_rate).tolist()
    levels = {
        "primary": _level(primary),
        "reference": _level(reference_audio),
        "enhanced": _level(enhanced),
    }
    relationship = (
        _channel_relationship(primary, reference_audio)
        if has_reference
        else {
            "status": "unavailable",
            "zero_lag_correlation": 0.0,
            "normalized_difference": 0.0,
            "level_delta_db": 0.0,
            "message": "Mono laptop mode: no reference microphone is being used.",
        }
    )
    runtime = dict(runtime_status)
    if hop_length:
        runtime["frame_rtf"] = float(runtime.get("last_inference_ms", 0.0)) / (
            1000.0 * hop_length / sample_rate
        )
    return {
        "timestamp_unix": time.time(),
        "sample_rate": int(sample_rate),
        "frequency_hz": frequencies,
        "spectrum_dbfs": {
            "primary": _spectrum(primary, n_fft),
            "reference": _spectrum(reference_audio, n_fft),
            "enhanced": _spectrum(enhanced, n_fft),
        },
        "waveform": {
            "primary": _waveform(primary),
            "reference": _waveform(reference_audio),
            "enhanced": _waveform(enhanced),
        },
        "levels": levels,
        "channel_relationship": relationship,
        "output_level_reduction_db": float(
            levels["primary"]["rms_dbfs"] - levels["enhanced"]["rms_dbfs"]
        ),
        "wet_mix": float(wet_mix) if wet_mix is not None else None,
        "n_fft": int(n_fft),
        "hop_length": int(hop_length) if hop_length is not None else None,
        "playout_latency_ms": float(playout_latency_ms) if playout_latency_ms is not None else None,
        "session_elapsed_seconds": float(session_elapsed_seconds or 0.0),
        "operator_control": dict(operator_control or {}),
        "model": dict(model_info or {}),
        "signal_analysis": _signal_analysis(
            primary, reference_audio, enhanced, sample_rate=sample_rate, n_fft=n_fft
        ),
        "runtime": runtime,
        "engine": engine_stats,
        "live_quality_metrics_available": False,
        "quality_note": "Live audio has no clean target, so SNR/STOI/PESQ are not displayed.",
    }


def write_atomic_json(
    path: str | Path,
    value: dict[str, Any],
    *,
    replace_attempts: int = 8,
) -> None:
    """Write a snapshot without crashing live audio on transient Windows locks.

    Browsers, antivirus and indexers can briefly open the destination without
    delete sharing, which makes ``os.replace`` raise ``PermissionError`` on
    Windows.  A unique temporary file plus bounded retry keeps the dashboard
    atomic while avoiding the fixed ``.tmp`` collision used previously.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, separators=(",", ":"))
    temporary = target.with_name(
        f".{target.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    temporary.write_text(payload, encoding="utf-8")
    try:
        for attempt in range(max(1, int(replace_attempts))):
            try:
                os.replace(temporary, target)
                return
            except PermissionError:
                if attempt + 1 >= replace_attempts:
                    raise
                time.sleep(0.005 * (attempt + 1))
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
