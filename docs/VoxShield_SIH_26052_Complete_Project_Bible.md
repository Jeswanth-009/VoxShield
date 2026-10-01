# VoxShield SIH 26052 Complete Project Bible

Team Name: Team@  
Problem Statement ID: 26052  
Theme: Defence and National Security  
PS Category: Hardware  
Project Name: VoxShield  
Working Positioning: AI speech enhancement engine for noisy defence communication

---

## 1. What this document is

This is the full master document for VoxShield. It is not only a PPT guide. It covers the full project story from the beginning to the current state:

- what the problem statement is asking for
- what VoxShield is
- what we built
- what failed
- what actually worked
- what data was used
- what model versions were tried
- what evidence we have
- what limitations we must admit
- how the demo should be shown
- how the PPT should be designed
- how to answer judges
- what the next technical roadmap should be

This document should be used as the single source for the final SIH presentation, demo script, technical explanation, project report, and team speaking preparation.

---

## 2. The honest project identity

### The one-line identity

VoxShield is a local AI speech enhancement engine designed to improve speech intelligibility in noisy defence communication, with edge-runtime validation and a planned synchronized dual-microphone hardware path.

### The correct claim

Use this:

> VoxShield improves command speech clarity under mission-like noise using a lightweight streaming AI model, ONNX deployment, Raspberry Pi 5 benchmarking, and a dashboard/evidence workflow.

Do not use this:

> VoxShield is a fully completed battlefield ANC headset.

Why: the current work proves the AI engine and edge feasibility. It does not yet prove full physical adaptive noise cancellation in real hardware because that requires synchronized raw primary and reference microphones.

### The winning positioning

The strongest story is not “we already solved everything.”

The strongest story is:

> We built the AI engine, validated the runtime path, measured edge feasibility, identified the hardware gap, and have a clear plan to complete the physical prototype.

That sounds mature. It sounds like a team that understands engineering.

---

## 3. What the problem statement wants

The SIH problem asks for an AI/ML-enabled adaptive noise cancellation or noise suppression system for defence communication.

The expected system should:

- handle stationary noise
- handle nonstationary noise
- handle impulsive noise
- preserve intelligible speech
- operate with low latency
- be feasible for embedded or hardware deployment
- support real operational communication

In simple words:

> In a noisy defence environment, the operator must still hear the command clearly and quickly.

### Why the problem is hard

Normal noise suppression is not enough because defence noise is not one type of sound.

There can be:

- engine rumble
- rotor modulation
- wind
- vehicle vibration
- impulse blasts
- sirens
- radio distortion
- crowd or field background
- fan and air noise
- sudden transient events

The difficult part is not only removing noise. The difficult part is removing noise without deleting speech.

For communication, one missing word can matter.

Example:

```text
Hold position.
Move left.
Stop fire.
Retreat now.
Target clear.
```

If noise hides one of those words, the message can change.

---

## 4. What VoxShield should be presented as

### Product layer

VoxShield is the AI layer between noisy audio and communication output.

It takes:

- noisy speech
- reference/environment noise when available

It outputs:

- enhanced speech
- runtime health
- latency information
- evidence metrics
- logs or reports

### Hardware direction

The final intended physical system should include:

- primary microphone near the speaker
- reference microphone facing the noise environment
- raw synchronized audio capture
- edge compute such as Raspberry Pi 5
- wired headset or radio output
- dashboard or mission console

### Current prototype level

Current status:

- AI model pipeline exists
- ONNX export exists
- offline evaluation exists
- Pi 5 benchmark exists
- demo can be done with controlled replay
- physical synchronized dual-mic field validation is still next phase

This is the truth. The PPT should not hide it.

---

## 5. Project journey from start to now

### Stage 1: Initial goal

The first goal was to build a defence-noise cancellation system that could work live on a laptop and later on Raspberry Pi.

The expected outcome was:

- suppress noise
- preserve voice
- show live demo
- deploy on Pi
- align with SIH PS 26052

### Stage 2: Early implementation

The project began with:

- Python codebase under `C:\anc`
- VoxShield model scripts
- live inference command
- ONNX export path
- dashboard or mission console
- laptop demo script
- Pi transfer scripts
- documentation attempts

The system had a live console and could list audio devices.

### Stage 3: Laptop live demo problems

The laptop demo exposed a major issue:

- audio device combinations were unstable
- some input/output combinations failed
- PortAudio produced illegal I/O combination errors
- Bluetooth and laptop array devices did not behave like proper synchronized dual-channel hardware
- air noise and gun sounds still came through
- sometimes the enhanced output made voice worse

This felt like a model failure, but technically it revealed a hardware-path problem too.

### Stage 4: Realization about reference audio

