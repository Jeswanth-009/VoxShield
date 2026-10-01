# VoxShield v4 — complete presentation content pack

This is source material for a presentation, not a generated PPT file. Each section gives the
recommended slide title, on-slide content, speaker notes, evidence and a visual suggestion.

Use these status labels consistently:

- **MEASURED:** produced by an existing artifact or completed test.
- **IMPLEMENTED / NOT YET FULLY TRAINED:** code exists and smoke tests pass, but final quality is
  not established.
- **REQUIRED / PLANNED:** depends on missing data, training, Raspberry Pi or physical hardware.

Never convert a smoke-test number into a quality claim. Never describe communication speech
enhancement as physical ANC.

---

## Slide 1 — Title

**VoxShield v4: AI/ML-Enabled Hybrid Noise Suppression and Active Noise Control for Defence Communications**

Subtitle: *Causal dual-microphone speech enhancement, edge deployment and a safety-gated
physical ANC path*

Footer: SIH Problem Statement 26052 · DRDO · Hardware category

Speaker note: The project is a complete engineering pipeline, not only a neural-network demo.
It covers data, training, validation, real-time inference, edge deployment, monitoring and the
separate path needed for true anti-noise control.

Suggested visual: headset/operator, two microphones, Pi 5, and a waveform changing from noisy to
enhanced. Label it “concept,” not a measured result.

## Slide 2 — Problem statement, word by word

| Requirement | Engineering interpretation |
| --- | --- |
| AI/ML-enabled | A learned causal speech-enhancement model is trained on paired noisy/clean speech |
| Adaptive noise cancellation | Neural communication enhancement plus an optional separately calibrated FxNLMS physical control loop |
| Stationary noise | Fans, hum, steady engines and continuous vehicle noise |
| Non-stationary noise | Rotor, moving vehicles, wind gusts, speech babble and changing machinery |
| Impulsive defence noise | Gunshots, shelling, impacts and short high-energy transients |
| Maintain speech intelligibility | Preserve phonemes and voice level, especially when a transient overlaps speech |
| Real-time | Stateful causal inference with bounded queues and measured end-to-end latency |
| Embedded hardware | ONNX Runtime on Raspberry Pi 5, followed by target-device benchmarking and soak tests |

Target acceptance values supplied by the problem statement: output SNR above 15 dB, STOI above
0.85 and PESQ above 2.5, while maintaining low real-time latency.

Speaker note: Those are release gates, not current v4 results.

## Slide 3 — Critical lesson from the v3 prototype

**MEASURED:** The final v3 single-microphone GTCRN baseline improved noisy-only held-out test
examples by +8.638 dB SNR, +7.713 dB SI-SNR and +0.0542 STOI. It also improved all tested MAD
labels. However, the complete test gate failed because clean and near-clean speech were slightly
over-processed, PESQ was unavailable, and listening exposed voice loss around tank/impulse
overlap.

Main conclusion: optimizing average denoising scores is not enough. A model can suppress noise
while deleting wanted speech or damaging already-clean input.

Why v4 is a rebuild rather than another v3 tuning pass:

- A second synchronized reference microphone provides noise-dominant information.
- Clean-identity and speech-retention objectives explicitly penalize speech damage.
- Fixed strict gates include clean/near-clean preservation and transient deletion.
- Training is staged from broad noise to defence-weighted to final-device recordings.
- Runtime failures use time-aligned dry bypass instead of broken or late audio.

Evidence: `artifacts/voxshield-v3-final-model-card.md`.

## Slide 4 — Honest scope: two related but different outputs

### A. Communication speech enhancement

```text
primary microphone + reference microphone
               ↓
causal neural enhancer
               ↓
cleaner transmitted/recorded/headphone speech
```

It changes the audio signal used for communication. This is the main v4 system and can run on a
laptop or Pi 5.

### B. Physical active noise control

```text
reference noise → FxNLMS controller → anti-noise loudspeaker/headphone
                                      ↓
                              error microphone feedback
```

