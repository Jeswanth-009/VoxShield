# Dataset acquisition and ingestion plan

This is the data plan for the v4 rebuild. It distinguishes what is already indexed from what
must still be obtained or recorded. Dataset licenses and access terms must be checked at the
official source before use or redistribution.

## 1. Current indexed corpus

The current `data/manifests_v4/catalog.jsonl` references 114,805 source files in place. It does
not duplicate the audio. The exact roots already indexed are:

```text
C:\Users\jeswa\Downloads\Datasets_n\VCTK-Corpus
C:\Users\jeswa\Downloads\Datasets_n\musan
C:\Users\jeswa\Downloads\Datasets_n\esc-50
C:\Users\jeswa\Downloads\Datasets_n\MAD_dataset
C:\Users\jeswa\Downloads\Datasets_n\RIRS_NOISES\simulated_rirs
C:\anc\data\derived\small_uav_acoustics
```

The current audit records 39.33 hours of clean training speech and the following label counts:
1,573 gunshot, 987 artillery/shelling, 1,032 vehicle/tank, 1,065 helicopter/rotor, 1,031
aircraft, 62 drone/UAV, 40 wind and 40 siren. It contains 60,000 simulated RIR files. The audit
has no missing source paths, no group leakage, no missing coverage requirements, and reports
`ready: true`. These counts are path/metadata labels, not a guarantee that every clip is
acoustically useful; samples still require listening checks.

## 2. Required additions before long training

