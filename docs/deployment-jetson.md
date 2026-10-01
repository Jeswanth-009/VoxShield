# Jetson AGX Orin Deployment Runbook (TensorRT)

VoxShield targets the NVIDIA Jetson AGX Orin named in the DRDO/SIH problem
statement. The Windows development machine cannot build or run TensorRT
engines, so this runbook is written for execution on the Orin itself. The
ONNX exports and all runner code are validated on the dev machine; only the
TensorRT engine build and its parity/latency checks require the Jetson.

## 1. Prerequisites (JetPack 5.1.1+)

```bash
sudo apt update
sudo apt install -y nvidia-jetpack    # includes TensorRT 8.5.x + trtexec
python3 -m pip install pycuda onnxruntime soundfile sounddevice psutil pyyaml numpy
```

Verify the toolchain:

```bash
trtexec --help | head -n 2
python3 -c "import tensorrt; print(tensorrt.__version__)"
```

## 2. Ship the project to the Jetson

Copy the repository (or at minimum `src/`, `configs/`, `artifacts/`) and the
matched checkpoint + ONNX pair. The ONNX must carry its `.validation.json`
report — `voxshield-benchmark --tensorrt` refuses to run against an unpaired
checkpoint.

```bash
rsync -av --exclude .venv --exclude data anc@dev-pc:~/anc ~/anc
```

## 3. Build the engine

Recommended path — `trtexec` (ships with JetPack, no Python TensorRT wheel
needed):

```bash
python3 -m voxshield.export_tensorrt \
  --onnx artifacts/voxshield-v6-stream.onnx \
  --output artifacts/voxshield-v6-stream.engine \
  --builder trtexec --fp16
```

Equivalent manual command:

```bash
trtexec --onnx=artifacts/voxshield-v6-stream.onnx \
  --saveEngine=artifacts/voxshield-v6-stream.engine --fp16
```

Alternative — Python API builder (TensorRT >= 8.5):

```bash
python3 -m voxshield.export_tensorrt \
  --onnx artifacts/voxshield-v6-stream.onnx \
  --output artifacts/voxshield-v6-stream.engine --builder python
```

Both paths produce a static-shape FP16 engine for the streaming contract
`["spectrum", "conv_cache", "tfa_cache", "inter_cache"] →
["enhanced", "conv_cache_out", "tfa_cache_out", "inter_cache_out"]` (GTCRN
exports use the same contract with a `tra_cache`).

## 4. Validate parity and latency

Frame-level parity against the shipped ONNX, then latency/RTF (the runner
implementing the WOLA `(B, 2, F, 1)` contract is
`voxshield.export_tensorrt.TensorRTFrameRunner`):

```bash
python3 -m voxshield.benchmark \
  --checkpoint checkpoints_ulunas_v6_full/best.pt \
  --tensorrt artifacts/voxshield-v6-stream.engine \
  --output artifacts/v6-tensorrt-benchmark-jetson.json
```

Acceptance for the engine build:

* `max |tensorrt - onnxruntime|` over 2000 random frames `<= 1e-3` (FP16
  accumulation differs slightly from FP32; larger drift means a broken build).
* `real_time_factor < 0.25` and `runtime_deadline_overruns == 0` (frame
  deadline is 16 ms at hop 256 / 16 kHz).
* Power mode: `sudo nvpmodel -m 0` (MAXN) and `sudo jetson_clocks` for
  benchmarking; measure again in 30 W mode for realistic field numbers.

## 5. Live two-microphone check

The Jetson host usually enumerates a USB audio interface as a single
multi-channel capture device; pass both channel indices explicitly:

```bash
python3 -m voxshield.live \
  --checkpoint checkpoints_ulunas_v6_full/best.pt \
  --device "$(arecord -l | grep -i usb | head -n1)" \
  --primary-channel 0 --reference-channel 1 \
  --telemetry-file artifacts/jetson-telemetry.json
```

`live.py` reads `/sys/class/thermal/thermal_zone0/temp` and
`vcgencmd get_throttled` on the Jetson as well; watch the session report for
`xruns` / `output_underflows` — any nonzero value means the engine or the USB
link missed the real-time budget.

## 6. Known limitations

* **Dynamic INT8 for UL-UNAS fails the repo's state-drift guard** (tfa_cache
  GRU-state error 1.29 vs 0.25 tolerance at frame 64; model size also grows,
  960 KB → 1008 KB, because dynamic INT8 cannot quantize Conv kernels). The
  FP32/FP16 engine is the approved v6 artifact. Static QDQ quantization with
  a real calibration set is the future path if INT8 UL-UNAS is required.
* The TensorRT runner targets static shapes (batch 1, T = 1 frames). Re-export
  with dynamic axes only together with profile code in
  `TensorRTFrameRunner._tensor_shape`.
* `execute_async_v3` requires TensorRT >= 8.5 (JetPack 5.1+). On older JetPack
  releases the runner needs the legacy binding API — port before use.
