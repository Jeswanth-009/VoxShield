# VoxShield v4 — master technical and project dossier

**Project:** AI/ML-enabled hybrid noise suppression and active noise control for defence communication  
**Problem statement:** SIH 2026, ID 26052, DRDO, Hardware category, Miscellaneous theme  
**Repository:** `C:\anc` only  
**Document date:** 25 September 2026  
**Current truthful status:** research and validation; not yet a field-ready or SIH-target-compliant release

This document is a continuous technical dossier and presentation source. It is deliberately not
organized slide by slide. It contains the material needed to prepare a presentation, technical
report, jury defence, demonstration script, model card and implementation plan.

Three evidence labels are used throughout:

- **Measured:** supported by a saved project artifact, log, hash, test or user-performed run.
- **Implemented, awaiting final validation:** code exists and engineering/smoke tests pass, but the
  completed trained system has not yet passed all release gates.
- **Required or planned:** depends on further training, real target recordings, Raspberry Pi tests,
  physical hardware or human evaluation.

The most important honesty rule is this: a microphone speech-enhancement model and physical active
noise control are related but different systems. VoxShield v4 implements the complete research
and runtime framework for communication speech enhancement and provides a bounded FxNLMS research
path for physical ANC. It does not yet prove acoustic anti-noise cancellation at a listener's ear.

---

## 1. Executive summary

Defence communication is affected by several acoustically different disturbances: steady engine
and fan noise, rotor and vehicle modulation, wind and sirens, moving machinery, competing sounds,
and very short high-energy events such as gunshots and artillery. A fixed spectral filter cannot
handle all of these conditions well. A neural model can learn nonlinear time-frequency structure,
but an aggressive model may also remove consonants, alter the speaker's timbre or erase speech
that overlaps an impulse. Real-time deployment adds strict latency, compute, memory, thermal,
audio-driver and fail-safe constraints.

VoxShield v4 therefore uses a systems approach rather than treating the neural network as the
whole project:

1. Large datasets are indexed in place, validated and split by speaker/source/session groups.
2. Clean speech is dynamically mixed with stationary, non-stationary, impulsive, environmental,
   military and UAV noise over controlled SNRs.
3. Two synchronized channels are synthesized for training: a close-talk primary channel and a
   noise-dominant reference channel with realistic delay, gain mismatch, spectral change, speech
   leakage and self-noise.
4. A causal, lightweight, complex-domain recurrent model estimates enhanced speech from those two
   channels using full-band, ERB/sub-band and inter-channel cues.
5. Training combines suppression losses with explicit clean-speech identity, active-speech
   retention, spectral identity and phase-consistency losses.
6. Frozen validation and test mixtures prevent benchmark manipulation.
7. Offline, chunked and live inference share safe conditioning, bounded output and aligned bypass.
8. Stateful ONNX export, PyTorch-versus-ONNX comparison, INT8 candidacy and Raspberry Pi 5
   benchmarking provide a realistic embedded path.
9. A separate FxNLMS path is reserved for physical ANC because it requires a reference microphone,
   error microphone, actuator and measured secondary path.

The current v4 Stage-1 checkpoint has 12,259 trainable parameters and was trained for ten broad
pretraining epochs. On a 50-item military subset it improved the noisy-only SNR by 13.60 dB,
SI-SNR by 12.74 dB and STOI by 0.179. However, the same checkpoint still colored clean speech and
did not meet the strict military output targets. PESQ was not computed. It must not be described as
the final model. The next experiment is a five-epoch preservation correction, after which the
unchanged broad and military sets must be evaluated before defence-weighted Stage 2 is permitted.

---

## 2. Problem statement and exact engineering meaning

### 2.1 Problem identity

- Problem Statement ID: **26052**
- Organization: **Defence Research and Development Organisation (DRDO)**
- Department: **Department of Defence R&D** as supplied in the problem statement
- Category: **Hardware**
- Theme: **Miscellaneous**
- Title: **To develop an AI/ML-enabled adaptive noise cancellation (ANC) system that effectively
  suppresses stationary, non-stationary, and impulsive defence noises while maintaining high
  speech intelligibility and real-time performance on embedded hardware.**

The problem statement describes gunshots, artillery, helicopter rotor noise, armored vehicle
sound, wind, drones and emergency sirens. It calls for clean-plus-noise dataset generation at
varying SNR, STFT or waveform processing, full-band and sub-band features, complex-domain phase
handling, SI-SNR and L1/L2/perceptual training losses, reverberation and clipping augmentation,
real-time inference, optional LMS residual filtering, edge deployment, ONNX/TensorRT-style
optimization and microphone/headset integration. Its stated targets are:

- enhanced/output SNR greater than 15 dB;
- STOI greater than 0.85;
- PESQ greater than 2.5;
- low latency suitable for real-time communication.

These are acceptance targets, not current measured achievements.

### 2.1A Complete normalized problem-statement text supplied for the project

**Background.** In defence and mission-critical communication systems, reliable speech
transmission is severely affected by diverse acoustic disturbances such as gunshots, artillery
fire, helicopter rotor noise, armored-vehicle sound and emergency sirens. Traditional signal-
processing techniques such as spectral subtraction, Wiener filtering and classical LMS-based ANC
are limited in highly dynamic and nonlinear noise environments. These methods often assume
stationary noise and can introduce artifacts or speech distortion under rapidly changing
conditions.

Recent AI/ML advances have transformed speech enhancement and ANC. Deep-learning and time-domain
architectures can learn complex spectral-temporal patterns directly from data and can improve
perceptual quality, intelligibility and noise suppression. Edge-AI platforms also make real-time
deployment possible on embedded systems.

**Description.** The proposed system integrates AI/ML-driven noise suppression with adaptive
filtering to create a robust ANC pipeline. Development begins with dataset generation, in which
clean speech is combined with curated defence noise—gunshots, drones, artillery, vehicle engines,
wind and related sounds—at varying SNR. Synthetic generation must cover stationary and impulsive
scenarios.

Training may transform audio to time-frequency representations such as STFT spectrograms or use
waveforms directly. Models should process full-band and sub-band features to capture global and
local dependencies and operate in the complex domain to preserve phase information. Training uses
losses such as SI-SNR, L1/L2 and perceptual loss; evaluation uses SNR, STOI and PESQ. Random noise
mixing, reverberation and clipping are included for generalization.

During inference, the trained model processes incoming noisy audio in real time, estimating a mask
or directly reconstructing enhanced speech. A lightweight adaptive filter such as LMS may be
included for residual suppression.

For the prototype, the model is deployed on embedded/edge hardware such as a DSP or AI-enabled SoC
(the statement gives NVIDIA Jetson AGX Orin 64 GB or a similar platform as an example).
Quantization, pruning and ONNX/TensorRT conversion are used where appropriate to meet latency and
power constraints. Primary/reference microphones and a headphone or communication unit are used
to validate real-time performance.

**Expected solution.** A hybrid AI-driven ANC system must operate in real time across diverse,
impulsive and highly dynamic defence environments. It should provide:

- a scalable pipeline for realistic noisy-clean speech pairs;
- a state-of-the-art-quality AI/ML model demonstrated by controlled comparison rather than merely
  described with that label;
- an optimized training framework with suitable hyperparameters and perceptual objectives;
- a real-time inference engine deployable on edge hardware;
- a prototype demonstrating live microphone/headset noise reduction;
- significant improvement targeting SNR above 15 dB, STOI above 0.85 and PESQ above 2.5 at low
  real-time latency.

The intended impact is more reliable and intelligible communication in defence, aerospace and
high-noise industrial environments.

### 2.2 Requirement decomposition

| Wording in the problem statement | Engineering interpretation | Current status |
| --- | --- | --- |
| AI/ML-enabled | A learned causal speech-enhancement model is trained on paired noisy and clean speech | Implemented; v4 training incomplete |
| Adaptive noise cancellation | Neural communication enhancement plus, where physical anti-noise is required, a separately calibrated adaptive controller | Neural path implemented; physical path simulation only |
| Stationary noise | Fans, hum, continuous engines and stable machinery | Data, mixing and category evaluation implemented |
| Non-stationary noise | Rotor modulation, moving vehicles, changing machinery, wind gusts and sirens | Data, mixing and category evaluation implemented |
| Impulsive defence noise | Gunshots, shelling, impacts and other high-energy transients | MAD ingestion, overlap sampling and dedicated evaluation implemented |
| Maintain intelligibility | Preserve phonemes and level, especially during noise/speech overlap | STOI, deletion and level metrics implemented; final gate not passed |
| Preserve quality | Avoid musical noise, robot voice, phase damage and speaker-identity change | New preservation objectives implemented; fine-tune not yet run |
| Real-time | Causal state, bounded queues, inference deadlines and measured end-to-end latency | Runtime implemented; Pi/physical loopback not yet measured |
| Embedded hardware | Exportable compact model and ARM64 runtime | ONNX smoke path implemented; final Pi validation pending |
| Primary + reference microphones | Two synchronized channels on the same audio clock | Model and capture software implemented; target hardware data pending |
| Optional adaptive filter | Residual/physical ANC controller must include secondary-path handling | Offline bounded FxNLMS simulator implemented; physical calibration pending |
| Prototype demonstration | Live headset/radio-compatible path with visible health and safe bypass | Laptop engineering runtime exists; final hardware prototype pending |

### 2.3 What success must mean

A successful result is not merely that background noise sounds quieter. It must simultaneously:

- improve intelligibility and/or objective separation on difficult noisy speech;
- avoid deleting words during impulses;
- leave clean and near-clean speech essentially unchanged;
- preserve speaker character and naturalness in matched listening tests;
- process continuously within the frame deadline;
- remain stable under input loss, clipping, late inference and model faults;
- run on the target edge device without thermal throttling or audio xruns;
- state clearly whether it is enhancing a communication signal or physically cancelling sound.

---

## 3. Terminology: speech enhancement, AEC and physical ANC

### 3.1 Communication speech enhancement

Speech enhancement transforms a recorded/transmitted signal:

```text
primary microphone + reference microphone
                  ↓
       causal neural enhancer
                  ↓
 cleaner communication/recording signal
```

It can make a radio transmission, recording or headphone monitoring feed clearer. It cannot make
the external acoustic wave disappear from the room.

### 3.2 Acoustic echo cancellation

AEC removes the known far-end loudspeaker signal from a near-end microphone. That is a different
reference relationship from defence noise suppression. It may be necessary in a duplex intercom,
but it is not the same as ambient-noise ANC.

### 3.3 Physical active noise control

Physical ANC generates an anti-noise waveform through a speaker/headphone so that destructive
interference reduces noise at an error microphone or the listener's ear:

```text
reference noise x(n) → adaptive control filter W(z) → actuator/headphone
          │                                         ↓
          └──── filtered by estimated secondary path S^(z)

primary disturbance d(n) + secondary anti-noise → error microphone e(n)
```

