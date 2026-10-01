# VoxShield v7 current engineering status

Date: 26 September 2026

## Architecture

The selected checkpoint uses `fusion_dual_ulunas`: a causal dual-channel
UL-UNAS core widened for five ERB-domain spatial features (primary and
reference log magnitude, cosine and sine inter-channel phase difference, and
log-magnitude ratio), followed by a two-channel complex ratio-mask head. The
model has 172,748 parameters and consumes synchronized primary and
noise-reference microphone channels. GTCRN remains in the repository as an
older comparison architecture; it is not a component of the v7 graph.

## Selected artifacts

- Checkpoint: `checkpoints_fusion_v7_stage2/best.pt`
- FP32 ONNX: `artifacts/voxshield-v7-stage2-final.onnx`
- ONNX validation: `artifacts/voxshield-v7-stage2-final.validation.json`
- Laptop CPU benchmark: `artifacts/v7-stage2-benchmark-onnx-cpu.json`
- Broad 50-pair ONNX gate: `artifacts/v7-stage2-onnx-broad-50.json`
- Military 50-pair ONNX gate: `artifacts/v7-stage2-onnx-military-50.json`

The ONNX numerical comparison passed with maximum enhanced-output absolute
error `1.0430813e-7` and maximum packed-state error `1.5258789e-5`, below the
declared `2e-4` tolerance.

## Current measurements

The one-thread Windows ONNX benchmark measured 6.91 ms mean frame inference,
11.41 ms p99 frame inference, 12.19 ms full-pipeline p99 callback time and RTF
0.43 for a 16 ms hop. It observed two synthetic deadline overruns and therefore
does not replace a live soak test. These are laptop measurements, not Raspberry
Pi 5 results, and end-to-end audio latency still requires physical loopback.

The 50-pair broad ONNX gate measured output SNR 26.87 dB, STOI 0.902 and PESQ
3.58. Its noisy-only subset measured 17.17 dB, 0.867 and 3.18 respectively;
the strict SIH metric gate passed.

The 50-pair military ONNX gate measured output SNR 17.98 dB, STOI 0.855 and
PESQ 2.86. Its deliberately difficult noisy-only subset measured 10.66 dB,
0.816 and 2.38, so the strict absolute SIH metric gate did not pass. Speech
deletion remained below 0.05 percent in that check.

## Laptop live demonstration

List devices in PowerShell:

```powershell
cd C:\anc
& ".\.venv\Scripts\voxshield-live.exe" `
  --checkpoint ".\checkpoints_fusion_v7_stage2\best.pt" `
  --onnx ".\artifacts\voxshield-v7-stage2-final.onnx" `
  --list-devices
```

Use headphones to avoid acoustic feedback. For the current Realtek DirectSound
device listing, input 6 and output 9 provide a convenient engineering test:

```powershell
cd C:\anc
& ".\scripts\run_v7_laptop_demo.ps1" `
  -InputDevice 6 -OutputDevice 9 `
  -PrimaryChannel 0 -ReferenceChannel 1 -WetMix 0.90
```

Open `http://127.0.0.1:8765/` while the command runs. The monitor displays
primary/reference/enhanced spectra, a scrolling enhanced spectrogram, inference
latency, underflows and runtime health. It intentionally does not display live
SNR, STOI or PESQ because live microphone audio has no aligned clean target.

The built-in laptop microphone array is acceptable for functional testing but
does not prove dual-microphone performance. Final validation needs a synchronized
interface with a speech-dominant boom microphone and an outward-facing,
noise-dominant reference microphone.

Do not add `--lms` to the v7 live command. The evaluated NLMS pre-cancellation
variant severely regressed speech quality. Physical FxNLMS remains a separate
hardware workstream requiring an error microphone and measured secondary path.

## Remaining acceptance work

1. Run full-manifest ONNX gates after the 50-pair integration gates.
2. Conduct matched listening tests and run the optional five-epoch preservation
   stage only if v7 Stage 2 still sounds robotic.
3. Mine difficult military validation failures and perform a bounded,
   preservation-replayed hard-example refinement without tuning on final test.
4. Collect synchronized real target-microphone sessions and perform low-rate
   target-device fine-tuning.
5. Benchmark the selected FP32 model on Raspberry Pi 5, then evaluate INT8 only
   as a quality-gated candidate.
6. Measure physical loopback latency and complete a two-hour zero-xrun thermal
   soak test.
7. Build and calibrate the separate bounded FxNLMS physical ANC loop with an
   error microphone, actuator, secondary-path model and hardware bypass.

## Military limitation diagnosis and bounded refinement

The complete Stage-2 military report shows that the weakest noisy labels are
helicopter (7.54 dB output SNR, 0.72 STOI, 1.90 PESQ), fighter (8.89 dB,
0.76, 1.99) and vehicle (9.86 dB, 0.77, 2.13). Inputs below -10 dB average
only 5.25 dB output SNR, 0.74 STOI and 1.63 PESQ. By comparison, inputs at or
above 5 dB average 15.04 dB, 0.86 and 2.93. This establishes that the remaining
failure is concentrated in rotor/engine-like low-SNR cases rather than a broad
failure across every military label.

`configs/fusion_v7_stage2c_hard_military.yaml` is a prepared eight-epoch,
low-rate candidate recipe. It oversamples helicopter/fighter/vehicle cases and
the MAD corpus while retaining 45 percent clean/near-clean replay and stronger
speech-preservation selection. Do not run it merely because it exists: first
complete the Stage-2 live listening gate. If Stage 2 sounds robotic, run the
preservation stage first. If Stage 2 sounds natural but leaves rotor/vehicle
noise, run Stage 2C. Stage 2C may replace Stage 2 only after the unchanged broad
and military validation sets, matched listening test and clean-preservation
gate all pass; the final test set must not be used for tuning.
