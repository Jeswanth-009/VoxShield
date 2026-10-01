from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import torch

from .adaptive import NormalizedLMS
from .audio import sqrt_hann
from .df_model import DeepFilterDualChannelNet
from .fusion_model import FusionDualChannelULUNAS
from .hybrid_model import HybridDualChannelGTCRN
from .model import CausalComplexMaskNet
from .official_gtcrn import OfficialGTCRN
from .official_stream import StreamGTCRN, convert_to_stream
from .ulunas_adapter import OfficialULUNAS


class FrameRunner(Protocol):
    def reset(self) -> None: ...
    def enhance(self, spectrum_ri: np.ndarray) -> np.ndarray: ...


class DualFrameRunner(Protocol):
    def reset(self) -> None: ...
    def enhance(self, primary_ri: np.ndarray, reference_ri: np.ndarray) -> np.ndarray: ...


class TorchFrameRunner:
    def __init__(self, model: CausalComplexMaskNet, device: str | torch.device = "cpu") -> None:
        self.model = model.to(device).eval()
        self.device = torch.device(device)
        self.state: torch.Tensor | None = None

    def reset(self) -> None:
        self.state = None

    def enhance(self, spectrum_ri: np.ndarray) -> np.ndarray:
        tensor = torch.from_numpy(spectrum_ri).to(self.device)
        with torch.inference_mode():
            output, self.state = self.model.forward_ri(tensor, self.state)
        return output.cpu().numpy()


class OfficialTorchFrameRunner:
    """Stateful frame runner for the complete official GTCRN architecture."""

    def __init__(self, model: OfficialGTCRN, device: str | torch.device = "cpu") -> None:
        self.device = torch.device(device)
        self.model = StreamGTCRN().to(self.device).eval()
        convert_to_stream(self.model, model.to(self.device).eval())
        self.states: tuple[torch.Tensor, torch.Tensor, torch.Tensor] | None = None

    def reset(self) -> None:
        self.states = None

    def enhance(self, spectrum_ri: np.ndarray) -> np.ndarray:
        # WOLA uses [B,2,F,1]; official GTCRN uses [B,F,1,2].
        value = torch.from_numpy(spectrum_ri).to(self.device).permute(0, 2, 3, 1)
        if self.states is None or self.states[0].shape[1] != value.shape[0]:
            self.states = StreamGTCRN.initial_states(value.shape[0], self.device)
        with torch.inference_mode():
            output, conv, tra, inter = self.model(value, *self.states)
        self.states = (conv, tra, inter)
        return output.permute(0, 3, 1, 2).cpu().numpy()


class HybridTorchFrameRunner:
    def __init__(
        self, model: HybridDualChannelGTCRN, device: str | torch.device = "cpu"
    ) -> None:
        self.model = model.to(device).eval()
        self.device = torch.device(device)
        self.state: torch.Tensor | None = None

    def reset(self) -> None:
        self.state = None

    def enhance(self, primary_ri: np.ndarray, reference_ri: np.ndarray) -> np.ndarray:
        primary = torch.from_numpy(primary_ri).to(self.device)
        reference = torch.from_numpy(reference_ri).to(self.device)
        with torch.inference_mode():
            output, self.state = self.model.forward_ri(primary, reference, self.state)
        return output.cpu().numpy()


class ULUNASTorchFrameRunner:
    """Stateful frame runner for the UL-UNAS architecture via StreamULUNAS."""

    def __init__(self, model: OfficialULUNAS, device: str | torch.device = "cpu") -> None:
        self.device = torch.device(device)
        from .ulunas_adapter import make_stream_ulunas
        self.stream_model = make_stream_ulunas(model).to(self.device).eval()
        self.conv_cache: torch.Tensor | None = None
        self.tfa_cache: torch.Tensor | None = None
        self.inter_cache: torch.Tensor | None = None
        self.reset()

    def reset(self) -> None:
        self.conv_cache, self.tfa_cache, self.inter_cache = (
            self.stream_model.init_caches(1, self.device)
        )

    def enhance(self, spectrum_ri: np.ndarray) -> np.ndarray:
        # spectrum_ri is (B, 2, F, 1) -> StreamULUNAS expects (B, F, 1, 2)
        tensor = torch.from_numpy(spectrum_ri).to(self.device)
        spec = tensor.permute(0, 2, 3, 1)
        with torch.inference_mode():
            enhanced_spec, self.conv_cache, self.tfa_cache, self.inter_cache = (
                self.stream_model(
                    spec, self.conv_cache, self.tfa_cache, self.inter_cache
                )
            )
        # enhanced_spec is (B, F, 1, 2) -> permute back to (B, 2, F, 1)
        output = enhanced_spec.permute(0, 3, 1, 2)
        return output.cpu().numpy()