The model expects synchronized reference audio. A normal laptop mic or Bluetooth headset does not provide clean synchronized reference input.

This changed the correct interpretation:

- the model may work in controlled paired-audio evaluation
- the live hardware path may be invalid
- Bluetooth is especially risky because it may add its own compression/noise suppression
- laptop “stereo” or mic arrays are not proof of reference mic geometry

This became one of the most important learnings in the project.

### Stage 5: Raspberry Pi transfer and setup

The project was transferred to Raspberry Pi using a zip transfer method after SSH/SCP login problems.

Important Pi steps completed:

- files were transferred
- model and ONNX were arranged
- install script ran
- Python environment installed
- missing external dependency issue was patched
- validation report was transferred
- benchmark verification ran

### Stage 6: Pi 5 benchmark success

The Pi 5 benchmark produced strong evidence:

- backend: ONNX runtime
- frame duration: 16 ms
- mean latency: about 5.33 ms
- p95 latency: about 5.49 ms
- p99 latency: about 6.05 ms
- full pipeline p99 callback: about 6.50 ms
- real-time factor: about 0.33
- deadline overruns: 0
- simulated callback drops: 0

This is one of the best project achievements.

Meaning:

> The model runtime is fast enough for real-time edge experimentation on Raspberry Pi 5.

Not meaning:

> The final field headset is already complete.

### Stage 7: Bluetooth experiment

Bluetooth headset testing showed why Bluetooth is bad for proof:

- device connected
- PipeWire detected sink and source
- output playback worked after Pulse/PipeWire setup
- mic recording could work through ALSA/Pulse bridge
- but the live VoxShield path still did not prove proper synchronized reference processing

The key conclusion:

> Bluetooth may be useful for casual listening, but it should not be used as the main SIH proof path.

### Stage 8: Dataset expansion

Because real-world results were poor, the project moved toward better data.

Datasets involved:

- VCTK
- MUSAN
- ESC-50
- MAD dataset
- small UAV acoustics
- RIRS NOISES
- DNS Challenge
- user recordings
- targeted AudioSet clips

The user also recorded personal clips:

- normal speech
- only fan
- speech with fan slow
- speech with fan medium
- speech with fan high
- speech with high fan
- speech with helicopter
- helicopter with speech

These recordings are very valuable for demo and future fine-tuning because they match the user’s real demo environment.

### Stage 9: DNS Challenge and storage constraints

DNS data download revealed storage problems:

- full DNS training data is huge
- noise and impulse responses alone took significant space
- user had around 37 to 50 GB free during parts of the work
- not all datasets could be downloaded fully

Important lesson:

> For this project, targeted data is better than blindly downloading huge datasets.

Good strategy:

- use smaller targeted subsets
- focus on defence-relevant noise categories
- keep hard failure clips
- avoid 1 TB full dataset requirement

### Stage 10: Manifest ingestion

The ingestion pipeline successfully referenced over 124,000 files without copying audio.

This matters because it proves:

- data pipeline exists
- multiple dataset adapters exist
- clean speech, noise and RIR categories are indexed
- the project is not trained on only one toy folder

This is a strong PPT point.

### Stage 11: v11 and v14 issues

Some training attempts failed or underperformed.

Examples:

- missing validation category issue
- `mad_dataset` split naming issue
- resume conflict between initialization and checkpoint resume
- v14 broad/military strict gate reliability failures
- wet mix did not fix the core problem

This was frustrating, but it produced engineering learning:

- more data alone does not guarantee improvement
- hard-case repair is more useful than blind training
- strict reliability gates matter
- live demo quality and offline metric quality can diverge

### Stage 12: v15 hard failure repair

v15 became the current best narrative candidate because:

- ONNX export passed
- broad strict gate passed
- metrics improved over v14
- military average was strong
- speech deletion stayed at 0.0

v15 is not perfect because military strict reliability still did not fully pass, but it is a strong candidate for PPT evidence.

---

## 6. Current best evidence

### v15 ONNX export

Reported export:

- checkpoint: `checkpoints_deep_filter_v15_hard_failure_repair\best.pt`
- ONNX: `artifacts\voxshield-v15-hard-failure-repair-final.onnx`
- architecture: deep filter dual
- opset: 17
- max output absolute error: about `1.82e-08`
- max state absolute error: about `4.07e-06`
- tolerance: `0.0002`
- export status: passed

Meaning:

> The model can be exported for runtime deployment and matches PyTorch closely enough in validation.

### v15 broad audit

Reported broad results:

| Metric | Value |
|---|---:|
| SNR enhanced | 30.48 dB |
| SI-SNR enhanced | 30.64 dB |
| STOI enhanced | 0.938 |
| PESQ enhanced | 3.94 |
| Pause noise attenuation | 20.24 dB |
| Speech deletion rate | 0.0 |
| Active level error | 0.10 dB |
| Strict SIH gate | Passed |