| Priority | Data | Why it is required | Official starting point | Split unit |
| --- | --- | --- | --- | --- |
| Done | Room impulse responses | 60,000 simulated RIRs are indexed for reverberation | [OpenSLR SLR28](https://www.openslr.org/28/) | Room/recording |
| Done | Drone/UAV audio | 62 NASA flights were converted from MATLAB pressure data to 16 kHz WAV | [NASA Small UAS Flyover Acoustics](https://catalog.data.gov/dataset/small-uas-flyover-acoustics-data) | Flight/session/device |
| P0 | Real synchronized target captures | Synthetic channels cannot reproduce clocking, leakage, microphone mismatch or target geometry | Record with `voxshield-capture` and the intended interface/headset | Entire session/room/device |
| P1 | More clean, speaker-diverse speech | Current 39.33 training hours is useful but below the planning target | [LibriSpeech](https://www.openslr.org/12/) and/or [AI4Bharat IndicVoices](https://github.com/AI4Bharat/IndicVoices) | Speaker |
| P1 | Broad real noise | Improves out-of-domain robustness | [Microsoft DNS Challenge](https://github.com/microsoft/DNS-Challenge) | Original recording/source |
| P1 | More target defence recordings | MAD labels alone do not represent the final microphones, distances and rooms | Lawful, safe, consented field/loudspeaker sessions | Entire session |

MUSAN is distributed by OpenSLR and contains music, speech and noise; the archive is roughly
11 GB and is licensed under CC BY 4.0 at the official page. ESC-50 contains 2,000 five-second
environmental recordings arranged into five source-aware folds and is CC BY-NC, so its
non-commercial restriction must be checked for the intended use. Microsoft DNS provides data
and generation recipes, but a full download can be very large; use only the subsets whose terms
and storage requirements fit the project. Do not download thousands of hours merely to claim
scale. Coverage, source diversity and target relevance matter.

The local MAD copy is useful, but its exact official release URL and license have not been
established in this repository. Record that provenance in
`docs/evidence/data-inventory.template.csv` before using it in a public submission.

## 3. Recommended disk layout

Large corpora may stay wherever they are extracted. A practical layout is:

```text
D:\VoxShieldData\
  speech\
    LibriSpeech\
    IndicVoices\
  noise\
    DNS-Challenge\
    drone-uav\
    target-field\
  rir\
    RIRS_NOISES\
    target-measured\

C:\anc\data\
  manifests_v4\                 small JSONL indexes only
  manifests_target\             final-device/session manifests
  mixtures\val_v4\              frozen, generated validation pairs
  mixtures\test_v4\             frozen, generated test pairs
  captures\<session-id>\         synchronized local captures
```

The scanner accepts nested folders, CSV-backed ESC-50 and MAD layouts, and WAV/FLAC/OGG audio.
It reads only headers while indexing. During training, each selected file is decoded, converted
to mono where appropriate, resampled to 16 kHz, and cropped/zero-padded to a four-second sample.

## 4. Rebuild the catalog after adding data

The NASA small-UAS download stores acoustic pressure in MATLAB files, not audio WAVs. Convert it
once using the microphone selection documented in the dataset's own playback scripts:

```powershell
voxshield-convert-uav `
  --input "C:\Users\jeswa\Downloads\Datasets_n\small_uav_acoustics" `
  --output "C:\anc\data\derived\small_uav_acoustics" `
  --sample-rate 16000 --seed 1337
```

The converter retains source pressure/scaling metadata and makes flight-disjoint 50/6/6
train/validation/test splits. Run the ingestion command from `C:\anc`:

```powershell
voxshield-data ingest --data-root data --manifest-dir manifests_v4 `
  --source "clean=C:\Users\jeswa\Downloads\Datasets_n\VCTK-Corpus" `
  --source "noise=C:\Users\jeswa\Downloads\Datasets_n\musan" `
  --source "noise=C:\Users\jeswa\Downloads\Datasets_n\esc-50" `
  --source "noise=C:\Users\jeswa\Downloads\Datasets_n\MAD_dataset" `
  --source "noise:nonstationary=C:\anc\data\derived\small_uav_acoustics" `
  --source "rir=C:\Users\jeswa\Downloads\Datasets_n\RIRS_NOISES\simulated_rirs" `
  --source "clean=D:\VoxShieldData\speech\additional-clean" `
  --seed 1337 --train-ratio 0.90 --val-ratio 0.05 --test-ratio 0.05

voxshield-data audit --data-root data --manifest-dir manifests_v4 `
  --output artifacts/data-audit-v4.json --fail-on-leakage
```

Review `data/manifests_v4/ingest-summary.json`, the audit, and random catalog rows. The current
audit now passes. It is a minimum machine check, not permission to skip manual label/license QA.

Only `RIRS_NOISES/simulated_rirs` is forced into the RIR manifest. The package's
`pointsource_noises` and the files named `*_noise_*` in `real_rirs_isotropic_noises` are ordinary
noise recordings and must not be mislabeled as impulse responses.

## 5. What the training sample actually contains

For each optimizer step, the loader dynamically selects clean speech `s` and one or more noise
recordings `n`. It creates the primary microphone mixture at a sampled SNR. A synchronized
reference channel is simulated from a differently delayed/gained/filtered version of the noise,
with controlled speech leakage and sensor self-noise:

```text
s = clean speech target
n = stationary / non-stationary / impulsive / environmental noise
x = primary mixture = s + scaled/augmented n
r = reference = delayed/filtered n + low speech leakage + self-noise
y = model(x, r)
loss = compare y with the original clean target s
```

The model is not given a clean voice during real use. During training only, the clean recording
is the answer used to calculate the error and update weights. At inference, it receives the
primary and reference microphones and estimates enhanced speech. Mixtures are generated on the
fly, so terabytes of duplicated mixture WAV files are not needed. Only the validation and test
sets are materialized and frozen for reproducible comparison.

## 6. Target recording protocol

Use one synchronized multi-input interface; never use unrelated USB microphones as a pair.
Channel 0 is the close-talk primary microphone. Channel 1 is the outward reference microphone.
Record at least these conditions, retaining isolated noise-only and speech-only calibration
takes as well as overlap takes:

- Quiet speech from each target language/accent and several speakers.
- Steady engine/fan/vehicle noise at several levels and angles.
- Changing rotor/helicopter/drone-like noise with movement or level modulation.
- Sirens, alarms and lawful safe impulses.
- Tank/artillery recordings played through a calibrated loudspeaker at safe levels; do not
  create hazardous real events for data collection.
- Transients deliberately overlapping active syllables, which exposes speech-erasure failure.
- Different rooms, outdoors, microphone placement errors, wind protection and device gains.

Example:

```powershell
voxshield-capture --list-devices
voxshield-capture --input-device DEVICE --primary-channel 0 --reference-channel 1 `
  --seconds 60 --name rotor-overlap-speaker01-room01 --label nonstationary
voxshield-capture --analyze data\captures\SESSION\synchronized.wav
```

Move a complete session into exactly one of train, validation or test. Never split neighboring
clips from the same recording across sets.

## 7. Frozen evaluation set

Only after the catalog is final, generate the two fixed sets once:

```powershell
voxshield-data make-fixed --data-root data --manifest-dir manifests_v4 --split val `
  --count 500 --seconds 4 --snr-min -15 --snr-max 20 --clean-fraction 0.15 `
  --near-clean-fraction 0.15 --reverb-fraction 0.35 --multichannel `
  --output-dir data/mixtures/val_v4 --seed 2029

voxshield-data make-fixed --data-root data --manifest-dir manifests_v4 --split test `
  --count 1000 --seconds 4 --snr-min -15 --snr-max 20 --clean-fraction 0.15 `
  --near-clean-fraction 0.15 --reverb-fraction 0.35 --multichannel `
  --output-dir data/mixtures/test_v4 --seed 2030
```

Do not regenerate the test set because a model performed poorly. Improve the model on training
and validation only; use the frozen test set for the final claim.
