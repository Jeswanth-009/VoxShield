"""Non-blocking bridge between a real-time audio callback and neural inference."""

from __future__ import annotations

import queue
import threading
from dataclasses import asdict, dataclass

import numpy as np

from .runtime import StreamingDualChannelEnhancer, StreamingEnhancer


@dataclass
class LiveEngineStats:
    submitted_blocks: int = 0
    enhanced_blocks: int = 0
    bypass_blocks: int = 0
    output_underflows: int = 0
    dropped_input_blocks: int = 0
    stream_resets: int = 0
    worker_failures: int = 0


@dataclass
class _InputBlock:
    sequence: int
    primary: np.ndarray
    reference: np.ndarray | None


class AsyncLiveEngine:
    """Run the stateful enhancer outside the PortAudio callback.

    The callback submits one hop and requests one aligned output hop. A single
    additional hop gives the worker time to finish. If a result misses its
    playout time, the corresponding delayed primary block is returned instead;
    late neural output is discarded rather than shifting the conversation.
    """

    def __init__(
        self,
        stream: StreamingEnhancer | StreamingDualChannelEnhancer,
        hop_length: int,
        *,
        queue_blocks: int = 8,
        playout_extra_blocks: int = 1,
    ) -> None:
        if hop_length <= 0 or queue_blocks < 2 or playout_extra_blocks < 1:
            raise ValueError("invalid live-engine buffering configuration")
        self.stream = stream
        self.hop = int(hop_length)
        self.dual_channel = bool(
            getattr(stream, "consumes_reference", isinstance(stream, StreamingDualChannelEnhancer))
        )
        self.algorithmic_blocks = int(
            np.ceil(stream.algorithmic_latency_samples / self.hop)
        )
        self.playout_delay_blocks = self.algorithmic_blocks + int(playout_extra_blocks)
        self.input_queue: queue.Queue[_InputBlock | None] = queue.Queue(maxsize=queue_blocks)
        self.stats = LiveEngineStats()
        self._outputs: dict[int, np.ndarray] = {}
        self._dry: dict[int, np.ndarray] = {}
        self._lock = threading.Lock()
        self._sequence = 0
        self._rendered_through = -1
        self._closed = False
        self._worker = threading.Thread(
            target=self._run,
            name="voxshield-inference",
            daemon=True,
        )
        self._worker.start()

    @property
    def added_latency_samples(self) -> int:
        return self.playout_delay_blocks * self.hop

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return asdict(self.stats)

    def _clear_outputs(self) -> None:
        with self._lock:
            self._outputs.clear()

    def _run(self) -> None:
        previous_sequence: int | None = None
        while True:
            item = self.input_queue.get()
            if item is None:
                return
            if previous_sequence is not None and item.sequence != previous_sequence + 1:
                self.stream.reset()
                self._clear_outputs()
                with self._lock:
                    self.stats.stream_resets += 1
            previous_sequence = item.sequence
            try:
                if self.dual_channel:
                    assert item.reference is not None
                    output = self.stream.process(item.primary, item.reference)
                else:
                    output = self.stream.process(item.primary)
            except Exception:  # noqa: BLE001 - worker failure must fall back, never kill callback
                self.stream.reset()
                with self._lock:
                    self.stats.worker_failures += 1
                    self.stats.stream_resets += 1
                    self._outputs.clear()
                continue
            if len(output) != self.hop:
                continue
            source_sequence = item.sequence - self.algorithmic_blocks
            with self._lock:
                if source_sequence > self._rendered_through:
                    self._outputs[source_sequence] = np.asarray(output, dtype=np.float32).copy()

    def _enqueue(self, item: _InputBlock) -> None:
        try:
            self.input_queue.put_nowait(item)
            return
        except queue.Full:
            pass
        try:
            self.input_queue.get_nowait()
        except queue.Empty:
            pass
        with self._lock:
            self.stats.dropped_input_blocks += 1
        try:
            self.input_queue.put_nowait(item)
        except queue.Full:
            with self._lock:
                self.stats.dropped_input_blocks += 1

    def submit_and_render(
        self,
        primary: np.ndarray,
        reference: np.ndarray | None = None,
    ) -> np.ndarray:
        if self._closed:
            raise RuntimeError("live engine is closed")
        primary = np.nan_to_num(
            np.asarray(primary, dtype=np.float32).reshape(-1),
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )
        if len(primary) != self.hop:
            raise ValueError(f"callback block must contain exactly {self.hop} samples")
        if self.dual_channel:
            if reference is None:
                raise ValueError("dual-channel runtime requires reference samples")
            reference = np.nan_to_num(
                np.asarray(reference, dtype=np.float32).reshape(-1),
                nan=0.0,
                posinf=0.0,
                neginf=0.0,
            )
            if len(reference) != self.hop:
                raise ValueError("reference block must match primary block")
        sequence = self._sequence
        self._sequence += 1
        with self._lock:
            self.stats.submitted_blocks += 1
            self._dry[sequence] = primary.copy()
        self._enqueue(_InputBlock(sequence, primary.copy(), reference.copy() if reference is not None else None))
        target = sequence - self.playout_delay_blocks
        if target < 0:
            return np.zeros(self.hop, dtype=np.float32)
        with self._lock:
            enhanced = self._outputs.pop(target, None)
            dry = self._dry.pop(target, np.zeros(self.hop, dtype=np.float32))
            self._rendered_through = target
            stale_outputs = [key for key in self._outputs if key <= target]
            for key in stale_outputs:
                self._outputs.pop(key, None)
            stale_dry = [key for key in self._dry if key < target]
            for key in stale_dry:
                self._dry.pop(key, None)
            if enhanced is None:
                self.stats.output_underflows += 1
                self.stats.bypass_blocks += 1
                return dry
            self.stats.enhanced_blocks += 1
            return enhanced

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.input_queue.put_nowait(None)
        except queue.Full:
            try:
                self.input_queue.get_nowait()
            except queue.Empty:
                pass
            self.input_queue.put_nowait(None)
        self._worker.join(timeout=2.0)

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