It creates anti-noise acoustically at the ear. It requires secondary-path identification,
strict output bounds, an error microphone, stable low-latency I/O and hardware bypass.

Speaker note: A speech denoiser alone is not proof of physical ANC. VoxShield keeps the two paths
separate so the project does not make a false claim.

## Slide 5 — Proposed end-to-end architecture

```text
Close-talk primary mic ─┐
                        ├─ synchronized USB interface ─ Pi/laptop ─ enhanced communication audio
Outward reference mic ──┘                              │
                                                      ├─ health monitor / dry bypass
                                                      ├─ telemetry dashboard
                                                      └─ logging and evidence

Reference mic ─ optional low-level ANC controller ─ headphone driver ─ ear/error microphone
```

Design rules:

- Both neural inputs must share one sample clock.
- Two unrelated USB microphones are rejected because clock drift destroys alignment.
- The primary microphone is speech-dominant; the reference is noise-dominant.
- Physical ANC needs at least one additional in-ear error microphone and a calibrated actuator
  path.

Suggested visual: use this as a block diagram with the communication path in blue and the
physical ANC loop in orange.

## Slide 6 — Hardware bill of materials

Minimum communication-enhancement prototype:

- Raspberry Pi 5, official 27 W USB-C supply and active cooling.
- 64-bit Raspberry Pi OS.
- One synchronized two-input USB audio interface.
- Close-talk boom microphone.
- Outward/environmental reference microphone.
- Closed-back communication headset or safe test loudspeaker.
- Laptop with RTX 4060 for training.

Additional physical-ANC research hardware:

- At least three synchronized inputs and two outputs.
- In-ear error microphone or acoustic test fixture.
- Calibrated loudspeaker/headphone path, SPL meter and loopback cable.
- Hardware fail-safe/bypass; a DSP or MCU is preferable for the final sample-by-sample control
  loop while the Pi supervises the system.

The Raspberry Pi documentation recommends a 27 W supply for Pi 5 and active cooling to reduce
thermal throttling. Pi 5 begins progressive CPU throttling in the 80–85 °C region, so sustained
tests must record temperature and throttling state.

## Slide 7 — Data already available

**MEASURED current catalog:** 114,805 files indexed/referenced from VCTK, MUSAN, ESC-50, MAD,
NASA small-UAS and OpenSLR RIR data.

| Data type | Current measured coverage |
| --- | ---: |
| Clean training speech | 39.33 hours |
| Gunshot labels | 1,573 files |
| Artillery/shelling labels | 987 files |
| Vehicle/tank labels | 1,032 files |
| Helicopter/rotor labels | 1,065 files |
| Aircraft labels | 1,031 files |
| Wind / siren labels | 40 / 40 files |
| Drone labels | 62 |
| Room impulse responses | 60,000 |
| Detected group split leakage | 0 |
| Missing referenced source files | 0 |

Conclusion: the machine audit now reports `ready: true`, with no missing paths or group leakage.
Real target-device recordings and license/listening QA are still required before stage 3 and
final claims.

Evidence: `artifacts/data-audit-v4.json`.

## Slide 8 — Dataset roles and provenance

| Dataset | Role | Important caution |
| --- | --- | --- |
| VCTK 0.92 | English multi-speaker clean speech | Keep speakers disjoint across splits |
| MUSAN | Stationary/ambient noise, music and interfering speech | Retain source-level separation; official distribution is CC BY 4.0 |
| ESC-50 | Environmental and event diversity | 2,000 five-second clips, five folds, CC BY-NC; verify allowed use |
| MAD | Gunshot, shelling, vehicle, helicopter, fighter and related labels | Verify the exact official source and license; preserve official train/test |
| OpenSLR SLR28 | Real/simulated RIR and background noise | Add before long v4 training; split by room/recording |
| DNS Challenge | Broad real/synthetic noise and generation recipes | Potentially very large; use relevant subsets |
| UAV/drone corpus | Missing target class | Split by flight/session/device, not random clips |
| Target captures | Final microphones, rooms, gains and geometry | Required for stage 3 and final claims |

