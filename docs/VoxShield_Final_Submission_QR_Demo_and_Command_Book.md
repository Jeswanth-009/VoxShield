# VoxShield Final Submission: QR Evidence Room, Demo and Command Book

This is the final operational checklist for SIH PS 26052. It separates verified evidence from proposed hardware, gives the QR landing-page structure, defines the video flow, and collects the commands needed on the Windows laptop and Raspberry Pi 5.

## 1. What the QR code should open

The QR code should open a permanent HTTPS landing page that works without login on a phone. Do not point it directly at a ZIP, a local IP address, a large PDF, or a folder that asks the judge to request access.

Recommended first screen:

1. **VoxShield** — Local dual-channel speech enhancement for defence communication.
2. A 20–30 second demonstration video with captions.
3. Three large buttons:
   - **Hear Before / After**
   - **See Verified Results**
   - **View Technical Dossier**
4. A short status label:
   - AI engine: validated
   - ONNX export: validated
   - Raspberry Pi runtime: validated with the exact version named
   - Synchronized dual-microphone hardware: in progress until physically completed

The first screen must load quickly on mobile data. Keep the initial page below roughly 2 MB and load larger reports only when selected.

## 2. Evidence-room page structure

### Section A — 30-second overview

- Exact problem statement and PS ID 26052.
- One sentence explaining the operational failure: noise masks short commands.
- One sentence explaining VoxShield: a causal, dual-channel, stateful ONNX enhancement pipeline for local edge execution.
- One real photograph containing the Raspberry Pi 5, the JBL device actually used for the laptop demo, and the dashboard. Label each item accurately. Do not show a fabricated dual-capsule headset as completed hardware.

### Section B — Listen to the result

Provide three to five carefully chosen samples. Each sample must have aligned controls:

- Noisy input
- Enhanced v15 output
- Clean target, when available

Display the audit record ID, noise category, input SNR and model version. Do not use invented battlefield names. Suggested groups:

- Stationary engine/fan noise
- Rotor or periodic noise
- Impulsive noise
- Mixed hard case
- One failure or difficult case, with a brief explanation

Normalize only playback loudness consistently; do not make the enhanced file louder to create a false improvement. Use WAV for download and compressed AAC/MP3/Opus copies for instant browser playback.

### Section C — Verified metrics

Show a compact table:

| Audit | n | Output SNR | SNR improvement | STOI | PESQ | Speech deletion |
|---|---:|---:|---:|---:|---:|---:|
| Broad v15 | 50 | 30.48 dB | +10.07 dB | 0.938 | 3.94 | 0.0% |
| Military v15 | 50 | 25.15 dB | +14.05 dB | 0.915 | 3.63 | 0.0% |

Under the table state:

> The broad strict reliability gate passed. The military audit passed mean-quality checks but did not pass every strict per-clip reliability target; these hard cases form the next field-tuning set.

Link the raw JSON reports so the values can be checked.

### Section D — Architecture

Use one readable diagram:

`Primary speech+noise mic + reference noise mic -> causal STFT -> four grouped recurrent blocks -> five-tap complex deep filter -> ISTFT -> runtime guard -> output`

Verified architecture facts:

- 16 kHz audio
- 32 ms STFT analysis window
- 16 ms hop
- 50% overlap
- 1,141,389 parameters
- Stateful streaming ONNX
- Approximately 4.69 MB ONNX file, or 4.48 MiB
- Dual-channel reference-conditioned processing

### Section E — Raspberry Pi proof

Include:

- A real photograph of the Pi running the benchmark.
- Terminal screenshot showing the v15 filenames.
- Full benchmark JSON.
- Checkpoint and ONNX SHA-256 values.
- Mean model inference time.
- Full-pipeline p99 callback time.
- Runtime deadline overruns.
- Dropped/underflowed callbacks.

Do not call model inference time end-to-end audio latency. Physical end-to-end latency requires loopback measurement.

### Section F — Engineering evidence downloads

Publish these as separate, clearly named downloads:

