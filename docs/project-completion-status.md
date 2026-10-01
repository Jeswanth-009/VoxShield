# VoxShield project completion status

Updated 2026-09-28 after the v10 and v10b frozen audits. This document separates
implemented software, measured evidence, rejected experiments, and work that still
requires the user's physical hardware or new recordings.

## Selected model

The selected deployment baseline remains **v10 deep-filter dual**:

- checkpoint: `checkpoints_deep_filter_v10/best.pt` (epoch 58);
- ONNX: `artifacts/voxshield-v10-deep-filter-final.onnx`;
- architecture: causal dual-channel complex mask plus five-tap multi-frame deep filter;
- trainable parameters: 1,116,813;
- ONNX/PyTorch maximum output error: `6.10e-8` (passed, tolerance `2e-4`).

V10b is **not promoted**. It is retained as a reproducible rejected experiment:

- checkpoint: `checkpoints_deep_filter_v10b_stoi/best.pt` (epoch 13);
- ONNX: `artifacts/voxshield-v10b-stoi-final.onnx`;
- ONNX/PyTorch maximum output error: `3.91e-8` (passed);
- reason for rejection: it did not improve any frozen target-attainment rate and
  reduced military PESQ attainment from 86.8% to 84.2%.

## Frozen 50-file audit results

The strict gate requires mean output SNR >15 dB, STOI >0.85, PESQ >2.5,
speech-deletion rate <=2%, clean level error <=1 dB, at least 80% attainment for
each individual target, and at least 60% joint attainment.

| Set / model | Output SNR | STOI | PESQ | SNR target | STOI target | PESQ target | All three | Strict result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Broad v10 | 23.645 dB | 0.9213 | 3.7018 | 80.0% | 82.9% | 91.4% | 74.3% | PASS |
| Broad v10b | 23.748 dB | 0.9231 | 3.7272 | 80.0% | 82.9% | 91.4% | 74.3% | PASS |
| Military v10 | 19.455 dB | 0.8926 | 3.3911 | 84.2% | 68.4% | 86.8% | 60.5% | FAIL: STOI reliability |
| Military v10b | 19.452 dB | 0.8956 | 3.3919 | 84.2% | 68.4% | 84.2% | 60.5% | FAIL: STOI reliability |

Both candidates measured zero speech deletion on these audits. These results are
development evidence on frozen validation manifests, not proof from independently
recorded field trials.

## Completed software and evidence

- Recursive dataset ingestion and group-aware manifests for VCTK, MUSAN, ESC-50,
  MAD military sounds, UAV audio and RIRS_NOISES.
- Dynamic stationary, non-stationary, impulsive, environmental and mixed-noise
  generation; clean and near-clean preservation examples; SNR curricula; RIR,
  clipping and simulated reference-microphone paths.
- Causal full-band plus ERB/sub-band, dual-channel, complex-domain enhancement.
- SI-SNR, SNR, waveform, compressed complex/magnitude, phase, spectral-hole,
  spectral-delta, clean-preservation, speech-retention and STOI-envelope losses.
- Checkpoint/resume, early stopping, TensorBoard/JSONL logging and deterministic
  epoch-local sampling.
- Offline and stateful streaming inference, safe conditioning, runtime health,
  software bypass and degraded modes.
- ONNX export/parity, CPU benchmark support, laptop live demo/dashboard and Pi 5
  deployment scripts.
- SNR, SI-SNR, STOI, PESQ and optional DNSMOS evaluation with per-file target
  reliability and category/SNR/source breakdowns.
- FP32 remains the deployment format. The tested dynamic INT8 model is smaller but
  slower for this GRU-heavy per-frame workload, so it was rejected.
- Complete automated suite: **106 tests passed** after the Mission Console/control integration.

## V10b numerical defect and repair

The first v10b run produced finite forward losses but an AMP scaler that fell to
zero. The root cause was an infinite derivative at `sqrt(0)` in silent/inactive
STOI-envelope bands and correlation windows. Masking those windows after the
square root did not make the backward pass safe (`0 * NaN`). The repair:

1. clamps band and centred-window energies before square root;
2. returns a differentiable zero for fully inactive examples;
3. validates saved AMP scaler state and rejects zero/non-finite scales;
4. lets GradScaler handle recoverable AMP overflow while treating non-finite
   full-precision gradients as fatal;
5. explicitly refuses a zero/non-finite final scale before checkpointing.

The repaired resume completed epochs 6-14, selected epoch 13, exported cleanly,
and passed the full test suite. Its frozen audit still did not justify promotion.

## Remaining work

### Work that can continue in software

1. Build a failure-driven data recipe centred on the 12 military STOI failures,
   especially vehicle and helicopter recordings between roughly -13 and +6 dB.
2. Add controlled microphone response, AGC/limiter, radio codec and moving-source
   augmentation, each with ablation tests; do not combine unvalidated transforms.
3. Train a bounded v11 data-specialisation experiment from v10 and promote it only
   if both frozen gates improve without clean/PESQ regression.
4. Run larger untouched test manifests and report confidence intervals and
   source/SNR-bin performance, not only 50-file development subsets.
5. Conduct a matched-level blind listening test for naturalness and robotic voice.

### Work requiring user hardware or recordings

1. Capture genuinely synchronized primary/reference microphones on one audio clock.
2. Record target-device speech plus vehicle, rotor/UAV and impulse scenarios with
   calibration metadata; phone-through-laptop playback is only a demo.
3. Run v10 FP32 ONNX on Raspberry Pi 5 and measure p50/p95/p99 processing time,
   callback faults, RAM, CPU, temperature, throttling and power.
4. Perform physical input-to-output loopback latency and a 30-60 minute soak test.
5. Verify headset/radio integration and hardware or system-level bypass behavior.

Until those measurements exist, do not claim Pi latency/power, field-level blast
performance, a validated physical reference microphone, or complete military
reliability. The current accurate claim is: broad strict validation passes; military
mean targets and joint attainment pass, but military per-clip STOI reliability is
68.4% against the chosen 80% acceptance threshold.
