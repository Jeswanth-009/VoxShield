from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path

import numpy as np

from .checkpoint import load_model, verify_onnx_pair
from .runtime import (
    StreamingDualChannelEnhancer,
    StreamingEnhancer,
    make_onnx_frame_runner,
    make_torch_frame_runner,
)


def _memory_mb() -> float | None:
    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark frame latency, RTF, and memory")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--onnx", default=None)
    parser.add_argument("--tensorrt", default=None, help="TensorRT .engine file (Jetson only)")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--warmup", type=int, default=100)
    parser.add_argument("--frames", type=int, default=2000)
    parser.add_argument("--output", default="artifacts/benchmark.json")
    args = parser.parse_args()
    model, config, _ = load_model(args.checkpoint, args.device if not (args.onnx or args.tensorrt) else "cpu")
    if args.onnx:
        verify_onnx_pair(args.checkpoint, args.onnx)
    if args.tensorrt:
        from .export_tensorrt import TensorRTFrameRunner

        runner = TensorRTFrameRunner(args.tensorrt)
        backend = "tensorrt"
    else:
        runner = (
            make_onnx_frame_runner(model, args.onnx, args.threads)
            if args.onnx
            else make_torch_frame_runner(model, args.device)
        )
        backend = "onnxruntime" if args.onnx else f"pytorch-{args.device}"
    frequency = config["audio"]["n_fft"] // 2 + 1
    frame = np.random.default_rng(0).normal(0, 0.1, (1, 2, frequency, 1)).astype(np.float32)
    reference_frame = np.random.default_rng(2).normal(
        0, 0.1, (1, 2, frequency, 1)
    ).astype(np.float32)
    dual_channel = bool(getattr(model, "requires_reference", False))
    for _ in range(args.warmup):
        runner.enhance(frame, reference_frame) if dual_channel else runner.enhance(frame)
    runner.reset()
    memory_before = _memory_mb()
    timings = []
    for _ in range(args.frames):
        start = time.perf_counter()
        runner.enhance(frame, reference_frame) if dual_channel else runner.enhance(frame)
        timings.append(time.perf_counter() - start)
    memory_after = _memory_mb()
    frame_seconds = config["audio"]["hop_length"] / config["audio"]["sample_rate"]
    ordered = sorted(timings)
    runner.reset()
    stream_class = StreamingDualChannelEnhancer if dual_channel else StreamingEnhancer
    stream = stream_class(
        runner,
        sample_rate=config["audio"]["sample_rate"],
        n_fft=config["audio"]["n_fft"],
        hop_length=config["audio"]["hop_length"],
        **config["runtime"],
    )
    rng = np.random.default_rng(1)
    callback_times = []
    process_cpu_start = time.process_time()
    process_wall_start = time.perf_counter()
    for _ in range(args.frames):
        block = rng.normal(0.0, 0.03, config["audio"]["hop_length"]).astype(np.float32)
        start = time.perf_counter()
        if dual_channel:
            reference_block = rng.normal(
                0.0, 0.03, config["audio"]["hop_length"]
            ).astype(np.float32)
            stream.process(block, reference_block)
        else:
            stream.process(block)
        callback_times.append(time.perf_counter() - start)
    stream.flush()
    process_wall = time.perf_counter() - process_wall_start
    process_cpu = time.process_time() - process_cpu_start
    callback_ordered = sorted(callback_times)
    report = {
        "backend": backend,
        "input_channels": 2 if dual_channel else 1,
        "frames": args.frames,
        "frame_duration_ms": frame_seconds * 1000,
        "mean_latency_ms": statistics.mean(timings) * 1000,
        "p50_latency_ms": ordered[int(0.50 * (len(ordered) - 1))] * 1000,
        "p95_latency_ms": ordered[int(0.95 * (len(ordered) - 1))] * 1000,
        "p99_latency_ms": ordered[int(0.99 * (len(ordered) - 1))] * 1000,
        "real_time_factor": sum(timings) / (args.frames * frame_seconds),
        "full_pipeline_real_time_factor": process_wall / (args.frames * frame_seconds),
        "full_pipeline_p99_callback_ms": callback_ordered[int(0.99 * (len(callback_ordered) - 1))] * 1000,
        "process_cpu_percent_during_pipeline": 100.0 * process_cpu / max(process_wall, 1e-9),
        "rss_before_mb": memory_before,
        "rss_after_mb": memory_after,
        "rss_delta_mb": None if memory_before is None else memory_after - memory_before,
        "meets_realtime_mean": statistics.mean(timings) < frame_seconds,
        "runtime_deadline_overruns": stream.monitor.status.total_overruns,
        "dropped_or_underflowed_audio_callbacks": stream.monitor.status.audio_status_events,
        "algorithmic_latency_ms":
            1000
            * (config["audio"]["n_fft"] - config["audio"]["hop_length"])
            / config["audio"]["sample_rate"],
        "end_to_end_latency_ms": None,
        "end_to_end_latency_note": "Measure with physical loopback; model timing is not audio I/O latency.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