1. `01-VoxShield-SIH-Deck.pdf`
2. `02-VoxShield-Two-Page-Brief.pdf`
3. `03-VoxShield-Technical-Dossier.pdf`
4. `04-VoxShield-v15-Model-Card.pdf`
5. `05-VoxShield-v15-Broad-Audit.json`
6. `06-VoxShield-v15-Military-Audit.json`
7. `07-VoxShield-v15-ONNX-Validation.json`
8. `08-VoxShield-Pi5-v15-Benchmark.json`
9. `09-VoxShield-Test-Report.pdf` or JUnit XML plus a readable HTML/PDF summary
10. `10-VoxShield-Data-Provenance-and-Licences.pdf`
11. `11-VoxShield-Prototype-BOM.pdf`
12. `12-VoxShield-Risk-Limitations-and-Roadmap.pdf`
13. `13-SHA256-MANIFEST.json`
14. `14-Demo-Video.mp4`

Optional:

- Selected source files or a public repository
- Dashboard screenshots
- A one-page API/runtime integration note
- Hardware wiring diagram
- Poster or one-page architecture sheet

### Section G — Data provenance

State the exact indexed composition:

- 44,243 clean-speech assets
- 19,829 noise assets
- 60,466 RIR assets
- 124,538 indexed assets in total

List each dataset with its original link, licence, permitted use, number of indexed entries and role in training/evaluation. Do not redistribute datasets through the QR page unless their licences permit it.

### Section H — Limitations and next milestones

Explicitly state:

- The current Windows dual-endpoint demonstration is engineering validation, not synchronized production capture.
- The proposed production capture unit uses two microphone capsules connected to one single-clock stereo ADC. This hardware is not currently owned or assembled.
- The military strict per-clip gate still contains difficult cases.
- Physical loopback latency and field SPL tests remain to be conducted.
- MIL-STD or ruggedization compliance is a future validation target, not a present certification.

This section increases trust; it does not weaken the project.

## 3. What must not be published through the QR

- Private dataset audio that cannot legally be redistributed
- API tokens, passwords, Wi-Fi details or personal addresses
- Absolute local paths such as `C:\Users\...`
- Training checkpoints unless intentionally open-sourced
- Huge raw datasets
- Unsupported field-test claims
- Live localhost dashboard links
- Editable cloud folders where files can accidentally disappear

## 4. QR reliability checklist

- Use one permanent short HTTPS URL.
- Test using mobile data, not the presentation Wi-Fi.
- Test on Android and iPhone if possible.
- Ensure no login or access request appears.
- Keep the QR at least 25–30 mm wide in the PDF.
- Use high contrast with a white quiet zone.
- Put the short URL below the QR as a fallback.
- Export the QR as SVG or a high-resolution PNG.
- Do not replace the destination after submitting unless the URL remains identical.
- Keep a read-only mirror or release snapshot.

## 5. Video recording sequence

Use a 100–110 second master video.

1. **0–7 s:** show the real JBL device, laptop and phone. Play raw noise and ask: “Can you hear the command?”
2. **7–18 s:** state the problem and describe VoxShield as an inline local audio optimizer; show a simple target-path graphic, not nonexistent hardware.
3. **18–32 s:** show the actual laptop setup. Identify the JBL microphone as the primary speech input and the laptop microphone array as the environmental reference. Caption this `LIVE WINDOWS DUAL-ENDPOINT ENGINEERING DEMO`.
4. **32–55 s:** show the dashboard while switching bypass/enhancement. Repeat the same short phrase with the phone at a marked position and fixed volume. Keep both input waveforms visible.
5. **55–75 s:** switch to a controlled noisy/enhanced/clean replay and show the verified broad/military aggregate results. Caption it `CONTROLLED PAIRED AUDIT`, not live field evidence.
6. **75–94 s:** physically show the Raspberry Pi 5 and its SSH/terminal benchmark using the exact v15 filenames. Caption it `LOCAL PI 5 INFERENCE BENCHMARK`. Do not imply the JBL live stream is passing through the Pi.
7. **94–108 s:** show the target inline product path—two synchronized microphone capsules, one stereo ADC, Pi/runtime and communication output—clearly labelled `TARGET HARDWARE ARCHITECTURE`; finish with the current status and next milestone.

