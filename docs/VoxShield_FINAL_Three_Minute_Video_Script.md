# VoxShield — Final Three-Minute Two-Person Video Script

## Production target

- **Final duration:** approximately 3:00; keep a 2:58 competition cut if the portal enforces a hard limit.
- **Recording master:** approximately 3:25–3:40 before trimming pauses and optional lines.
- **Balance:** Approximately 40% cinematic presentation and 60% technical explanation/evidence.
- **People:** Person 1 opens and closes. Person 2 handles architecture, demonstration, evidence and Raspberry Pi proof.
- **Locations:** The two speakers may record separately. A travelling waveform connects both locations visually.

Use subtitles throughout. Remove background music during every audio comparison.

---

## 0:00–0:12 — Cinematic hook

### Camera and sound

Person 1's palm completely covers the lens, creating a black screen.

1. At 0:00, begin quiet radio static.
2. At 0:01, add rotor/engine noise.
3. At 0:02, play a masked radio command:

> “Alpha team… hold… move left…”

4. Show faint text through the darkness:

> `SIGNAL LOST IN NOISE`

5. At 0:04, Person 1 slowly removes their hand from the lens.
6. As the face is revealed, sharply reduce the static and fade the rotor noise beneath the voice.

### Person 1

> “Sorry about that. But that is exactly how a critical command disappears—not because communication stops, but because noise hides the words that matter.”

### Animation

Show the reconstructed command:

> `ALPHA TEAM, HOLD POSITION. MOVE LEFT.`

Emphasize `HOLD POSITION` and `LEFT`.

---

## 0:12–1:02 — Person 1: problem, requirements, initial idea and engineering journey

### Camera

Person 1 remains visible, framed slightly left so graphics appear on the right.

### Person 1

> “SIH Problem Statement 26052 is not asking for ordinary background-noise removal. The system must handle stationary engine rumble, changing rotor and wind noise, and sudden impulsive events—while keeping speech intelligible, causal and fast enough for embedded hardware.
>
> When we selected it, we did not begin by asking which AI model to use. We asked: can we improve the audio path without replacing the complete communication system?
>
> That became VoxShield—an offline inline audio optimizer between microphone capture and communication output. Our design priorities were clear: no cloud dependency, low and bounded latency, continued audio during failure, and evidence that important speech is preserved rather than merely made quieter.
>
> We first studied adaptive cancellation, then tested GTCRN, UL-UNAS fusion and several dual-channel architectures. Every candidate faced the same speech-quality, preservation and real-time gates. Models that failed were rejected. Our current v15 model is the result of failure-driven refinement—not simply more epochs.”

### Animation

Build this sequence beside Person 1:

```text
Existing microphone → VoxShield → Communication output

GTCRN → UL-UNAS → Fusion experiments → Dual-channel v15
```

Briefly show the four engineering constraints around the inline block:

```text
OFFLINE · CAUSAL · FAIL-SAFE · EDGE DEPLOYABLE
```

Display a small caption:

> `PROMOTION BASED ON UNCHANGED EVALUATION GATES`

### Handoff

Person 1 looks toward the right edge of the frame:

> “To show what we actually built and measured, over to [Person 2 name].”

A red noisy waveform exits Person 1’s frame and enters Person 2’s frame.

---

## 1:02–1:29 — Person 2: technical architecture

### Camera

Person 2 is visible beside a simple architecture diagram. Do not display a dense PPT slide.

### Person 2

> “VoxShield uses two signal roles. A primary channel carries speech with noise, while a reference channel observes the environment.
>
> A causal STFT feeds a 1.14-million-parameter recurrent network that predicts a complex mask and a five-tap deep filter. It advances every 16 milliseconds, preserves streaming state and exports to ONNX for local execution.
>
> If runtime health becomes unsafe, the system returns aligned dry audio instead of failing silently.”

### Animation

Construct the diagram one block at a time:

```text
Primary speech + noise ─┐
                       ├→ Causal STFT → Recurrent deep filter → Runtime guard → Output
Environmental reference ┘
```

Show four small fact cards:

- `16 kHz`
- `32 ms window / 16 ms hop`
- `1,141,389 parameters`
- `Stateful ONNX`

---

## 1:29–2:05 — Person 2: real demonstration

### Opening physical shot

Show the real equipment together:

- JBL device
- Laptop
- Phone/noise source
- Raspberry Pi 5

### Person 2

> “This demonstration uses the hardware available to us. The JBL microphone supplies speech, the laptop microphone captures environmental noise, and this phone reproduces the test noise.”

Show the caption:

> `LIVE CONTROLLED WINDOWS ENGINEERING DEMO`

Person 2 continues:

> “Because these are separate Windows endpoints, the demo creates one repeatable noisy test input by electronically combining JBL speech with a bounded thirty-percent reference signal. Dry and enhanced modes therefore receive the same input. This is a disclosed engineering demonstration—not field capture.”

### Dashboard action

Use a split screen: Person 2 and devices on the left, dashboard on the right.

1. Show both input waveforms moving differently.
2. Confirm the banner reads `CONTROLLED ELECTRONIC MIX`.
3. Select **Dry input**.
4. Show `0%` effective wet mix.
5. Person 2 says:

> “Alpha team, hold position. Move left on command.”

6. Allow approximately three seconds with no narration.
7. Select **Enhance**.
8. Show `100%` effective wet mix.
9. Repeat exactly:

> “Alpha team, hold position. Move left on command.”

10. Again allow approximately three seconds with no narration.
11. Briefly toggle emergency bypass to show immediate return to the dry noisy input, then turn it off.

Person 2 concludes:

> “The dashboard reports real waveforms, runtime state, inference timing and audio faults. Objective quality scores are measured separately because live audio has no clean target.”

---

## 2:05–2:27 — Person 2: controlled evaluation evidence

### Visual

Show one genuine audit example with three aligned controls:

```text
Noisy input | Enhanced v15 | Clean target
```

Caption:

> `CONTROLLED PAIRED AUDIT · 50 CLIPS PER SET`

### Person 2

> “Using paired clips with known clean targets, the broad audit reached 30.48 dB output SNR, 0.938 STOI and 3.94 PESQ, with zero measured speech deletion.
>
> The military audit reached 25.15 dB output SNR and 0.915 STOI. Mean quality improved strongly, while difficult per-clip cases remain visible for field tuning.”

### Results graphic

| Audit | Output SNR | Improvement | STOI | PESQ |
|---|---:|---:|---:|---:|
| Broad, n=50 | 30.48 dB | +10.07 dB | 0.938 | 3.94 |
| Military, n=50 | 25.15 dB | +14.05 dB | 0.915 | 3.63 |

Use green for the broad passed gate and amber for remaining military reliability work.

---

## 2:27–2:46 — Person 2: Raspberry Pi 5 proof

### Cinematic hardware shots

1. Power cable connects.
2. Pi LED turns on.
3. Cooling fan starts.
4. Cut to the Pi terminal.
5. Show exact v15 checkpoint and ONNX filenames.
6. Show the new v15 benchmark and SHA-256 hashes.

Caption:

> `LOCAL RASPBERRY PI 5 INFERENCE BENCHMARK`

### Person 2

> “The live demonstration runs on the laptop. Separately, the exact same v15 ONNX artifact runs locally on this Raspberry Pi 5 without a cloud connection. The benchmark measures model and callback timing, memory, overruns and dropped blocks.”

If the exact v15 Pi benchmark has been completed, add:

> “It measured [MEAN] milliseconds mean inference and [P99] milliseconds full-pipeline p99, with [OVERRUNS] overruns and [DROPS] dropped callbacks.”

Do not use the earlier v10 timing as a v15 result.

### Return handoff

Person 2 looks toward the left:

> “The AI and edge-runtime path is working. [Person 1 name], what comes next?”

