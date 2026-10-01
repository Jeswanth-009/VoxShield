from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from .checkpoint import load_model, sha256_file
from .df_model import DeepFilterDualChannelNet
from .fusion_model import FusionDualChannelULUNAS
from .hybrid_model import HybridDualChannelGTCRN
from .official_gtcrn import OfficialGTCRN
from .official_stream import StreamGTCRN, convert_to_stream
from .ulunas_adapter import OfficialULUNAS, make_stream_ulunas


def fusion_export_spec(
    model: FusionDualChannelULUNAS | DeepFilterDualChannelNet, frequency: int
) -> tuple[tuple[torch.Tensor, ...], list[str], list[str], dict[str, dict[int, str]]]:
    """Build the one-frame, stateful dual-input signature used by v7 and v10.

    Works for any dual-input model whose streaming state is one packed
    ``(batch, STATE_SIZE)`` vector with ``initial_state``/``forward_ri``.
    """
    primary = torch.randn(1, 2, frequency, 1, dtype=torch.float32) * 0.1
    reference = torch.randn(1, 2, frequency, 1, dtype=torch.float32) * 0.1
    state = model.initial_state(1)
    inputs = (primary, reference, state)
    input_names = ["primary_ri", "reference_ri", "state_in"]
    output_names = ["enhanced_ri", "state_out"]
    dynamic_axes = {
        "primary_ri": {0: "batch"},
        "reference_ri": {0: "batch"},
        "state_in": {0: "batch"},
        "enhanced_ri": {0: "batch"},
        "state_out": {0: "batch"},
    }
    return inputs, input_names, output_names, dynamic_axes


def main() -> None:
    parser = argparse.ArgumentParser(description="Export and validate VoxShield ONNX")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", default="artifacts/voxshield-v3.onnx")
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument("--tolerance", type=float, default=2e-4)
    args = parser.parse_args()
    try:
        import onnx
        import onnxruntime as ort
    except ImportError as exc:
        raise SystemExit("Install ONNX dependencies with: pip install -e .[onnx]") from exc
    model, config, _ = load_model(args.checkpoint, "cpu")
    model.eval()
    frequency = config["audio"]["n_fft"] // 2 + 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(model, OfficialGTCRN):
        export_model: torch.nn.Module = StreamGTCRN().eval()
        convert_to_stream(export_model, model)
        spectrum = torch.randn(1, frequency, 1, 2, dtype=torch.float32) * 0.1
        states = StreamGTCRN.initial_states(1, torch.device("cpu"))
        inputs = (spectrum, *states)
        input_names = ["spectrum", "conv_cache", "tra_cache", "inter_cache"]
        output_names = [
            "enhanced", "conv_cache_out", "tra_cache_out", "inter_cache_out"
        ]
        dynamic_axes = None
    elif isinstance(model, OfficialULUNAS):
        export_model = make_stream_ulunas(model).eval()
        spectrum = torch.randn(1, frequency, 1, 2, dtype=torch.float32) * 0.1
        caches = export_model.init_caches(1, torch.device("cpu"))
        inputs = (spectrum, *caches)
        input_names = ["spectrum", "conv_cache", "tfa_cache", "inter_cache"]
        output_names = [
            "enhanced", "conv_cache_out", "tfa_cache_out", "inter_cache_out"
        ]
        dynamic_axes = None
    elif isinstance(model, FusionDualChannelULUNAS):
        export_model = model
        inputs, input_names, output_names, dynamic_axes = fusion_export_spec(
            model, frequency
        )
    elif isinstance(model, DeepFilterDualChannelNet):
        export_model = model
        inputs, input_names, output_names, dynamic_axes = fusion_export_spec(
            model, frequency
        )
    elif isinstance(model, HybridDualChannelGTCRN):
        export_model = model
        primary = torch.randn(1, 2, frequency, 8, dtype=torch.float32) * 0.1
        reference = torch.randn(1, 2, frequency, 8, dtype=torch.float32) * 0.1
        state = model.initial_state(1)
        inputs = (primary, reference, state)
        input_names = ["primary_ri", "reference_ri", "state_in"]
        output_names = ["enhanced_ri", "state_out"]
        dynamic_axes = {
            "primary_ri": {0: "batch", 3: "frames"},
            "reference_ri": {0: "batch", 3: "frames"},
            "state_in": {1: "batch"},
            "enhanced_ri": {0: "batch", 3: "frames"},
            "state_out": {1: "batch"},
        }
    else:
        export_model = model
        spectrum = torch.randn(1, 2, frequency, 8, dtype=torch.float32) * 0.1
        state = model.initial_state(1)
        inputs = (spectrum, state)
        input_names = ["spectrum_ri", "state_in"]
        output_names = ["enhanced_ri", "state_out"]
        dynamic_axes = {
            "spectrum_ri": {0: "batch", 3: "frames"},
            "state_in": {1: "batch"},
            "enhanced_ri": {0: "batch", 3: "frames"},
            "state_out": {1: "batch"},
        }
    torch.onnx.export(
        export_model,
        inputs,
        output,
        input_names=input_names,
        output_names=output_names,
        dynamic_axes=dynamic_axes,
        opset_version=args.opset,
        do_constant_folding=True,
    )
    graph = onnx.load(str(output))
    onnx.checker.check_model(graph)
    session = ort.InferenceSession(str(output), providers=["CPUExecutionProvider"])
    with torch.inference_mode():
        torch_outputs = export_model(*inputs)
    if not isinstance(torch_outputs, tuple):
        torch_outputs = (torch_outputs,)
    ort_outputs = session.run(
        output_names, {name: value.numpy() for name, value in zip(input_names, inputs)}
    )
    errors = [
        float(np.max(np.abs(ort_value - torch_value.numpy())))
        for ort_value, torch_value in zip(ort_outputs, torch_outputs)
    ]
    output_error = errors[0]
    state_error = max(errors[1:], default=0.0)
    passed = output_error <= args.tolerance and state_error <= args.tolerance
    report = {
        "checkpoint": str(args.checkpoint),
        "checkpoint_sha256": sha256_file(args.checkpoint),
        "onnx": str(output),
        "onnx_sha256": sha256_file(output),
        "opset": args.opset,
        "architecture": config.get("model", {}).get("architecture", "legacy_gtcrn_derived"),
        "max_output_absolute_error": output_error,
        "max_state_absolute_error": state_error,
        "per_output_absolute_error": dict(zip(output_names, errors)),
        "tolerance": args.tolerance,
        "passed": passed,
    }
    report_path = output.with_suffix(".validation.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not passed:
        raise SystemExit("ONNX validation failed")


if __name__ == "__main__":
    main()
