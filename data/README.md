# Data directory

## Recommended for large downloads: scan in place

You do not have to rearrange or duplicate a large extracted corpus. `ingest` recursively scans
WAV, FLAC, and OGG files, validates their headers, creates deterministic train/validation/test
splits, assigns noise categories, and writes lightweight manifests. Use `data/manifests_v4`
for the clean rebuild so the frozen v3 catalog remains reproducible.
Original audio stays on its existing disk.

Run a no-write preview first:

```powershell
voxshield-data ingest --data-root data --manifest-dir manifests_v4 --dry-run `
  --source "D:\datasets\LibriSpeech" `
  --source "D:\datasets\DNS-Challenge\datasets" `
  --source "D:\datasets\musan" `
  --source "D:\datasets\ESC-50"
```

Native adapters are included for LibriSpeech, VCTK, DNS Challenge-style trees, MUSAN, ESC-50,
and the official Military Audio Dataset (MAD). VCTK uses the speaker folders in
`wav48_silence_trimmed` (or `wav48`) and hashes whole speakers into disjoint splits. ESC-50 uses
either `meta/esc50.csv` or a root-level `esc50.csv`. MAD uses `training.csv` and `test.csv`, including their `path` and `label`
columns, and preserves its official split.

If an ESC-50 package contains original, 44.1 kHz, and 16 kHz rendered copies, the scanner
catalogs only the 16 kHz set. Header validation uses bounded concurrency (`--scan-workers 8` by
default) so large VCTK trees do not require an in-memory file list or a long serial scan.

For MAD, gunshot/footsteps/shelling become impulsive noise and vehicle/helicopter/fighter become
non-stationary noise. Its communication class is excluded by default: for this speech-enhancement
task, automatically treating speech as unwanted noise risks teaching the model to suppress wanted
speech. It can still be included deliberately by forcing a category in the source specification.

Then rerun without `--dry-run`. A source may use any of these forms:

```text
--source "D:\dataset"                              auto-detect a known layout
--source "clean=D:\dataset\speech"                 force clean speech
--source "noise=D:\dataset\noise"                  force noise; auto-classify category
--source "noise:stationary=D:\field\fans"           force one noise category
--source "noise:nonstationary=D:\field\babble"
--source "noise:impulsive=D:\field\impacts"
--source "noise:environmental=D:\field\ambience"
--source "rir=D:\dataset\room_impulse_responses"    optional RIRs
```

Explicit category labels are safer than inference for a local or unfamiliar dataset. Add
`--analyze-unknown-noise` only when useful: it reads up to 30 seconds of each otherwise-unknown
noise file and applies an acoustic heuristic, so it can be slow and is not ground truth. Review
`data/manifests_v4/ingest-summary.json` and spot-check `catalog.jsonl` before training. Then run:

```powershell
voxshield-data audit --data-root data --manifest-dir manifests_v4 `
  --output artifacts/data-audit-v4.json --fail-on-leakage
```

`ready: false` means the catalog still lacks required defence labels or RIR coverage even when
all files and split boundaries are valid.

The manifests use absolute paths. Do not move the extracted folders afterward, and keep their
drive mounted during training. Re-run `ingest` if paths change. The command writes manifests
only; it never modifies source audio.

## Alternative: manually arranged repository data

The repository never downloads or redistributes speech/noise corpora. Put only audio you
are licensed to use under `data/raw` using the exact tree below. Files may be WAV, FLAC,
or OGG; indexing validates that each file can be opened.

```text
data/raw/
  clean/{train,val,test}/**/*.{wav,flac,ogg}
  noise/
    stationary/{train,val,test}/**/*.{wav,flac,ogg}
    nonstationary/{train,val,test}/**/*.{wav,flac,ogg}
    impulsive/{train,val,test}/**/*.{wav,flac,ogg}
    environmental/{train,val,test}/**/*.{wav,flac,ogg}
  rir/{train,val,test}/**/*.{wav,flac,ogg}       # optional room impulse responses
```

Do not put the same speaker, recording session, or source noise in multiple splits.
Run `voxshield-data index --data-root data` after copying files. Generated manifests go
to `data/manifests`; fixed evaluation mixtures go to `data/mixtures`.

## How training uses these files

Training does not pre-generate a huge mixture corpus. Each item is created on demand:

```text
clean speech s + randomly scaled/augmented noise n -> primary input x
delayed/filtered n + controlled speech leakage + self-noise -> synchronized reference input r
model(x, r) -> estimated clean speech
loss(estimated clean speech, original clean target s) -> model update
```

Short clean utterances are zero-padded rather than repeated. The default recipe also generates
clean identity pairs and very-high-SNR near-clean pairs so the model learns when to preserve its
input. Fixed v4 evaluation sets include both cases, every noise category, and the synchronized
reference channel.

The clean and noise recordings are independent; they do not have to describe the same event.
Validation/test fixed mixtures are generated separately so every checkpoint is compared against
the same examples. In deployment there is no clean target—the v4 model estimates speech from the
synchronized primary and reference microphones.