Indian-language/accent diversity can be added from consented recordings and/or an appropriate
subset of AI4Bharat IndicVoices, whose official project covers 22 Indian languages. Access terms
must be recorded before use.

## Slide 9 — Automated large-dataset ingestion

**IMPLEMENTED:** The user does not need to manually rearrange huge datasets.

The ingestion command:

- Recursively finds WAV, FLAC and OGG files.
- Understands VCTK, MUSAN, ESC-50 metadata/folds, MAD CSV files, LibriSpeech and DNS-style trees.
- Validates audio headers concurrently.
- Preserves official splits when available.
- Otherwise hashes a complete speaker/source group into a deterministic split.
- Writes small JSONL manifests containing paths and metadata.
- Never copies or modifies the source audio.

Core command:

```powershell
voxshield-data ingest --data-root data --manifest-dir manifests_v4 `
  --source "clean=PATH_TO_SPEECH" --source "noise=PATH_TO_NOISE" `
  --source "rir=PATH_TO_RIRS"
voxshield-data audit --data-root data --manifest-dir manifests_v4 `
  --output artifacts/data-audit-v4.json --fail-on-leakage
```

Speaker note: Group-disjoint splitting matters because random clips from one speaker or one long
noise recording in both train and test produce falsely optimistic metrics.

## Slide 10 — Dynamic paired-mixture generation

Training sample generation:

```text
clean target s + scaled/augmented noise n → primary mixture x
delayed/filtered n + controlled speech leakage + self-noise → reference r
model(x, r) → enhanced estimate y
compare y with original clean target s → loss and weight update
```

The clean recording and noise recording do not need to come from the same event. During training,
the clean file is the known target. During real inference there is no clean target; the model
estimates speech from the two microphones.

Why dynamic mixing is used:

- It generates many combinations without storing a huge duplicated mixture corpus.
- SNR, crop position, delay, gain and augmentation change each epoch.
- One or two noise types can overlap.
- Exact-clean and near-clean examples teach the identity behavior.
- Fixed validation and test mixtures are materialized once for reproducibility.

## Slide 11 — Noise and channel augmentation

Implemented v4 sampling range:

- Training SNR: −15 to +20 dB in broad stage; −20 to +15 dB in defence stage.
- Near-clean SNR: +25 to +40 dB.
- Exact-clean probability: 15–20% depending on stage.
- Multi-noise probability: 35% broad, 45% defence.
- RIR/reverberation probability: 35% when RIRs are available.
- Clipping probability: 8% broad, reduced to 3% in final-device fine-tuning.
- Inter-channel delay: −16 to +16 samples.
- Reference noise gain: −6 to +6 dB.
- Reference speech leakage: −35 to −12 dB.
- Reference self-noise SNR: 35 to 55 dB.
- Random reference spectral tilt.

Special handling for impulses places some events over active speech, rather than mostly over
silence. This directly trains against the previously observed voice-wiping failure.

## Slide 12 — v4 signal processing front end

**IMPLEMENTED / NOT YET FULLY TRAINED**

- Sample rate: 16 kHz mono per channel.
- Analysis window: 512 samples = 32 ms.
- Hop: 128 samples = 8 ms.
- Window: square-root Hann.
- Reconstruction: weighted overlap-add (WOLA).
- Algorithmic WOLA buffering: 512 − 128 = 384 samples = 24 ms.
- Features: complex primary/reference spectra, magnitude, phase relation, relative level and
  ERB/sub-band context.
- Output: bounded complex ratio mask applied to the primary spectrum plus an identity/preservation
  gate.
- Conditioning: NaN/Inf removal, DC control and conservative output limiting.

Why complex-domain processing: magnitude-only suppression cannot directly correct phase, while
complex masks can model both real and imaginary spectral components.

## Slide 13 — Neural architecture

Name: **Hybrid Dual-Channel Causal GTCRN-style Enhancer**.

Main blocks:

1. Causal encoder over synchronized primary/reference features.
2. ERB/sub-band representation for local frequency detail and full-band context.
3. Two recurrent causal blocks with persistent state.
4. Complex mask head with bounded minimum/maximum gain.
5. Preservation/identity gate biased toward passing input safely.
6. Stateful one-frame ONNX input/output for deterministic streaming.

Safety-oriented initialization: mask heads are initialized so a new model behaves close to an
identity mapping instead of emitting arbitrary destructive audio.

V3's complete official GTCRN remains a frozen single-channel comparison; v4 is a different
two-input architecture and starts a new checkpoint family.

## Slide 14 — Training objectives

The total objective combines complementary errors:

| Loss | Purpose |
| --- | --- |
| SI-SNR | Scale-invariant waveform separation quality |
| Scale-sensitive SNR | Penalizes wrong output level |
| Multi-resolution STFT | Matches spectral structure at several time/frequency resolutions |
| Power-compressed complex loss | Preserves complex spectral detail and phase-sensitive structure |
| Waveform L1 | Controls sample-domain reconstruction errors |
| Clean-identity loss | Prevents unnecessary changes when input is clean |
| Short-time speech-retention loss | Penalizes brief deletion of active speech during transients |

Broad-stage weights: SI-SNR 0.50, SNR 0.50, multi-resolution STFT 0.50, complex 0.25,
waveform L1 0.50, clean identity 0.75 and retention 0.10. An evidence-triggered five-epoch
preservation correction adds preservation-SNR, spectral-identity, spectral-delta and
phase-consistency objectives before defence fine-tuning.

Speaker note: No single metric represents all required behavior; the loss mirrors suppression,
quality, level and preservation simultaneously.

## Slide 15 — Gated curriculum

### Stage 1: broad pretraining

- 40 epochs, 20,000 generated samples per epoch.
- Broad categories and SNR range.
- Learns general speech/noise separation.
- Output: `checkpoints_v4_stage1/best.pt`.

### Preservation correction gate

- Initialize from the accepted Stage-1 checkpoint with a fresh optimizer.
- Five bounded epochs at learning rate 7.5e−5; 30% clean and 25% near-clean examples.
- Select `best.pt` with an explicit preservation-aware score.
- Use a 90% processed / 10% aligned-input runtime blend to limit residual coloration.
- Output: `checkpoints_v4_preserve/best.pt`.

### Stage 2: defence-weighted fine-tuning

- Initialize model weights from the preservation checkpoint, but start a fresh optimizer.
- 25 epochs, lower learning rate 1e−4.
- Oversample MAD 4× and emphasize impulsive/non-stationary labels.
- Strengthen clean preservation and transient speech retention.
- Output: `checkpoints_v4_stage2/best.pt`.

### Stage 3: target-hardware fine-tuning

- Initialize from stage 2 with fresh optimizer.
- 15 epochs, learning rate 3e−5.
- Use synchronized final-device/session manifests and target RIRs.
- Retain broad validation to detect catastrophic forgetting.
- Output: `checkpoints_v4_stage3/best.pt`.

Resume is separate from initialization: `resume` restores the exact stage, optimizer, scheduler
and scaler after interruption. Therefore training can be safely stopped and continued.

## Slide 16 — Exact training workflow

```powershell
# 1. Bounded integration test only
voxshield-train --config configs/hybrid_v4_smoke.yaml --device cuda

