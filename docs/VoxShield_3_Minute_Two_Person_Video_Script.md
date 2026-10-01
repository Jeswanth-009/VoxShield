# VoxShield: Three-Minute, Two-Person SIH Video Script

**Recording-master duration:** approximately 3 minutes 20 seconds to 3 minutes 40 seconds  
**Final edited target:** 2 minutes 50 seconds to 3 minutes  
**Format:** Person 1 opens and closes; Person 2 explains the technical work and performs the demonstration. The two people may record in different locations.

**Style balance:** approximately 40% cinematic storytelling and transitions, 60% calm technical explanation and evidence.

## Recording rules

- Record both speakers horizontally at 1080p, 30 fps.
- Use the same font, lower-third style and navy/green colour palette throughout.
- Keep background music very low and remove it completely during A/B audio playback.
- Add subtitles for every spoken line.
- Use real hardware and real screenshots. Do not use cinematic battlefield footage as proof.
- Label each segment accurately: `CONCEPT`, `LIVE WINDOWS DEMO`, `CONTROLLED AUDIT`, `PI 5 BENCHMARK`, or `TARGET HARDWARE`.
- Person 1 should look toward the right side of the frame during the handoff. Person 2 should begin looking slightly toward the left. Reverse this for the return handoff. This makes two separately recorded locations feel connected.
- Speak naturally at approximately 125–135 words per minute. Do not rush the numerical results.

---

## 0:00–0:15 — Cinematic cold open

**Visual**

The screen is completely black because Person 1's palm covers the camera lens. Begin with low radio static. After one second, add distant rotor/engine noise and a partially masked command:

> “Alpha team… hold… move left…”

For the first two seconds show only faint text:

> SIGNAL LOST IN NOISE

At approximately 0:04, Person 1 slowly removes their hand from the lens. As the face is revealed, reduce the static sharply but leave a faint rotor bed. Allow the exposure to settle naturally for half a second.

**Person 1 dialogue**

> “Sorry about that.”

Brief pause and direct eye contact.

> “But that is exactly how a critical command disappears—not because communication stops, but because noise hides the words that matter.”

Display the reconstructed command briefly:

> ALPHA TEAM, **HOLD POSITION**. MOVE **LEFT**.

---

## 0:15–0:50 — Person 1: problem and original idea

**Shot**

Medium shot of Person 1. Use a clean background. Place a small lower third:

> PERSON 1 NAME · TEAM VOXSHIELD

**Person 1 dialogue**

> “When we selected this problem statement, we did not begin by asking which AI model to use. We asked: why replace existing communication equipment if we can improve its audio path? That became VoxShield—an offline inline optimizer between microphone capture and communication output.
>
> We explored adaptive cancellation, GTCRN, UL-UNAS fusion and several dual-channel models. Each candidate faced unchanged quality and real-time gates. v15 is the result of failure-driven refinement—not simply more training.”

**Supporting visuals while Person 1 speaks**

Use a simple animated strip, not a dense slide:

```text
Masked command
      ↓
Inline optimizer concept
      ↓
GTCRN / UL-UNAS / fusion experiments
      ↓
Failure-driven dual-channel v15
```

Person 1 remains visible while the signal-chain and model-history cards animate into the empty side of the frame. Near the end, Person 1 looks toward the right of frame.

**Person 1 handoff**

> “To show what we actually built and measured, over to [Person 2 name].”

---

## 0:50–1:17 — Person 2: architecture

**Transition**

Use a fast waveform travelling from the right edge of Person 1’s shot into the left edge of Person 2’s shot.

**Shot**

Person 2 beside the laptop, JBL device, phone and Raspberry Pi 5. Lower third:

> PERSON 2 NAME · AI AND EDGE IMPLEMENTATION

**Person 2 dialogue**

> “A primary channel carries speech with noise; a reference channel observes the environment. A causal STFT feeds a 1.14-million-parameter recurrent network that predicts a complex mask and five-tap deep filter. It advances every 16 milliseconds, preserves streaming state, exports to ONNX and falls back to aligned dry audio if runtime health becomes unsafe.”

**On-screen architecture**

```text
Primary speech + noise ─┐
                       ├→ STFT → recurrent deep filter → runtime guard → output
Environmental reference ┘
```

Small fact cards:

- 16 kHz
- 32 ms window / 16 ms hop
- 1,141,389 parameters
- Stateful ONNX

---

## 1:17–1:55 — Person 2: honest live laptop demonstration

**Caption throughout this segment**

> LIVE WINDOWS DUAL-ENDPOINT ENGINEERING DEMO

**Shot**

Start with a wide shot showing the physical equipment, then cut to screen capture of the dashboard.

