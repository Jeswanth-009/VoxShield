import numpy as np

from voxshield.model import CausalComplexMaskNet
from voxshield.runtime import (
    HybridStreamingEnhancer,
    StreamingDualChannelEnhancer,
    StreamingEnhancer,
    TorchFrameRunner,
)


def _model() -> CausalComplexMaskNet:
    return CausalComplexMaskNet(
        n_fft=512,
        sample_rate=16000,
        channels=8,
        recurrent_blocks=1,
    ).eval()


def test_streaming_arbitrary_chunks_preserves_length_and_is_finite() -> None:
    rng = np.random.default_rng(8)
    audio = (rng.normal(size=1003) * 0.05).astype(np.float32)
    stream = StreamingEnhancer(
        TorchFrameRunner(_model()),
        sample_rate=16000,
        n_fft=512,
        hop_length=128,
        wet_mix=1.0,
        deadline_fraction=1000.0,
    )
    sizes = [1, 7, 31, 2, 64, 13, 111, 256, 518]
    outputs = []
    position = 0
    for size in sizes:
        outputs.append(stream.process(audio[position : position + size]))
        position += size
    outputs.append(stream.flush())
    result = np.concatenate(outputs)
    assert len(result) == len(audio)
    assert np.isfinite(result).all()
    assert np.max(np.abs(result)) <= 0.98


class BrokenRunner:
    def reset(self) -> None:
        pass

    def enhance(self, spectrum_ri: np.ndarray) -> np.ndarray:
        return np.full_like(spectrum_ri, np.nan)


def test_invalid_model_output_activates_bypass() -> None:
    stream = StreamingEnhancer(BrokenRunner(), n_fft=512, hop_length=128)
    stream.process(np.ones(1024, dtype=np.float32) * 0.01)
    assert stream.monitor.status.mode == "bypass"
    assert stream.monitor.status.failures > 0


class SilencingDualRunner:
    def __init__(self) -> None:
        self.calls = 0

    def reset(self) -> None:
        pass

    def enhance(self, primary_ri: np.ndarray, reference_ri: np.ndarray) -> np.ndarray:
        self.calls += 1
        return np.zeros_like(primary_ri)


def test_duplicated_reference_activates_safe_dry_bypass() -> None:
    runner = SilencingDualRunner()
    stream = StreamingDualChannelEnhancer(
        runner,
        n_fft=512,
        hop_length=256,
        wet_mix=1.0,
        deadline_fraction=1000.0,
    )
    time = np.arange(256, dtype=np.float32) / 16000.0
    block = (0.1 * np.sin(2.0 * np.pi * 440.0 * time)).astype(np.float32)
    outputs = [stream.process(block, block.copy()) for _ in range(16)]
    audible = np.concatenate([value for value in outputs if len(value)])
    assert stream.monitor.status.mode == "bypass"
    assert "duplicated" in stream.monitor.status.reason
    assert np.max(np.abs(audible[-512:])) > 0.01


def test_hybrid_checks_raw_channels_before_lms() -> None:
    runner = SilencingDualRunner()
    stream = HybridStreamingEnhancer(
        runner,
        sample_rate=16000,
        n_fft=512,
        hop_length=256,
        neural_dual_channel=True,
        wet_mix=1.0,
        deadline_fraction=1000.0,
    )
    time = np.arange(256, dtype=np.float32) / 16000.0
    block = (0.1 * np.sin(2.0 * np.pi * 440.0 * time)).astype(np.float32)
    outputs = [stream.process(block, block.copy()) for _ in range(32)]
    audible = np.concatenate([value for value in outputs if len(value)])
    assert stream.monitor.status.mode == "bypass"
    assert "duplicated" in stream.monitor.status.reason
    assert np.max(np.abs(audible[-512:])) > 0.01