# 2. Run only after data-audit-v4.json says ready=true
voxshield-train --config configs/hybrid_v4_stage1_broad.yaml --device cuda
voxshield-train --config configs/hybrid_v4_stage1_preserve.yaml --device cuda
voxshield-train --config configs/hybrid_v4_stage2_defence.yaml --device cuda

# 3. Run only after real target manifests exist
voxshield-train --config configs/hybrid_v4_stage3_target.yaml --device cuda
```

Training features:

- CUDA or CPU selection.
- Automatic mixed precision when supported.
- Train/validation logging by epoch.
- Best and latest checkpoints.
- Early stopping.
- Full optimizer/scheduler/scaler state for exact resume.
- TensorBoard-compatible run directories.

Important: stage 3 configuration is intentionally unusable until real target manifests are
created. This prevents a generic synthetic model from being mislabeled as target-hardware ready.

## Slide 17 — Evaluation design

Every candidate is evaluated on the same frozen pairs and reported:

- Overall and noisy-only SNR and SI-SNR.
- STOI for intelligibility.
- PESQ when installed; missing PESQ fails the strict gate.
- Pause-noise attenuation.
- Speech-deletion rate.
- Active-speech output-level error.
- Per-category results: stationary, non-stationary, impulsive, environmental and mixed.
- Per-SNR-bin results.
- Per-source-label results such as gunshot, shelling, tank/vehicle and helicopter.
- Clean and near-clean preservation.
- Checkpoint, ONNX and manifest SHA-256 provenance.

PESQ is the ITU-T P.862 family metric for perceptual speech quality, while STOI estimates speech
intelligibility. Objective metrics complement rather than replace listening tests.

## Slide 18 — Release quality gates

Minimum regression gate:

- Noisy-only SNR improvement ≥ 1 dB.
- Noisy-only SI-SNR improvement ≥ 1 dB.
- STOI change ≥ −0.01.
- Pause-noise attenuation ≥ 3 dB.
- Speech deletion rate ≤ 2%.
- Every required noise category must be present and avoid >1 dB SNR/SI-SNR regression.
- Clean and near-clean preservation must pass.

Strict SIH gate:

- Enhanced noisy output SNR ≥ 15 dB.
- Enhanced STOI ≥ 0.85.
- Enhanced PESQ ≥ 2.5.
- Speech deletion rate ≤ 2%.
- Clean active-level error ≤ 1 dB.

Final evidence also requires matched listening, not only automatic metrics.

## Slide 19 — Candidate selection without metric cherry-picking

**IMPLEMENTED:** `voxshield-compare` evaluates candidate reports on the same manifest/provenance.

Selection rule:

- A candidate must pass the required gate.
- A unique winner is declared only if it Pareto-dominates alternatives: it is no worse on the
  chosen metrics and better on at least one.
- If one model has better suppression but worse speech preservation, the tool reports the
  trade-off instead of hiding it in an arbitrary weighted score.
- Listening and runtime evidence break unresolved ties.

This avoids choosing a model only because one headline metric improved.

## Slide 20 — Streaming inference design

**IMPLEMENTED:** neural inference is outside the PortAudio callback.

```text
audio callback → bounded input queue → inference worker → aligned output store
       │                                             │
       └──────── delayed dry primary fallback ◄──────┘
