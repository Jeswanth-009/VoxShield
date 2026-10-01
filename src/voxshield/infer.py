from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch

from .audio import read_audio, sanitize_audio, write_audio
from .checkpoint import load_model, verify_onnx_pair
from .runtime import (
    HybridStreamingEnhancer,
    StreamingDualChannelEnhancer,
    StreamingEnhancer,
    make_onnx_frame_runner,
    make_torch_frame_runner,
)


def build_stream(
    checkpoint: str,
    onnx_path: str | None,
    device: str,
    wet_mix: float | None = None,
    use_lms: bool = False,
    lms_taps: int = 128,
    lms_step_size: float = 0.05,
) -> tuple[StreamingEnhancer, dict]:
    model, config, _ = load_model(checkpoint, device if not onnx_path else "cpu")
    if onnx_path:
        verify_onnx_pair(checkpoint, onnx_path)
        runner = make_onnx_frame_runner(
            model, onnx_path, config.get("onnx", {}).get("intra_op_threads", 1)
        )
    else:
        runner = make_torch_frame_runner(model, device)
    runtime = dict(config["runtime"])
    if wet_mix is not None:
        if not 0.0 <= wet_mix <= 1.0:
            raise ValueError("wet_mix must be between 0 and 1")
        runtime["wet_mix"] = wet_mix
    # File inference/evaluation is not a real-time callback. A transient CUDA or
    # Python scheduling delay must never silently replace enhanced audio with dry
    # input; the live command retains the configured deadline-based safe bypass.
    runtime["deadline_fraction"] = float("inf")
    neural_dual_channel = bool(getattr(model, "requires_reference", False))
    if use_lms:
        stream = HybridStreamingEnhancer(
            runner,
            sample_rate=config["audio"]["sample_rate"],
            n_fft=config["audio"]["n_fft"],
            hop_length=config["audio"]["hop_length"],
            neural_dual_channel=neural_dual_channel,
            lms_taps=lms_taps,
            lms_step_size=lms_step_size,
            **runtime,
        )
    else:
        stream_class = (
            StreamingDualChannelEnhancer if neural_dual_channel else StreamingEnhancer
        )
        stream = stream_class(
            runner,
            sample_rate=config["audio"]["sample_rate"],
            n_fft=config["audio"]["n_fft"],
            hop_length=config["audio"]["hop_length"],
            **runtime,
        )
    return stream, config


def enhance_file(
    input_path: str | Path,
    output_path: str | Path,
    checkpoint: str,
    device: str = "cpu",
    onnx_path: str | None = None,
    chunk_samples: int = 4096,
    stream: StreamingEnhancer | None = None,
    config: dict | None = None,
    wet_mix: float | None = None,
    reference_path: str | Path | None = None,
    use_lms: bool = False,
    lms_taps: int = 128,
    lms_step_size: float = 0.05,
) -> dict[str, object]:
    if stream is None or config is None:
        stream, config = build_stream(
            checkpoint, onnx_path, device, wet_mix, use_lms, lms_taps, lms_step_size
        )
    else:
        stream.reset()
    sample_rate = config["audio"]["sample_rate"]
    audio = read_audio(input_path, sample_rate)
    consumes_reference = bool(
        getattr(stream, "consumes_reference", isinstance(stream, StreamingDualChannelEnhancer))
    )
    if consumes_reference:
        if reference_path is None:
            raise ValueError(
                "This checkpoint requires synchronized reference audio; pass --reference"
            )
        reference = read_audio(reference_path, sample_rate)
        if len(reference) != len(audio):
            raise ValueError("Primary and reference files must have the same sample count")
        pieces = [
            stream.process(
                audio[start : start + chunk_samples],
                reference[start : start + chunk_samples],
            )
            for start in range(0, len(audio), chunk_samples)
        ]
    else:
        pieces = [
            stream.process(audio[start : start + chunk_samples])
            for start in range(0, len(audio), chunk_samples)
        ]
    pieces.append(stream.flush())
    output = np.concatenate([piece for piece in pieces if len(piece)]) if pieces else np.empty(0)
    output = sanitize_audio(output[: len(audio)])
    write_audio(output_path, output, sample_rate)
    return {
        "input_samples": len(audio),
        "output_samples": len(output),
        "sample_rate": sample_rate,
        "algorithmic_latency_ms": 1000.0 * stream.algorithmic_latency_samples / sample_rate,
        "runtime_mode": stream.monitor.status.mode,
        "runtime_reason": stream.monitor.status.reason,
        "wet_mix": stream.wet_mix,
        "input_channels": 2 if consumes_reference else 1,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline or chunked VoxShield inference")
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--onnx", default=None)
    parser.add_argument(
        "--reference",
        default=None,
        help="Synchronized reference-microphone WAV required by dual-channel v4 models",
    )
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--chunk-samples", type=int, default=4096)
    parser.add_argument(
        "--wet-mix",
        type=float,
        default=None,
        help="Enhanced fraction from 0 to 1; lower values preserve more aligned input",
    )
    parser.add_argument(
        "--lms",
        action="store_true",
        help="Run the hybrid chain: NormalizedLMS pre-cancellation from the "
        "reference channel, then the neural model on the residual",
    )
    parser.add_argument("--lms-taps", type=int, default=128)
    parser.add_argument("--lms-step-size", type=float, default=0.05)
    args = parser.parse_args()
    result = enhance_file(
        args.input,
        args.output,
        args.checkpoint,
        args.device,
        args.onnx,
        args.chunk_samples,
        wet_mix=args.wet_mix,
        reference_path=args.reference,
        use_lms=args.lms,
        lms_taps=args.lms_taps,
        lms_step_size=args.lms_step_size,
    )
    print(result)


if __name__ == "__main__":
    main()
