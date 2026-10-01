import numpy as np

from voxshield.adaptive import FilteredXNLMS, NormalizedLMS, simulate_filtered_x_nlms


def test_nlms_reduces_correlated_reference_noise() -> None:
    rng = np.random.default_rng(4)
    reference = rng.normal(0.0, 0.1, 12000).astype(np.float32)
    speech = (0.02 * np.sin(2 * np.pi * 220 * np.arange(len(reference)) / 16000)).astype(
        np.float32
    )
    primary = speech + np.concatenate(([0.0], 0.8 * reference[:-1])).astype(np.float32)
    canceller = NormalizedLMS(taps=16, step_size=0.1)
    residual, _ = canceller.process(primary, reference)
    before = np.mean((primary[4000:] - speech[4000:]) ** 2)
    after = np.mean((residual[4000:] - speech[4000:]) ** 2)
    assert after < before * 0.2


def test_fxnlms_is_bounded_and_resettable() -> None:
    controller = FilteredXNLMS(np.array([0.8, 0.1], dtype=np.float32), output_limit=0.1)
    outputs = [controller.step(1.0, 0.2) for _ in range(100)]
    assert np.max(np.abs(outputs)) <= 0.1
    assert np.any(controller.weights != 0)
    controller.reset()
    assert np.all(controller.weights == 0)


def test_offline_fxnlms_simulation_reduces_correlated_disturbance() -> None:
    rng = np.random.default_rng(9)
    reference = rng.normal(0.0, 0.08, 24000).astype(np.float32)
    disturbance = np.concatenate((np.zeros(4), 0.7 * reference[:-4])).astype(np.float32)
    secondary_path = np.array([0.0, 0.8, 0.15], dtype=np.float32)
    residual, control, _ = simulate_filtered_x_nlms(
        reference,
        disturbance,
        secondary_path,
        taps=24,
        step_size=0.005,
        output_limit=0.25,
    )
    before = np.mean(disturbance[8000:] ** 2)
    after = np.mean(residual[8000:] ** 2)
    assert after < before * 0.25
    assert np.max(np.abs(control)) <= 0.25