```

- The callback never waits for the neural model.
- Default playout delay is WOLA 24 ms plus one 8 ms worker block = 32 ms before device/driver
  latency.
- Late neural output is discarded rather than played at the wrong time.
- Its corresponding delayed dry block is used on underflow.
- Sequence gaps reset recurrent state.
- Queues are bounded, preventing unlimited latency growth.
- Live report records underflows, dropped inputs, worker failures and runtime bypasses.

Only physical loopback can establish true microphone-to-output latency.

## Slide 21 — Runtime health and degraded mode

Protection layers:

- Sanitize non-finite input and output.
- Bound output amplitude.
- Track inference deadline misses and audio status events.
- Enter aligned degraded/bypass mode after repeated failures.
- Recover only after a stable sequence of valid frames.
- Record all counters in the session report.
- Hardware bypass remains required because software bypass cannot help after Pi, power or USB
  failure.

Two-hour Pi acceptance requires:

- 7,200 seconds completed.
- Zero audio xruns/status events.
- Zero inference output underflows.
- Zero dropped input blocks.
- Zero worker/model failures and invalid-model bypasses.
- No thermal throttling.

## Slide 22 — Interactive Mission Console

**IMPLEMENTED:** A local operator console connected to the real live engine displays:

- Primary, reference and enhanced spectra over 0–8 kHz.
- Scrolling enhanced spectrogram/waterfall.
- Reference level.
- Runtime mode and last inference time.
- Output-underflow count and degradation reason.
- Wet/dry strength, Safe/Balanced/Tactical presets, output trim, bypass and mute.
- Channel correlation, level delta, normalized difference and leakage warning.
- Waveforms, six-band energy, runtime counters, artifact hash and timestamped event markers.

It deliberately does **not** show live SNR, STOI or PESQ because live audio has no known clean
target. Displaying those values would be fabricated telemetry.

Commands:

```powershell
& ".\scripts\run_v10_laptop_demo.ps1" -InputDevice 9 -OutputDevice 12 `
  -PrimaryChannel 0 -ReferenceChannel 1 -WetMix 0.82 -Threads 1
```

