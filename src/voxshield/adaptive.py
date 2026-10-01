"""Bounded adaptive-filter primitives for hybrid VoxShield processing.

These routines are deterministic research baselines.  The FxNLMS controller
must be calibrated against the real headset secondary path and moved to a
hard-real-time DSP/MCU before it is treated as protective physical ANC.
"""

from __future__ import annotations

import numpy as np


class NormalizedLMS:
    """Reference-noise canceller with leakage and bounded coefficients."""

    def __init__(
        self,
        taps: int = 128,
        step_size: float = 0.05,
        leakage: float = 1e-5,
        coefficient_limit: float = 2.0,
        eps: float = 1e-8,
    ) -> None:
        if taps < 1 or not 0.0 < step_size <= 1.0:
            raise ValueError("taps must be positive and step_size must be in (0, 1]")
        self.taps = int(taps)
        self.step_size = float(step_size)
        self.leakage = float(leakage)
        self.coefficient_limit = float(coefficient_limit)
        self.eps = float(eps)
        self.weights = np.zeros(self.taps, dtype=np.float32)
        self.history = np.zeros(self.taps, dtype=np.float32)

    def reset(self) -> None:
        self.weights.fill(0.0)
        self.history.fill(0.0)

    def process(
        self,
        primary: np.ndarray,
        reference: np.ndarray,
        adaptation_gate: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        primary = np.asarray(primary, dtype=np.float32)
        reference = np.asarray(reference, dtype=np.float32)
        if primary.shape != reference.shape or primary.ndim != 1:
            raise ValueError("primary and reference must be equal-length mono arrays")
        if adaptation_gate is None:
            adaptation_gate = np.ones_like(primary)
        else:
            adaptation_gate = np.asarray(adaptation_gate, dtype=np.float32)
            if adaptation_gate.shape != primary.shape:
                raise ValueError("adaptation_gate must match primary")
        residual = np.empty_like(primary)
        predicted = np.empty_like(primary)
        for index, (desired, sample) in enumerate(zip(primary, reference)):
            self.history[1:] = self.history[:-1]
            self.history[0] = sample
            estimate = float(np.dot(self.weights, self.history))
            error = float(desired) - estimate
            normalizer = float(np.dot(self.history, self.history)) + self.eps
            update = self.step_size * float(np.clip(adaptation_gate[index], 0.0, 1.0))
            self.weights *= 1.0 - self.leakage
            self.weights += update * error * self.history / normalizer
            np.clip(
                self.weights,
                -self.coefficient_limit,
                self.coefficient_limit,
                out=self.weights,
            )
            predicted[index] = estimate
            residual[index] = error
        return residual, predicted


class FilteredXNLMS:
    """Feed-forward physical ANC controller using an estimated secondary path.

    `step(reference_sample, error_sample)` returns the next controller output.
    The caller must obtain `error_sample` from the synchronized in-ear error
    microphone after the real secondary path.  Output sign and gain must be
    verified at low level during headset calibration.
    """

    def __init__(
        self,
        secondary_path: np.ndarray,
        taps: int = 128,
        step_size: float = 0.01,
        leakage: float = 1e-6,
        output_limit: float = 0.25,
        coefficient_limit: float = 2.0,
        eps: float = 1e-8,
    ) -> None:
        secondary_path = np.asarray(secondary_path, dtype=np.float32).reshape(-1)
        if not len(secondary_path) or not np.isfinite(secondary_path).all():
            raise ValueError("secondary_path must be a finite non-empty impulse response")
        if taps < 1 or not 0.0 < step_size <= 1.0:
            raise ValueError("taps must be positive and step_size must be in (0, 1]")
        self.secondary_path = secondary_path
        self.taps = int(taps)
        self.step_size = float(step_size)
        self.leakage = float(leakage)
        self.output_limit = float(output_limit)
        self.coefficient_limit = float(coefficient_limit)
        self.eps = float(eps)
        self.weights = np.zeros(self.taps, dtype=np.float32)
        self.reference_history = np.zeros(self.taps, dtype=np.float32)
        self.secondary_history = np.zeros(len(secondary_path), dtype=np.float32)
        self.filtered_history = np.zeros(self.taps, dtype=np.float32)
        self._last_control_saturated = False

    def reset(self) -> None:
        self.weights.fill(0.0)
        self.reference_history.fill(0.0)
        self.secondary_history.fill(0.0)
        self.filtered_history.fill(0.0)
        self._last_control_saturated = False

    def output(self, reference_sample: float) -> float:
        """Produce one bounded control sample and advance reference state."""
        self.reference_history[1:] = self.reference_history[:-1]
        self.reference_history[0] = float(reference_sample)
        self.secondary_history[1:] = self.secondary_history[:-1]
        self.secondary_history[0] = float(reference_sample)
        filtered_reference = float(np.dot(self.secondary_path, self.secondary_history))
        self.filtered_history[1:] = self.filtered_history[:-1]
        self.filtered_history[0] = filtered_reference
        raw_control = float(np.dot(self.weights, self.reference_history))
        control = float(np.clip(raw_control, -self.output_limit, self.output_limit))
        self._last_control_saturated = control != raw_control
        return control

    def adapt(self, error_sample: float, enabled: bool = True) -> None:
        """Update coefficients after observing the synchronized error sample."""
        self.weights *= 1.0 - self.leakage
        if enabled and not self._last_control_saturated:
            normalizer = float(np.dot(self.filtered_history, self.filtered_history)) + self.eps
            # The negative sign minimizes the measured physical error when the
            # secondary-path estimate uses the same polarity as the real path.
            self.weights -= self.step_size * float(error_sample) * self.filtered_history / normalizer
        np.clip(
            self.weights,
            -self.coefficient_limit,
            self.coefficient_limit,
            out=self.weights,
        )

    def step(self, reference_sample: float, error_sample: float, adapt: bool = True) -> float:
        """Convenience step for a real loop where the current error is already available."""
        control = self.output(reference_sample)
        self.adapt(error_sample, enabled=adapt)
        return control


def simulate_filtered_x_nlms(
    reference: np.ndarray,
    disturbance: np.ndarray,
    secondary_path: np.ndarray,
    *,
    taps: int = 128,
    step_size: float = 0.01,
    leakage: float = 1e-6,
    output_limit: float = 0.25,
    adaptation_gate: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run an explicitly offline FxNLMS simulation.

    `disturbance` is the signal measured at the error microphone with the
    control loudspeaker muted. This function does not operate audio hardware
    and cannot establish real-world stability.
    """
    reference = np.asarray(reference, dtype=np.float32).reshape(-1)
    disturbance = np.asarray(disturbance, dtype=np.float32).reshape(-1)
    secondary_path = np.asarray(secondary_path, dtype=np.float32).reshape(-1)
    if len(reference) != len(disturbance) or not len(reference):
        raise ValueError("reference and disturbance must be equal-length, non-empty arrays")
    if adaptation_gate is None:
        adaptation_gate = np.ones_like(reference)
    else:
        adaptation_gate = np.asarray(adaptation_gate, dtype=np.float32).reshape(-1)
        if len(adaptation_gate) != len(reference):
            raise ValueError("adaptation_gate must match the input length")
    controller = FilteredXNLMS(
        secondary_path,
        taps=taps,
        step_size=step_size,
        leakage=leakage,
        output_limit=output_limit,
    )
    control = np.zeros_like(reference)
    residual = np.zeros_like(reference)
    control_history = np.zeros(len(secondary_path), dtype=np.float32)
    for index, sample in enumerate(reference):
        control[index] = controller.output(float(sample))
        control_history[1:] = control_history[:-1]
        control_history[0] = control[index]
        anti_noise = float(np.dot(secondary_path, control_history))
        residual[index] = float(disturbance[index]) + anti_noise
        controller.adapt(
            float(residual[index]), enabled=bool(adaptation_gate[index] > 0.5)
        )
    return residual, control, controller.weights.copy()
