# VoxShield v10 laptop demonstration

This is the operator demonstration for the selected `v10 deep-filter dual` baseline. It uses the
real checkpoint and FP32 ONNX artifact; the dashboard is not a prerecorded animation. Use wired
headphones to avoid acoustic feedback.

## 1. Select synchronized input channels

List Windows devices:

```powershell
cd C:\anc
& ".\.venv\Scripts\voxshield-live.exe" --checkpoint ".\checkpoints_deep_filter_v10\best.pt" --onnx ".\artifacts\voxshield-v10-deep-filter-final.onnx" --list-devices
```

Choose a single multi-channel input endpoint. Channel 0 and channel 1 must come from the same
hardware clock. A laptop microphone array is acceptable for an engineering demonstration, but it
does not prove reference-microphone placement or field performance. Two unrelated Windows audio
devices are not sample synchronized.

## 2. Launch the demonstration

Replace device numbers with the values printed on the current laptop. Device IDs are temporary
and normally change when a USB/Bluetooth headset is connected or disconnected; never reuse an
old number without listing devices again:

```powershell
& ".\scripts\run_v10_laptop_demo.ps1" -InputDevice 9 -OutputDevice 12 -PrimaryChannel 0 -ReferenceChannel 1 -WetMix 0.82 -Threads 1
```

The script launches the live engine and opens the local operator console. Controls are live:

- **Safe:** 55% wet output for conservative speech preservation.
- **Balanced:** 82% wet output, recommended for the first demonstration.
- **Max:** 100% wet output for maximum model effect; artifacts may be more audible.
- **Output trim:** monitoring gain from -18 dB to +6 dB.
- **Operator bypass:** returns the time-aligned dry signal while the model remains observable.
- **Mute:** silences monitored output without stopping evidence capture.

## 3. What the console proves

The console shows model inference time, per-frame real-time factor, stream health, underflows,
channel correlation, input/output levels, clipping, synchronized waveforms, spectra, a waterfall,
band energy, artifact identity and timestamped operator markers. Controls are passed to the running
audio engine through a local control file.

It deliberately does **not** display live SNR, STOI or PESQ. Those metrics require a known,
time-aligned clean target and would be fabricated in an uncontrolled microphone demonstration.
Use the frozen offline evaluation reports for those claims.

## 4. Recommended video sequence

1. Show the model/hash and `NORMAL` runtime state.
2. Speak in quiet conditions and show primary/reference/enhanced levels.
3. Add moderate steady noise and mark `STEADY`.
4. Add a short impulse at a safe acoustic level and mark `IMPULSE`.
5. Toggle bypass to make the comparison audible, then return to `BALANCED`.
6. Show zero failures/drops/overruns and export a dashboard snapshot.
7. State the limitation: laptop-array channels are demonstration inputs; the final hardware test
   requires a synchronized primary/reference microphone arrangement and physical loopback latency.

Do not place a phone or loudspeaker directly against a microphone. That clips the input and masks
speech before the model receives it; no algorithm can reconstruct speech that the microphone did
not capture cleanly.

## 5. Repeatable laptop software benchmark

```powershell
& ".\.venv\Scripts\voxshield-benchmark.exe" --checkpoint ".\checkpoints_deep_filter_v10\best.pt" --onnx ".\artifacts\voxshield-v10-deep-filter-final.onnx" --device cpu --threads 1 --warmup 100 --frames 2000 --output ".\artifacts\v10-laptop-benchmark.json"
```

This measures model and simulated callback processing. It does not measure physical microphone,
driver, buffering, DAC or headphone latency.

## 6. Freeze the evidence

```powershell
& ".\scripts\build_v10_evidence_pack.ps1"
```

The script creates a timestamped evidence directory under `artifacts`, copies the selected model,
reports, sample outputs and documentation, and creates a SHA-256 manifest.
