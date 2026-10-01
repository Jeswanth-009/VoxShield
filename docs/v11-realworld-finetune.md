# VoxShield v11 real-world fine-tune

This stage targets the live-demo failure mode: laptop/Bluetooth style capture,
clipped microphones, bad reference channels, air/fan noise, and speech deletion.
It starts from `checkpoints_deep_filter_v10/best.pt` and uses on-the-fly mixing,
so it does not create large mixture WAV folders.

## DNS data now available

Expected local paths:

```text
C:\Users\jeswa\DNS-Challenge\V5_dev_testset
C:\Users\jeswa\DNS-Challenge\datasets_fullband\noise_fullband
C:\Users\jeswa\DNS-Challenge\datasets_fullband\impulse_responses
```

## Build v11 manifests

Run from PowerShell:

```powershell
cd C:\anc

& ".\.venv\Scripts\voxshield-data.exe" ingest `
  --manifest-dir manifests_v11 `
  --source "C:\Users\jeswa\Downloads\Datasets\_n\VCTK-Corpus" `
  --source "C:\Users\jeswa\Downloads\Datasets\_n\musan" `
  --source "C:\Users\jeswa\Downloads\Datasets\_n\esc-50" `
  --source "C:\Users\jeswa\Downloads\Datasets\_n\MAD_dataset" `
  --source "C:\Users\jeswa\Downloads\Datasets\_n\small_uav_acoustics" `
  --source "C:\Users\jeswa\Downloads\Datasets\_n\RIRS_NOISES" `
  --source "C:\Users\jeswa\DNS-Challenge"
```

This references audio in place and writes only JSONL manifests under
`C:\anc\data\manifests_v11`.

## Train

Short smoke:

```powershell
cd C:\anc

& ".\.venv\Scripts\voxshield-train.exe" `
  --config configs\deep_filter_v11_realworld.yaml `
  --device cuda
```

Expected time on RTX 4060 Laptop GPU: roughly 1.5-3 hours for 12 compact
fine-tune epochs, depending on DNS scanning and data loader speed.

## Evaluate

Use the existing frozen broad and military gates first:

```powershell
& ".\.venv\Scripts\voxshield-evaluate.exe" `
  --checkpoint checkpoints_deep_filter_v11_realworld\best.pt `
  --manifest data\mixtures\audit_broad_val\manifest.jsonl `
  --device cuda `
  --limit 50 `
  --strict-sih-gate `
  --output artifacts\v11-realworld-broad-50.json `
  --save-audio artifacts\v11-realworld-broad-audio `
  --save-audio-limit 30

& ".\.venv\Scripts\voxshield-evaluate.exe" `
  --checkpoint checkpoints_deep_filter_v11_realworld\best.pt `
  --manifest data\mixtures\audit_military_val\manifest.jsonl `
  --device cuda `
  --limit 50 `
  --strict-sih-gate `
  --output artifacts\v11-realworld-military-50.json `
  --save-audio artifacts\v11-realworld-military-audio `
  --save-audio-limit 30
```

Then repeat the laptop raw-mic test with low wet mix. If v11 improves voice
preservation but weakens noise suppression, keep both v10 and v11 and present
v11 as the live-demo-safe profile.
