import time

import numpy as np

from voxshield.live_engine import AsyncLiveEngine


class DelayedPassthrough:
    algorithmic_latency_samples = 8

    def __init__(self) -> None:
        self.blocks: list[np.ndarray] = []
        self.monitor = type("Monitor", (), {"status": type("Status", (), {"mode": "normal"})()})()

    def reset(self) -> None:
        self.blocks.clear()

    def process(self, audio: np.ndarray) -> np.ndarray:
        self.blocks.append(audio.copy())
        if len(self.blocks) <= 2:
            return np.empty(0, dtype=np.float32)
        return self.blocks.pop(0)


def test_async_live_engine_returns_aligned_enhanced_block() -> None:
    stream = DelayedPassthrough()
    with AsyncLiveEngine(stream, 4, queue_blocks=4, playout_extra_blocks=1) as engine:
        outputs = []
        for index in range(5):
            outputs.append(engine.submit_and_render(np.full(4, index, dtype=np.float32)))
            time.sleep(0.01)
    assert np.array_equal(outputs[3], np.zeros(4, dtype=np.float32))
    assert np.array_equal(outputs[4], np.ones(4, dtype=np.float32))
    stats = engine.snapshot()
    assert stats["enhanced_blocks"] >= 1


def test_async_live_engine_uses_delayed_dry_fallback() -> None:
    stream = DelayedPassthrough()

    def slow_process(audio: np.ndarray) -> np.ndarray:
        time.sleep(0.05)
        return audio.copy()

    stream.process = slow_process  # type: ignore[method-assign]
    with AsyncLiveEngine(stream, 4, queue_blocks=2, playout_extra_blocks=1) as engine:
        outputs = [
            engine.submit_and_render(np.full(4, index, dtype=np.float32))
            for index in range(5)
        ]
    assert np.array_equal(outputs[3], np.zeros(4, dtype=np.float32))
    assert np.array_equal(outputs[4], np.ones(4, dtype=np.float32))
    assert engine.snapshot()["output_underflows"] >= 2