**Person 2 dialogue**

> “This uses our available hardware: the JBL microphone for speech, the laptop microphone array for environmental reference, and this phone for noise. They are separate Windows endpoints—not the proposed synchronized production capture.”

**Action**

1. Keep the phone at a marked, fixed position near the laptop microphone.
2. Show that the JBL and environmental waveforms move independently.
3. Select `DRY` operating mode for the unprocessed comparison. Use this explicit mode rather than relying only on the separate operator-bypass safety switch.
4. Say: “Alpha team, hold position. Move left on command.”
5. Select `ENHANCED` operating mode.
6. Repeat the exact phrase at the same speaking position and phone volume.

**Person 2 dialogue after the comparison**

> “The dashboard shows real waveforms, runtime state, timing and audio faults. Objective scores are measured separately because live audio has no clean target.”

Do not narrate over the two audio examples. Allow approximately three seconds for each result to be heard.

---

## 1:55–2:19 — Person 2: controlled audit evidence

**Caption**

> CONTROLLED PAIRED AUDIT · 50 CLIPS PER SET

**Visual**

Display one real record with three play controls:

- Noisy
- Enhanced v15
- Clean target

Then display the two-row results table.

**Person 2 dialogue**

> “Using paired clips with clean targets, the 50-clip broad audit reached 30.48 dB output SNR, 0.938 STOI and 3.94 PESQ, with zero measured speech deletion. The military audit reached 25.15 dB and 0.915 STOI, while still exposing hard cases for field tuning.”

**Results table**

| Audit | Output SNR | Improvement | STOI | PESQ |
|---|---:|---:|---:|---:|
| Broad, n=50 | 30.48 dB | +10.07 dB | 0.938 | 3.94 |
| Military, n=50 | 25.15 dB | +14.05 dB | 0.915 | 3.63 |

---

## 2:19–2:39 — Person 2: Raspberry Pi proof

**Caption**

> LOCAL RASPBERRY PI 5 INFERENCE BENCHMARK

**Visual**

Show the real Pi first, then a close screen recording of its terminal. The terminal must show:

- `checkpoints_deep_filter_v15_hard_failure_repair/best.pt`
- `artifacts/voxshield-v15-hard-failure-repair-final.onnx`
- Exact v15 benchmark output
- Zero overruns/drops only if the new benchmark actually reports them
- SHA-256 hashes

**Person 2 dialogue**

> “Separately, the exact v15 ONNX artifact runs locally on this Raspberry Pi 5 without cloud dependency. The benchmark measures timing, memory, overruns and dropped blocks. The JBL demo runs on the laptop; this segment proves Pi deployment using the same model artifact.”

If the final v15 benchmark has been completed, add one sentence using the newly measured mean and p99 values. Do not reuse v10 timing and call it v15.

At 2:30 Person 2 looks toward the left of frame.

**Person 2 return handoff**

> “The software path is working. [Person 1 name], what comes next?”

---

## 2:39–3:00 — Person 1: impact, roadmap and closing

**Transition**

Reverse the waveform transition used during the first handoff.

**Person 1 dialogue**

> “Next, we replace the Windows endpoints with a single-clock stereo ADC and two purpose-positioned microphones, then measure physical loopback latency and conduct real acoustic trials.
>
> VoxShield is an auditable offline pipeline with reference-aware enhancement, ONNX parity, runtime monitoring and fail-safe continuity. We are presenting a validated AI and edge-runtime foundation—not completed battlefield hardware—with a testable deployment path.
>
> We are Team VoxShield. Our goal is simple: when the environment becomes louder, the command must remain clear.”

**Closing visual**

Show:

- VoxShield logo
- `PS 26052`
- QR code
- Short evidence-room URL
- Text: `HEAR THE EVIDENCE · VERIFY THE RESULTS · VIEW THE ROADMAP`

Hold the final frame for at least three seconds so the QR can be scanned.

---

## Timing budget

| Segment | Duration |
|---|---:|
| Cinematic cold open | 15 s |
| Person 1 opening | 35 s |
| Person 2 architecture | 27 s |
| Live demonstration | 38 s |
| Controlled evidence | 24 s |
| Pi benchmark | 20 s |
| Person 1 closing | 21 s |
| **Total** | **180 s / 3:00** |

## If the video exceeds three minutes

Cut in this order:

1. Remove “wind” from Person 1’s first sentence.
2. Shorten the model-history line to “We tested several compact causal architectures.”
3. Remove the architecture fact-card narration; keep the cards visually.
4. Reduce the controlled-audit narration to the broad results plus one military sentence.
5. Never cut the honest hardware disclaimer, Pi version identification, or final status statement.
