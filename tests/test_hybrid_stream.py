"""Hybrid (adaptive filter + neural) streaming runtime tests."""

import numpy as np
import pytest

from voxshield.runtime import (
    HybridStreamingEnhancer,
    StreamingDualChannelEnhancer,
    StreamingEnhancer,
)


class IdentityRunner:
    """Mono frame runner that returns its input unchanged."""

    def reset(self) -> None:
        return None

    def enhance(self, spectrum_ri: np.ndarray) -> np.ndarray:
        return spectrum_ri


class IdentityDualRunner:
    """Dual frame runner that returns the primary unchanged."""

    def reset(self) -> None:
        return None

    def enhance(self, primary_ri: np.ndarray, reference_ri: np.ndarray) -> np.ndarray:
        return primary_ri


class ReferenceSpyRunner:
    """Dual frame runner that records what the neural stage actually receives."""

    def __init__(self) -> None:
        self.primaries: list[np.ndarray] = []
        self.references: list[np.ndarray] = []

    def reset(self) -> None:
        self.primaries.clear()
        self.references.clear()

    def enhance(self, primary_ri: np.ndarray, reference_ri: np.ndarray) -> np.ndarray:
        self.primaries.append(primary_ri.copy())
        self.references.append(reference_ri.copy())
        return primary_ri


def _coherent_fixture(samples: int = 16128) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(4)
    reference = rng.normal(0.0, 0.1, samples).astype(np.float32)
    time = np.arange(samples) / 16000
    speech = (0.02 * np.sin(2 * np.pi * 220 * time)).astype(np.float32)
    primary = speech + np.concatenate(([0.0], 0.8 * reference[:-1])).astype(np.float32)
    return primary.astype(np.float32), reference


def _make_hybrid(runner, neural_dual_channel: bool) -> HybridStreamingEnhancer:
    return HybridStreamingEnhancer(
        runner,
        sample_rate=16000,
        n_fft=512,
        hop_length=256,
        wet_mix=1.0,
        deadline_fraction=float("inf"),
        neural_dual_channel=neural_dual_channel,
        lms_taps=64,
        lms_step_size=0.1,
    )


def _stream_chunks(hybrid, primary: np.ndarray, reference: np.ndarray) -> np.ndarray:
    outputs = []
    hop = 256
    for start in range(0, len(primary), hop):
        outputs.append(
            hybrid.process(primary[start : start + hop], reference[start : start + hop])
        )
    return np.concatenate(outputs)


def test_hybrid_reduces_coherent_noise_against_neural_only() -> None:
    primary, reference = _coherent_fixture()
    hybrid = _make_hybrid(IdentityRunner(), neural_dual_channel=False)
    neural_only = StreamingEnhancer(
        IdentityRunner(),
        sample_rate=16000,
        n_fft=512,
        hop_length=256,
        wet_mix=1.0,
        deadline_fraction=float("inf"),
    )
    hybrid_output = _stream_chunks(hybrid, primary, reference)
    neural_output = []
    hop = 256
    for start in range(0, len(primary), hop):
        neural_output.append(neural_only.process(primary[start : start + hop]))
    neural_output = np.concatenate(neural_output)
    region = slice(8000, 14000)
    before = np.mean(primary[region] ** 2)
    after_hybrid = np.mean(hybrid_output[region] ** 2)
    after_neural = np.mean(neural_output[region] ** 2)
    assert after_neural > before * 0.5  # identity neural stage cannot cancel noise
    assert after_hybrid < before * 0.3  # the LMS stage can


def test_dual_channel_neural_stage_receives_raw_reference() -> None:
    spy = ReferenceSpyRunner()
    hybrid = _make_hybrid(spy, neural_dual_channel=True)
    rng = np.random.default_rng(11)
    reference = rng.normal(0.0, 0.3, 4096).astype(np.float32)
    primary = np.zeros_like(reference)
    _stream_chunks(hybrid, primary, reference)
    primary_energy = max(
        float(np.mean(frame**2)) for frame in spy.primaries
    )
    reference_energy = max(
        float(np.mean(frame**2)) for frame in spy.references
    )
    # The neural stage sees the LMS residual on the primary path but the
    # untouched reference, so its spatial features survive stage 1.
    assert reference_energy > primary_energy * 25.0


def test_hybrid_reset_restores_identical_output() -> None:
    primary, reference = _coherent_fixture()
    hybrid = _make_hybrid(IdentityRunner(), neural_dual_channel=False)
    first = _stream_chunks(hybrid, primary, reference)
    hybrid.reset()
    second = _stream_chunks(hybrid, primary, reference)
    assert np.array_equal(first, second)


def test_hybrid_latency_and_reference_contract() -> None:
    hybrid = _make_hybrid(IdentityRunner(), neural_dual_channel=False)
    assert hybrid.consumes_reference is True
    assert hybrid.algorithmic_latency_samples == 512 - 256
    primary, reference = _coherent_fixture(2048)
    with pytest.raises(ValueError):
        hybrid.process(primary[:256], reference[:512])
    output = _stream_chunks(hybrid, primary, reference)
    assert np.isfinite(output).all()
    assert len(output) == len(primary) - (512 - 256)  # startup discard only


def test_hybrid_wraps_dual_channel_enhancer_for_dual_models() -> None:
    hybrid = _make_hybrid(IdentityDualRunner(), neural_dual_channel=True)
    assert isinstance(hybrid.inner, StreamingDualChannelEnhancer)
    mono_hybrid = _make_hybrid(IdentityRunner(), neural_dual_channel=False)
    assert isinstance(mono_hybrid.inner, StreamingEnhancer)