Suggested visual: screenshot the dashboard only while a real live run is active; label the
signals and test condition.

## Slide 23 — ONNX export and numerical validation

Final export:

```powershell
voxshield-export --checkpoint checkpoints_v4_stage3/best.pt `
  --output artifacts/voxshield-v4-final.onnx
```

The exporter checks sequential one-frame outputs and recurrent states between PyTorch and ONNX.
It records hashes, architecture, per-output maximum error, tolerance and pass/fail. A model is
not promoted when the numerical comparison fails.

**MEASURED integration evidence only:** the untrained v4 smoke model exported successfully and
passed PyTorch/ONNX equivalence. This proves the export path works; it says nothing about final
speech quality.

## Slide 24 — Quantization strategy

Dynamic INT8 is created as a candidate, not automatically accepted:

```powershell
voxshield-quantize --checkpoint checkpoints_v4_stage3/best.pt `
  --input artifacts/voxshield-v4-final.onnx `
  --output artifacts/voxshield-v4-final-int8.onnx
```

Validation sequence:

1. Numerically compare FP32 and INT8 stateful outputs.
2. Evaluate both on the identical frozen test manifest.
3. Compare quality and preservation with `voxshield-compare`.
4. Benchmark both on the Pi 5.
5. Choose FP32 when INT8 is not faster or quality regresses.

ONNX Runtime notes that dynamic quantization is generally suitable for RNNs but has on-the-fly
scaling overhead, so speed improvement is hardware/model dependent.

**MEASURED smoke evidence:** INT8 reduced the smoke ONNX file from 211,622 to 165,427 bytes, but
was slightly slower on the laptop CPU. Therefore Pi measurement, not assumption, decides.

## Slide 25 — Raspberry Pi 5 deployment plan

1. Use 64-bit Raspberry Pi OS, official power supply and active cooling.
2. Install dependencies with `scripts/pi/install.sh`.
3. Copy the final matching checkpoint and ONNX model.
4. List and verify synchronized audio devices.
5. Benchmark FP32 and INT8 with 1–3 threads.
6. Require p99 inference below the 8 ms hop, not just average RTF below 1.
7. Measure physical loopback latency ≤ 50 ms.
8. Run two hours with a session report and zero faults.
9. Review temperature, `vcgencmd get_throttled`, memory and audio counters.
10. Enable the systemd service only after the manual tests pass.

Two-hour command:

```bash
voxshield-live --checkpoint checkpoints_v4_stage3/best.pt \
  --onnx artifacts/voxshield-v4-final.onnx --input-device DEVICE \
  --output-device DEVICE --primary-channel 0 --reference-channel 1 --threads 1 \
  --duration-seconds 7200 --session-report artifacts/pi5-soak.json
```

## Slide 26 — Physical ANC development path

The repository includes bounded NLMS/FxNLMS components and a safe offline simulator:

```powershell
voxshield-anc-simulate --reference reference.wav `
  --disturbance error-muted.wav --secondary-path secondary-path.wav `
  --output-dir artifacts/anc-simulation
