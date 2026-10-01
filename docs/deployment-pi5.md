# Raspberry Pi 5 deployment

## Current v10 path

The selected artifact is `artifacts/voxshield-v10-deep-filter-final.onnx` with checkpoint
`checkpoints_deep_filter_v10/best.pt`. Older v3/v4 commands later in this document are retained as
historical examples; do not use them for the final v10 evidence.

Install, verify CPU timing/thermal state, and then list audio devices:

```bash
sudo bash scripts/pi/install.sh
bash scripts/pi/verify-v10.sh
.venv/bin/voxshield-live --checkpoint checkpoints_deep_filter_v10/best.pt \
  --onnx artifacts/voxshield-v10-deep-filter-final.onnx --list-devices
```

Run the live dual-channel demonstration after identifying a synchronized capture endpoint:

```bash
bash scripts/pi/run-v10-demo.sh INPUT_DEVICE OUTPUT_DEVICE 0 1
```

Open `http://PI_ADDRESS:8765/` from a laptop on the same trusted local network. The verification
script produces health snapshots, a 10,000-frame ONNX CPU benchmark, artifact hashes and an
acceptance report under `artifacts/pi5-v10-verification/`. This is software timing evidence only;
measure physical end-to-end latency with loopback and run a sustained live soak before claiming
hardware completion.

V3 remains available as the mono baseline.  V4 requires a single synchronized
multi-input USB interface: channel 0 is the close-talk primary microphone and
channel 1 is the outward environmental reference microphone.  Two unrelated
USB microphones are not supported because their sample clocks drift.

Use 64-bit Raspberry Pi OS. Train and export on a workstation; copy only the repository,
the selected ONNX model, and its matching checkpoint/config to the Pi. The checkpoint is used
to recover architecture metadata; live inference itself can run through ONNX Runtime.

```bash
sudo bash scripts/pi/install.sh
source .venv/bin/activate
voxshield-export --checkpoint checkpoints_v3/best.pt --output artifacts/voxshield-v3.onnx
voxshield-benchmark --checkpoint checkpoints_v3/best.pt --onnx artifacts/voxshield-v3.onnx \
  --threads 1 --frames 10000 --output artifacts/pi5-benchmark.json
```

For a trained v4 release, use:

```bash
voxshield-export --checkpoint checkpoints_v4_stage3/best.pt --output artifacts/voxshield-v4-final.onnx
voxshield-benchmark --checkpoint checkpoints_v4_stage3/best.pt \
  --onnx artifacts/voxshield-v4-final.onnx --threads 1 --frames 10000 \
  --output artifacts/pi5-v4-benchmark.json
voxshield-quantize --checkpoint checkpoints_v4_stage3/best.pt \
  --input artifacts/voxshield-v4-final.onnx \
  --output artifacts/voxshield-v4-final-int8.onnx
voxshield-live --checkpoint checkpoints_v4_stage3/best.pt \
  --onnx artifacts/voxshield-v4-final.onnx --list-devices
voxshield-live --checkpoint checkpoints_v4_stage3/best.pt \
  --onnx artifacts/voxshield-v4-final.onnx --input-device DEVICE \
  --output-device DEVICE --primary-channel 0 --reference-channel 1 --threads 1 \
  --telemetry-file artifacts/live-telemetry.json
```

Start with one ONNX thread and test 1-3 threads. Choose the lowest p99 latency that remains below
the 8 ms v4 hop budget; mean RTF alone can hide glitches. Watch temperature and throttling during a
30-minute run (`vcgencmd measure_temp` and `vcgencmd get_throttled`). Use a supported power supply
and active cooling.

Inference is deliberately outside the PortAudio callback. The default adds one 8 ms worker
playout block beyond the 24 ms WOLA buffering. If inference misses that playout time, the runtime
uses the corresponding aligned primary block and discards the late neural output. Check the final
`live engine` counters: dropped inputs, output underflows, resets, and worker failures must all be
zero during the two-hour acceptance run. Do not increase queueing to hide an overloaded Pi;
measure physical loopback latency after every buffering change.

List ALSA/PortAudio devices with `voxshield-live ... --list-devices`, then test headphones at low
volume. A USB audio interface may offer more reliable full-duplex latency than an arbitrary USB
microphone/output pair. Avoid acoustic feedback.

The example v4 systemd unit is `scripts/pi/voxshield-v4.service`. It assumes the repository is installed at `/opt/voxshield`, the virtual
environment is `/opt/voxshield/.venv`, and an unprivileged `voxshield` user has audio-device
access. Edit device IDs and paths before installation:

```bash
sudo cp scripts/pi/voxshield.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now voxshield
journalctl -u voxshield -f
```

Replace `voxshield.service` with `voxshield-v4.service` for the dual-channel
model and edit the device/channel values before enabling it. Run
`sudo bash scripts/pi/health-check.sh` to capture temperature, throttling,
ALSA-device and service evidence for the test report.

The optional `scripts/pi/voxshield-dashboard.service` serves the read-only monitor on
`127.0.0.1:8765`. Keep it loopback-only unless an authenticated reverse proxy and appropriate
network policy are deliberately added; it is an engineering display, not a remote-control API.

The required acceptance test is a two-hour full-duplex run with zero xruns, underflows,
dropped blocks, worker/model failures or invalid-model bypasses, p99 inference below the 8 ms hop, and measured
physical loopback latency at or below 50 ms. Model timing is not a substitute
for the loopback measurement.

Create the machine-readable soak report with:

```bash
voxshield-live --checkpoint checkpoints_v4_stage3/best.pt \
  --onnx artifacts/voxshield-v4-final.onnx --input-device DEVICE \
  --output-device DEVICE --primary-channel 0 --reference-channel 1 --threads 1 \
  --duration-seconds 7200 --session-report artifacts/pi5-soak.json
voxshield-readiness --project-root . --output artifacts/readiness.json
```

Use `docs/evidence/physical-loopback.template.json` for the separate measured loopback result.

Software bypass is not a safety-rated bypass. For operational equipment, provide a hardware path
that remains usable if the Pi, process, power, USB device, or model fails.