Recommended closing line:

> VoxShield is an auditable, offline communication pipeline: dual-channel enhancement, stateful ONNX inference, runtime health monitoring and fail-safe audio continuity. The AI engine is validated; a synchronized two-microphone capture unit and physical field testing are the next milestones.

## 6. Windows command book

Open PowerShell and enter one command block at a time.

### 6.1 Open the project and activate the environment

```powershell
cd C:\anc
& ".\.venv\Scripts\Activate.ps1"
```

Activation is optional when commands use their complete `.venv` path.

### 6.2 Confirm required v15 artifacts

```powershell
cd C:\anc

Get-Item `
  ".\checkpoints_deep_filter_v15_hard_failure_repair\best.pt", `
  ".\artifacts\voxshield-v15-hard-failure-repair-final.onnx", `
  ".\artifacts\voxshield-v15-hard-failure-repair-final.validation.json", `
  ".\artifacts\v15-onnx-broad-50.json", `
  ".\artifacts\v15-onnx-military-50.json" |
  Select-Object FullName,Length,LastWriteTime
```

### 6.3 List current audio devices

```powershell
cd C:\anc

& ".\.venv\Scripts\voxshield-live.exe" `
  --checkpoint ".\checkpoints_deep_filter_v15_hard_failure_repair\best.pt" `
  --onnx ".\artifacts\voxshield-v15-hard-failure-repair-final.onnx" `
  --list-devices
```

Device numbers can change after reconnecting Bluetooth devices or rebooting Windows. Always run this first.

### 6.4 Test both microphones independently

Replace the IDs when the device listing changes.

```powershell
cd C:\anc

& ".\.venv\Scripts\python.exe" ".\scripts\test_dual_mics.py" `
  --primary-device 1 `
  --reference-device 2 `
  --duration 15
```

Expected result: the voice and environment bars respond differently.

### 6.5 Start the v15 live dashboard demo

```powershell
cd C:\anc

powershell -ExecutionPolicy Bypass -File ".\scripts\run_v15_jbl_dashboard_demo.ps1" `
  -PrimaryDevice 1 `
  -ReferenceDevice 2 `
  -OutputDevice 5 `
  -WetMix 0.82 `
  -DashboardPort 8765
```

During the first four seconds, remain silent and play representative noise near the reference microphone. Use headphones to prevent feedback. The dashboard is normally opened at `http://127.0.0.1:8765/`.

### 6.6 Export v15 again if required

```powershell
cd C:\anc

& ".\.venv\Scripts\voxshield-export.exe" `
  --checkpoint ".\checkpoints_deep_filter_v15_hard_failure_repair\best.pt" `
  --output ".\artifacts\voxshield-v15-hard-failure-repair-final.onnx"
```

### 6.7 Re-run the broad audit

```powershell
cd C:\anc

& ".\.venv\Scripts\voxshield-evaluate.exe" `
  --checkpoint ".\checkpoints_deep_filter_v15_hard_failure_repair\best.pt" `
  --onnx ".\artifacts\voxshield-v15-hard-failure-repair-final.onnx" `
  --manifest ".\data\mixtures\audit_broad_val\manifest.jsonl" `
  --device cpu `
  --limit 50 `
  --strict-sih-gate `
  --fail-on-regression `
  --output ".\artifacts\v15-onnx-broad-50.json" `
  --save-audio ".\artifacts\v15-broad-audio" `
  --save-audio-limit 50
```

### 6.8 Re-run the military audit

```powershell
cd C:\anc

& ".\.venv\Scripts\voxshield-evaluate.exe" `
  --checkpoint ".\checkpoints_deep_filter_v15_hard_failure_repair\best.pt" `
  --onnx ".\artifacts\voxshield-v15-hard-failure-repair-final.onnx" `
  --manifest ".\data\mixtures\audit_military_val\manifest.jsonl" `
  --device cpu `
  --limit 50 `
  --strict-sih-gate `
  --expected-noisy-categories "impulsive,nonstationary,mixed" `
  --output ".\artifacts\v15-onnx-military-50.json" `
  --save-audio ".\artifacts\v15-military-audio" `
  --save-audio-limit 50
```

