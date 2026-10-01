"""Guarded dynamic INT8 quantization for stateful streaming VoxShield ONNX models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

from .checkpoint import sha256_file, verify_onnx_pair


def _shape(values: list[Any]) -> tuple[int, ...]:
    result = []
    for value in values:
        if isinstance(value, int) and value > 0:
            result.append(value)
        else:
            result.append(1)
    return tuple(result)


def _session(path: str | Path):
    try:
        import onnxruntime as ort
    except ImportError as exc:
        raise RuntimeError("Install the ONNX extra: pip install -e .[onnx]") from exc
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(
        str(path),
        sess_options=options,
        providers=["CPUExecutionProvider"],
    )


def _state_output_name(state_name: str) -> str:
    if state_name == "state_in":
        return "state_out"
    if state_name.endswith("_cache"):
        return state_name + "_out"
    raise ValueError(f"unrecognized state input: {state_name}")


def validate_quantized_pair(
    original_path: str | Path,
    quantized_path: str | Path,
    *,
    frames: int = 64,
    seed: int = 26052,
) -> dict[str, Any]:
    original = _session(original_path)
    quantized = _session(quantized_path)
    original_inputs = {value.name: value for value in original.get_inputs()}
    quantized_inputs = {value.name: value for value in quantized.get_inputs()}
    if original_inputs.keys() != quantized_inputs.keys():
        raise ValueError("quantized model input contract differs from the original")
    output_names = [value.name for value in original.get_outputs()]
    if output_names != [value.name for value in quantized.get_outputs()]:
        raise ValueError("quantized model output contract differs from the original")
    state_names = [
        name for name in original_inputs
        if name == "state_in" or name.endswith("_cache")
    ]
    frame_names = [name for name in original_inputs if name not in state_names]
    if not frame_names or not state_names:
        raise ValueError(
            "INT8 helper requires a stateful streaming ONNX model with frame and state inputs"
        )
    state_outputs = {name: _state_output_name(name) for name in state_names}
    missing = [name for name in state_outputs.values() if name not in output_names]
    if missing:
        raise ValueError(f"state outputs missing from the ONNX contract: {missing}")
    rng = np.random.default_rng(seed)
    original_states = {
        name: np.zeros(_shape(original_inputs[name].shape), dtype=np.float32)
        for name in state_names
    }
    quantized_states = {name: state.copy() for name, state in original_states.items()}
    primary_output = "enhanced" if "enhanced" in output_names else output_names[0]
    output_errors = []
    state_errors = []
    for _ in range(frames):
        feeds = {
            name: rng.normal(
                0.0,
                0.1,
                _shape(original_inputs[name].shape),
            ).astype(np.float32)
            for name in frame_names
        }
        original_outputs = original.run(output_names, {**feeds, **original_states})
        quantized_outputs = quantized.run(output_names, {**feeds, **quantized_states})
        if not all(np.isfinite(value).all() for value in quantized_outputs):
            raise ValueError("quantized model produced NaN or Inf")
        original_map = dict(zip(output_names, original_outputs))
        quantized_map = dict(zip(output_names, quantized_outputs))
        output_errors.append(
            float(np.max(np.abs(original_map[primary_output] - quantized_map[primary_output])))
        )
        state_errors.append(
            max(
                float(np.max(np.abs(original_map[out] - quantized_map[out])))
                for out in state_outputs.values()
            )
        )
        for name, out in state_outputs.items():
            original_states[name] = original_map[out]
            quantized_states[name] = quantized_map[out]
    return {
        "frames": frames,
        "primary_output": primary_output,
        "state_outputs": sorted(state_outputs.values()),
        "maximum_output_absolute_error": max(output_errors),
        "p99_output_absolute_error": float(np.percentile(output_errors, 99)),
        "maximum_state_absolute_error": max(state_errors),
        "p99_state_absolute_error": float(np.percentile(state_errors, 99)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dynamically quantize and numerically guard a stateful streaming ONNX model"
    )
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--input", required=True, help="Validated FP32 ONNX model")
    parser.add_argument("--output", required=True, help="Destination INT8 ONNX model")
    parser.add_argument("--frames", type=int, default=64)
    parser.add_argument("--max-output-error", type=float, default=0.10)
    parser.add_argument("--max-state-error", type=float, default=0.25)
    args = parser.parse_args()
    if args.frames < 1 or args.max_output_error <= 0 or args.max_state_error <= 0:
        parser.error("frames and error thresholds must be positive")
    verify_onnx_pair(args.checkpoint, args.input)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        from onnxruntime.quantization import QuantType, quantize_dynamic
    except ImportError as exc:
        raise SystemExit("Install the ONNX extra: pip install -e .[onnx]") from exc
    quantize_dynamic(
        model_input=str(args.input),
        model_output=str(output),
        per_channel=True,
        weight_type=QuantType.QInt8,
    )
    validation = validate_quantized_pair(args.input, output, frames=args.frames)
    original_size = Path(args.input).stat().st_size
    quantized_size = output.stat().st_size
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    passed = bool(
        validation["maximum_output_absolute_error"] <= args.max_output_error
        and validation["maximum_state_absolute_error"] <= args.max_state_error
    )
    report = {
        "checkpoint": str(Path(args.checkpoint)),
        "checkpoint_sha256": sha256_file(args.checkpoint),
        "source_onnx": str(Path(args.input)),
        "source_onnx_sha256": sha256_file(args.input),
        "onnx": str(output),
        "onnx_sha256": sha256_file(output),
        "architecture": checkpoint["config"]["model"]["architecture"],
        "quantization": "dynamic_qint8_weights",
        "source_bytes": original_size,
        "quantized_bytes": quantized_size,
        "size_ratio": float(quantized_size / original_size),
        "validation": validation,
        "tolerances": {
            "maximum_output_absolute_error": args.max_output_error,
            "maximum_state_absolute_error": args.max_state_error,
        },
        "passed": passed,
        "warning": (
            "Numerical validation is only a corruption guard. Run full strict evaluation, "
            "listening tests, and Pi latency/thermal tests before selecting this model."
        ),
    }
    report_path = output.with_suffix(".validation.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not passed:
        raise SystemExit("Quantized model exceeded the declared numerical tolerances")


if __name__ == "__main__":
    main()