def make_torch_frame_runner(
    model: torch.nn.Module, device: str | torch.device = "cpu"
) -> FrameRunner:
    if isinstance(model, OfficialGTCRN):
        return OfficialTorchFrameRunner(model, device)
    if isinstance(model, OfficialULUNAS):
        return ULUNASTorchFrameRunner(model, device)
    if isinstance(model, HybridDualChannelGTCRN):
        return HybridTorchFrameRunner(model, device)
    if isinstance(model, FusionDualChannelULUNAS):
        return HybridTorchFrameRunner(model, device)
    if isinstance(model, DeepFilterDualChannelNet):
        return HybridTorchFrameRunner(model, device)
    if isinstance(model, CausalComplexMaskNet):
        return TorchFrameRunner(model, device)
    raise TypeError(f"No streaming runner registered for {type(model).__name__}")


class OnnxFrameRunner:
    def __init__(self, path: str | Path, state_shape: tuple[int, ...], threads: int = 1) -> None:
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("Install the ONNX extra: pip install -e .[onnx]") from exc
        options = ort.SessionOptions()
        options.intra_op_num_threads = int(threads)
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(str(path), sess_options=options, providers=["CPUExecutionProvider"])
        self.state_shape = tuple(int(value) for value in state_shape)
        self.state: np.ndarray | None = None

    def reset(self) -> None:
        self.state = None

    def enhance(self, spectrum_ri: np.ndarray) -> np.ndarray:
        if self.state is None or self.state.shape[1] != spectrum_ri.shape[0]:
            shape = list(self.state_shape)
            shape[1] = spectrum_ri.shape[0]
            self.state = np.zeros(tuple(shape), dtype=np.float32)
        output, self.state = self.session.run(
            ["enhanced_ri", "state_out"],
            {"spectrum_ri": spectrum_ri.astype(np.float32), "state_in": self.state},
        )
        return output


