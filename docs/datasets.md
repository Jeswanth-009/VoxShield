# Dataset acquisition and labeling

The model needs broad clean speech and noise diversity. Dataset licenses change, so verify the
current license and permitted use at the official source before downloading. Do not commit
corpora to this repository.

## Recommended starting set

Clean speech:

- **LibriSpeech** (`https://www.openslr.org/12/`) train-clean-100 and train-clean-360 for training, dev-clean for validation,
  test-clean for testing. Preserve speaker-disjoint official splits.
- Add locally recorded Indian English and relevant Indian-language speech, with written consent
  and a clear data-use policy, because LibriSpeech alone does not represent the target users.

Noise:

- **Microsoft DNS Challenge** (`https://github.com/microsoft/DNS-Challenge`) noise/audio resources: broad real and synthetic noise. Sort files
  by source/recording into the categories below; preserve source-disjoint splits.
- **MUSAN** (`https://www.openslr.org/17/`) noise portions: useful for stationary and ambient sources. Speech and music may be
  useful as non-stationary interference, subject to its license and the intended task.
- **ESC-50** (`https://github.com/karolpiczak/ESC-50`): environmental events. It is CC BY-NC,
  so verify that non-commercial terms fit the project before use. Its clips can supply
  validation/test events, but avoid leaking folds or source recordings between splits.
- Purpose-recorded target noise: engines, fans, HVAC, generators, vehicles, machinery, wind,
  alarms, knocks, weapon-like impulses only where collection is lawful and safe. Target-domain
  recordings matter more than simply increasing generic corpus size.
- A licensed drone/UAV corpus or safely recorded UAV-like target audio. Do not substitute a few
  generic engine clips and claim drone coverage.

Room impulse responses are required for the v4 full recipe. Use a licensed public RIR corpus
(for example OpenSLR SLR28 where its terms fit) and controlled local measurements from the
intended rooms/headset geometry. VCTK, MUSAN, ESC-50, and MAD do not provide this coverage.

The final gate also requires real, synchronized two-microphone recordings from the intended
primary/reference geometry. Synthetic dual-channel mixtures are useful for training but cannot
validate clock sync, acoustic leakage, device buffering, microphone mismatch, or real tank/
rotor/impulse overlap behavior.

## Category rules

- `stationary`: fans, steady engines, HVAC, electrical hum, broadband steady noise.
- `nonstationary`: speech babble, music, moving vehicles, changing machinery, wind gusts.
- `impulsive`: clicks, knocks, door slams, tool impacts, short alarms, safely obtained impulses.
- `environmental`: traffic, rain, crowds, outdoor/indoor ambience and mixed soundscapes that do
  not fit the first three classes.

One file may be assigned to only one category/split. Use the dominant behavior. Store original
long recordings in only one split; cutting a recording into clips does not make the clips
independent.

## Exact layout and assumptions

For large corpora, use the in-place ingestion workflow in `data/README.md`; it avoids making a
second copy. Nested directories and arbitrary filenames are accepted. Audio is decoded with
libsndfile, averaged to mono, resampled with polyphase filtering to 16 kHz, and converted to
float32 only when a sample is loaded. Training draws four-second segments. Short speech files
are placed once in a zero-padded segment with faded joins; they are never repeated. Long speech
files use the most active of several deterministic random crops. Fixed evaluation pairs are
written as 16-bit WAV.

The scanner has specific adapters for LibriSpeech, VCTK, DNS Challenge-style trees, MUSAN,
ESC-50, and the official MAD military-audio corpus.
It uses official/path splits when they exist and otherwise hashes a speaker/source group into a
deterministic split. Noise categories come from an explicit source label, known metadata/layout,
or path keywords, in that priority order. Unknown noise defaults to `environmental`; the optional
`--analyze-unknown-noise` heuristic can inspect up to 30 seconds per unknown file, but it is
slower and its labels must be spot-checked.

Suggested scale for a serious first run:

- 100+ hours of speaker-diverse clean training speech.
- 50+ hours of diverse training noise, with meaningful coverage in every category.
- Source-disjoint validation/test audio, including target hardware recordings.

These are planning targets, not guarantees of quality. First run a small subset through the
indexer and smoke training, then scale up.

## Integrity checklist

1. Listen to a random sample from every source and category.
2. Remove corrupt, silent, clipped, mislabeled, and personally sensitive files.
3. Normalize neither the corpus files nor evaluation results globally; the mixer controls level.
4. Record dataset name, release, URL, license, checksum, and local split policy in a separate
   data inventory. The generated `catalog.jsonl` records file metadata, not license permission.
5. Run the fixed-mixture generator once per benchmark and retain its seed/manifest.
