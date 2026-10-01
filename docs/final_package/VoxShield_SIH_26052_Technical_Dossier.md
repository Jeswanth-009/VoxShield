# VoxShield SIH 26052 Technical Dossier

Team Name: Team@
Problem Statement ID: 26052

## Technical objective

The technical objective is to build a real-time AI speech enhancement system for noisy defence communication. The system should suppress or reduce stationary, nonstationary and impulsive noise while preserving command speech. The intended deployment direction is edge hardware such as Raspberry Pi 5 connected to a controlled dual-microphone input path.

## System definition

VoxShield consists of six major layers:

1. data and mixture generation layer
2. training and hard-case repair layer
3. streaming AI enhancement model
4. ONNX export and parity validation
5. edge runtime and benchmark layer
6. dashboard and evidence reporting layer

## Audio input model

The model is designed around synchronized audio channels:

- primary channel: speech plus noise near the mouth or communication source
- reference channel: environmental noise reference

This is important because a single Bluetooth microphone or laptop microphone array does not provide a reliable raw reference channel. Physical deployment needs a dual-microphone hardware rig with stable timing.

## Data sources used or planned

| Source | Role |
|---|---|
| VCTK | clean speech |
| DNS Challenge | speech/noise challenge material |
| MAD dataset | military-like or hard acoustic material |
| ESC-50 | environmental noise categories |
| AudioSet targeted subset | gunshot, explosion, vehicle, engine, siren, helicopter, aircraft |
| RIRS NOISES | room impulse responses and reverb |
| user recordings | personal clean/noisy examples such as fan and helicopter playback |

## Data ingestion status

The user has already ingested a large referenced catalog without copying audio. A later manifest included targeted AudioSet folders mapped into impulsive and nonstationary categories. The manifest counts showed more than 124,000 referenced files, with clean speech, environmental noise, impulsive noise, nonstationary noise, stationary noise and RIR categories.

This is useful because the deck can claim a real data pipeline, not a toy dataset.

## Model and runtime

The current candidate model family is a dual-channel deep-filter model exported to ONNX. The model is lightweight enough for edge testing, around 1.1M parameters in reported slides. The model runs in a frame-based streaming style at 16 kHz with a 16 ms frame duration.

The runtime stack includes:

- Python training and evaluation tools
- ONNX export
- ONNX runtime inference
- Pi 5 benchmark
- live console or dashboard telemetry

## Current strongest model candidates

| Candidate | Strength | Limitation |
|---|---|---|
| v12 hard repair | strong metric candidate | older than v15 |
| v14 realworld audioset | added more real-world targeted data | broad gate initially failed strict reliability |
| v15 hard failure repair | broad strict gate passed, strong export and metrics | military strict gate still fails reliability thresholds |

Recommended deck candidate: v15 for recent narrative and broad gate proof. If comparing final numbers internally, keep v12 as a backup candidate if it outperforms in selected audits.

## v15 export evidence

v15 ONNX export passed parity validation. Reported values:

- checkpoint: checkpoints_deep_filter_v15_hard_failure_repair/best.pt
- ONNX: artifacts/voxshield-v15-hard-failure-repair-final.onnx
- max output absolute error: about 1.82e-08
- max state absolute error: about 4.07e-06
- tolerance: 0.0002
- export status: passed

This proves the PyTorch model and ONNX export are numerically aligned enough for runtime deployment testing.

## v15 broad audit

Reported v15 broad results:

- SNR enhanced: 30.48 dB
- SI-SNR enhanced: 30.64 dB
- STOI enhanced: 0.938
- PESQ enhanced: 3.94
- pause noise attenuation: 20.24 dB
- speech deletion rate: 0.0
- active level error: 0.10 dB
- strict SIH gate: passed

This should be used in the PPT as broad controlled-audit evidence.

## v15 military audit

Reported v15 military results:

- SNR enhanced: 25.15 dB
- SI-SNR enhanced: 25.30 dB
- STOI enhanced: 0.915
- PESQ enhanced: 3.63
- pause noise attenuation: 24.58 dB
- speech deletion rate: 0.0
- active level error: 0.19 dB

The quality gate did not fully pass strict military reliability because STOI target reliability and joint target reliability missed thresholds. This should not be hidden in the technical dossier. It means the average is strong, but some hard clips still fail. That is a normal engineering finding and justifies the hard-case repair roadmap.

## Pi 5 benchmark evidence

Reported Pi 5 verification:

- backend: ONNX runtime
- frame duration: 16 ms
- mean latency: about 5.33 ms
- p95 latency: about 5.49 ms
- p99 latency: about 6.05 ms
- full pipeline p99 callback: about 6.50 ms
- real-time factor: about 0.33
- deadline overruns: 0
- simulated callback drops: 0

This is one of the strongest project facts. Use it repeatedly, but do not overstate it as full headset validation.

## Why live Bluetooth sounded bad

Bluetooth headsets commonly apply their own processing and use profiles that trade bandwidth, latency and microphone quality. Laptop and Bluetooth paths may:

- downsample or compress audio
- apply built-in noise suppression
- expose only mono audio
- fail to provide a clean reference channel
- add unpredictable latency
- prevent raw synchronized capture

Therefore, a bad Bluetooth demo does not automatically prove the model is useless. It proves the hardware path is wrong for validating physical cancellation.

## Correct hardware architecture

Minimum next hardware rig:

- Raspberry Pi 5
- USB audio interface or multi-channel USB microphone device
- primary microphone near mouth
- reference microphone placed toward noise source
- wired headset or speaker output
- controlled noise playback source
- dashboard running locally or on same network

Avoid Bluetooth for proof demos.

## Evaluation metrics

| Metric | Meaning |
|---|---|
| SNR | energy-level noise reduction relative to clean target |
| SI-SNR | scale-invariant signal quality |
| STOI | intelligibility estimate |
| PESQ | perceptual quality estimate |
| speech deletion rate | checks whether speech was removed |
| active level error | checks whether speech loudness is preserved |
| latency | real-time feasibility |

## Technical risks and mitigations

| Risk | Technical reason | Mitigation |
|---|---|---|
| Bad live demo with laptop/Bluetooth | no synchronized raw reference | use controlled replay and wired/USB audio |
| Model overfits synthetic mixtures | real noise differs | add field recordings and targeted hard-case repair |
| Speech deletion | aggressive suppression can remove speech | keep STOI and speech deletion gates |
| Impulse and rotor failures | hard transient/nonstationary noise | hard-failure dataset and loss weighting |
| Edge CPU load | real-time deadline risk | ONNX optimization and frame-level benchmark |

## Next build plan

Phase 1: freeze v15 as current demo candidate and keep v12 as backup.

Phase 2: create a controlled demo set:

- clean command
- vehicle noise mix
- rotor noise mix
- impulse noise mix
- fan/air noise mix
- one user-recorded scenario

Phase 3: build hardware rig:

- wired mic path
- synchronized dual input
- Pi 5 runtime
- dashboard

Phase 4: record real validation clips and rerun audit.

## Technical conclusion

VoxShield is not yet a fully proven physical ANC product. It is a strong AI speech enhancement prototype with a validated edge-runtime path and a clear hardware validation roadmap. This is the correct, defensible technical story.