```

Required real development steps:

1. Build a safe test fixture; do not begin on a person.
2. Measure the secondary path from digital output through DAC/headphone/acoustic path to error
   microphone.
3. Verify polarity and latency at very low output.
4. Run offline simulation on recorded synchronized signals.
5. Implement bounded low-level real-time FxNLMS, preferably on DSP/MCU.
6. Add feedback detection, saturation protection and output slew limits.
7. Validate attenuation by frequency band, stability and maximum safe output.
8. Verify hardware bypass for process crash, Pi failure, USB loss and power loss.

High-frequency/impulsive physical cancellation is fundamentally harder because acoustic-path
uncertainty and latency grow important. The neural communication path remains the primary method
for those events.

## Slide 27 — Current v4 engineering evidence

**MEASURED, but not final quality:**

- 39 automated tests pass after UAV conversion, RIR-aware freezing and dashboard/report additions;
  Ruff reports no lint issues.
- One-epoch CPU smoke training completed.
- Stateful dual-input ONNX export passed numerical validation.
- Laptop ONNX smoke benchmark over 200 frames: 0.362 ms mean, 0.677 ms p99, 0.045 frame RTF.
- Dynamic INT8 export passed guarded numerical comparison and reduced the smoke file by about
  21.8%.
- Dataset audit found no missing references and no group split leakage.

What these prove: the code paths integrate and are fast on the development laptop.

What they do not prove: trained enhancement quality, SIH target achievement, Pi timing, real
microphone robustness, physical ANC, safety or field readiness.

## Slide 28 — Remaining blockers and risk controls

| Blocker/risk | Control |
| --- | --- |
| Generic UAV data differs from final deployment | Retain NASA corpus and add real target sessions |
| Simulated RIRs differ from headset geometry | Add measured target-geometry responses for stage 3 |
| Only 39.33 h clean training speech | Add speaker/accent/language-diverse clean subsets |
| Speech deletion under impulses | Retention loss, overlap sampling, per-event and listening gate |
| Reference mic contains speech | Leakage augmentation, identity gate, synchronized real fine-tuning |
| Domain gap | Stage-3 final-device/session fine-tuning |
| Average metric hides failures | Per-category, per-label, per-SNR and speech-deletion reports |
| Pi glitches despite good mean RTF | p99 deadline, physical loopback and two-hour zero-fault soak |
| Quantization harms quality | Treat INT8 as candidate and compare against FP32 |
| Software crash | Aligned dry fallback plus independent hardware bypass |
| Physical ANC instability | Offline simulation, bounded controller, fixture testing and calibrated secondary path |

## Slide 29 — Exact plan of action from today

### Phase 1 — Complete data readiness

1. RIR/UAV acquisition, conversion and audit are complete.
2. Verify MAD and UAV provenance/license records.
3. Add more clean Indian-accent/language speech where permitted.
4. Run broad and defence training using the ready catalog.
5. Record synchronized target sessions before stage 3.

### Phase 2 — Train and iterate economically

1. Run smoke test.
2. Train stage 1; evaluate validation at each checkpoint.
3. Continue only if suppression and preservation both improve.
4. Fine-tune stage 2 and compare Pareto performance.
5. Capture failure examples and add them only to training, never the frozen test set.
6. Fine-tune stage 3 on target hardware recordings.

### Phase 3 — Freeze and validate

1. Freeze final checkpoint and manifest hashes.
2. Run strict held-out evaluation including PESQ.
3. Complete randomized matched listening.
4. Export FP32/INT8 and validate ONNX equivalence.
5. Select candidate using quality plus runtime evidence.

### Phase 4 — Pi and prototype

1. Pi benchmark and thread tuning.
2. Physical loopback measurement.
3. Two-hour thermal/xrun soak.
4. Live demo through intended microphones/headset.
5. Only then begin calibrated physical ANC fixture testing.

## Slide 30 — Definition of “complete”

Communication enhancement is complete only when:

- Dataset audit is ready and provenance is recorded.
- All three v4 stages have trained checkpoints.
- Final ONNX matches the final checkpoint.
- Strict held-out SNR/STOI/PESQ and preservation gates pass.
- Listening tests pass.
- Pi p99 timing and physical loopback limits pass.
- Two-hour Pi soak has zero faults and no throttling.

Physical ANC is complete only when all communication gates pass **and**:

- The secondary path is measured on the final headset/fixture.
- Stable measured attenuation is reported by band.
- Safe output bounds are documented.
- Hardware bypass is verified under crash, device and power failures.

Until then the truthful status is **research and validation**, which is exactly what
`voxshield-readiness` reports.

## Slide 31 — Expected final deliverables

- Versioned data inventory and leak-free manifests.
- Reproducible fixed validation/test pairs.
- Three-stage training configs, logs and resumable checkpoints.
- Final PyTorch checkpoint and validated ONNX models.
- Objective and per-category evaluation reports.
- Listening-test evidence and selected audio examples.
- Offline, streaming and live inference commands.
- Local engineering dashboard.
- Pi benchmark, loopback and two-hour soak reports.
- Model card with limitations and hashes.
- Offline FxNLMS simulation and, only after calibration, physical ANC test evidence.
- Source code, tests, setup guide and deployment service.

## Slide 32 — Closing message

VoxShield v4 is designed around the real failure mode discovered in v3: noise reduction is not
success if the voice is damaged. The rebuilt system combines synchronized reference sensing,
causal complex-domain enhancement, preservation-aware training, strict evidence gates, bounded
real-time execution and a separate safe path toward physical ANC.

Closing line: **Suppress the environment, preserve the message, prove the result on the target
hardware.**

---

## Appendix A — Commands for the final demonstration

```powershell
# Readiness report
voxshield-readiness --project-root . --output artifacts/readiness.json

