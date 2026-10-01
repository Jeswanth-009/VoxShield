import numpy as np
import pytest

from voxshield.live_dual_device import SampleDelay, _controlled_demo_primary


def test_sample_delay_is_causal_across_blocks() -> None:
    delay = SampleDelay(3)
    first = delay.process(np.array([1.0, 2.0], dtype=np.float32))
    second = delay.process(np.array([3.0, 4.0], dtype=np.float32))
    third = delay.process(np.array([5.0, 6.0], dtype=np.float32))
    np.testing.assert_array_equal(first, [0.0, 0.0])
    np.testing.assert_array_equal(second, [0.0, 1.0])
    np.testing.assert_array_equal(third, [2.0, 3.0])


def test_sample_delay_rejects_negative_delay() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        SampleDelay(-1)


def test_controlled_demo_primary_combines_and_clips_safely() -> None:
    primary = np.array([0.2, -0.2, 0.9], dtype=np.float32)
    reference = np.array([0.4, 0.4, 0.9], dtype=np.float32)
    mixed = _controlled_demo_primary(primary, reference, 0.5)
    np.testing.assert_allclose(mixed, [0.4, 0.0, 0.98], atol=1e-6)


def test_controlled_demo_primary_zero_mix_preserves_primary() -> None:
    primary = np.array([0.2, -0.2], dtype=np.float32)
    reference = np.array([0.9, 0.9], dtype=np.float32)
    np.testing.assert_array_equal(
        _controlled_demo_primary(primary, reference, 0.0), primary
    )
