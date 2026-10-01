from __future__ import annotations

import warnings

import numpy as np


def snr(reference: np.ndarray, estimate: np.ndarray, eps: float = 1e-8) -> float:
    length = min(len(reference), len(estimate))
    ref, est = reference[:length].astype(np.float64), estimate[:length].astype(np.float64)
    return float(10.0 * np.log10((np.sum(ref**2) + eps) / (np.sum((ref - est) ** 2) + eps)))


def si_snr(reference: np.ndarray, estimate: np.ndarray, eps: float = 1e-8) -> float:
    length = min(len(reference), len(estimate))
    ref, est = reference[:length].astype(np.float64), estimate[:length].astype(np.float64)
    ref, est = ref - ref.mean(), est - est.mean()
    projection = np.dot(est, ref) * ref / max(np.dot(ref, ref), eps)
    residual = est - projection
    return float(10.0 * np.log10((np.sum(projection**2) + eps) / (np.sum(residual**2) + eps)))


def pause_noise_attenuation(
    clean: np.ndarray,
    noisy: np.ndarray,
    enhanced: np.ndarray,
    frame_samples: int = 320,
    eps: float = 1e-10,
) -> float | None:
    """Measure residual-noise reduction in reference speech pauses.

    This catches the exact failure a global SI-SNR average can hide: clearly
    audible background noise remaining between words.
    """
    length = min(len(clean), len(noisy), len(enhanced))
    frames = length // frame_samples
    if frames < 2:
        return None
    reference = clean[: frames * frame_samples].reshape(frames, frame_samples).astype(np.float64)
    noisy_error = (
        noisy[: frames * frame_samples].reshape(frames, frame_samples).astype(np.float64)
        - reference
    )
    enhanced_error = (
        enhanced[: frames * frame_samples].reshape(frames, frame_samples).astype(np.float64)
        - reference
    )
    reference_rms = np.sqrt(np.mean(reference**2, axis=1) + eps)
    threshold = max(float(np.max(reference_rms)) * 0.08, 1e-4)
    pauses = reference_rms <= threshold
    if int(pauses.sum()) < 2:
        return None
    before = float(np.mean(noisy_error[pauses] ** 2))
    after = float(np.mean(enhanced_error[pauses] ** 2))
    return float(10.0 * np.log10((before + eps) / (after + eps)))


def speech_deletion_rate(
    clean: np.ndarray,
    enhanced: np.ndarray,
    frame_samples: int = 320,
    maximum_attenuation_db: float = 20.0,
    eps: float = 1e-10,
) -> float | None:
    """Fraction of active-speech frames attenuated beyond a safe limit."""
    length = min(len(clean), len(enhanced))
    frames = length // frame_samples
    if frames < 2:
        return None
    reference = clean[: frames * frame_samples].reshape(frames, frame_samples).astype(np.float64)
    estimate = enhanced[: frames * frame_samples].reshape(frames, frame_samples).astype(np.float64)
    reference_rms = np.sqrt(np.mean(reference**2, axis=1) + eps)
    estimate_rms = np.sqrt(np.mean(estimate**2, axis=1) + eps)
    threshold = max(float(np.max(reference_rms)) * 0.08, 1e-4)
    active = reference_rms >= threshold
    if not np.any(active):
        return None
    attenuation = 20.0 * np.log10((reference_rms + eps) / (estimate_rms + eps))
    return float(np.mean(attenuation[active] > maximum_attenuation_db))


def active_level_error_db(
    clean: np.ndarray,
    enhanced: np.ndarray,
    eps: float = 1e-10,
) -> float | None:
    """Absolute active-speech RMS level change in decibels."""
    length = min(len(clean), len(enhanced))
    if length == 0:
        return None
    reference = clean[:length].astype(np.float64)
    estimate = enhanced[:length].astype(np.float64)
    threshold = max(float(np.max(np.abs(reference))) * 0.08, 1e-4)
    active = np.abs(reference) >= threshold
    if not np.any(active):
        return None
    reference_rms = np.sqrt(np.mean(reference[active] ** 2) + eps)
    estimate_rms = np.sqrt(np.mean(estimate[active] ** 2) + eps)
    return float(abs(20.0 * np.log10((estimate_rms + eps) / (reference_rms + eps))))


def optional_dnsmos(audio: np.ndarray, sample_rate: int) -> dict[str, float | None]:
    """No-reference DNSMOS/P.835 quality estimates (SIG/BAK/OVRL).

    Returns ``None`` values when the optional ``speechmos`` package is not
    installed or the sample rate is unsupported, so evaluation remains
    functional without it.  DNSMOS requires mono audio in [-1, 1] at 16 kHz.
    """
    result: dict[str, float | None] = {
        "dnsmos_sig": None,
        "dnsmos_bak": None,
        "dnsmos_ovrl": None,
    }
    if sample_rate != 16000:
        return result
    try:
        from speechmos.dnsmos import run
    except ImportError:
        return result
    audio = np.nan_to_num(np.asarray(audio, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    if audio.size == 0:
        return result
    peak = float(np.max(np.abs(audio)))
    if peak > 1.0:
        audio = audio / peak
    try:
        scores = run(audio, sample_rate, model_type="dnsmos", return_df=False)
    except (ValueError, RuntimeError) as exc:
        warnings.warn(f"DNSMOS unavailable for this clip: {exc}", RuntimeWarning, stacklevel=2)
        return result
    return {
        "dnsmos_sig": float(scores["sig_mos"]),
        "dnsmos_bak": float(scores["bak_mos"]),
        "dnsmos_ovrl": float(scores["ovrl_mos"]),
    }


def optional_metrics(reference: np.ndarray, estimate: np.ndarray, sample_rate: int) -> dict[str, float | None]:
    result: dict[str, float | None] = {"stoi": None, "pesq": None}
    try:
        from pystoi import stoi

        result["stoi"] = float(stoi(reference, estimate, sample_rate, extended=False))
    except (ImportError, ValueError):
        pass
    if sample_rate in (8000, 16000):
        try:
            from pesq import pesq

            result["pesq"] = float(pesq(sample_rate, reference, estimate, "wb" if sample_rate == 16000 else "nb"))
        except (ImportError, ValueError, RuntimeError) as exc:
            warnings.warn(f"PESQ unavailable for this pair: {exc}", RuntimeWarning, stacklevel=2)
    return result