# Final evaluation
voxshield-evaluate --checkpoint checkpoints_v4_stage3/best.pt `
  --onnx artifacts/voxshield-v4-final.onnx `
  --manifest data/mixtures/test_v4/manifest.jsonl --device cpu `
  --strict-sih-gate --fail-on-regression `
  --output artifacts/v4-final-test.json --save-audio artifacts/v4-final-test-audio

# Offline dual-channel demonstration
voxshield-infer primary.wav enhanced.wav --reference reference.wav `
  --checkpoint checkpoints_v4_stage3/best.pt --onnx artifacts/voxshield-v4-final.onnx

# Pi benchmark
voxshield-benchmark --checkpoint checkpoints_v4_stage3/best.pt `
  --onnx artifacts/voxshield-v4-final.onnx --threads 1 --frames 10000 `
  --output artifacts/pi5-v4-benchmark.json
```

## Appendix B — Recommended figures and tables

- Problem-to-requirement traceability table from slide 2.
- Blue/orange dual-path architecture from slides 4–5.
- Stacked bar of current hours/files by noise class from `data-audit-v4.json`.
- Dynamic mixing diagram from slide 10.
- STFT → features → recurrent core → complex mask → WOLA reconstruction.
- Three-stage curriculum timeline.
- Metric table broken out by noise category and SNR bin.
- Latency budget: 24 ms WOLA + 8 ms worker playout + measured device/driver latency.
- Pi thermal, p99 inference and xrun timeline from the final soak report.
- Before/noisy/enhanced spectrograms from the same frozen test example.
- Physical ANC reference/controller/secondary-path/error loop.

## Appendix C — Sources for citations in the presentation

- [Microsoft DNS Challenge official repository](https://github.com/microsoft/DNS-Challenge)
- [MUSAN at OpenSLR](https://www.openslr.org/17/)
- [ESC-50 official repository](https://github.com/karolpiczak/ESC-50/blob/master/README.md?plain=1)
- [VCTK 0.92, University of Edinburgh](https://datashare.ed.ac.uk/handle/10283/3443)
- [OpenSLR SLR28 RIR and noise data](https://www.openslr.org/28/)
- [AI4Bharat IndicVoices official repository](https://github.com/AI4Bharat/IndicVoices)
- [NASA Small UAS Flyover Acoustics](https://catalog.data.gov/dataset/small-uas-flyover-acoustics-data)
- [Official GTCRN implementation](https://github.com/Xiaobin-Rong/gtcrn)
- [ITU-T P.862 PESQ recommendation](https://www.itu.int/ITU-T/recommendations/rec.aspx?rec=5374)
- [ONNX Runtime quantization documentation](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html)
- [Raspberry Pi computer hardware and thermal documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