The controller update uses the reference filtered by an estimate of the secondary path. The
secondary path includes DAC, filters, amplifier, transducer, acoustic cavity, error microphone,
preamplifier, anti-alias filter and ADC. Published ANC work emphasizes that secondary-path
estimation and the relative primary/secondary delay are central to convergence and attenuation.
Therefore a Python denoiser connected to a laptop microphone must not be presented as proof of
physical ANC. See the [FxLMS secondary-path study](https://doi.org/10.1016/j.apacoust.2017.10.026),
the [ANC survey](https://doi.org/10.1016/j.sigpro.2021.108039) and the
[headset electroacoustic implementation](https://pubmed.ncbi.nlm.nih.gov/29604695/).

### 3.4 Hybrid meaning in VoxShield

“Hybrid” has two legitimate meanings here:

- neural enhancement combines learned spectral-temporal processing with classical STFT/WOLA,
  conditioning, limiting and runtime control; and
- a future full prototype combines the neural communication path with a separately calibrated
  physical FxNLMS loop.

The adaptive filter must not be placed blindly after the enhancer. For speech enhancement, an
unknown LMS reference can cancel wanted speech. For physical ANC, controller stability depends on
actual electro-acoustic geometry.

---

## 4. System use cases and stakeholders

Primary use cases include clearer push-to-talk speech from an armored vehicle, rotorcraft or UAV
ground environment; improved intercom speech in machinery noise; robust recorded commands in
industrial safety settings; and research into low-frequency physical attenuation in a controlled
headset fixture.

Stakeholders and their success criteria are different:

- **Operator/soldier:** speech is understandable, natural and never unexpectedly muted.
- **Receiving operator:** commands remain intelligible without listening fatigue.
- **System integrator:** deterministic audio interface, documented levels, PTT behavior and API.
- **Safety engineer:** bounded output, physical bypass, fault records and reproducible validation.
- **ML engineer:** leak-free data, traceable checkpoints, held-out tests and honest model cards.
- **Embedded engineer:** frame-deadline, CPU, memory, power and thermal evidence on the real board.
- **DRDO/SIH jury:** clear mapping from requirements to implementation and measured evidence.

Out of scope for the present release are certified hearing protection, connection to classified
or operational defence radios, medical hearing claims, battlefield readiness and safety-critical
autonomous operation.

---

## 5. Development history and why the plan changed

### 5.1 Starting from an empty project

The deleted earlier prototype was not reused. VoxShield was rebuilt in `C:\anc` without assuming
legacy source, checkpoints, datasets, configs or test audio. The repository now contains the data
pipeline, model families, training, evaluation, runtime, export, deployment and tests.

### 5.2 v3 single-channel baseline

V3 used the official GTCRN family as a compact single-microphone baseline. The official repository
describes GTCRN as an ICASSP 2024 ultra-lightweight model with 48.2k parameters and 33 MMAC/s and
provides a streaming implementation; this justified it as a baseline, not as an automatic final
choice. See the [official GTCRN repository](https://github.com/jiayukk/complex_gtcrn).

An early five-epoch v3 experiment improved its training and validation loss but failed on the
500-pair evaluation: enhanced SNR was 11.78 dB versus 14.15 dB for the noisy input, and enhanced
SI-SNR was 10.91 dB versus 14.18 dB. STOI rose only from 0.8002 to 0.8099. This proved that a lower
training loss was not enough.

After the v3 recipe was revised, its full validation set passed the project regression gate:
overall SNR rose from 14.15 to 16.11 dB, SI-SNR from 14.18 to 15.63 dB and STOI from 0.8002 to
0.8439. On the noisy-only subset SNR improved by 12.45 dB and SI-SNR by 11.82 dB.

However, the independent 1,000-pair test set failed. Overall SNR fell from 15.66 to 13.04 dB and
SI-SNR from 15.72 to 12.33 dB, even though noisy-only examples improved strongly. Clean and
near-clean speech were being unnecessarily processed. Live listening with tank/blast playback
also revealed a worse failure: when an impulse overlapped the voice, portions of speech were
wiped or sounded robotic.

The v3 ONNX export itself was numerically correct—maximum enhanced-output absolute error was about
2.27e-8 and maximum state error about 3.10e-6—so export was not the cause. The problem was the
learned behavior and domain mismatch.

### 5.3 Root causes of the poor live result

The failure was not simply a bad laptop microphone. The microphone and speaker test geometry made
the test less representative, but several technical causes were present:

- a single microphone had no independent noise-dominant observation;
- loudspeaker-played “tank sound” did not reproduce the dataset acoustics, level or spatial path;
- synthetic train mixtures did not match the laptop's AGC, room, speaker and microphone response;
- aggressive masks treated impulse-overlapped speech components as noise;
- average loss and STOI reward intelligibility but do not guarantee natural timbre or identity;
- clean/near-clean identity behavior was underweighted;
- real-time device buffers and feedback can create breaks independently of model inference;
- information completely masked by a blast cannot be perfectly reconstructed from one channel.

### 5.4 Why v4 is a real redesign

V4 is not just “more epochs.” It adds synchronized dual-channel information, complex inter-channel
features, explicit preservation objectives, transient-over-speech sampling, frozen military/UAV
tests, target-device fine-tuning, bounded stateful streaming, aligned fallback and a separate
physical ANC path. V3 artifacts remain frozen for comparison.

---

## 6. Repository and software architecture

```text
C:\anc
├── configs/                 model, training and Pi runtime recipes
├── data/                    manifests and generated fixed mixtures
├── docs/                    architecture, datasets, deployment, evidence and this dossier
├── external/                pinned external model/reference material
├── scripts/pi/              Pi installation, health and service assets
├── src/voxshield/           package implementation
├── tests/                   unit, causality, data, streaming and runtime tests
├── checkpoints_v3/          frozen v3 baseline
├── checkpoints_v4_stage1/   current broad v4 checkpoint
├── artifacts/               reports, models, audio comparisons and provenance
└── runs_v*/                 append-only metrics and TensorBoard logs
```

The installed command-line interfaces are:

| Command | Role |
| --- | --- |
| `voxshield-data` | ingest, audit and create fixed mixtures |
| `voxshield-convert-uav` | convert NASA MATLAB recordings to WAV/manifests |
| `voxshield-train` | train, checkpoint, initialize or resume |
| `voxshield-evaluate` | intrusive metrics, breakdowns, audio saving and gates |
| `voxshield-compare` | provenance-aware Pareto comparison of candidate reports |
| `voxshield-infer` | offline PyTorch/ONNX enhancement |
| `voxshield-export` | stateful ONNX export and numerical equivalence |
| `voxshield-quantize` | guarded INT8 candidate creation |
| `voxshield-benchmark` | latency, RTF and memory benchmark |
| `voxshield-live` | bounded live audio runtime and degraded/bypass mode |
| `voxshield-capture` | synchronized capture and channel diagnostics |
| `voxshield-dashboard` | local read-only spectrum/waterfall monitor |
| `voxshield-anc-simulate` | bounded offline FxNLMS simulation |
| `voxshield-readiness` | evidence-based release status |
| `voxshield-smoke` | bounded integration smoke test |

The project targets Python 3.10–3.12. PESQ is optional because its Python extension may need a
compatible compiler/toolchain. The user's Windows Python 3.12 PESQ installation failed because
Microsoft Visual C++ 14 or later was not installed; this does not invalidate SNR, SI-SNR or STOI,
but it prevents the strict target gate from passing.

---

## 7. Data strategy

### 7.1 Datasets already indexed

The current machine audit references 114,805 files with no missing source paths and no detected
group split leakage.

| Dataset | Purpose | Current use and caution |
| --- | --- | --- |
| VCTK 0.92 | Clean multi-speaker speech | Speaker-disjoint splits; 110 English speakers in the official corpus |
| MUSAN | General stationary/non-stationary noise | 2,016 training-noise entries; official OpenSLR distribution is CC BY 4.0 |
| ESC-50 | Environmental/event diversity | 1,200 training entries; preserve its original source/fold grouping; CC BY-NC 3.0 |
| MAD_dataset | Military noise | 5,655 training entries with gunshot, shelling, vehicle, helicopter, fighter and footsteps; exact provenance/license still requires human verification |
| NASA Small UAS | Drone/aircraft acoustics | 62 converted flights, split 50/6/6 by flight; public-access metadata but no explicit resource license was shown, so reuse terms must still be recorded |
| RIRS_NOISES / OpenSLR SLR28 | Reverberation simulation | 60,000 simulated RIR entries; do not mislabel the separate point noises as RIRs; Apache 2.0 |

Authoritative sources include the [VCTK 0.92 record](https://doi.org/10.7488/ds/2645),
[MUSAN/OpenSLR 17](https://www.openslr.org/17/),
[ESC-50 repository](https://github.com/karolpiczak/ESC-50/blob/master/README.md),
[RIRS_NOISES/OpenSLR 28](https://www.openslr.org/28/) and the
[NASA Small UAS dataset](https://data.nasa.gov/dataset/small-uas-flyover-acoustics-data).

### 7.2 Measured catalog coverage

- Clean train speech: 39,703 files, 39.331 hours.
- Clean validation: 1,667 files, 1.725 hours.
- Clean test: 2,872 files, 2.983 hours.
- Training environmental noise: 1,458 files, 6.960 hours.
- Training impulsive noise: 3,237 files, 4.120 hours.
- Training non-stationary noise: 4,058 files, 108.772 hours.
- Training stationary noise: 168 files, 0.233 hours.
- RIRs: 53,100 train, 3,000 validation and 3,900 test entries.
- Label coverage: gunshot 1,573; artillery/shelling 987; vehicle/tank 1,032;
  helicopter/rotor 1,065; aircraft 1,031; drone 62; wind 40; siren 40.

The audit's `ready: true` means the declared data and leakage checks are present. It does not mean
licenses, acoustic relevance, label correctness or final target-domain coverage have been approved
by a human.

### 7.3 Why data is indexed in place

Large corpora are not manually rearranged or copied. Recursive ingestion reads known metadata,
validates audio headers concurrently and writes small JSONL manifests with absolute source paths.
This saves disk space and avoids duplicate data. The original drives/paths must remain accessible
during training.

For known datasets, official folds are preserved where meaningful. Otherwise, a deterministic
hash assigns a complete speaker, original recording, flight or session group to one split. Clip-
level random splitting is prohibited because neighboring clips from the same source in training
and testing would inflate metrics.

### 7.4 How a training pair is generated

Let clean speech be `s(t)` and one or more selected noise signals be `n(t)`. After active-region
cropping and augmentation, noise is scaled to target SNR `R`:

```text
alpha = RMS(s) / (RMS(n) × 10^(R/20))
x_primary(t) = s(t) + alpha n(t)
```

The reference channel is not a copy of the primary. It is synthesized as a delayed, filtered and
gain-shifted version of the noise with controlled speech leakage and self-noise:

```text
x_reference(t) = g · H_ref{n(t − d)} + beta · H_leak{s(t)} + n_self(t)
```

The model sees `x_primary` and `x_reference`; the original `s` is used only as the supervised
target. At inference time no clean target exists—the model must estimate speech from the two live
channels.

### 7.5 Augmentation

Broad Stage 1 uses SNR from −15 to +20 dB, 15% exact-clean examples, 15% near-clean examples at
25–40 dB SNR, 35% multiple-noise mixtures, 35% RIR use and 8% clipping. Simulated inter-channel
delay is −16 to +16 samples, reference noise gain is −6 to +6 dB, speech leakage is −35 to −12 dB,
reference self-noise is 35–55 dB SNR and the reference may receive spectral tilt.

Defence Stage 2 increases difficult category weights, samples −20 to +15 dB SNR, uses 45%
multi-noise and oversamples MAD fourfold. Gunshot, shelling and drone labels receive the largest
label weights. Stage 3 reduces clipping to 3% and uses target-device recordings.

Impulsive crop selection was revised so transients are deliberately placed over active speech.
This matters because random crops often place a short gunshot in silence, producing an easy or
meaningless sample. One frozen broad impulsive item had a nominal difficult setting but an actual
near-silent/noise crop, which explains an apparently contradictory category regression. Frozen
tests were retained for fair comparison; the generator was corrected for future training.

### 7.6 Frozen evaluation sets

The following sets were created once and hashed:

| Set | Count | Seed | SHA-256 |
| --- | ---: | ---: | --- |
| Validation | 500 | 2029 | `300862c07972a16d73f1ae94fefcb638a49b8520a0c1cb550e4e686916230a9e` |
| Broad test | 1,000 | 2030 | `0ef0e8d255f0f2c60620c8cb2331dac12d3491367edf66c6f20355fcceecc4c4` |
| UAV test | 200 | 2031 | `17c19138c4aa2aa0016f8714bc8266ed330fbd6c960fbefdbf5d0a3c012c73de` |
| MAD military test | 400 | 2032 | `a45a238109052f4af8e1f316fbe140e0bfda6c7123a7916767018377ec17ec76` |

The rule is: do not regenerate them because a result is disappointing. Change training, then test
again on the same pairs.

### 7.7 Data still required

The largest remaining data gap is synchronized target-domain recording. Required sessions should
retain isolated or controlled clean speech and noise wherever possible and record:

- final close-talk primary microphone;
- final outward/noise reference microphone;
- error microphone for physical ANC research;
- exact interface, gain, channel mapping and sample clock;
- room/vehicle/headset geometry and source distances;
- clean speech, noise-only and simultaneous speech-plus-noise segments;
- engine/rotor/drone/tank/siren/wind/impact conditions at safe reproduced levels;
- multiple speakers, accents, languages, voice levels and microphone positions;
- session, device and environment IDs for group-disjoint splitting.

Operational or classified audio is not required for an SIH prototype and must never be collected
without authorization. Public/safely reproduced sounds and controlled recordings are sufficient
for the research demonstration.

---

## 8. Signal-processing front end

V4 processes two mono 16 kHz channels. A 512-sample analysis window corresponds to 32 ms and the
128-sample hop corresponds to 8 ms. A square-root Hann window and weighted overlap-add provide
analysis/reconstruction. The overlap contributes `512 − 128 = 384` samples, or 24 ms, of
algorithmic buffering. End-to-end latency is larger because input/output device buffers, worker
queuing, inference and OS scheduling must be added and measured by physical loopback.

For frame `m` and frequency bin `k`, the primary and reference STFTs are `X_p(k,m)` and
`X_r(k,m)`. Features include:

- real and imaginary spectra;
- log magnitude or compressed magnitude;
- ERB/sub-band summaries;
- inter-channel log-level ratio;
- normalized cross/phase features such as cosine and sine of phase difference;
- temporal context carried by recurrent state.

The network predicts a bounded complex ratio mask `M(k,m)`. Enhanced spectrum is conceptually:

```text
Y(k,m) = M(k,m) · X_p(k,m)
```

The mask gain is bounded between configured minimum and maximum values, and an identity/preservation
gate blends toward the primary input. Reconstruction uses inverse STFT and WOLA. Input and output
are sanitized for NaN/Inf, DC and excessive peaks. The output limiter is protection, not a quality
enhancer.

Complex processing is important because magnitude-only attenuation leaves noisy phase untouched.
However, complex masks can also create robot-like coloration if they disturb harmonic phase, which
is why phase consistency and spectral identity were added.

---

## 9. Neural architecture and research rationale

The v4 model is a **Hybrid Dual-Channel Causal GTCRN-style Enhancer**. It is inspired by the edge
efficiency of GTCRN and the complementary full-band/sub-band principle demonstrated by FullSubNet,
but it is a custom two-input model and not the official single-channel GTCRN architecture.

Key blocks are:

1. synchronized primary/reference feature construction;
2. lightweight causal encoder;
3. ERB/sub-band representation for local frequency structure;
4. two recurrent causal blocks with persistent streaming state;
5. bounded complex-mask output head;
6. preservation/identity gate initialized toward safe pass-through;
7. one-frame stateful export contract for streaming ONNX.

Current configuration: 16 channels, two recurrent blocks, minimum mask gain 0.08, maximum gain
1.20 and preservation bias 2.0. The measured parameter count is 12,259. This is intentionally tiny
for Pi feasibility, but that size is also a quality risk: it may lack capacity to distinguish
speech harmonics from unseen military transients.

The research basis is sound:

- [GTCRN](https://github.com/jiayukk/complex_gtcrn) demonstrates an ultra-light streaming design.
- [FullSubNet](https://arxiv.org/abs/2010.15508) shows that global full-band and local sub-band
  information are complementary.
- [Fast FullSubNet](https://arxiv.org/abs/2212.09019) shows that sub-band acceleration matters for
  latency-sensitive embedded platforms.
- [DeepFilterNet2](https://arxiv.org/abs/2205.05474) demonstrates perceptually motivated full-band
  enhancement with an embedded real-time objective.

These papers justify design components; they do not prove VoxShield's performance. Only its own
held-out and hardware measurements can do that.

---

## 10. Training objectives

No single loss captures suppression, intelligibility, phase, level and naturalness. V4 combines
several terms.

### 10.1 SI-SNR

For zero-mean target `s` and estimate `y`, project the estimate onto the target:

```text
s_target = <y,s> s / (||s||² + epsilon)
e_noise  = y − s_target
SI-SNR   = 10 log10((||s_target||² + epsilon) / (||e_noise||² + epsilon))
```

Training minimizes negative SI-SNR. It is robust to overall scale, which is useful for separation,
but it cannot by itself enforce correct output level. The
[SI-SDR analysis](https://arxiv.org/abs/1811.02508) explains why a clear scale-invariant
definition is preferable to ambiguous legacy SDR implementations.

### 10.2 Scale-sensitive SNR

Scale-sensitive SNR penalizes waveform error at the actual output amplitude. It complements
SI-SNR so the model cannot obtain a good score with an undesirable gain change.

### 10.3 Multi-resolution STFT loss

Spectral convergence and/or log-magnitude error are computed at multiple FFT/hop resolutions
(256/64, 512/128 and 1024/256). Short windows emphasize transients; longer windows give finer
frequency resolution for harmonics and engine tones.

### 10.4 Power-compressed complex loss

Real and imaginary compressed spectra are compared, retaining phase-sensitive information while
reducing domination by high-energy bins.

### 10.5 Waveform L1

Sample-domain absolute error discourages broad reconstruction drift and complements frequency-
domain objectives.

### 10.6 Clean identity and speech retention

Clean-identity loss penalizes any change when the correct behavior is pass-through. Short-time
speech-retention loss inspects active frames and penalizes severe local attenuation, targeting the
observed failure where a blast caused speech to disappear.

### 10.7 Preservation correction losses

The new bounded correction experiment adds:

- preservation SNR, to directly reward low error on clean/near-clean items;
- clean spectral identity, to preserve magnitude structure on clean speech;
- spectral delta, to reduce unnecessary frame-to-frame coloration;
- phase consistency, to reduce phase-induced robotic character.

Its weights are: SI-SNR 0.40, SNR 0.40, multi-resolution STFT 0.60, complex 0.30, waveform L1
0.65, clean identity 1.50, speech retention 0.25, preservation SNR 0.25, clean spectral identity
0.75, spectral delta 0.20 and phase consistency 0.05.

Checkpoint selection uses a lower-is-better composite containing total validation loss plus clean
identity ×2, preservation SNR ×0.10 and clean spectral identity ×1. This prevents a noisy-sample
improvement from hiding worsening clean coloration.

---

## 11. Training curriculum, checkpointing and interruption

### 11.1 Stage 1: broad pretraining

- 40 planned epochs; only 10 have been completed and evaluated.
- 20,000 dynamic samples per epoch, batch size 8.
- Learning rate 3e-4.
- Broad categories, −15 to +20 dB SNR.
- Checkpoints: `checkpoints_v4_stage1/best.pt` and `last.pt`.

### 11.2 Preservation correction

- Initialize model weights from the accepted Stage-1 checkpoint.
- Fresh optimizer; do not resume the Stage-1 optimizer into a changed objective.
- Five epochs, 12,000 samples per epoch, learning rate 7.5e-5.
- 30% clean and 25% near-clean examples.
- Runtime comparison uses a conservative aligned 90% enhanced / 10% primary blend.
- Output: `checkpoints_v4_preserve/best.pt`.

### 11.3 Stage 2: defence-weighted fine-tuning

- Initialize from the preservation checkpoint with a fresh optimizer.
- 25 epochs at 1e-4.
- MAD dataset weight 4.0.
- Category weights: impulsive 2.5, non-stationary 2.0, stationary/environmental 0.75.
- Label emphasis: gunshot and shelling 2.0; drone 2.0; vehicle, helicopter and fighter 1.5.
- SNR range −20 to +15 dB.
- Output: `checkpoints_v4_stage2/best.pt`.

### 11.4 Stage 3: target-device fine-tuning

- It is intentionally unusable until `data/manifests_target` exists.
- Initialize from Stage 2 with a fresh optimizer.
- 15 epochs, 8,000 samples per epoch, learning rate 3e-5.
- Use synchronized final microphone/interface sessions and target RIRs.
- Retain broad validation to detect catastrophic forgetting.
- Output: `checkpoints_v4_stage3/best.pt`.

### 11.5 Resume behavior

`last.pt` stores model, optimizer, scheduler, mixed-precision scaler, epoch and configuration.
After Ctrl+C, the current incomplete epoch is lost, but all completed epochs are safe. Resume uses
`--resume` and restores the same stage. `initialize_from` is different: it transfers model weights
to a new stage with a fresh optimizer and lower learning rate.

### 11.6 GPU utilization and time

The RTX 4060 was correctly used. Observed utilization was bursty from 0–82%, with about 2.1 GB
VRAM, 56–61 °C and modest power draw. This is expected because the 12k-parameter network is tiny;
CPU audio decoding, dynamic mixing, RIR convolution, augmentation, worker scheduling and validation
can starve the GPU between short kernels. Maximizing GPU percentage is not the goal; reducing wall
time without changing statistical behavior is.

Stage-1 epochs took about 329–527 seconds. From that evidence, five 12k-sample preservation epochs
should normally take roughly 25–45 minutes on the same laptop, plus evaluation. A 25-epoch Stage 2
is roughly 2.5–4 hours if its per-epoch behavior is similar. These are planning estimates, not
guarantees; thermal mode, disk speed, Windows load and data augmentation change them.

---

## 12. Current measured training evidence

Epoch 0 validation total loss was −18.875 and validation SI-SNR loss was −18.963. At epoch 9 they
were −20.178 and −20.298 respectively; validation MRSTFT fell from 0.1708 to 0.1384 and waveform L1
from 0.2429 to 0.2023. Training and validation remained stable without obvious divergence.

This shows that the optimization was learning its configured objective. It does not show that
human-perceived voice quality is acceptable. The listening complaint and clean-speech gate have
priority over continued loss reduction.

The current Stage-1 best-checkpoint SHA-256 is:

`3A31EA91C5CB1E77EDEEB14A4A3D29BAE46C2FEB46B12BF12A2DC493D7175E5C`

That hash should be recorded whenever epoch-10 reports are cited.

---

## 13. Evaluation methodology

### 13.1 Metrics

- **SNR:** scale-sensitive energy ratio; useful for residual error and output level.
- **SI-SNR/SI-SDR:** separation quality after optimal scalar projection; useful but insensitive to
  overall gain.
- **STOI:** an intrusive short-time intelligibility predictor. It measures intelligibility, not
  naturalness or speaker identity. A model can have higher STOI and still sound robotic.
- **PESQ:** the problem statement explicitly requires it, so it must be reported when available.
  However, ITU deleted the P.862 family on 5 January 2024 and refers new work to P.863/POLQA. PESQ
  should therefore be treated as a compliance metric, not the sole modern quality measure. See the
  [ITU deletion notice](https://www.itu.int/md/T22-TSB-CIR-0169/en).
- **Pause-noise attenuation:** reduction during target-speech pauses.
- **Speech-deletion rate:** proportion of active-speech regions that suffer catastrophic local
  attenuation. The present threshold catches large deletion, not all timbre damage.
- **Active-level error:** gain difference on active target speech.
- **RTF:** processing time divided by audio duration; must be below 1, with per-frame p99 below the
  hop deadline for streaming.
- **CPU, RSS memory, temperature, throttling, xruns and underflows:** deployment health.

Future final evaluation should add DNSMOS P.835-style SIG/BAK/OVRL, ASR word error rate and matched
human listening. P.835 separates speech quality, background quality and overall quality, which is
more informative for a denoiser than one number. The
[DNSMOS P.835 paper](https://arxiv.org/abs/2110.01763) describes those three dimensions.

### 13.2 Minimum regression gate

- noisy-only SNR and SI-SNR improvement at least 1 dB;
- STOI change at least −0.01;
- pause attenuation at least 3 dB;
- speech deletion rate no more than 2%;
- every expected noisy category present and no worse than −1 dB regression;
- clean and near-clean enhanced SNR at least 20 dB and STOI change at least −0.01.

### 13.3 Strict problem-statement gate

- output SNR at least 15 dB;
- enhanced STOI at least 0.85;
- enhanced PESQ at least 2.5;
- speech deletion no more than 2%;
- clean active-level error no more than 1 dB;
- plus category, listening, runtime and target-hardware gates.

An overall mean must never hide a failed military label or clean-speech regression. Results are
reported overall, noisy-only, by category, label and SNR bin.

---

## 14. Current v4 evaluation results and interpretation

### 14.1 Epoch-10 broad 50-pair check

| Metric | Noisy | Enhanced | Change |
| --- | ---: | ---: | ---: |
| SNR | 18.108 dB | 18.131 dB | +0.023 dB |
| SI-SNR | 18.170 dB | 17.975 dB | −0.194 dB |
| STOI | 0.8333 | 0.9185 | +0.0852 |
| Pause attenuation | — | 6.644 dB | — |
| Speech deletion rate | — | 0% | — |

The overall set mixes clean, near-clean and noisy examples, so the mean hides the more useful
noisy-only result:

| Noisy-only metric | Noisy | Enhanced | Change |
| --- | ---: | ---: | ---: |
| SNR | 6.971 dB | 16.808 dB | +9.837 dB |
| SI-SNR | 7.052 dB | 16.610 dB | +9.558 dB |
| STOI | 0.7882 | 0.9014 | +0.1132 |
| Pause attenuation | — | 14.765 dB | — |

Environmental, mixed, non-stationary and stationary categories improved strongly. The fixed broad
impulsive category failed because of the anomalous/easy primary crop described earlier. Clean
speech reached 23.29 dB enhanced SNR and 0.9517 STOI, which is intelligible but still far from
identity; its STOI dropped about 0.048 from perfect clean input. The gate therefore failed.

### 14.2 Epoch-10 military 50-pair check

| Metric | Noisy | Enhanced | Change |
| --- | ---: | ---: | ---: |
| Overall SNR | 9.779 dB | 12.107 dB | +2.329 dB |
| Overall SI-SNR | 9.804 dB | 11.457 dB | +1.653 dB |
| Overall STOI | 0.6905 | 0.8278 | +0.1373 |
| Pause attenuation | — | 8.213 dB | — |
| Active-level error | — | 0.759 dB | — |
| Speech deletion rate | — | 0% | — |

Noisy-only military results were much stronger:

| Noisy-only metric | Noisy | Enhanced | Change |
| --- | ---: | ---: | ---: |
| SNR | −4.038 dB | 9.564 dB | +13.602 dB |
| SI-SNR | −4.005 dB | 8.740 dB | +12.745 dB |
| STOI | 0.6091 | 0.7885 | +0.1793 |
| Pause attenuation | — | 17.680 dB | — |
| Active-level error | — | 0.969 dB | — |

Impulsive, mixed and non-stationary military categories all passed the noisy-category regression
check. Impulsive SNR improved by 11.84 dB and STOI reached 0.8567; mixed SNR improved 9.43 dB and
STOI reached 0.8298; non-stationary SNR improved 16.22 dB but STOI reached only 0.7252. The strict
military SNR/STOI target did not pass, clean preservation failed, and PESQ was missing.

This is promising research evidence, not a final success claim. It shows that the model can learn
strong military-noise suppression while exposing the precise trade-off that remains.

### 14.3 Epoch 5 to epoch 10

Military overall enhanced SNR rose from 11.868 to 12.107 dB and STOI from 0.8210 to 0.8278. The
noisy-only SNR gain rose from 13.322 to 13.602 dB. Broad noisy-only SNR gain rose from 9.612 to
9.837 dB and STOI from 0.8951 to 0.9014. These are incremental gains, while clean coloration
remained. Blindly running 30 more broad epochs would risk spending time without fixing the actual
failure mode; this evidence triggered the preservation correction.

### 14.4 Very hard cases

Some fixed military samples remain poor, including gunshot and vehicle examples near −13 to −14 dB
input SNR with enhanced STOI around 0.47–0.53. Such cases may contain speech information that is
almost fully masked. They must remain in the failure analysis rather than being removed. Targeted
training can improve robustness, but no system should promise perfect recovery when the microphone
never captured a separable speech cue.

### 14.5 Why 0% deletion does not contradict robotic speech

The deletion metric detects severe local attenuation, such as an active-speech segment becoming
more than the configured threshold quieter. Robot voice can arise from harmonic modulation,
phase inconsistency, spectral holes or rapidly changing masks without crossing that deletion
threshold. Listening evidence is therefore not invalidated by a 0% deletion score.

---

## 15. Naturalness and robot-voice correction plan

The model can sound robotic because complex masks alter harmonics and phase, the tiny network must
make hard binary-like decisions, the full-wet output exposes every artifact, synthetic reference
channels do not match the actual microphone geometry, and the loss optimized separation more
directly than speaker identity.

The correction plan is deliberately bounded:

1. Run the five-epoch preservation configuration from the unchanged Stage-1 checkpoint.
2. Evaluate its `best.pt` on exactly the same broad 50 and military 50 subsets.
3. Listen blindly to matched noisy/current/preservation triplets at equal loudness.
4. Accept the new checkpoint only if clean/near-clean improves without materially losing military
   noisy-only performance.
5. Compare 100%, 90% and 85% wet mixes on the same files. A dry/wet blend is a deployment trade-off,
   not proof that the model itself improved.
6. If timbre is still unacceptable, increase capacity moderately and compare against the same
   manifests; do not keep enlarging a model without Pi latency evidence.
7. Add target-microphone recordings before Stage 3.

Potential later experiments include a noise-aware soft bypass, harmonic/deep-filter head,
multi-task voice-activity/preservation head and a teacher-student model. They are not currently
implemented and should be introduced only through controlled ablation.

---

## 16. Offline and live inference

### 16.1 Offline inference

Offline inference resamples/conditions input, runs the checkpoint or ONNX model, reconstructs the
same sample count and applies conservative output conditioning. It is the correct first way to
compare audio because no real-time driver fault can contaminate the result.

### 16.2 Streaming runtime

Neural inference never runs inside the PortAudio callback:

```text
audio callback → bounded input queue → inference worker → sequence-indexed output store
       │                                                 │
       └──────────── delayed, time-aligned dry fallback ◄─┘
```

The callback remains bounded. If output is late, the corresponding delayed primary block is used;
late enhanced blocks are discarded rather than played at the wrong time. Sequence gaps reset
recurrent state. Queues are finite so latency cannot grow indefinitely.

With the 24 ms WOLA overlap plus one 8 ms worker block, the default software playout alignment is
about 32 ms before audio-device and driver latency. Only a cable/physical loopback measurement can
establish true microphone-to-output latency.

### 16.3 Health modes

- **Normal:** valid output arrives within deadline.
- **Degraded:** repeated overruns, stale state or channel/reference health problems cause guarded
  behavior.
- **Bypass:** aligned primary audio is used when the model/runtime cannot be trusted.

Health checks cover NaN/Inf, peak level, queue overflow, underflow, missing channel, reference
leakage, inference deadline, worker exception and discontinuity. Crossfade avoids clicks during
mode changes. A software bypass is not a hardware fail-safe; the final prototype needs a physical
path that works after Pi power loss.

### 16.4 Why the first live voice broke

Possible live-only causes include using MME/DirectSound device pairs with different buffering,
sample-rate conversion, Windows audio enhancements/AGC, acoustic feedback, underflows and separate
device clocks. The raw 10-second recording and offline enhancement were therefore essential: if
raw audio is already broken, fix the audio device; if offline output is robotic, fix model/data;
if offline output is good but live output breaks, fix runtime/device configuration.

The final two-channel setup must use one synchronized interface. Two unrelated USB microphones
drift and are unsuitable for stable inter-channel phase/reference features.

---

## 17. ONNX, quantization and deployment integrity

Stateful export exposes audio frame input plus recurrent/convolution caches and returns enhanced
audio plus updated caches. Export must satisfy ONNX checker and numerical comparison against
PyTorch over a sequence, not just one isolated frame.

The v3 final export passed with very small errors; v4 smoke FP32 and INT8 artifacts also validate
the software path. These do not validate the final untrained v4 model.

Dynamic INT8 is a candidate, not an automatic upgrade. ONNX Runtime documents that quantization
maps floating-point values to 8-bit values and warns that performance depends on supported
operators/hardware and quantize/dequantize overhead; it can even be slower. See the
[ONNX Runtime quantization documentation](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html).

Acceptance procedure:

1. export the final FP32 checkpoint;
2. run PyTorch-versus-ONNX stateful equivalence;
3. create the INT8 candidate;
4. evaluate FP32 and INT8 on identical frozen manifests;
5. compare audio and preservation, not only numerical tensor error;
6. benchmark both on Pi 5;
7. select INT8 only if its speed/power benefit is real and quality stays inside tolerance.

Pruning is not automatically useful: unstructured sparsity often reduces file size without
speeding generic CPU kernels. Any pruning claim needs measured Pi latency and quality.

---

## 18. Raspberry Pi 5 feasibility and acceptance

The Pi 5 uses a 2.4 GHz quad-core 64-bit Arm Cortex-A76 CPU. Raspberry Pi recommends a high-quality
5V/5A supply such as its 27 W USB-C supply and notes that active cooling gives best sustained
performance. See the [official Pi 5 product page](https://www.raspberrypi.com/products/raspberry-pi-5/)
and [product brief](https://datasheets.raspberrypi.com/rpi5/raspberry-pi-5-product-brief.pdf).

ONNX Runtime supports IoT/edge deployment and Arm builds, but desktop timing cannot prove Pi
real-time behavior. See [ONNX Runtime edge guidance](https://onnxruntime.ai/docs/tutorials/iot-edge/).

Recommended Pi configuration:

- 64-bit Raspberry Pi OS Lite;
- official 27 W supply and active cooling;
- synchronized USB audio interface;
- ONNX Runtime CPU execution, initially one intra-op and one inter-op thread;
- ALSA/PortAudio with fixed 16 kHz, channels and block size;
- no desktop/audio enhancements during measurement;
- CPU governor/affinity tuning only after baseline results;
- systemd service with logs and safe restart;
- read-only engineering dashboard separate from DSP state.

Acceptance evidence:

- median, p95 and p99 per-frame inference below the 8 ms hop budget, with margin;
- RTF below 1 for offline and continuous streaming;
- real microphone-to-output loopback no more than the declared 50 ms project gate;
- zero xruns, underflows, drops and worker failures in a two-hour soak;
- no thermal throttling;
- bounded RSS memory and stable CPU utilization;
- unplug/replug, process crash and model-failure tests produce safe bypass;
- FP32/INT8 quality comparison on frozen data.

Pi feasibility is high for a 12k-parameter model, but the final result remains unproven until the
actual board, audio interface and runtime are measured.

---

## 19. Physical ANC development path

The present FxNLMS simulator is for controlled research. A real headset loop requires at least:

- noise reference microphone placed so it observes the disturbance early;
- primary/communication microphone as appropriate;
- in-ear/error microphone near the cancellation point;
- headphone/secondary actuator;
- synchronized multi-input/multi-output codec;
- measured secondary path;
- conservative output gain and hardware emergency bypass.

Safe sequence:

1. Use a dummy fixture, not a human ear.
2. Measure the secondary impulse response at low level.
3. Verify causality: the reference must provide enough advance relative to the secondary delay.
4. Validate bounded fixed-filter playback.
5. Enable slow FxNLMS adaptation on low-frequency stationary noise.
6. Log error reduction, output level and stability.
7. Test path changes, microphone movement and actuator saturation.
8. Add independent hardware limiter and bypass.
9. Only after review, perform low-level supervised human testing.

Physical ANC is most feasible for predictable low-frequency periodic components such as engine or
rotor fundamentals. Broadband high-frequency impulses are harder because causality and secondary-
path delay leave little time. Passive attenuation and communication enhancement remain important.

---

## 20. Hardware architecture and bill-of-material categories

Minimum communication-enhancement prototype:

- Raspberry Pi 5;
- official 27 W supply and active cooling;
- synchronized two-input USB audio interface;
- close-talk boom microphone;
- outward/reference microphone;
- closed-back headset;
- safe monitor gain and physical bypass path;
- cables, mounting and repeatable microphone spacing.

Physical ANC research adds an error microphone, additional synchronized input, safe headphone
driver/output, SPL measurement, loopback cable and acoustic fixture. A dedicated DSP/MCU is likely
better than Linux/Python for the final sample-by-sample control loop, with the Pi supervising the
neural communication path and telemetry.

Do not place fixed rupee costs in a final submission without current vendor quotations, tax,
availability and exact part numbers. The feasibility argument should instead separate reusable
compute, audio interface, microphones, headset, protection/fixture and enclosure, then attach a
dated quotation table.

---

## 21. Operator UI concept

The supplied spectrum/waterfall screenshots are a visual reference, not an RF specification. At
16 kHz, the audio frequency display must span 0–8 kHz and use dBFS.

The engineering UI should show:

- Normal/Degraded/Bypass state and reason;
- active backend, sample rate, block size and latency estimate;
- primary, reference and enhanced spectra;
- synchronized noisy/enhanced waterfall with fixed color scale;
- device/channel selection, start/stop, monitor mute and software bypass;
- RMS, clipping, reference health, queue/overrun counts and pause attenuation;
- recording control for evidence collection.

It must not display live STOI, PESQ or true SNR because live audio has no clean reference. It must
label the neural path “Speech enhancement,” not “ANC active.” The latter is allowed only when a
calibrated error-microphone FxNLMS loop is running.

The UI is intentionally downstream of DSP correctness. It should consume telemetry and never own
model state; closing it must not stop or corrupt the audio service.

---

## 22. Competitive and reference landscape

VoxShield should not claim to be the first noise suppressor. Its defensible differentiation is the
combination of defence-specific evidence, synchronized reference sensing, preservation gates,
edge deployment, transparent failure handling and an honest physical-ANC boundary.

| Reference/alternative | Strength | Limitation relative to this project | VoxShield use |
| --- | --- | --- | --- |
| Spectral subtraction/Wiener | Explainable, low compute | Musical noise and difficulty with rapid nonlinear change | Classical baseline |
| LMS/NLMS/FxLMS | Adaptive and efficient; essential for physical ANC | Needs correlated reference; FxLMS needs secondary path; not a general speech prior | Physical low-frequency branch |
| RNNoise | Mature open hybrid RNN/DSP real-time denoiser | General single-channel suppression; not defence/dual-mic/physical ANC proof | Lightweight baseline; [official repo](https://github.com/xiph/rnnoise) |
| Official GTCRN | Very low parameter/MAC count and streaming support | Published results do not transfer automatically to military or this microphone geometry | v3 baseline and efficiency inspiration |
| DeepFilterNet2 | Strong full-band perceptual/embedded research | Different bandwidth, model and training domain; not the current Pi pipeline | Quality/efficiency comparison candidate |
| FullSubNet/Fast FullSubNet | Strong full/sub-band research | Larger/different single-channel architecture; deployment must be re-measured | Structural inspiration or benchmark |
| NVIDIA Maxine AFX | Production-oriented GPU denoise/dereverb and speaker focus | NVIDIA platform/license and general communication focus; not Pi 5 or transparent defence retraining | Commercial comparison; [official docs](https://docs.nvidia.com/maxine/afx/latest/index.html) |
| Krisp SDK | Productized multi-platform communication noise filtering | Closed commercial model; limited control over defence data and evidence | User-experience comparison |
| Commercial ANC headset | Mature physical low-frequency cancellation | Closed design; not customizable defence speech model; hardware-specific | Physical performance reference |

Competition evaluation should compare the same recordings at matched loudness and report compute,
latency, clean preservation and failure modes. Published scores on different datasets cannot be
placed in one ranking as if directly comparable.

---

## 23. Innovation and unique value proposition

The strongest project innovations are system-level:

- a defence-weighted but broad data curriculum including gunshot, shelling, vehicle, rotor,
  aircraft and UAV labels;
- dynamic synchronized primary/reference simulation rather than duplicated mono input;
- explicit transient-over-active-speech sampling;
- causal complex/ERB/sub-band processing in a 12k-parameter model;
- preservation-aware loss and checkpoint selection motivated by an observed failure;
- frozen broad, MAD and UAV evaluation with provenance hashes;
- category and label gates that prevent headline averages from hiding failures;
- aligned dry bypass and bounded worker design for late inference;
- separation of neural communication enhancement from calibrated physical ANC;
- evidence-based readiness status instead of a demo-only “works” claim.

The project should not call the current architecture “state of the art” without a controlled
benchmark against current baselines on the same test distribution. “Research-informed,
ultra-lightweight and defence-targeted” is accurate.

---

## 24. Technical feasibility

### 24.1 What is already feasible

- The dataset scale is sufficient for continued research, and ingestion does not require manual
  rearrangement.
- CUDA training works on the RTX 4060.
- Ten epochs completed stably and military noisy-only metrics improved substantially.
- The model is extremely small and has a stateful ONNX pathway.
- Offline/live runtime, monitoring and Pi scripts exist.
- Tests cover signal, model, causality, ingestion, runtime and readiness behavior.

### 24.2 What remains uncertain

- natural speech quality after preservation correction;
- generalization to the final microphones and real geometry;
- PESQ and modern perceptual/listening evidence;
- full held-out 500/1,000/400/200-set v4 results;
- actual Pi p99/loopback/thermal results;
- physical ANC stability and attenuation;
- license approval for the local MAD dataset and any redistribution.

### 24.3 Feasibility conclusion

The communication-enhancement prototype is technically feasible, with medium remaining model and
integration risk. Raspberry Pi deployment is plausible but unproven. Physical ANC is a separate,
higher-risk hardware research work package and should be demonstrated first at low frequencies on
a fixture.

---

## 25. Operational and economic viability

### 25.1 Operational viability

An offline/on-device system has privacy, connectivity and deterministic-latency advantages. It can
operate without cloud service and can integrate before radio transmission. Operational viability
depends on rugged connectors, a synchronized interface, simple bypass, repeatable mounting and a
calibration workflow understandable by technicians.

### 25.2 Productization path

1. Laptop research demonstrator.
2. Pi 5 headset/intercom prototype using commodity synchronized audio I/O.
3. Target-device data and optimized native runtime.
4. Rugged enclosure and radio-specific isolated interface.
5. DSP/SoC implementation for lower power and deterministic control.
6. Controlled field evaluation and organization-specific qualification.

### 25.3 Economic rationale

The software is modular and retrainable across environments, uses public/research datasets for
early development and avoids recurring cloud inference. The main cost drivers are synchronized
audio hardware, robust microphones/headset, validation fixtures, data collection, qualification
and maintenance—not the tiny model file.

A commercial plan must account for dataset licenses, third-party code licenses, support, model
updates, hardware replacement, cybersecurity, supply chain and certification. ESC-50's
non-commercial license is especially important: a commercial product would need licensed
replacement data or permission.

### 25.4 Users and adjacent markets

Potential non-classified markets include industrial plants, mining, aviation ground crews,
emergency response, construction, marine machinery and high-noise maintenance. These are adjacent
applications, not validated current deployments.

---

## 26. Privacy, cybersecurity and responsible use

- Process audio locally by default.
- Minimize raw recording retention; obtain consent for human speech.
- Encrypt stored target recordings and restrict access.
- Separate telemetry from audio content where possible.
- Hash checkpoints, manifests and exported models.
- Pin dependencies and retain third-party notices.
- Sign release artifacts and verify them before loading on the Pi.
- Run the service without administrative privileges and restrict network access.
- Treat model/config updates as controlled releases with rollback.
- Never ingest classified audio into unmanaged development systems.
- Document bias across accents, languages, speakers and vocal effort.
- Do not claim hearing protection or mission-critical certification without the required tests.

---

## 27. Risk register and controls

| Risk | Effect | Present evidence | Control |
| --- | --- | --- | --- |
| Robot voice/identity loss | Unnatural or distrusted communication | Heard live; clean gate fails | Preservation fine-tune, matched listening, wet-mix comparison |
| Speech erased during impulse | Lost command/word | Observed in v3 | Active-overlap sampling, retention loss, hard-case test |
| Reference contains speech | Model cancels target | Simulated leakage only | Placement, leakage telemetry, target recording, soft bypass |
| Unsynchronized microphones | Drifting phase/features | Known hardware issue | One shared-clock multichannel interface |
| Dataset leakage | Inflated test results | Audit currently shows none | Group hashing, frozen hashes, duplicate audit |
| Dataset/license mismatch | Cannot redistribute/commercialize | MAD/UAV review pending | Provenance register and legal review; replacement data |
| Synthetic-to-real domain gap | Live performance below benchmark | Laptop test exposed gap | Stage-3 target captures and device-specific validation |
| Very low SNR | Information unrecoverable | Hard samples remain low STOI | Reference geometry, limits disclosure, reject overclaim |
| Audio clipping/AGC | Distortion before model | Possible PC path issue | Disable enhancements, record raw, headroom and diagnostics |
| Deadline miss/xrun | Broken audio | Runtime counters implemented | Worker queue, aligned bypass, native optimization |
| Pi throttling | Latency spikes | Not yet tested | Active cooling, 27 W supply, soak logging |
| INT8 quality loss | More artifacts | Only smoke candidate exists | Same-manifest evaluation and Pareto comparison |
| Physical ANC instability | Loud or unsafe output | No physical test yet | Fixture, secondary-path calibration, limiter, hardware bypass |
| Metric gaming | Good number, poor sound | STOI improved despite coloration | Multi-metric gates and blind listening |
| Scope confusion | False ANC claim | Historically likely | Explicit two-path terminology throughout UI/docs |

---

## 28. Verification and software quality

The current suite contains 42 passing automated tests and Ruff passes. Tests cover audio/STFT,
dataset ingestion/mixing, model causality and state, official GTCRN compatibility, v4 model,
runtime health, live engine, telemetry, diagnostics, UAV conversion, comparison, adaptive filter
and readiness logic. A CPU preservation smoke run also completed and exposed the new loss
components.

Software tests prove implementation properties; they do not prove acoustic quality. Required
evidence layers are:

1. unit tests;
2. bounded smoke training;
3. PyTorch/ONNX equivalence;
4. frozen objective evaluation;
5. equal-loudness listening;
6. target-device recordings;
7. Pi real-time/thermal soak;
8. physical loopback;
9. safe ANC fixture test.

---

## 29. Exact next action plan

### Phase A — preservation correction now

Run the bounded five-epoch correction. Do not overwrite Stage 1.

```powershell
cd C:\anc
& ".\.venv\Scripts\voxshield-train.exe" `
  --config "configs\hybrid_v4_stage1_preserve.yaml" `
  --device cuda
```

Evaluate broad and military samples on the unchanged manifests:

```powershell
& ".\.venv\Scripts\voxshield-evaluate.exe" `
  --checkpoint "checkpoints_v4_preserve\best.pt" `
  --manifest "data\mixtures\val_v4\manifest.jsonl" `
  --device cuda --limit 50 `
  --output "artifacts\v4-preserve-broad-check.json" `
  --save-audio "artifacts\v4-preserve-broad-audio" `
  --save-audio-limit 20

& ".\.venv\Scripts\voxshield-evaluate.exe" `
  --checkpoint "checkpoints_v4_preserve\best.pt" `
  --manifest "data\mixtures\mad_test_v4\manifest.jsonl" `
  --device cuda --limit 50 `
  --expected-noisy-categories "impulsive,nonstationary,mixed" `
  --output "artifacts\v4-preserve-military-check.json" `
  --save-audio "artifacts\v4-preserve-military-audio" `
  --save-audio-limit 20
```

Accept only if clean and near-clean preservation improves audibly and numerically without losing
the strong noisy-only military result. Otherwise revise the model/loss before Stage 2.

### Phase B — defence Stage 2

```powershell
& ".\.venv\Scripts\voxshield-train.exe" `
  --config "configs\hybrid_v4_stage2_defence.yaml" `
  --device cuda
```

Evaluate full validation, broad test, MAD test and UAV test. Save audio examples from best, median
and worst cases. Do not select the model on one 50-item subset.

### Phase C — acquire target data

Use one synchronized multichannel interface. Record clean speech, noise-only and combined sessions,
then ingest them with session/device group IDs. Measure microphone placement and gain. Without
this step, the laptop speaker/mic domain gap remains.

### Phase D — target Stage 3

Populate `data/manifests_target`, run its audit, then run the Stage-3 config. Re-evaluate both target
and broad frozen sets to detect catastrophic forgetting.

### Phase E — quality and release evidence

- Install PESQ in a compatible Python 3.11 evaluation environment or install the required MSVC
  build tools; never fabricate the missing value.
- Add DNSMOS/P.835-style evidence if licensing/runtime allows.
- Conduct randomized equal-loudness listening with multiple listeners.
- Export FP32 ONNX and validate stateful equivalence.
- Evaluate INT8 on the same test pairs.
- Complete model card with hashes, limitations and failures.

### Phase F — Pi and hardware

- Install the Pi runtime and copy only final artifacts.
- Run offline benchmark, then live two-channel capture.
- Measure physical loopback latency.
- Run two-hour soak with thermal/xrun logging.
- Demonstrate unplug, process crash and bypass.
- Only then attempt physical ANC on a fixture.

---

## 30. Commands for inspection, export and Pi workflow

Check CUDA:

```powershell
cd C:\anc
& ".\.venv\Scripts\python.exe" -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NOT AVAILABLE')"
```

Resume the same interrupted stage by adding its last checkpoint:

```powershell
& ".\.venv\Scripts\voxshield-train.exe" `
  --config "configs\hybrid_v4_stage1_preserve.yaml" `
  --device cuda `
  --resume "checkpoints_v4_preserve\last.pt"
```

Export the final Stage-3 model only after it passes evaluation:

```powershell
& ".\.venv\Scripts\voxshield-export.exe" `
  --checkpoint "checkpoints_v4_stage3\best.pt" `
  --output "artifacts\voxshield-v4-final.onnx"
```

Create an INT8 candidate:

```powershell
& ".\.venv\Scripts\voxshield-quantize.exe" `
  --checkpoint "checkpoints_v4_stage3\best.pt" `
  --input "artifacts\voxshield-v4-final.onnx" `
  --output "artifacts\voxshield-v4-final-int8.onnx"
```

Benchmark:

```powershell
& ".\.venv\Scripts\voxshield-benchmark.exe" `
  --checkpoint "checkpoints_v4_stage3\best.pt" `
  --onnx "artifacts\voxshield-v4-final.onnx" `
  --frames 5000 --threads 1 `
  --output "artifacts\v4-final-benchmark-windows.json"
```

List devices and start the future synchronized two-channel live path:

```powershell
& ".\.venv\Scripts\voxshield-live.exe" `
  --checkpoint "checkpoints_v4_stage3\best.pt" `
  --onnx "artifacts\voxshield-v4-final.onnx" `
  --list-devices

& ".\.venv\Scripts\voxshield-live.exe" `
  --checkpoint "checkpoints_v4_stage3\best.pt" `
  --onnx "artifacts\voxshield-v4-final.onnx" `
  --input-device DEVICE_ID --output-device DEVICE_ID `
  --primary-channel 0 --reference-channel 1 --threads 1 `
  --telemetry-file "artifacts\live-telemetry.json"
```

Generate current evidence status:

```powershell
& ".\.venv\Scripts\voxshield-readiness.exe" `
  --project-root . `
  --output "artifacts\readiness.json"
```

The exact Pi setup commands are kept in `docs/deployment-pi5.md` and `scripts/pi`. They should be
run on the Pi, not simulated on Windows.

---

## 31. Demonstration plan

A credible demonstration should use matched evidence rather than a single dramatic recording.

1. State the distinction between communication enhancement and physical ANC.
2. Show the data audit, source groups and frozen hashes.
3. Play equal-loudness triplets: clean target, noisy input, enhanced output.
4. Include stationary, rotor/vehicle, gunshot/shelling, UAV, mixed and near-clean cases.
5. Show at least one known failure; explain the next control.
6. Run live synchronized dual-channel enhancement with visible Normal/Bypass status.
7. Disconnect the reference or deliberately stop inference to show safe fallback.
8. Show ONNX equivalence and Pi benchmark/soak evidence.
9. Demonstrate physical FxNLMS only if the calibrated fixture and hardware bypass have passed.

Audio must be loudness matched. Louder output is often perceived as “better” and would bias the
demo. Keep exact file IDs, checkpoint hash, runtime configuration and manifest hash in the report.

Existing comparison folders include:

- `artifacts/v4-epoch5-comparison`
- `artifacts/v4-epoch5-military-comparison`
- `artifacts/v4-epoch10-broad-audio`
- `artifacts/v4-epoch10-military-audio`

---

## 32. Definition of done

### Communication enhancement release

The release is complete only when all of the following exist and pass:

- verified data/license inventory and leak-free split audit;
- completed preservation, Stage 2 and target Stage 3 checkpoints;
- final model hash and immutable configs;
- full broad, military, UAV and target results;
- stated SNR/STOI/PESQ targets on the declared distribution;
- clean/near-clean preservation and no catastrophic speech deletion;
- matched listening approval;
- validated FP32 ONNX and selected FP32/INT8 candidate;
- Pi p99/frame, RTF, memory, temperature and two-hour soak;
- physical microphone-to-output latency measurement;
- runtime fault/bypass evidence;
- complete model card, third-party notices and reproduction commands.

### Physical ANC release

In addition, physical ANC requires:

- measured secondary path;
- stable attenuation on the declared fixture/frequency range;
- safe actuator/output bounds;
- error microphone evidence;
- movement/path-change testing;
- independent hardware bypass under process, USB and power failure;
- expert review before human use.

Until those conditions pass, the truthful status remains **research and validation**.

---

## 33. Deliverables

Software deliverables:

- data cataloger, audit and fixed-pair generator;
- multichannel dynamic mixer and augmentation pipeline;
- v3 baseline and v4 causal model;
- preservation and defence training recipes;
- training logs/checkpoints/resume;
- offline and live inference;
- evaluation/gating/comparison;
- ONNX export, quantization and benchmark;
- Pi setup/service/health scripts;
- engineering dashboard;
- FxNLMS simulator;
- automated test suite.

Evidence deliverables:

- dataset inventory and licenses;
- frozen-manifest hashes;
- model card and checkpoint/model hashes;
- overall/category/label/SNR-bin reports;
- matched before/after audio;
- listening-test report;
- Pi benchmark, loopback and soak reports;
- physical ANC calibration report if attempted;
- risk register and limitation statement.

Presentation/technical-document material:

- requirement-to-implementation matrix;
- architecture and data-flow diagrams;
- mixture equations and front-end parameters;
- loss and curriculum rationale;
- measured v3/v4 comparison;
- failure analysis and corrective action;
- feasibility, viability, competition and differentiation;
- deployment/safety plan;
- exact next steps and definition of done.

---

## 34. Likely jury questions and accurate answers

**Is this really ANC?**  
The main validated software path is communication speech enhancement. True physical ANC is a
separate FxNLMS loop requiring a reference mic, error mic, actuator and calibrated secondary path.
The project includes that path but will not claim it is complete before physical evidence.

**Why two microphones?**  
The primary is speech-dominant while the outward reference is noise-dominant. Their synchronized
level and phase relationship gives information unavailable to a single channel. They must share a
sample clock.

**Why not just use GTCRN?**  
GTCRN is an excellent efficiency baseline, but published general-noise results do not guarantee
defence transients, dual-microphone use, clean preservation or the target hardware. V4 adapts the
design to those requirements and tests it independently.

**Why did the first model sound bad even when STOI improved?**  
STOI predicts intelligibility, not naturalness. The model suppressed noise but altered harmonics,
phase and clean speech. Listening exposed a failure that the metric did not fully capture, so the
loss, selection rule and runtime blend were changed.

**Was military noise actually used?**  
Yes. MAD is indexed and weighted for Stage 2; a dedicated 400-pair military test exists. The
epoch-10 50-pair MAD check passed all noisy-category regression checks and produced large noisy-
only improvements, but it did not meet final SNR/STOI/PESQ/clean gates.

**Why was military noise not visible in the first evaluation?**  
The first report used a broad mixed manifest and summarized broad categories. A dedicated MAD
manifest and explicit expected category list were later used so military evidence could not be
hidden or omitted.

**Why is GPU utilization not 100%?**  
The model is only 12,259 parameters. CPU decoding, dynamic augmentation, RIR convolution and
validation dominate parts of the pipeline, so the GPU receives short bursts. This is a pipeline
characteristic, not evidence that CUDA failed.

**Can training be stopped?**  
Yes. Stop with Ctrl+C. Resume from `last.pt`; only the incomplete epoch is repeated. Do not confuse
resume with initializing a new training stage.

**Will it definitely work after more epochs?**  
No honest answer can guarantee that. More epochs improve the configured objective, but may not fix
robotic timbre. That is why the next step is a bounded preservation experiment with unchanged
tests and listening, not a long blind run.

**Why Raspberry Pi 5?**  
It is available, ARM64, capable enough for a very small causal model and suitable for a prototype.
The final claim depends on measured p99 latency, loopback, soak and thermals.

**Why is PESQ missing?**  
The optional package failed to compile in the current Windows/Python 3.12 environment because the
required MSVC toolchain was absent. The report correctly uses `null`. A compatible evaluation
environment must compute it before the strict gate can pass.

**Can the system recover speech completely covered by a blast?**  
No. If the sensors contain no separable speech information, reconstruction becomes guesswork. The
reference microphone and target geometry improve the odds, but the project reports hard limits.

---

## 35. Glossary

- **ANC:** physical active noise control unless explicitly qualified.
- **AEC:** acoustic echo cancellation of known loudspeaker/far-end content.
- **Speech enhancement:** transforming a noisy communication signal into a cleaner estimate.
- **STFT/iSTFT:** short-time Fourier transform and reconstruction.
- **WOLA:** weighted overlap-add.
- **ERB:** perceptually motivated equivalent rectangular bandwidth frequency scale.
- **Complex mask:** mask with real/imaginary components that can change magnitude and phase.
- **Causal:** uses only present/past inputs, not future frames.
- **Stateful:** carries recurrent/cache state between streaming frames.
- **SNR:** signal-to-noise ratio.
- **SI-SNR/SI-SDR:** scale-invariant separation/distortion ratio.
- **STOI:** short-time objective intelligibility measure.
- **PESQ:** P.862 perceptual speech-quality metric required by the problem statement.
- **DNSMOS/P.835:** speech/background/overall quality estimator derived from P.835-style ratings.
- **RTF:** processing time divided by audio duration.
- **Xrun:** audio buffer underflow/overflow.
- **FxLMS/FxNLMS:** filtered-x adaptive algorithms for physical ANC.
- **Secondary path:** controller-output-to-error-sensor electro-acoustic transfer path.
- **Dry/wet mix:** aligned input and enhanced-output blend.
- **Frozen manifest:** immutable test list with a recorded hash.
- **Domain gap:** difference between training simulation and real hardware/environment.

---

## 36. Reference list

### Problem and implementation context

- User-supplied SIH/DRDO Problem Statement 26052, the controlling requirement for this project.
- Project evidence: `artifacts/data-audit-v4.json`, `artifacts/frozen-manifests-v4.json`,
  `runs_v4_stage1/metrics.jsonl`, `artifacts/v4-epoch10-broad-check.json`,
  `artifacts/v4-epoch10-military-check.json` and `artifacts/readiness.json`.

### Models and metrics

- [Official GTCRN implementation](https://github.com/jiayukk/complex_gtcrn)
- [FullSubNet](https://arxiv.org/abs/2010.15508)
- [Fast FullSubNet](https://arxiv.org/abs/2212.09019)
- [DeepFilterNet2](https://arxiv.org/abs/2205.05474)
- [RNNoise official repository](https://github.com/xiph/rnnoise)
- [SI-SDR: SDR — half-baked or well done?](https://arxiv.org/abs/1811.02508)
- [DNSMOS P.835](https://arxiv.org/abs/2110.01763)
- [ITU deletion of P.862 recommendations](https://www.itu.int/md/T22-TSB-CIR-0169/en)

### ANC

- [Active noise control survey](https://doi.org/10.1016/j.sigpro.2021.108039)
- [Secondary-path modeling for ANC](https://doi.org/10.1016/j.apacoust.2017.10.026)
- [Frequency-domain FxLMS review](https://www.mdpi.com/2076-3417/8/11/2313)
- [Headset electroacoustics and delay](https://doi.org/10.1121/1.5027818)

### Datasets

- [VCTK Corpus 0.92](https://doi.org/10.7488/ds/2645)
- [MUSAN / OpenSLR 17](https://www.openslr.org/17/)
- [ESC-50 official repository](https://github.com/karolpiczak/ESC-50)
- [RIRS_NOISES / OpenSLR 28](https://www.openslr.org/28/)
- [NASA Small UAS Flyover Acoustics Data](https://data.nasa.gov/dataset/small-uas-flyover-acoustics-data)
- MAD dataset: local copy; exact authoritative source and license must be added before release.

### Edge deployment

- [Raspberry Pi 5 official product page](https://www.raspberrypi.com/products/raspberry-pi-5/)
- [Raspberry Pi 5 product brief](https://datasheets.raspberrypi.com/rpi5/raspberry-pi-5-product-brief.pdf)
- [ONNX Runtime edge deployment](https://onnxruntime.ai/docs/tutorials/iot-edge/)
- [ONNX Runtime quantization](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html)
- [NVIDIA Maxine Audio Effects SDK](https://docs.nvidia.com/maxine/afx/latest/index.html)

---

## 37. Final project statement

VoxShield v4 is already a substantial, modular engineering platform: it covers scalable data
ingestion, realistic paired mixture generation, military/UAV/RIR coverage, a lightweight causal
dual-channel complex enhancer, preservation-aware training, reproducible evaluation, live
health/bypass, ONNX deployment and a safe research path toward physical ANC.

Its current evidence supports one careful conclusion: **the model strongly improves many noisy and
military examples, but it is not yet complete because clean/natural voice preservation, PESQ,
target-device generalization, Pi real-time evidence and physical ANC validation remain open.**

The correct next step is not a claim or an indefinite long training run. It is the five-epoch
preservation correction, unchanged broad and military evaluation, matched listening, then gated
defence and target-device training. That evidence-driven process is the project's strongest
technical and presentation narrative.
