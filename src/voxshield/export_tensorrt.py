"""TensorRT engine build and streaming runner for VoxShield ONNX exports.

Two build paths:
  * ``trtexec`` subprocess (default) — ships with JetPack on the Jetson AGX
    Orin; no Python TensorRT package needed for building.
  * Python API build via the ``tensorrt`` package (TensorRT >= 8.5).

``TensorRTFrameRunner`` implements the same ``FrameRunner`` protocol as the
ONNX runners in :mod:`voxshield.runtime` and is generic over the streaming
input contract: frame inputs plus ``*_cache``/``state_in`` recurrent states
(GTCRN: conv/tra/inter caches, UL-UNAS: conv/tfa/inter caches — both consume
``(B, F, 1, 2)`` spectra and return ``(B, 2, F, 1)``).

This module is intended for TensorRT-equipped targets (Jetson AGX Orin with
JetPack 5.1+). It is import-safe anywhere — TensorRT is only imported inside
functions — but the runner and builder can only be exercised on hardware with
TensorRT and PyCUDA installed. See docs/deployment-jetson.md for the Jetson
validation runbook.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


def _is_state_input(name: str) -> bool:
    return name == "state_in" or name.endswith("_cache")


def build_engine_trtexec(
    onnx_path: str | Path,
    output_path: str | Path,
    *,
    fp16: bool = True,
    trtexec_path: str = "trtexec",
    workspace_mb: int = 1024,
    extra_args: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Build a TensorRT engine with the trtexec binary (JetPack ships it)."""
    onnx_path = Path(onnx_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        trtexec_path,
        f"--onnx={onnx_path}",
        f"--saveEngine={output_path}",
        f"--memPoolSize=workspace:{workspace_mb}",
        *extra_args,
    ]
    if fp16:
        command.append("--fp16")
    subprocess.run(command, check=True)
    report = {
        "builder": "trtexec",
        "onnx": str(onnx_path),
        "engine": str(output_path),
        "engine_bytes": output_path.stat().st_size,
        "fp16": fp16,
        "command": command,
    }
    return report


def build_engine_python(
    onnx_path: str | Path,
    output_path: str | Path,
    *,
    fp16: bool = True,
    workspace_bytes: int = 1 << 30,
) -> dict[str, Any]:
    """Build a TensorRT engine with the Python API (TensorRT >= 8.5)."""
    try:
        import tensorrt as trt
    except ImportError as exc:
        raise RuntimeError(
            "The tensorrt package is not installed; on Jetson use the trtexec builder "
            "or install the JetPack TensorRT wheels."
        ) from exc
    logger = trt.Logger(trt.Logger.WARNING)
    builder = trt.Builder(logger)
    network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    parser = trt.OnnxParser(network, logger)
    onnx_path = Path(onnx_path)
    if not parser.parse(onnx_path.read_bytes()):
        errors = [str(parser.get_error(index)) for index in range(parser.num_errors)]
        raise RuntimeError(f"TensorRT failed to parse {onnx_path}: {errors}")
    config = builder.create_builder_config()
    config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, workspace_bytes)
    if fp16 and builder.platform_has_fast_fp16:
        config.set_flag(trt.BuilderFlag.FP16)
    serialized = builder.build_serialized_network(network, config)
    if serialized is None:
        raise RuntimeError("TensorRT engine build failed; inspect TensorRT log output")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(serialized)
    report = {
        "builder": "python",
        "onnx": str(onnx_path),
        "engine": str(output_path),
        "engine_bytes": output_path.stat().st_size,
        "fp16": bool(fp16 and builder.platform_has_fast_fp16),
    }
    return report