This is the strongest slide metric set.

### v15 military audit

Reported military average:

| Metric | Value |
|---|---:|
| SNR enhanced | 25.15 dB |
| SI-SNR enhanced | 25.30 dB |
| STOI enhanced | 0.915 |
| PESQ enhanced | 3.63 |
| Pause noise attenuation | 24.58 dB |
| Speech deletion rate | 0.0 |
| Active level error | 0.19 dB |

But strict military gate did not fully pass reliability because some individual clips missed STOI/joint target thresholds.

Correct explanation:

> Military average quality is strong, but reliability on all hard clips still needs improvement.

Do not hide this in technical explanation. It makes the roadmap real.

### Raspberry Pi 5 benchmark

| Benchmark item | Value |
|---|---:|
| Mean latency | 5.33 ms |
| p95 latency | 5.49 ms |
| p99 latency | 6.05 ms |
| Frame duration | 16 ms |
| Real-time factor | 0.33 |
| Deadline overruns | 0 |
| Simulated callback drops | 0 |

Correct claim:

> The ONNX runtime is feasible for real-time Pi 5 experimentation.

Wrong claim:

> Full live field headset is proven.

---

## 7. What failed and why it matters

### Failure 1: Laptop live demo sounded bad

Likely reasons:

- no proper reference mic
- unsynchronized input channels
- laptop mic array preprocessing
- speaker feedback risk
- wrong I/O device combinations
- room acoustics
- model trained on paired conditions but used in uncontrolled live path

Lesson:

> Laptop live demo is not a fair proof of the actual intended system.

### Failure 2: Bluetooth live path was unreliable

Likely reasons:

- Bluetooth profiles compress audio
- mic quality is limited
- headset may apply built-in noise suppression
- mono capture
- latency is unpredictable
- no synchronized reference path

Lesson:

> Bluetooth should not be used for final proof.

### Failure 3: More data did not automatically solve everything

v14 showed that adding targeted data can help but may not solve reliability.

Lesson:

> Hard failure repair and real paired validation are more important than random dataset growth.

### Failure 4: Slide design became cinematic

The design attempts became too much like:

- defence game poster
- AI product ad
- cinematic hero scene

This did not match finalist reference decks.

Lesson:

> Final PPT should be visually strong but built around diagrams, workflows, proof and feasibility.

---

## 8. Correct demo strategy

### Do not rely on raw live Bluetooth

It is risky and can embarrass the project.

### Use controlled replay demo

Best demo structure:

1. Show noisy input clip.
2. Show dashboard or waveform.
3. Play enhanced output.
4. Show metrics.
5. Show Pi 5 benchmark.
6. Explain hardware next step.

Label it:

> Controlled mission replay demo

This is honest and believable.

### Demo video structure

Duration: 90 to 120 seconds.

#### Scene 1: Problem

Show noisy command clip.

Text:

> Noise hides command words.

#### Scene 2: VoxShield system

Show workflow:

> noisy audio + reference path -> VoxShield model -> enhanced speech + telemetry

#### Scene 3: Before and after

Play:

- noisy input
- enhanced output

Do not say “perfectly removes all noise.”

Say:

> Speech becomes clearer while command content is preserved.

#### Scene 4: Pi 5 proof

Show:

> Mean latency 5.33 ms for 16 ms frame.

#### Scene 5: Next hardware phase

Show dual-mic diagram.

Text:

> Next: synchronized raw dual-microphone validation.

---

## 9. Correct PPT direction

The PPT must be:

- dense but organized
- visually strong but not fake
- technical but easy to scan
- factual but ambitious
- finalist-reference style

The correct aesthetic:

> Premium SIH finalist technical board.

Not:

> cinematic battlefield poster.

Not:

> boring plain report.

### Visual language

Use:

- light grey or white canvas
- navy headers
- clean cards
- icons
- arrows
- architecture maps
- proof strips
- evidence boards
- limited dark panels for model/runtime blocks

Avoid:

- full war backgrounds
- giant soldier face
- glowing neon UI everywhere
- huge product logo on every slide
- unsupported cost claims
- unsupported SPL/dB environment claims

---

## 10. Six-slide PPT blueprint

### Slide 1: Title

Purpose:

> Establish project identity.

Should show:

- VoxShield name
- SIH PS ID 26052
- Team@
- theme and category
- one clean system visual
- three small proof badges

Do not overload.

### Slide 2: Idea title and proposed solution

Purpose:

> Explain the product concept in five seconds.

Layout:

- left: problem context
- middle: proposed system workflow
- right: prototype outputs
- bottom: proof strip

Exact title:

