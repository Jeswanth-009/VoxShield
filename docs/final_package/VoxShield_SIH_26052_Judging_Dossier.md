# VoxShield SIH 26052 Judging Dossier

Team Name: Team@
Problem Statement ID: 26052
Theme: Defence and National Security
PS Category: Hardware

## Executive summary

VoxShield is an AI speech enhancement engine for noisy defence communication. The system is designed to improve command intelligibility when vehicle engines, rotor noise, impulse sounds, wind, fan noise and ambient field noise make speech unclear. The current prototype validates the software and edge-runtime path: model training, ONNX export, offline quality audits, Raspberry Pi 5 latency benchmark, and a dashboard/evidence workflow. The project should be presented honestly as an AI engine and edge-ready prototype path, not as a fully field-proven physical ANC headset.

The winning framing is simple: the team has built the intelligence layer and deployment path; the next SIH phase will complete synchronized dual-microphone hardware validation.

## What problem VoxShield solves

In defence communication, the critical issue is not only loud background noise. The real issue is command-word loss. A short word such as hold, left, stop, clear, move, fire, wait or retreat can be masked by engine rumble, rotor modulation, wind bursts, sudden impulse events, sirens or crowd noise. A communication system that only increases volume does not solve this because it amplifies both speech and noise.

VoxShield targets the layer between raw noisy audio and operator communication output. It attempts to preserve speech content while reducing interfering noise and exposing runtime health to the operator.

## Correct product positioning

Use this sentence in the PPT and presentation:

VoxShield is a local AI speech enhancement engine for noisy defence communication, validated as a software and edge-runtime prototype, with synchronized dual-microphone hardware validation planned as the next phase.

Do not say:

- Fully battlefield-ready ANC headset
- Complete physical ANC solution
- Removes all defence noise
- Mission-ready final product

These claims are risky because the current demo hardware does not provide a synchronized reference microphone path. The system should instead be judged as a strong AI/ML solution with a realistic hardware roadmap.

## Why the earlier slide direction was wrong

The cinematic defence slides looked polished but did not match the SIH finalist reference style. They looked like product trailers rather than engineering submissions. The reference decks use structured boards: problem blocks, workflow diagrams, architecture maps, proof cards, implementation roadmaps, cost/viability blocks, and evidence sections.

VoxShield should therefore use a clean finalist-board design:

- Light background, not battlefield background
- Workflow diagram, not glowing sci-fi engine
- Proof strip, not dramatic metric posters
- Hardware limitation note, not overclaim
- Dataset and evaluation evidence, not decorative war imagery

## Core value proposition

VoxShield improves speech intelligibility in noisy communication by combining:

- dual-channel input design: primary speech path plus reference-noise path
- streaming deep-filter enhancement
- speech-retention evaluation gates
- ONNX edge deployment path
- Raspberry Pi 5 feasibility benchmark
- dashboard/evidence reporting

## What has been built so far

The current work includes:

- data ingestion across clean speech, environmental noise, military-like audio, impulse noise, reverberation and user recordings
- targeted AudioSet sampling for gunshot, explosion, footsteps, engine, vehicle, siren, helicopter and aircraft categories
- model training and repair cycles including hard failure repair
- v15 ONNX export and parity validation
- broad and military audit evaluations
- Pi 5 runtime verification
- laptop and Pi live runtime experiments
- failure analysis showing where the system still needs improvement
- dashboard and demo planning for controlled replay

## Evidence snapshot

| Evidence item | Current result | How to use in PPT |
|---|---:|---|
| v15 broad SNR | 30.48 dB | Use as broad audit proof |
| v15 broad STOI | 0.938 | Use as intelligibility proof |
| v15 broad PESQ | 3.94 | Use as quality proof |
| v15 military SNR | 25.15 dB | Use as harder-case average |
| v15 military STOI | 0.915 | Use as harder-case intelligibility |
| v15 military PESQ | 3.63 | Use as harder-case quality |
| Pi 5 mean latency | 5.33 ms | Use as edge feasibility proof |
| Frame duration | 16 ms | Shows latency budget |
| Speech deletion | 0.0 in reported audits | Use as speech preservation proof |
| ONNX export | Passed | Use as deployment proof |

## Known limitation

Laptop and Bluetooth audio paths are not valid proof of physical ANC because they may apply internal processing and do not guarantee synchronized raw reference audio. Real physical validation needs:

- primary microphone near the speaker mouth
- reference microphone facing environmental noise
- raw synchronized capture through USB audio interface
- controlled hardware geometry
- repeatable field recordings

This limitation should not be hidden. It should be converted into a feasibility strength: the team knows the difference between AI enhancement validation and physical ANC hardware validation.

## Judge-safe demo strategy

The live demo should be a controlled replay and dashboard demo, not a risky Bluetooth live demo. The user can still show live interaction, but the source should be controlled:

1. Play a noisy command clip.
2. Show waveform/spectrogram and dashboard health.
3. Run or replay VoxShield enhanced output.
4. Show latency and metrics.
5. Explain that synchronized dual-mic hardware is the next phase.

Label the demo:

Controlled mission replay demo

Do not label it:

Live battlefield ANC proof

## Competitive story

Many teams will use AI. VoxShield should compete on completeness:

- not just an AI model
- data pipeline plus training
- model export plus ONNX runtime
- latency benchmark on Pi 5
- evaluation gates with STOI/PESQ/SNR
- failure analysis
- dashboard concept
- honest hardware roadmap

The story is: the team has done enough real engineering to deserve the hardware build phase.

## Final recommendation

The PPT should look like a serious technical board. Avoid cinematic images. Make slide 2 a clean workflow board. Make slide 3 a dense architecture map. Make slide 4 a proof and feasibility board. Make slide 5 a human communication impact slide. Make slide 6 an evidence board.

The strongest line for the judges:

We built the AI engine, validated the edge runtime, identified the hardware gap, and now need synchronized microphone validation to complete the physical prototype.