The military command may return a non-zero status because the strict reliability gate is not fully passed. Preserve the report instead of hiding the failure.

### 6.9 Run the test suite and save a report

```powershell
cd C:\anc

& ".\.venv\Scripts\python.exe" -m pytest `
  --junitxml ".\artifacts\v15-test-report.xml"
```

Only claim that every test passes after this command finishes successfully.

### 6.10 Generate local SHA-256 hashes

```powershell
cd C:\anc

Get-FileHash `
  ".\checkpoints_deep_filter_v15_hard_failure_repair\best.pt", `
  ".\artifacts\voxshield-v15-hard-failure-repair-final.onnx", `
  ".\artifacts\v15-onnx-broad-50.json", `
  ".\artifacts\v15-onnx-military-50.json" `
  -Algorithm SHA256 |
  Format-Table Path,Hash -AutoSize
```

### 6.11 Copy the exact v15 model to Raspberry Pi

Replace `192.168.1.34` if `hostname -I` on the Pi reports a different address.

```powershell
cd C:\anc

ssh jeswanth@192.168.1.34 "mkdir -p ~/anc/checkpoints_deep_filter_v15_hard_failure_repair ~/anc/artifacts/pi5-v15-verification"

scp ".\checkpoints_deep_filter_v15_hard_failure_repair\best.pt" `
  "jeswanth@192.168.1.34:~/anc/checkpoints_deep_filter_v15_hard_failure_repair/best.pt"

scp ".\artifacts\voxshield-v15-hard-failure-repair-final.onnx" `
  "jeswanth@192.168.1.34:~/anc/artifacts/voxshield-v15-hard-failure-repair-final.onnx"
```

## 7. Raspberry Pi 5 command book

### 7.1 Display the current address

```bash
hostname -I
```

### 7.2 Confirm v15 files

```bash
cd ~/anc
ls -lh checkpoints_deep_filter_v15_hard_failure_repair/best.pt
ls -lh artifacts/voxshield-v15-hard-failure-repair-final.onnx
```

### 7.3 Run the exact v15 Pi benchmark

```bash
cd ~/anc
mkdir -p artifacts/pi5-v15-verification

.venv/bin/voxshield-benchmark \
  --checkpoint checkpoints_deep_filter_v15_hard_failure_repair/best.pt \
  --onnx artifacts/voxshield-v15-hard-failure-repair-final.onnx \
  --device cpu \
  --threads 1 \
  --warmup 200 \
  --frames 10000 \
  --output artifacts/pi5-v15-verification/benchmark.json
```

### 7.4 Display the benchmark cleanly

```bash
cd ~/anc
python3 -m json.tool artifacts/pi5-v15-verification/benchmark.json
```

### 7.5 Hash the exact Pi artifacts

```bash
cd ~/anc

sha256sum \
  checkpoints_deep_filter_v15_hard_failure_repair/best.pt \
  artifacts/voxshield-v15-hard-failure-repair-final.onnx \
  | tee artifacts/pi5-v15-verification/artifact-sha256.txt
```

### 7.6 List Pi audio devices

```bash
cd ~/anc

.venv/bin/voxshield-live \
  --checkpoint checkpoints_deep_filter_v15_hard_failure_repair/best.pt \
  --onnx artifacts/voxshield-v15-hard-failure-repair-final.onnx \
  --list-devices
```

Do not present Bluetooth headset capture as final synchronized dual-microphone hardware. For the final rig, use two microphone channels captured by the same stereo ADC clock.

## 7A. Hardware truth for the current demonstration

The equipment currently available is:

- A JBL Bluetooth headset connected only to the Windows laptop
- The JBL microphone as the speech-dominant primary input
- The laptop Realtek microphone array as the environment/reference input
- A phone or speaker used to reproduce demonstration noise
- A Raspberry Pi 5 used separately to prove local model execution and timing
- No completed dual-capsule military headset
- No completed single-clock stereo microphone ADC
- No direct tactical-radio connection

