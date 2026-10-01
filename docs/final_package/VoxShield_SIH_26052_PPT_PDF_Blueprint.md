# VoxShield SIH 26052 PPT PDF Blueprint

Team Name: Team@
Required deck length: 6 slides total

## Design direction

The deck must look like a finalist technical board, not a cinematic defence poster. Use clean finalist-style design:

- light grey or white background
- navy section headers
- white content cards
- thin grey borders
- green proof highlights
- amber next-step/risk highlights
- real workflow diagrams
- proof cards
- evidence board

Avoid:

- soldier face full-background
- tank/helicopter battlefield scenes
- huge glowing product title
- neon cyber dashboard look
- repeated fake waveforms
- unsupported dB claims

## Slide 1: Title page

### Purpose

Establish identity and seriousness.

### Layout

Use official SIH header and footer. The slide body should have two zones:

- left: title and metadata
- right: clean system visual

### Exact text

Title:

VoxShield

Subtitle:

AI speech enhancement for noisy defence communication

Metadata:

Problem Statement ID: 26052
Theme: Defence and National Security
PS Category: Hardware
Team Name: Team@

Proof badges:

ONNX export passed
Pi 5 real-time benchmark
Broad strict gate passed

### Visual

Use a simple vector-style system visual:

headset mic -> VoxShield AI engine -> enhanced speech -> dashboard

No battlefield photo.

## Slide 2: Idea title and proposed solution

### Purpose

Explain the solution concept in five seconds.

### Correct layout

Three-column board plus proof strip:

- left: problem context
- middle: proposed system workflow
- right: prototype outputs
- bottom: proof strip

### Title

Idea title and proposed solution

### Product heading

VoxShield: AI speech enhancement engine for noisy defence communication

### Subtitle

Improves command intelligibility under vehicle, rotor, impulse and ambient noise using local real-time inference.

### Left card: Problem context

Header:

Problem context

Rows:

Vehicle and engine noise - masks low-frequency speech cues

Rotor and wind noise - creates modulated nonstationary noise

Impulse noise - can hide short command words

Ambient field noise - reduces communication intelligibility

Bottom result:

Command words can get masked in high-noise communication.

### Middle card: Proposed system workflow

Header:

Proposed system workflow

Supporting line:

Use a reference-noise path plus speech-preserving enhancement, then expose runtime health for the operator.

Workflow:

1. Primary mic - speech near mouth
2. Reference mic - environment noise
3. Streaming model - dual-channel deep filter
4. Retention guard - checks speech deletion risk
5. Enhanced output - audio plus telemetry

Lower boxes:

Validated software path: ONNX export, offline audits, failure analysis and controlled replay demo.

Hardware note: true physical validation needs synchronized raw dual-microphone capture.

### Right card: Prototype outputs

Header:

Prototype outputs

Rows:

Enhanced speech - clearer command audio

Runtime telemetry - latency, bypass and health state

Evidence report - SNR, STOI, PESQ and deletion

Edge deployment path - ONNX model and Pi 5 benchmark

Bottom note:

Output is a prototype evidence path, not a claimed field-ready headset.

### Bottom proof strip

Cards:

30.48 dB SNR - v15 broad strict

5.33 ms latency - Pi 5 mean for 16 ms frame

0.0 speech deletion - reported audits

Next: dual-mic validation - synchronized raw capture

### Design notes

Do not use photo background. Do not make VoxShield huge. Do not use waveforms except as tiny optional line art. Do not claim final battlefield readiness.

## Slide 3: Technical approach

### Purpose

Show that the team built a full pipeline.

### Layout

Use an architecture map with two layers.

Top layer: training pipeline

Data sources -> mixture builder -> training -> hard failure repair -> validation

Bottom layer: runtime pipeline

Primary mic + reference mic -> frame buffer -> ONNX streaming model -> enhanced audio -> dashboard/evidence report

Right proof rail:

1.1M parameters
ONNX parity passed
Pi 5 mean latency 5.33 ms
0.0 speech deletion in audits

Bottom amber note:

Laptop/Bluetooth demos are not proof of synchronized reference capture. Final field validation needs raw dual-mic hardware.

### Text blocks

Data sources:

VCTK, DNS Challenge, MAD, ESC-50, AudioSet, RIRS, user recordings

Training:

SNR variation, reverb, impulse noise, nonstationary noise and hard-case replay

Runtime:

ONNX model, 16 kHz audio, 16 ms frame, dashboard telemetry

## Slide 4: Feasibility and viability

### Purpose

Show proof, risk and practical next step.

### Layout

Top: four proof cards

Middle left: prototype readiness ladder

Middle right: hardware path diagram

Bottom: risk and mitigation table

### Proof cards

Broad strict gate passed
Pi 5 mean latency 5.33 ms
ONNX export parity passed
Speech deletion 0.0 in reported audits

### Readiness ladder

1. Offline model validation - done
2. ONNX export - done
3. Pi 5 benchmark - done
4. Controlled replay demo - ready
5. Synchronized dual-mic field validation - next

### Hardware diagram

Primary mic near mouth
Reference mic facing noise
USB audio interface
Raspberry Pi 5
Headset/radio output
Dashboard

### Risk table

| Risk | Why it matters | Mitigation |
|---|---|---|
| Laptop/Bluetooth not synchronized | weak live proof | raw USB dual-mic rig |
| Real noise differs from synthetic mixes | hard failures remain | field recordings and repair set |
| Suppression may damage speech | command content matters | STOI and speech deletion gates |

## Slide 5: Impact and benefits

### Purpose

Make the problem human and mission-relevant.

### Layout

Use before/after communication example.

Left:

Before VoxShield
Noise masks important command words.

Example:

Hold position... left... unclear

Right:

After VoxShield
Speech becomes clearer while command content is preserved.

Example:

Hold position. Left flank clear.

Bottom benefit cards:

Defence communication - improves command clarity in high noise

Emergency response - useful around sirens and crowd noise

Industrial safety - supports headset communication near machines

Edge operation - runs locally without cloud dependency

Metric card:

v15 broad audit: SNR 30.48 dB, STOI 0.938, PESQ 3.94

## Slide 6: Research and references

### Purpose

End with evidence and credibility.

### Layout

Four-quadrant evidence board.

Quadrant 1: Data sources

VCTK, DNS Challenge, MAD, ESC-50, AudioSet targeted, RIRS NOISES, user recordings

Quadrant 2: Metrics

SNR, SI-SNR, STOI, PESQ, speech deletion, active level error, latency

Quadrant 3: Artifacts

v15 broad strict result
v15 military audit
ONNX export report
Pi 5 verification
failure report
saved audio examples

Quadrant 4: Next hardware phase

dual USB mic rig
raw synchronized capture
field noise recordings
headset/radio integration
dashboard demo

Final line:

Current status: AI engine and edge runtime validated. Next phase: synchronized microphone hardware validation.

## Final deck rules

Use fewer photos and more diagrams. Use fewer slogans and more proof. Keep every claim defensible. Make the project feel engineered, not imagined.