The clean green waveform travels back toward Person 1.

---

## 2:46–3:23 — Person 1: achieved work, deployment value, roadmap and final statement

### Person 1

> “What we have today is more than a trained checkpoint. We built the data pipeline, a causal dual-channel engine, stateful ONNX deployment, paired quality audits, runtime health monitoring, a live operator dashboard and a Raspberry Pi execution path.
>
> Its intended value is retrofit: improve the audio path of existing communication equipment, process locally without sending mission audio to the cloud, and preserve communication even when enhancement becomes unavailable.
>
> We are also clear about what remains. Next, we replace the separate Windows endpoints with a single-clock stereo ADC and two purpose-positioned microphones. Then we measure physical loopback latency, collect target-device recordings, attack the remaining military hard cases, and conduct real acoustic and long-duration thermal tests.
>
> We are not claiming completed battlefield hardware. We are presenting a validated AI and edge-runtime foundation, the evidence behind it, and a clear path to synchronized deployment.
>
> We are Team VoxShield. When the environment becomes louder, the command must remain clear.”

Slowly move to a closer crop for the final sentence.

---

## 3:23 onward — End card for the recording master

Cut to the final card:

```text
VOXSHIELD
SIH 2026 · PS 26052

HEAR THE EVIDENCE
VERIFY THE RESULTS
VIEW THE ROADMAP

[QR CODE]   [SHORT URL]
```

For the final competition cut, introduce the QR unobtrusively during Person 1's final paragraph and retain the full end card for at least two seconds.

---

## Recording checklist

### Person 1

- Record the opening with the hand physically covering the lens.
- Leave two seconds before and after every take.
- Record the opening and closing at least three times.
- Frame slightly left to leave space for graphics.
- Look right during the handoff.

### Person 2

- Frame slightly right to receive the incoming waveform from the left.
- Record the architecture dialogue separately from the live demonstration.
- Record a clean screen capture of the dashboard.
- Keep phone position and volume marked and unchanged.
- Record Dry and Enhance commands using identical wording and speaking distance.
- Film the physical Pi and capture the terminal separately.

### Editor

- Use one navy/green visual system.
- Use red only for noise, failures and the unprocessed path.
- Keep Person 1 or Person 2 visible for most explanations.
- Remove all music during A/B playback.
- Label `LIVE DEMO`, `CONTROLLED AUDIT`, `PI BENCHMARK` and `TARGET HARDWARE` distinctly.
- Do not animate metrics counting upward.
- Do not use AI battlefield imagery as evidence.
- Maintain subtitles and readable text on mobile screens.

## Optional cuts if the edit exceeds three minutes

The expanded script intentionally creates a complete recording master. To make the strict three-minute cut, remove these lines in order:

1. From Person 1's opening, remove: “Our design priorities were clear: no cloud dependency, low and bounded latency, continued audio during failure, and evidence that important speech is preserved rather than merely made quieter.” Keep the four constraints visually.
2. From Person 2, remove: “It advances every 16 milliseconds, preserves streaming state and exports to ONNX for local execution.” Keep those facts on screen.
3. Shorten the hardware disclosure to: “This controlled demo electronically combines JBL speech with a bounded reference signal so Dry and Enhance receive the same input.” Keep the complete disclosure on screen.
4. Shorten the military result to: “The military audit improved strongly but retains difficult per-clip cases.”
5. From Person 1's ending, remove: “Its intended value is retrofit: improve the audio path of existing communication equipment, process locally without sending mission audio to the cloud, and preserve communication even when enhancement becomes unavailable.” Keep `RETROFIT · OFFLINE · FAIL-SAFE` visually.
6. Shorten the roadmap sentence to: “Next, we build synchronized capture, measure physical latency and validate on target-device recordings.”

Never remove:

- The controlled electronic-mix disclosure
- The distinction between laptop demo and Pi benchmark
- The statement that synchronized hardware is the next milestone
- The exact model/version shown in the Pi terminal