class TensorRTFrameRunner:
    """Streaming frame runner over a static-shape TensorRT engine.

    Mirrors :class:`voxshield.runtime.ULUNASOnnxFrameRunner`: ``enhance``
    takes a WOLA-convention ``(B, 2, F, 1)`` spectrum, transposes to the
    export contract ``(B, F, 1, 2)``, feeds the persistent cache states, and
    returns the enhanced ``(B, 2, F, 1)`` spectrum. Requires TensorRT >= 8.5
    and PyCUDA for CUDA memory management.
    """

    _FRAME_TRANSPOSE_IN = (0, 2, 3, 1)  # (B, 2, F, 1) -> (B, F, 1, 2)
    _FRAME_TRANSPOSE_OUT = (0, 3, 1, 2)  # (B, F, 1, 2) -> (B, 2, F, 1)

    def __init__(self, path: str | Path, threads: int = 1) -> None:
        del threads  # TensorRT manages its own execution threading
        try:
            import tensorrt as trt
        except ImportError as exc:
            raise RuntimeError(
                "TensorRT is not installed on this machine; build/run engines on "
                "TensorRT-equipped hardware (see docs/deployment-jetson.md)"
            ) from exc
        try:
            import pycuda.autoinit  # noqa: F401  initializes the CUDA context
            import pycuda.driver as cuda
        except ImportError as exc:
            raise RuntimeError("The TensorRT runner requires PyCUDA: pip install pycuda") from exc
        self._trt = trt
        self._cuda = cuda
        logger = trt.Logger(trt.Logger.WARNING)
        engine_data = Path(path).read_bytes()
        runtime = trt.Runtime(logger)
        self.engine = runtime.deserialize_cuda_engine(engine_data)
        if self.engine is None:
            raise RuntimeError(f"Failed to deserialize TensorRT engine: {path}")
        self.context = self.engine.create_execution_context()
        self.input_names, self.output_names = self._discover_io()
        self.state_names = [name for name in self.input_names if _is_state_input(name)]
        self.frame_names = [name for name in self.input_names if not _is_state_input(name)]
        self._buffers = {name: _DeviceBuffer(cuda, self._tensor_shape(name)) for name in self.input_names + self.output_names}
        self._stream = cuda.Stream()
        self.states: dict[str, np.ndarray] | None = None

    def _discover_io(self) -> tuple[list[str], list[str]]:
        inputs: list[str] = []
        outputs: list[str] = []
        for index in range(self.engine.num_io_tensors):
            name = self.engine.get_tensor_name(index)
            if self.engine.get_tensor_mode(name) == self._trt.TensorIOMode.INPUT:
                inputs.append(name)
            else:
                outputs.append(name)
        return inputs, outputs

    def _tensor_shape(self, name: str) -> tuple[int, ...]:
        shape = self.engine.get_tensor_shape(name)
        if any(dim < 0 for dim in shape):
            raise ValueError(
                "TensorRTFrameRunner requires a static-shape engine; rebuild the ONNX "
                "export without dynamic axes"
            )
        return tuple(int(dim) for dim in shape)

    def reset(self) -> None:
        self.states = None

    def _ensure_states(self, batch: int) -> None:
        if self.states is not None and all(
            state.shape[0] == batch for state in self.states.values()
        ):
            return
        self.states = {
            name: np.zeros(self._buffers[name].shape, dtype=np.float32)
            for name in self.state_names
        }

    def enhance(self, spectrum_ri: np.ndarray) -> np.ndarray:
        self._ensure_states(int(spectrum_ri.shape[0]))
        frame_input = self.frame_names[0]
        spectrum = spectrum_ri.transpose(*self._FRAME_TRANSPOSE_IN).astype(np.float32)
        self._buffers[frame_input].copy_host_to_device(spectrum, self._stream)
        for name in self.state_names:
            self._buffers[name].copy_host_to_device(self.states[name], self._stream)
        for name in self.input_names + self.output_names:
            self.context.set_tensor_address(name, int(self._buffers[name].device))
        if not self.context.execute_async_v3(stream_handle=self._stream.handle):
            raise RuntimeError("TensorRT inference failed (execute_async_v3 returned False)")
        for name in self.output_names:
            self._buffers[name].copy_device_to_host(self._stream)
        self._stream.synchronize()
        output_host = self._buffers[self.output_names[0]].host
        output = output_host.reshape(self._buffers[self.output_names[0]].shape)
        for name in self.state_names:
            self.states[name] = self._buffers[name].host.reshape(
                self._buffers[name].shape
            ).copy()
        return output.transpose(*self._FRAME_TRANSPOSE_OUT)


class _DeviceBuffer:
    """Pinned host buffer + device allocation pair for one engine tensor."""

    def __init__(self, cuda: Any, shape: tuple[int, ...]) -> None:
        self._cuda = cuda
        self.shape = tuple(int(dim) for dim in shape)
        self.size = max(int(np.prod(self.shape)), 1)
        self.nbytes = self.size * np.float32().itemsize
        self.host = cuda.pagelocked_empty(self.size, np.float32)
        self.device = cuda.mem_alloc(self.nbytes)

    def copy_host_to_device(self, array: np.ndarray, stream: Any) -> None:
        flat = np.ascontiguousarray(array.reshape(-1), dtype=np.float32)
        if flat.size != self.size:
            raise ValueError(f"engine tensor expects {self.size} elements, got {flat.size}")
        self.host[:] = flat
        self._cuda.memcpy_htod_async(self.device, self.host, stream)

    def copy_device_to_host(self, stream: Any) -> None:
        self._cuda.memcpy_dtoh_async(self.host, self.device, stream)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a TensorRT engine from a VoxShield streaming ONNX export "
        "(Jetson AGX Orin / any TensorRT-equipped machine)"
    )
    parser.add_argument("--onnx", required=True, help="Validated FP32 streaming ONNX model")
    parser.add_argument("--output", required=True, help="Destination .engine file")
    parser.add_argument(
        "--builder", choices=["trtexec", "python"], default="trtexec",
        help="trtexec binary (default, present on JetPack) or the TensorRT Python API",
    )
    parser.add_argument("--fp16", action="store_true", default=True)
    parser.add_argument("--no-fp16", dest="fp16", action="store_false")
    parser.add_argument("--trtexec", default="trtexec", help="Path to the trtexec binary")
    parser.add_argument("--workspace-mb", type=int, default=1024)
    args = parser.parse_args()
    if args.builder == "trtexec":
        report = build_engine_trtexec(
            args.onnx,
            args.output,
            fp16=args.fp16,
            trtexec_path=args.trtexec,
            workspace_mb=args.workspace_mb,
        )
    else:
        report = build_engine_python(
            args.onnx, args.output, fp16=args.fp16, workspace_bytes=args.workspace_mb * (1 << 20)
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