> VoxShield: AI speech enhancement engine for noisy defence communication

Core workflow:

```text
Primary mic + reference mic
-> Streaming AI enhancement
-> Speech retention guard
-> Enhanced audio + telemetry
```

Bottom proof strip:

- 30.48 dB SNR broad audit
- 5.33 ms Pi 5 latency
- 0.0 speech deletion
- next: dual-mic validation

### Slide 3: Technical approach

Purpose:

> Show engineering depth.

Layout:

- top: data pipeline
- middle: runtime architecture
- right: metric proof rail
- bottom: hardware note

Must include:

- VCTK
- DNS Challenge
- MAD
- ESC-50
- AudioSet
- RIRS
- user recordings
- ONNX runtime
- Pi 5
- dashboard

### Slide 4: Feasibility and viability

Purpose:

> Show what is proven and what remains.

Layout:

- proof cards
- readiness ladder
- hardware diagram
- risk mitigation table

Most important note:

> AI engine and edge runtime validated. Physical mic geometry validation next.

### Slide 5: Impact and benefits

Purpose:

> Show why it matters.

Use before/after command example:

Before:

> Hold... left... unclear

After:

> Hold position. Left flank clear.

Benefit cards:

- defence communication
- emergency response
- industrial safety
- local edge operation

### Slide 6: Research and references

Purpose:

> Show credibility.

Four quadrants:

- datasets
- metrics
- artifacts
- next hardware phase

Final line:

> Current status: AI engine and edge runtime validated. Next phase: synchronized microphone hardware validation.

---

## 11. Technical roadmap

### Immediate steps before SIH submission

1. Freeze v15 as current demo candidate.
2. Keep v12 as backup metric model if needed.
3. Create clean controlled demo audio set.
4. Build dashboard recording flow.
5. Create before/after clips.
6. Build final 6-slide PPT.
7. Create 90-second demo video.
8. Prepare judge Q&A.

### Next engineering steps after submission

1. Buy or arrange raw USB dual-mic input.
2. Record synchronized primary/reference clips.
3. Build field validation dataset.
4. Fine-tune on real paired data.
5. Optimize ONNX runtime.
6. Build Pi 5 dashboard integration.
7. Test headset/radio output path.
8. Run real-time hardware validation.

---

## 12. What hardware is actually needed

Minimum recommended hardware:

- Raspberry Pi 5
- USB audio interface or multichannel USB mic input
- two wired microphones
- wired headphones/headset
- stable power supply
- noise playback speaker for controlled testing
- optional small display or laptop dashboard

Avoid:

- Bluetooth as proof device
- laptop internal array as final proof
- random phone mic as reference

---

## 13. How to answer judges

### Question: Is this real ANC?

Answer:

> The current prototype is an AI speech enhancement engine for communication clarity. Full physical ANC validation needs synchronized primary and reference microphones. We designed the model and runtime for that path, and our next phase is raw dual-mic validation.

### Question: Why not use Bluetooth?

Answer:

> Bluetooth is useful for casual audio, but not for proving this system. It can compress audio, add internal suppression and create unpredictable latency. For validation we need raw synchronized audio capture.

### Question: What is actually proven?

Answer:

> We have validated the model export, offline enhancement metrics, edge latency on Raspberry Pi 5 and a controlled replay demo path. The physical microphone geometry is the next hardware validation step.

### Question: Why should this be selected?

Answer:

> Because we have not stopped at an idea. We built the data pipeline, model, ONNX export, evaluation gates, Pi 5 benchmark, failure analysis and dashboard concept. SIH support would help us complete the synchronized hardware prototype.

### Question: What is the biggest weakness?

Answer:

> The biggest current weakness is live physical validation without synchronized microphone hardware. We have identified this clearly and designed the next build around raw dual-channel capture.

---

## 14. The final story to tell

The final story should be:

1. Defence communication fails when command words are masked by complex noise.
2. VoxShield targets speech intelligibility, not just volume.
3. The team built a real AI enhancement pipeline.
4. The model is exported to ONNX and benchmarked on Raspberry Pi 5.
5. Broad controlled audits pass strongly.
6. Hard military clips still show reliability work remains.
7. The team understands the hardware gap.
8. The next step is synchronized dual-mic physical validation.
9. This is exactly the kind of project SIH can help convert from prototype engine to field-ready hardware.

---

## 15. Final project conclusion

VoxShield should not be presented as a finished magical ANC headset. It should be presented as a serious, technically developed AI speech enhancement system with strong evidence, visible engineering effort, edge feasibility and an honest hardware roadmap.

That is more credible, more defensible and more likely to impress judges than overclaiming.

The strongest final sentence:

> VoxShield has validated the intelligence layer. The next step is validating the physical microphone layer.