The video must therefore show two separate proof tracks:

1. **Laptop functional demonstration:** JBL primary microphone + laptop microphone array + v15 dashboard.
2. **Pi deployment proof:** the exact v15 checkpoint/ONNX benchmarked locally on the Raspberry Pi 5.

Do not imply that the JBL is connected to the Pi or that the Pi is processing the live laptop demonstration. A clean edit may move from the laptop demonstration to the Pi benchmark, but the captions must state the role of each platform.

## 7B. Project evolution story

The project did not begin directly with v15. The concise and defensible development story is:

1. **Inline audio optimizer concept.** The initial product idea was a small local appliance inserted in the communication audio path so existing equipment could gain noise suppression without cloud connectivity.
2. **Classical ANC exploration.** Adaptive cancellation and FxNLMS-style concepts were considered. Physical acoustic ANC requires an actuator, error microphone and measured secondary path, so it remained a separate hardware workstream rather than being falsely presented as the finished speech-enhancement system.
3. **Single-channel neural baselines.** Compact GTCRN/mono enhancement variants established causal streaming and deployment feasibility, but could not exploit a separate environmental reference.
4. **UL-UNAS dual-channel fusion.** v6/v7 explored a very small causal UL-UNAS-derived network with spatial/reference features. It was efficient, but difficult low-SNR military cases and runtime-tail behaviour prevented it from being the final candidate.
5. **Fusion and hybrid experiments.** Later v8/v9 candidates tested richer fusion and complex-domain behaviour. Experiments were retained or rejected according to unchanged audit gates rather than architecture novelty alone.
6. **Custom dual-channel deep filtering.** v10 moved to the current causal reference-conditioned complex-mask and five-tap deep-filter family. v10b was rejected when it failed to improve the frozen military reliability gate.
7. **Real-world data specialization.** v11–v14 added DNS material, RIRs, user recordings and targeted AudioSet classes. v14 improved mean quality but still missed strict per-clip reliability.
8. **Failure-driven v15 repair.** v15 was trained specifically around mined hard cases while replaying preservation cases. It passed the broad strict gate and improved military averages, while the remaining military reliability failures stayed visible.
9. **Operator and deployment layer.** The dashboard, telemetry, control modes, ONNX parity checks, dual-device Windows demo and Raspberry Pi benchmark complete the present engineering prototype.

The important narrative is not “we changed architectures many times.” It is:

> Each version answered a measured failure: reference use, causality, speech preservation, hard-noise reliability, export parity or edge runtime. Candidates that did not improve the frozen evidence were rejected.

### 7.7 Copy Pi evidence back to Windows

Run this in Windows PowerShell after the Pi benchmark:

```powershell
cd C:\anc
New-Item -ItemType Directory -Force ".\artifacts\pi5-v15-verification" | Out-Null

scp "jeswanth@192.168.1.34:~/anc/artifacts/pi5-v15-verification/benchmark.json" `
  ".\artifacts\pi5-v15-verification\benchmark.json"

scp "jeswanth@192.168.1.34:~/anc/artifacts/pi5-v15-verification/artifact-sha256.txt" `
  ".\artifacts\pi5-v15-verification\artifact-sha256.txt"
```

## 8. Final submission checklist

- Page 1 is completed.
- Slide 2 says output SNR 30.48 dB, not +30.48 dB gain.
- Parameter count is 1,141,389.
- STFT wording is 32 ms window / 16 ms hop / 50% overlap.
- Slide 5 contains controlled audits, not invented field trials.
- The exact v15 Pi benchmark is shown.
- Every screenshot displays v15 filenames.
- The video identifies live demo, controlled replay and proposed hardware separately.
- QR works without login on mobile data.
- Audio samples play directly on a phone.
- Raw reports and SHA-256 manifest can be downloaded.
- Dataset licences and limitations are visible.
- No unsupported certification, field SPL, savings or command-word claim remains.