class OfficialOnnxFrameRunner:
    def __init__(self, path: str | Path, threads: int = 1) -> None:
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("Install the ONNX extra: pip install -e .[onnx]") from exc
        options = ort.SessionOptions()
        options.intra_op_num_threads = int(threads)
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(
            str(path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.states: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None

    def reset(self) -> None:
        self.states = None

    def enhance(self, spectrum_ri: np.ndarray) -> np.ndarray:
        batch = spectrum_ri.shape[0]
        if self.states is None or self.states[0].shape[1] != batch:
            self.states = (
                np.zeros((2, batch, 16, 16, 33), dtype=np.float32),
                np.zeros((2, 3, 1, batch, 16), dtype=np.float32),
                np.zeros((2, 1, batch * 33, 16), dtype=np.float32),
            )
        spectrum = spectrum_ri.transpose(0, 2, 3, 1).astype(np.float32)
        output, conv, tra, inter = self.session.run(
            ["enhanced", "conv_cache_out", "tra_cache_out", "inter_cache_out"],
            {
                "spectrum": spectrum,
                "conv_cache": self.states[0],
                "tra_cache": self.states[1],
                "inter_cache": self.states[2],
            },
        )
        self.states = (conv, tra, inter)
        return output.transpose(0, 3, 1, 2)


class HybridOnnxFrameRunner:
    def __init__(self, path: str | Path, state_shape: tuple[int, ...], threads: int = 1) -> None:
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("Install the ONNX extra: pip install -e .[onnx]") from exc
        options = ort.SessionOptions()
        options.intra_op_num_threads = int(threads)
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(
            str(path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.state_shape = tuple(int(value) for value in state_shape)
        self.state: np.ndarray | None = None

    def reset(self) -> None:
        self.state = None

    def enhance(self, primary_ri: np.ndarray, reference_ri: np.ndarray) -> np.ndarray:
        if self.state is None or self.state.shape[1] != primary_ri.shape[0]:
            shape = list(self.state_shape)
            shape[1] = primary_ri.shape[0]
            self.state = np.zeros(tuple(shape), dtype=np.float32)
        output, self.state = self.session.run(
            ["enhanced_ri", "state_out"],
            {
                "primary_ri": primary_ri.astype(np.float32),
                "reference_ri": reference_ri.astype(np.float32),
                "state_in": self.state,
            },
        )
        return output


class FusionOnnxFrameRunner:
    """ONNX runner for the packed-state, dual-input v7 fusion model."""

    def __init__(self, path: str | Path, state_size: int, threads: int = 1) -> None:
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("Install the ONNX extra: pip install -e .[onnx]") from exc
        options = ort.SessionOptions()
        options.intra_op_num_threads = int(threads)
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(
            str(path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.state_size = int(state_size)
        self.state: np.ndarray | None = None

    def reset(self) -> None:
        self.state = None

    def enhance(self, primary_ri: np.ndarray, reference_ri: np.ndarray) -> np.ndarray:
        batch = int(primary_ri.shape[0])
        if self.state is None or self.state.shape[0] != batch:
            self.state = np.zeros((batch, self.state_size), dtype=np.float32)
        output, self.state = self.session.run(
            ["enhanced_ri", "state_out"],
            {
                "primary_ri": primary_ri.astype(np.float32),
                "reference_ri": reference_ri.astype(np.float32),
                "state_in": self.state,
            },
        )
        return output


class ULUNASOnnxFrameRunner:
    """ONNX runner for the StreamULUNAS export (packed conv/tfa/inter caches)."""

    _CACHE_NAMES = ("conv_cache", "tfa_cache", "inter_cache")

    def __init__(self, path: str | Path, threads: int = 1) -> None:
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("Install the ONNX extra: pip install -e .[onnx]") from exc
        options = ort.SessionOptions()
        options.intra_op_num_threads = int(threads)
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(
            str(path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.cache_shapes: dict[str, tuple[int, ...]] = {}
        for entry in self.session.get_inputs():
            if entry.name in self._CACHE_NAMES:
                self.cache_shapes[entry.name] = tuple(int(dim) for dim in entry.shape)
        missing = set(self._CACHE_NAMES) - set(self.cache_shapes)
        if missing:
            raise ValueError(f"UL-UNAS ONNX export missing cache inputs: {sorted(missing)}")
        self.states: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None

    def reset(self) -> None:
        self.states = None

    def enhance(self, spectrum_ri: np.ndarray) -> np.ndarray:
        batch = spectrum_ri.shape[0]
        if self.states is None or self.states[0].shape[0] != batch:
            self.states = tuple(
                np.zeros((batch,) + self.cache_shapes[name][1:], dtype=np.float32)
                for name in self._CACHE_NAMES
            )
        spectrum = spectrum_ri.transpose(0, 2, 3, 1).astype(np.float32)
        output, conv, tfa, inter = self.session.run(
            ["enhanced", "conv_cache_out", "tfa_cache_out", "inter_cache_out"],
            {
                "spectrum": spectrum,
                "conv_cache": self.states[0],
                "tfa_cache": self.states[1],
                "inter_cache": self.states[2],
            },
        )
        self.states = (conv, tfa, inter)
        return output.transpose(0, 3, 1, 2)


def make_onnx_frame_runner(
    model: torch.nn.Module, path: str | Path, threads: int = 1
) -> FrameRunner:
    if isinstance(model, OfficialGTCRN):
        return OfficialOnnxFrameRunner(path, threads)
    if isinstance(model, OfficialULUNAS):
        return ULUNASOnnxFrameRunner(path, threads)
    if isinstance(model, HybridDualChannelGTCRN):
        return HybridOnnxFrameRunner(path, tuple(model.initial_state(1).shape), threads)
    if isinstance(model, FusionDualChannelULUNAS):
        return FusionOnnxFrameRunner(path, model.STATE_SIZE, threads)
    if isinstance(model, DeepFilterDualChannelNet):
        return FusionOnnxFrameRunner(path, model.STATE_SIZE, threads)
    if isinstance(model, CausalComplexMaskNet):
        return OnnxFrameRunner(path, tuple(model.initial_state(1).shape), threads)
    raise TypeError(f"No ONNX runner registered for {type(model).__name__}")


@dataclass
class HealthStatus:
    mode: str = "normal"
    consecutive_overruns: int = 0
    good_frames: int = 0
    failures: int = 0
    total_overruns: int = 0
    audio_status_events: int = 0
    last_inference_ms: float = 0.0
    reason: str = ""


class HealthMonitor:
    def __init__(
        self,
        deadline_seconds: float,
        max_consecutive_overruns: int = 3,
        recovery_frames: int = 100,
    ) -> None:
        self.deadline_seconds = float(deadline_seconds)
        self.max_consecutive_overruns = int(max_consecutive_overruns)
        self.recovery_frames = int(recovery_frames)
        self.status = HealthStatus()

    def observe(self, elapsed: float, valid: bool) -> None:
        self.status.last_inference_ms = elapsed * 1000.0
        overrun = elapsed > self.deadline_seconds
        if not valid:
            self.status.failures += 1
            self.status.mode, self.status.reason = "bypass", "invalid model output"
            self.status.good_frames = 0
            return
        if overrun:
            self.status.total_overruns += 1
            self.status.consecutive_overruns += 1
            self.status.good_frames = 0
            if self.status.consecutive_overruns >= self.max_consecutive_overruns:
                self.status.mode, self.status.reason = "degraded", "repeated inference deadline misses"
        else:
            self.status.consecutive_overruns = 0
            self.status.good_frames += 1
            if self.status.mode != "normal" and self.status.good_frames >= self.recovery_frames:
                self.status.mode, self.status.reason = "normal", ""

    def observe_audio_status(self, status: object) -> None:
        if status:
            self.status.audio_status_events += 1
            self.status.reason = f"audio callback status: {status}"


class OutputConditioner:
    def __init__(self, limit: float = 0.98, dc_blocker: bool = False) -> None:
        self.limit = float(limit)
        self.dc_blocker = bool(dc_blocker)
        self.reset()

    def reset(self) -> None:
        self.previous_input = 0.0
        self.previous_output = 0.0

    def process(self, audio: np.ndarray) -> np.ndarray:
        audio = np.nan_to_num(audio.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        if not self.dc_blocker:
            return np.clip(audio, -self.limit, self.limit)
        output = np.empty_like(audio)
        for index, sample in enumerate(audio):
            value = float(sample) - self.previous_input + 0.995 * self.previous_output
            self.previous_input = float(sample)
            self.previous_output = value
            output[index] = value
        return np.clip(output, -self.limit, self.limit)


class StreamingEnhancer:
    """Arbitrary-chunk causal WOLA runtime with health-triggered aligned dry bypass."""

    consumes_reference = False

    def __init__(
        self,
        runner: FrameRunner,
        sample_rate: int = 16000,
        n_fft: int = 512,
        hop_length: int = 128,
        wet_mix: float = 0.9,
        output_limit: float = 0.98,
        deadline_fraction: float = 0.9,
        max_consecutive_overruns: int = 3,
        recovery_frames: int = 100,
        dc_blocker: bool = False,
    ) -> None:
        self.runner = runner
        self.sample_rate = int(sample_rate)
        self.n_fft = int(n_fft)
        self.hop = int(hop_length)
        self.wet_mix = float(np.clip(wet_mix, 0.0, 1.0))
        self.window = sqrt_hann(n_fft).numpy().astype(np.float32)
        deadline = self.hop / self.sample_rate * float(deadline_fraction)
        self.monitor = HealthMonitor(deadline, max_consecutive_overruns, recovery_frames)
        self.conditioner = OutputConditioner(output_limit, dc_blocker)
        self.reset()

    @property
    def algorithmic_latency_samples(self) -> int:
        return self.n_fft - self.hop

    def reset(self) -> None:
        self.runner.reset()
        self.conditioner.reset()
        self.monitor.status = HealthStatus()
        self.input_buffer = np.zeros(self.n_fft - self.hop, dtype=np.float32)
        self.enhanced_accumulator = np.zeros(self.n_fft, dtype=np.float32)
        self.dry_accumulator = np.zeros(self.n_fft, dtype=np.float32)
        self.weight_accumulator = np.zeros(self.n_fft, dtype=np.float32)
        self.discard_samples = self.n_fft - self.hop
        self.total_input = 0
        self.total_output = 0

    def _frame(self, frame: np.ndarray) -> np.ndarray:
        spectrum = np.fft.rfft(frame * self.window).astype(np.complex64)
        spectrum_ri = np.stack((spectrum.real, spectrum.imag), axis=0)[None, ..., None]
        started = time.perf_counter()
        valid = True
        try:
            enhanced_ri = self.runner.enhance(spectrum_ri)
            valid = enhanced_ri.shape == spectrum_ri.shape and np.isfinite(enhanced_ri).all()
        except Exception:  # noqa: BLE001 - any backend failure must trigger aligned bypass
            enhanced_ri = spectrum_ri
            valid = False
        elapsed = time.perf_counter() - started
        self.monitor.observe(elapsed, valid)
        if not valid:
            enhanced_ri = spectrum_ri
        enhanced_complex = enhanced_ri[0, 0, :, 0] + 1j * enhanced_ri[0, 1, :, 0]
        enhanced = np.fft.irfft(enhanced_complex, n=self.n_fft).astype(np.float32) * self.window
        dry = np.fft.irfft(spectrum, n=self.n_fft).astype(np.float32) * self.window
        self.enhanced_accumulator += enhanced
        self.dry_accumulator += dry
        self.weight_accumulator += self.window**2
        denominator = np.maximum(self.weight_accumulator[: self.hop], 1e-8)
        wet = self.enhanced_accumulator[: self.hop] / denominator
        dry_hop = self.dry_accumulator[: self.hop] / denominator
        if self.monitor.status.mode == "normal":
            output = self.wet_mix * wet + (1.0 - self.wet_mix) * dry_hop
        else:
            output = dry_hop
        for accumulator in (
            self.enhanced_accumulator,
            self.dry_accumulator,
            self.weight_accumulator,
        ):
            accumulator[:-self.hop] = accumulator[self.hop :]
            accumulator[-self.hop :] = 0.0
        return output

    def _consume(self) -> np.ndarray:
        outputs: list[np.ndarray] = []
        while len(self.input_buffer) >= self.n_fft:
            outputs.append(self._frame(self.input_buffer[: self.n_fft]))
            self.input_buffer = self.input_buffer[self.hop :]
        if not outputs:
            return np.empty(0, dtype=np.float32)
        output = np.concatenate(outputs)
        if self.discard_samples:
            discard = min(self.discard_samples, len(output))
            output = output[discard:]
            self.discard_samples -= discard
        return output

    def process(self, audio: np.ndarray) -> np.ndarray:
        audio = np.nan_to_num(np.asarray(audio, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        self.total_input += len(audio)
        self.input_buffer = np.concatenate((self.input_buffer, audio))
        output = self._consume()
        self.total_output += len(output)
        return self.conditioner.process(output)

    def flush(self) -> np.ndarray:
        needed = self.total_input - self.total_output
        outputs: list[np.ndarray] = []
        while sum(map(len, outputs)) < needed:
            self.input_buffer = np.concatenate((self.input_buffer, np.zeros(self.hop, dtype=np.float32)))
            outputs.append(self._consume())
        output = np.concatenate(outputs)[:needed] if outputs else np.empty(0, dtype=np.float32)
        self.total_output += len(output)
        return self.conditioner.process(output)


class StreamingDualChannelEnhancer(StreamingEnhancer):
    """Aligned two-input WOLA runtime for primary/reference microphone audio."""

    consumes_reference = True

    runner: DualFrameRunner

    def reset(self) -> None:
        super().reset()
        self.reference_buffer = np.zeros(self.n_fft - self.hop, dtype=np.float32)
        self._duplicate_reference_frames = 0
        self._distinct_reference_frames = 0
        self._reference_unusable = False

    def _update_reference_health(
        self, primary_frame: np.ndarray, reference_frame: np.ndarray
    ) -> None:
        primary = primary_frame.astype(np.float64) - float(np.mean(primary_frame))
        reference = reference_frame.astype(np.float64) - float(np.mean(reference_frame))
        denominator = float(np.linalg.norm(primary) * np.linalg.norm(reference))
        correlation = (
            float(np.dot(primary, reference) / denominator)
            if denominator > 1e-12
            else 0.0
        )
        primary_rms = float(np.sqrt(np.mean(primary**2)))
        reference_rms = float(np.sqrt(np.mean(reference**2)))
        difference = float(
            np.sqrt(np.mean((primary - reference) ** 2))
            / max(primary_rms + reference_rms, 1e-12)
        )
        duplicated = (
            max(primary_rms, reference_rms) >= 1e-5
            and abs(correlation) >= 0.995
            and difference <= 0.05
        )
        if duplicated:
            self._duplicate_reference_frames += 1
            self._distinct_reference_frames = 0
        else:
            self._duplicate_reference_frames = max(0, self._duplicate_reference_frames - 1)
            self._distinct_reference_frames += 1
        if not self._reference_unusable and self._duplicate_reference_frames >= 8:
            self._reference_unusable = True
            self.runner.reset()
        elif self._reference_unusable and self._distinct_reference_frames >= 50:
            self._reference_unusable = False
            self.runner.reset()

    def _frame_pair(self, primary_frame: np.ndarray, reference_frame: np.ndarray) -> np.ndarray:
        self._update_reference_health(primary_frame, reference_frame)
        primary_spectrum = np.fft.rfft(primary_frame * self.window).astype(np.complex64)
        reference_spectrum = np.fft.rfft(reference_frame * self.window).astype(np.complex64)
        primary_ri = np.stack(
            (primary_spectrum.real, primary_spectrum.imag), axis=0
        )[None, ..., None]
        reference_ri = np.stack(
            (reference_spectrum.real, reference_spectrum.imag), axis=0
        )[None, ..., None]
        started = time.perf_counter()
        valid = True
        if self._reference_unusable:
            enhanced_ri = primary_ri
            self.monitor.status.mode = "bypass"
            self.monitor.status.reason = (
                "primary/reference channels are effectively duplicated; safe dry bypass"
            )
        else:
            try:
                enhanced_ri = self.runner.enhance(primary_ri, reference_ri)
                valid = enhanced_ri.shape == primary_ri.shape and np.isfinite(enhanced_ri).all()
            except Exception:  # noqa: BLE001 - backend failure must trigger aligned bypass
                enhanced_ri = primary_ri
                valid = False
            self.monitor.observe(time.perf_counter() - started, valid)
            if self.monitor.status.mode == "bypass" and not self.monitor.status.reason:
                self.monitor.status.reason = "invalid model output"
        if not valid:
            enhanced_ri = primary_ri
        enhanced_complex = enhanced_ri[0, 0, :, 0] + 1j * enhanced_ri[0, 1, :, 0]
        enhanced = np.fft.irfft(enhanced_complex, n=self.n_fft).astype(np.float32) * self.window
        dry = np.fft.irfft(primary_spectrum, n=self.n_fft).astype(np.float32) * self.window
        self.enhanced_accumulator += enhanced
        self.dry_accumulator += dry
        self.weight_accumulator += self.window**2
        denominator = np.maximum(self.weight_accumulator[: self.hop], 1e-8)
        wet = self.enhanced_accumulator[: self.hop] / denominator
        dry_hop = self.dry_accumulator[: self.hop] / denominator
        output = (
            self.wet_mix * wet + (1.0 - self.wet_mix) * dry_hop
            if self.monitor.status.mode == "normal"
            else dry_hop
        )
        for accumulator in (
            self.enhanced_accumulator,
            self.dry_accumulator,
            self.weight_accumulator,
        ):
            accumulator[:-self.hop] = accumulator[self.hop :]
            accumulator[-self.hop :] = 0.0
        return output

    def _consume_pair(self) -> np.ndarray:
        outputs: list[np.ndarray] = []
        while len(self.input_buffer) >= self.n_fft and len(self.reference_buffer) >= self.n_fft:
            outputs.append(
                self._frame_pair(
                    self.input_buffer[: self.n_fft], self.reference_buffer[: self.n_fft]
                )
            )
            self.input_buffer = self.input_buffer[self.hop :]
            self.reference_buffer = self.reference_buffer[self.hop :]
        if not outputs:
            return np.empty(0, dtype=np.float32)
        output = np.concatenate(outputs)
        if self.discard_samples:
            discard = min(self.discard_samples, len(output))
            output = output[discard:]
            self.discard_samples -= discard
        return output

    def process(self, primary: np.ndarray, reference: np.ndarray) -> np.ndarray:
        primary = np.nan_to_num(np.asarray(primary, dtype=np.float32))
        reference = np.nan_to_num(np.asarray(reference, dtype=np.float32))
        if len(primary) != len(reference):
            raise ValueError("primary and reference chunks must have equal length")
        self.total_input += len(primary)
        self.input_buffer = np.concatenate((self.input_buffer, primary))
        self.reference_buffer = np.concatenate((self.reference_buffer, reference))
        output = self._consume_pair()
        self.total_output += len(output)
        return self.conditioner.process(output)

    def flush(self) -> np.ndarray:
        needed = self.total_input - self.total_output
        outputs: list[np.ndarray] = []
        while sum(map(len, outputs)) < needed:
            zeros = np.zeros(self.hop, dtype=np.float32)
            self.input_buffer = np.concatenate((self.input_buffer, zeros))
            self.reference_buffer = np.concatenate((self.reference_buffer, zeros))
            outputs.append(self._consume_pair())
        output = np.concatenate(outputs)[:needed] if outputs else np.empty(0, dtype=np.float32)
        self.total_output += len(output)
        return self.conditioner.process(output)


class HybridStreamingEnhancer:
    """Two-stage hybrid runtime: adaptive filter + neural enhancer.

    Stage 1 (classical): a NormalizedLMS canceller subtracts the component of
    the primary microphone that is coherent with the reference microphone —
    steady background noise the linear filter can track. Stage 2 (neural):
    the WOLA enhancer cleans the residual, which still carries impulsive and
    uncorrelated noise a linear filter cannot model. This is the hybrid
    AI/ML + adaptive-filtering chain requested by the problem statement.

    The neural stage receives the raw reference when it is dual-channel, so
    its spatial features are not degraded by the LMS stage; a mono neural
    model receives only the LMS residual. ``process`` always takes
    ``(primary, reference)``. The LMS adds no algorithmic latency; the hybrid
    latency equals the inner WOLA runtime's.
    """

    consumes_reference = True

    def __init__(
        self,
        runner: FrameRunner | DualFrameRunner,
        *,
        sample_rate: int = 16000,
        n_fft: int = 512,
        hop_length: int = 128,
        neural_dual_channel: bool,
        lms_taps: int = 128,
        lms_step_size: float = 0.05,
        lms_leakage: float = 1e-5,
        **kwargs: Any,
    ) -> None:
        inner: StreamingEnhancer | StreamingDualChannelEnhancer
        inner_class = StreamingDualChannelEnhancer if neural_dual_channel else StreamingEnhancer
        inner = inner_class(
            runner,
            sample_rate=sample_rate,
            n_fft=n_fft,
            hop_length=hop_length,
            **kwargs,
        )
        self.inner = inner
        self.neural_dual_channel = bool(neural_dual_channel)
        self.lms = NormalizedLMS(taps=lms_taps, step_size=lms_step_size, leakage=lms_leakage)
        self._raw_duplicate_frames = 0
        self._raw_distinct_frames = 0
        self._raw_reference_unusable = False

    @property
    def monitor(self) -> HealthMonitor:
        return self.inner.monitor

    @property
    def wet_mix(self) -> float:
        return self.inner.wet_mix

    @property
    def conditioner(self) -> OutputConditioner:
        return self.inner.conditioner

    @property
    def algorithmic_latency_samples(self) -> int:
        return self.inner.algorithmic_latency_samples

    def reset(self) -> None:
        self.lms.reset()
        self.inner.reset()
        self._raw_duplicate_frames = 0
        self._raw_distinct_frames = 0
        self._raw_reference_unusable = False

    def _update_raw_reference_health(
        self, primary: np.ndarray, reference: np.ndarray
    ) -> None:
        """Validate physical channels before LMS can decorrelate duplicates."""
        primary64 = primary.astype(np.float64) - float(np.mean(primary))
        reference64 = reference.astype(np.float64) - float(np.mean(reference))
        primary_rms = float(np.sqrt(np.mean(primary64**2)))
        reference_rms = float(np.sqrt(np.mean(reference64**2)))
        denominator = float(np.linalg.norm(primary64) * np.linalg.norm(reference64))
        correlation = (
            float(np.dot(primary64, reference64) / denominator)
            if denominator > 1e-12
            else 0.0
        )
        difference = float(
            np.sqrt(np.mean((primary64 - reference64) ** 2))
            / max(primary_rms + reference_rms, 1e-12)
        )
        active = max(primary_rms, reference_rms) >= 1e-5
        duplicated = active and abs(correlation) >= 0.999 and difference <= 0.01
        if not active:
            return
        if duplicated:
            self._raw_duplicate_frames += 1
            self._raw_distinct_frames = 0
        else:
            self._raw_duplicate_frames = max(0, self._raw_duplicate_frames - 1)
            self._raw_distinct_frames += 1
        if not self._raw_reference_unusable and self._raw_duplicate_frames >= 16:
            self._raw_reference_unusable = True
            self.lms.reset()
            if isinstance(self.inner, StreamingDualChannelEnhancer):
                self.inner._reference_unusable = True
                self.inner.runner.reset()
        elif self._raw_reference_unusable and self._raw_distinct_frames >= 125:
            self._raw_reference_unusable = False
            self.lms.reset()
            if isinstance(self.inner, StreamingDualChannelEnhancer):
                self.inner._reference_unusable = False
                self.inner.runner.reset()

    def process(self, primary: np.ndarray, reference: np.ndarray) -> np.ndarray:
        primary = np.nan_to_num(np.asarray(primary, dtype=np.float32))
        reference = np.nan_to_num(np.asarray(reference, dtype=np.float32))
        if len(primary) != len(reference):
            raise ValueError("primary and reference chunks must have equal length")
        self._update_raw_reference_health(primary, reference)
        if self._raw_reference_unusable:
            if self.neural_dual_channel:
                return self.inner.process(primary, reference)
            self.inner.monitor.status.mode = "bypass"
            self.inner.monitor.status.reason = (
                "primary/reference channels are effectively duplicated; safe dry bypass"
            )
            return self.inner.process(primary)
        residual, _ = self.lms.process(primary, reference)
        if self.neural_dual_channel:
            return self.inner.process(residual, reference)
        return self.inner.process(residual)

    def flush(self) -> np.ndarray:
        # The residual tail is already buffered in the inner runtime; the LMS
        # is linear so flushing silence through it would only inject the
        # decaying filter estimate into the session tail.
        return self.inner.flush()
