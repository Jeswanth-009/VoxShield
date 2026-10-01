import numpy as np

from voxshield.diagnostics import dual_channel_diagnostics


def test_dual_channel_diagnostics_finds_lag_and_routing_problem() -> None:
    rng = np.random.default_rng(12)
    reference = rng.normal(0.0, 0.05, 16000).astype(np.float32)
    primary = np.concatenate((np.zeros(7, dtype=np.float32), reference[:-7]))
    result = dual_channel_diagnostics(primary, reference, 16000)
    assert result["estimated_relative_lag_samples"] == 7
    assert result["peak_signed_correlation"] > 0.99
    assert any("identical" in warning for warning in result["warnings"])


def test_dual_channel_diagnostics_rejects_mismatched_lengths() -> None:
    with np.testing.assert_raises(ValueError):
        dual_channel_diagnostics(np.zeros(10), np.zeros(9), 16000)
