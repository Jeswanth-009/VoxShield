# VoxShield SIH 26052 PPT Exact Build Manual

Team name: Team@  
Problem Statement ID: 26052  
Deck length: 6 slides only  
Purpose: Make the deck look like a serious defence communication prototype, not a generic AI project.

This manual tells you exactly how I would rebuild the PPT after seeing your current slide and after studying the finalist reference decks. The main correction is this: your current visual style is powerful, but it looks too cinematic, too crowded, and slightly overclaimed. We need to keep the energy, but make it look more factual, engineered, and judge-safe.

---

## 0. The core deck strategy

### What the judge should think in 5 seconds

The judge should not think:

- “This is another AI noise removal idea.”
- “This looks generated.”
- “They are claiming too much.”
- “Where is the real proof?”

The judge should think:

- “They understood the defence communication problem.”
- “They built a real pipeline, not just a concept.”
- “They know their hardware limitation and have a realistic next step.”
- “The deck looks technically serious.”
- “This team can become one of the top 5 if mentored.”

### The story in one line

VoxShield is a local AI speech enhancement engine that keeps commands intelligible in defence noise, proves real-time edge feasibility on Raspberry Pi 5, and moves next into synchronized dual-microphone hardware validation.

### The honest positioning

Use this wording everywhere:

> AI speech enhancement for noisy defence communication

Avoid this as the main claim:

> Full physical adaptive noise cancellation headset

Why: your model can enhance speech in controlled and synthetic/recorded mixtures. True physical ANC needs synchronized microphone hardware. If judges catch that gap, they may lose trust. So we frame it as an AI engine with a clear hardware roadmap.

---

## 1. What is wrong with the current slide

Your current slide is visually strong, but it has six problems.

### Problem 1: Too many claims in one slide

The slide tries to be:

- problem slide
- solution slide
- architecture slide
- metrics slide
- uniqueness slide

That makes it look impressive but hard to judge quickly. In SIH, each slide should have one job.

### Problem 2: The dB ranges look dangerous

Examples from the current slide:

- 90 to 110 dB
- 100 to 130 dB
- 120 to 180 dB

These numbers may be technically possible in some environments, but unless you cite them and explain distance/measurement context, they look exaggerated. Judges may ask, “Where did you measure this?” Do not give them that opening.

Better:

- Engine and vehicle noise
- Rotor and wind noise
- Blast and impulse noise
- Movement and ambient noise

If you want numbers, say:

> Representative high-noise conditions, not field-measured SPL

But ideally do not show dB ranges on slide 2.

### Problem 3: Some model labels look decorative

Current labels like:

- GTCRN-based
- 64 ERB bands
- CRM

Only use these if they exactly match your model. If not, they make the slide feel fake. Use labels you can defend:

- Dual-channel streaming deep filter
- ONNX runtime
- Speech retention loss
- Hard failure repair set
- Pi 5 latency benchmark

### Problem 4: Too many fake waveforms

Waveforms look nice, but too many repeated waveforms make the slide look AI-generated. Use waveform visuals only where they explain before and after.

Rule:

- Maximum 2 large waveform pairs in the whole deck.
- Maximum 1 waveform pair per slide.
- If a waveform is decorative, remove it.

### Problem 5: The title is too long

Current:

> VoxShield - Mission Communication Engine

This is okay, but the full line plus subtitle plus hero image creates a lot of top weight.

Better:

> VoxShield

Subtitle:

> Mission communication engine for noisy defence audio

### Problem 6: The slide looks like a product ad, not a proof deck

The finalist decks use attractive visuals, but they also show evidence: workflows, architecture, feasibility, cost, references, prototype progress. Your slide needs to look less like a poster and more like a designed proof board.

---

## 2. The visual direction to follow

### Design personality

Use this personality:

> Tactical command dashboard plus engineering evidence board

Not:

> Sci-fi movie poster

Not:

> College project template

Not:

> ChatGPT-generated cyber dashboard

### Color system

Use only these colors:

- Background navy: `#07111F`
- Card navy: `#0B1F33`
- Border cyan: `#22D3EE`
- Signal green: `#23D18B`
- Warning amber: `#F59E0B`
- Risk red: `#EF4444`
- Text white: `#FFFFFF`
- Muted text: `#CBD5E1`
- Divider grey: `#334155`

Do not use too many neon colors. Green should mean output/proof. Amber should mean risk/limitation. Red should only mean noisy input or threat.

### Font system

Use the template font if it is fixed. Otherwise:

- Title: Aptos Display Bold or Bahnschrift Bold
- Body: Aptos, Calibri, or Segoe UI
- Numbers: Bahnschrift SemiBold or Aptos Display

Minimum sizes:

- Slide title: 30 to 36 pt
- Section title: 16 to 20 pt
- Card heading: 13 to 16 pt
- Body text: 10.5 to 12 pt
- Tiny source/caveat: 7.5 to 8.5 pt

If you need 8 pt for normal content, the slide has too much content.

### Shape style

Use:

- Rounded rectangles with 1.5 pt border
- Semi-transparent dark fills
- No heavy shadows except on the main engine block
- Thin divider lines
- Icons in one consistent style

Avoid:

- Too many glowing borders
- Too many nested boxes
- Repeating the same waveform everywhere
- Random 3D icons
- Very sharp neon effects

---

## 3. The 6-slide story

The six slides should not be six independent posters. They should form one flow.

1. Title page  
   Show the identity and mission feel.

2. Idea title and proposed solution  
   Show the problem-to-solution product concept.

3. Technical approach  
   Show the real engineering pipeline.

4. Feasibility and viability  
   Show proof, edge readiness, and risk mitigation.

5. Impact and benefits  
   Show why it matters in a mission communication moment.

6. Research and references  
   Show the evidence board and next hardware phase.

---

# Slide 1: Title page

## Goal

Make the first slide feel like a serious defence communication system, but keep it clean. Do not overload it.

## Inspiration from finalist decks

Use the polished title confidence from Team Kingpin and EarthBenders: strong identity, one visual, clean team/PS metadata.

## Layout

Use a 3-zone layout:

### Zone A: Official template header

Keep:

- Ministry logo
- SIH logo
- AICTE logo

Do not move them unless the template already allows it.

### Zone B: Main title area

Left 55 percent of slide.

Text:

```text
VoxShield
Mission communication engine for noisy defence audio
```

Under it, add a small line:

```text
AI speech enhancement with edge-ready real-time inference
```

Then metadata:

```text
Problem Statement ID: 26052
Theme: Defence and National Security
PS Category: Hardware
Team Name: Team@
```

### Zone C: Hero visual

Right 45 percent.

Use one of these:

Option 1, best:

- Soldier/radio operator silhouette
- Abstract waveform overlay
- Dark navy background
- No guns, no violence, no text inside image

Option 2, if no image:

- A clean dark dashboard mockup with one waveform
- Red noisy waveform on left becoming green waveform on right

## Exact design

Background:

- Use dark navy overlay below the official white SIH header.
- Add a subtle grid or faint waveform, not too visible.

Title:

- `Vox` in white
- `Shield` in green
- Do not make the green too bright.

Proof badges at bottom:

Use 3 small badges:

```text
ONNX export passed
Pi 5 real-time benchmark
Broad strict gate passed
```

Do not include all metrics on title slide.

## What to remove

- No long paragraph.
- No detailed architecture.
- No dB values.
- No “adaptive ANC headset fully ready” claim.

## Final slide 1 look

It should feel like a launch screen:

> “This is a real system name, with evidence behind it.”

---

# Slide 2: Idea title and proposed solution

## Goal

Explain the product in one glance.

This is where your current slide is closest, but it is too crowded. We will rebuild it into a cleaner product concept slide.

## Slide title

Use:

```text
Idea title and proposed solution
```

Inside the slide, use the product title:

```text
VoxShield Mission Communication Engine
```

Subtitle:

```text
Local AI enhancement for clear commands under mission noise
```

## Layout

Use a 3-part horizontal flow.

```text
Mission noise problem  ->  VoxShield engine  ->  Protected speech output
```

### Left panel: Mission noise problem

Width: 28 percent  
Purpose: show threat categories, not detailed proof.

Use only 3 rows:

1. Vehicles and engines
2. Helicopter and wind
3. Gunfire and blast impulse

Do not use 4 or 5 rows.

Each row should have:

- simple icon
- one noise label
- one short effect label

Example:

```text
Vehicles and engines
Low-frequency masking
```

```text
Helicopter and wind
Rotor modulation
```

```text
Gunfire and blast impulse
Sudden high-energy peaks
```

Remove the dB badges.

### Center panel: VoxShield engine

Width: 44 percent  
Purpose: show the core idea.

Main visual:

Large dark rounded rectangle:

```text
VoxShield AI Engine
```

Inside it, show 4 stacked internal modules:

```text
1. Dual-channel input
2. Streaming deep filter
3. Speech retention guard
4. Telemetry export
```

Use simple icons:

- mic pair
- chip
- shield/check
- dashboard

Do not use GTCRN/CRM/ERB unless exact.

Input line:

```text
Noisy speech + reference noise
```

Output line:

```text
Enhanced speech + signal health
```

### Right panel: Output proof

Width: 28 percent  
Purpose: show tangible outputs.

Use 3 cards:

Card 1:

```text
Enhanced speech
Preserves command content
```

Card 2:

```text
Live dashboard
Latency, levels, bypass state
```

Card 3:

```text
Edge-ready runtime
Pi 5 mean latency: 5.33 ms
```

## Bottom uniqueness strip

Keep a bottom strip, but make it shorter than your current one.

Four mini cards:

```text
Mission-noise trained
Uses defence-like noise categories and hard-case repair
```

```text
Speech-preserving
0.0 speech deletion in reported audits
```

```text
Edge-ready
ONNX runtime validated, Pi 5 benchmark completed
```

```text
Transparent
Dashboard shows latency, bypass and health
```

## Exact look

Left panel:

- red/amber accent
- no exact dB values
- no repeated large waveforms

Center panel:

- largest visual on slide
- green border
- one red input waveform, one green output waveform

Right panel:

- green proof cards
- numbers only where verified

Bottom strip:

- amber heading: `What makes VoxShield different`
- four cards with icon plus 1 line each

## Text to paste

```text
VoxShield Mission Communication Engine
Local AI enhancement for clear commands under mission noise
```

```text
Mission noise problem
Vehicles and engines: low-frequency masking
Helicopter and wind: rotor modulation
Gunfire and blast impulse: sudden high-energy peaks
```

```text
VoxShield AI Engine
Dual-channel input
Streaming deep filter
Speech retention guard
Telemetry export
```

```text
Outputs
Enhanced speech: preserves command content
Live dashboard: latency, levels, bypass state
Edge-ready runtime: Pi 5 mean latency 5.33 ms
```

## What your current slide should change

Delete:

- dB badges
- infantry row
- repeated waveforms in every row
- GTCRN, CRM, 64 ERB labels if not exact
- cost comparison to INVISIO unless you have a source

Keep:

- dark tactical visual style
- centre AI engine
- bottom uniqueness idea
- Pi 5 latency proof
- speech deletion proof

## Final slide 2 feel

It should feel like:

> “This is the product concept, and I understand what it does.”

Not:

> “This slide is trying to prove everything at once.”

---

# Slide 3: Technical approach

## Goal

This is the real engineering slide. It should make judges feel that you built a complete pipeline.

## Inspiration from finalist decks

CoalWorks and EarthBenders use dense architecture maps. Their density works because the blocks are organized. Do the same.

## Slide title

```text
Technical approach
```

Optional subtitle:

```text
Data, model, runtime and edge deployment pipeline
```

## Layout

Use two layers:

1. Training pipeline on top
2. Runtime pipeline below

Do not make this slide look like a dashboard. Make it look like a system architecture diagram.

## Top layer: Training pipeline

Height: top 32 percent.

Use 5 connected blocks:

```text
Datasets
VCTK, DNS, MAD, ESC-50, AudioSet, RIRS, user recordings
```

```text
Mixture builder
SNR variation, reverb, impulse noise, nonstationary noise
```

```text
Training
Dual-channel deep filter
```

```text
Hard-case repair
Failure clips, vehicle, helicopter, impulse cases
```

```text
Validation
SNR, SI-SNR, STOI, PESQ, speech deletion
```

Use arrows, but not too many. One clean line across the top.

## Bottom layer: Runtime pipeline

Height: middle 45 percent.

Flow:

```text
Primary mic
Reference mic
        ↓
Frame buffer, 16 kHz, 16 ms frame
        ↓
ONNX streaming model
        ↓
Enhanced audio
        ↓
Dashboard and evidence report
```

Show the two inputs entering the model. This is important because it aligns with the PS requirement and your actual model needs reference audio.

## Right proof rail

Right side, vertical 20 percent width.

Use 4 metric cards:

```text
1.1M
model parameters
```

```text
5.33 ms
Pi 5 mean latency
```

```text
0.0
speech deletion rate
```

```text
ONNX
export parity passed
```

Do not add too many numbers.

## Bottom caveat strip

Small amber strip at bottom:

```text
Hardware note: laptop and Bluetooth demos do not provide a synchronized reference channel. Final field validation needs a raw dual-microphone rig.
```

This honesty is a strength. It shows maturity.

## Exact visual style

- Data blocks: blue/cyan
- Model block: green
- Validation block: purple or cyan
- Hardware caveat: amber
- Use icons very small, not decorative

## Text to paste

```text
Training pipeline
Datasets -> mixture builder -> training -> hard-case repair -> validation
```

```text
Runtime pipeline
Primary mic and reference mic feed a streaming ONNX model, producing enhanced speech and dashboard telemetry.
```

```text
Validation metrics
SNR, SI-SNR, STOI, PESQ, speech deletion, active level error, latency
```

## What not to do

- Do not use terminal screenshots.
- Do not write a long paragraph about AI.
- Do not put all dataset counts on the slide.
- Do not hide the need for synchronized microphones.

## Final slide 3 feel

It should feel like:

> “This team built the technical pipeline and knows the real deployment requirement.”

---

# Slide 4: Feasibility and viability

## Goal

Convince judges that the project can work in the real world if selected.

This slide should not pretend everything is finished. It should show:

- what is validated now
- what is risky
- how you will fix the risk
- why it is feasible

## Inspiration from finalist decks

Mindsmiths used feasibility and ROI structure. Telhan Sathi showed risks and mitigation. Use that pattern.

## Slide title

```text
Feasibility and viability
```

Subtitle:

```text
Validated AI engine with a clear hardware path
```

## Layout

Use 4 sections:

1. Proof cards at top
2. Prototype readiness ladder on left
3. Hardware path diagram in center/right
4. Risk and mitigation table at bottom

## Top proof cards

Use 4 cards across the top.

Card 1:

```text
Broad strict gate passed
v15 evaluation passed all broad checks
```

Card 2:

```text
Edge latency proven
Pi 5 mean latency: 5.33 ms for 16 ms frame
```

Card 3:

```text
Speech retained
0.0 speech deletion in reported audits
```

Card 4:

```text
ONNX deployable
Export parity validation passed
```

## Prototype readiness ladder

Left side.

Use a vertical ladder with 5 steps:

```text
1. Offline model validation
2. ONNX export
3. Pi 5 benchmark
4. Controlled demo replay
5. Dual-mic field validation
```

Mark steps 1 to 4 as green or mostly complete.

Mark step 5 as amber:

```text
Next phase
```

## Hardware path diagram

Center/right.

Show:

```text
Primary mic near speaker mouth
Reference mic facing environment noise
USB audio interface
Raspberry Pi 5
Headset/radio output
Dashboard
```

This diagram is more important than a fancy image. It explains why laptop/Bluetooth demo is not enough.

## Risk and mitigation table

Bottom section.

Use 3 rows only.

| Risk | Why it matters | Mitigation |
|---|---|---|
| Bluetooth and laptop mics are not synchronized | Live cancellation depends on timing | Use raw USB dual-mic input |
| Real mission noise differs from synthetic mixtures | Model may fail on unseen noise | Add field recordings and hard-case repair |
| Aggressive suppression can damage speech | Commands must stay intelligible | Use speech deletion and STOI gates |

## Text to paste

```text
Validated now
AI engine, ONNX export, Pi 5 benchmark, broad strict gate
```

```text
Next hardware phase
Synchronized dual-microphone rig with raw audio capture
```

```text
Viability position
The current prototype validates the AI engine and edge runtime. The next build validates physical microphone geometry.
```

## What not to do

- Do not say “ready for battlefield deployment.”
- Do not hide Bluetooth/laptop limitation.
- Do not use only green success cards.
- Do not show risk as failure. Show risk as engineering plan.

## Final slide 4 feel

It should feel like:

> “They are honest, technically aware, and feasible.”

---

# Slide 5: Impact and benefits

## Goal

Make the technology emotionally meaningful.

This is where the human mission moment comes in.

## Inspiration from finalist decks

Finalist impact slides usually show who benefits, what changes, and why it matters. Do not make it generic.

## Slide title

```text
Impact and benefits
```

Subtitle:

```text
Clearer local communication when noise can hide a command
```

## Layout

Use a before-and-after communication scene.

### Left half: Before

Label:

```text
Before VoxShield
```

Show:

- red/amber noisy waveform or spectrogram
- command text partially masked

Example:

```text
“Hold position... left flank...”
```

Caption:

```text
Vehicle, rotor and impulse noise can mask key words.
```

### Right half: After

Label:

```text
After VoxShield
```

Show:

- green cleaner waveform or spectrogram
- command text clear

Example:

```text
“Hold position. Left flank clear.”
```

Caption:

```text
Local enhancement improves intelligibility while preserving speech content.
```

## Bottom benefit row

Use 4 benefit cards:

```text
Defence communication
Improves command clarity in high-noise settings
```

```text
Emergency response
Useful for rescue teams, sirens and crowd noise
```

```text
Industrial safety
Supports headset communication near machines
```

```text
Edge operation
Runs locally without cloud dependency
```

## One metric card

Place one small metric summary, not too large:

```text
v15 broad audit
SNR 30.48 dB
STOI 0.938
PESQ 3.94
```

Do not put too many metric cards on this emotional slide.

## Visual style

- Use a strong split screen.
- Left side red/amber, right side green.
- Use human context but not dramatic war imagery.
- If using a soldier/radio image, keep it subtle and in background.

## Text to paste

```text
Before VoxShield
Noise masks important command words.
```

```text
After VoxShield
Speech becomes clearer while command content is preserved.
```

```text
Primary benefit
More intelligible local communication in high-noise environments.
```

## What not to do

- Do not write generic impact like “saves lives” unless carefully worded.
- Do not say “removes all noise.”
- Do not make this a dataset slide.
- Do not show too many beneficiaries.

## Final slide 5 feel

It should feel like:

> “This matters because one hidden word can change a mission decision.”

---

# Slide 6: Research and references

## Goal

End with evidence, not a boring bibliography.

This slide should look like a final evidence board.

## Inspiration from finalist decks

CoalWorks and EarthBenders use final slides to show references, proof, market/evidence, and future scope. Use that pattern.

## Slide title

```text
Research and references
```

Subtitle:

```text
Evidence base, validation artifacts and next hardware phase
```

## Layout

Use 4 quadrants.

### Quadrant 1: Data sources

Top left.

Use chips:

```text
VCTK
DNS Challenge
MAD military audio
ESC-50
AudioSet targeted
RIRS NOISES
User recordings
```

Add one small line:

```text
Used for clean speech, environmental noise, impulse noise, reverb and hard-case testing.
```

### Quadrant 2: Validation metrics

Top right.

Use metric chips:

```text
SNR
SI-SNR
STOI
PESQ
Speech deletion
Active level error
Latency
```

Add:

```text
Metrics cover noise reduction, intelligibility, speech preservation and runtime feasibility.
```

### Quadrant 3: Evidence artifacts

Bottom left.

List:

```text
v15 broad strict gate result
v15 military audit result
ONNX export parity report
Pi 5 verification report
Hard failure report
Saved audio examples
```

Use small file icons.

### Quadrant 4: Next phase

Bottom right.

Use roadmap:

```text
Dual USB mic rig
Raw synchronized capture
Field noise recordings
Headset/radio integration
Live dashboard demo
```

Add QR/demo placeholder if you have a video:

```text
Demo video / GitHub / evidence folder
```

## Important final line

Put this at the bottom:

```text
Current status: AI engine and edge runtime validated. Next phase: synchronized microphone hardware validation.
```

This line is powerful because it is honest and mature.

## What not to do

- Do not paste huge URLs.
- Do not make references as plain text only.
- Do not hide the next phase.
- Do not add claims that are not in evidence.

## Final slide 6 feel

It should feel like:

> “They have evidence. They know what remains. They are ready for SIH mentoring.”

---

## 4. Exact correction plan for your current slide

Your shown slide should become slide 2, but corrected.

### Delete these immediately

- Delete all red dB pills.
- Delete the infantry row.
- Delete repeated waveform rows or reduce them to small texture.
- Delete “GTCRN-based Subband Enhancement” unless it is exact.
- Delete “64 ERB bands, CRM” unless exact.
- Delete “Cost-effective indigenous solution targeted to significantly lower cost than imported systems” unless you have source and comparison.
- Delete “Adaptive Noise Cancellation” as the big pipeline label. Replace with “AI Speech Enhancement Pipeline.”

### Replace these labels

Replace:

```text
Adaptive Noise Cancellation & Speech Enhancement Pipeline
```

With:

```text
AI Speech Enhancement Pipeline
```

Replace:

```text
Noisy Input (SNR -5 dB)
```

With:

```text
Noisy mission audio
```

Replace:

```text
VoxShield Output (SNR 25+ dB)
```

With:

```text
Enhanced speech output
```

Use exact metrics only in proof card:

```text
v15 military average: SNR 25.15 dB, STOI 0.915, PESQ 3.63
```

or simpler:

```text
Military audit average: SNR 25.15 dB
```

### Replace the left panel

Use 3 rows:

```text
Vehicles and engines
Low-frequency masking
```

```text
Helicopter and wind
Rotor modulation
```

```text
Gunfire and blast impulse
Sudden high-energy peaks
```

### Replace the center pipeline

Use 4 boxes:

```text
Dual-channel input
Primary speech plus reference noise
```

```text
Streaming deep filter
Learns speech and noise separation
```

```text
Speech retention guard
Reduces deletion risk
```

```text
Telemetry
Shows latency, bypass and health
```

### Replace the right output panel

Use 3 proof cards:

```text
Enhanced speech
Preserves command content
```

```text
Real-time edge path
Pi 5 mean latency: 5.33 ms
```

```text
Model audit
0.0 speech deletion in reported audits
```

### Replace the bottom uniqueness row

Use:

```text
Mission-noise trained
Realistic noise categories and hard-case repair
```

```text
Edge deployable
ONNX runtime and Raspberry Pi 5 benchmark
```

```text
Speech preserving
STOI and speech deletion gates
```

```text
Transparent demo
Dashboard shows runtime health
```

---

## 5. What to say if judges ask hard questions

### If they ask: “Is this actual ANC?”

Say:

```text
The current prototype is an AI speech enhancement engine for communication clarity. Full physical ANC needs synchronized primary and reference microphones. We have designed the model and runtime for that path, and the next hardware phase is raw dual-mic validation.
```

### If they ask: “Why did the laptop/Bluetooth demo sound bad?”

Say:

```text
Bluetooth and laptop audio paths apply processing and do not guarantee synchronized reference capture. That makes them unsuitable for proving physical cancellation. We use controlled replay for demonstration and Pi 5 benchmarking for edge feasibility, then move to a raw USB dual-mic rig.
```

### If they ask: “What is actually proven?”

Say:

```text
We have proven ONNX export, CPU runtime, Pi 5 latency feasibility, and offline enhancement quality on curated noisy audits. The physical microphone geometry still needs hardware validation.
```

### If they ask: “Why should you be selected?”

Say:

```text
Because we are not only proposing an AI model. We already built the data pipeline, model export, evaluation gates, dashboard concept, Pi 5 benchmark and failure analysis. SIH support would help us complete the synchronized hardware prototype.
```

---

## 6. Video demo plan

You need a believable video because live Bluetooth is unreliable.

### Video structure

Duration: 90 to 120 seconds.

#### Scene 1: Problem, 10 seconds

Show:

- noisy defence-like audio
- waveform/spectrogram
- subtitle: “Command masked by rotor/vehicle noise”

Voiceover:

```text
In high-noise communication, the problem is not only loudness. The problem is losing command words.
```

#### Scene 2: VoxShield pipeline, 20 seconds

Show:

- your dashboard or mockup
- input waveform
- output waveform
- latency panel

Voiceover:

```text
VoxShield processes noisy speech locally through a streaming AI enhancement model and shows runtime health on a dashboard.
```

#### Scene 3: Before and after, 30 seconds

Play:

- noisy input
- enhanced output

Use captions:

```text
Noisy input
Enhanced output
```

Do not claim this is live physical ANC. Say:

```text
Controlled mission replay demo
```

#### Scene 4: Pi 5 proof, 15 seconds

Show:

- Raspberry Pi terminal or screen
- metric overlay: 5.33 ms mean latency

Voiceover:

```text
The same ONNX runtime was benchmarked on Raspberry Pi 5 with real-time frame latency.
```

#### Scene 5: Hardware roadmap, 15 seconds

Show:

- diagram of dual mic rig
- next phase labels

Voiceover:

```text
The next step is synchronized dual-microphone hardware validation for physical deployment.
```

### Video visual rule

Make the video look like an engineering demo, not a fake live miracle.

Use labels:

- Controlled replay
- ONNX inference
- Pi 5 benchmark
- Next hardware phase

This makes it believable.

---

## 7. Final PPT quality checklist

Before submission, check each slide:

### Slide 1

- Is the title clean?
- Is there only one hero visual?
- Are there only 3 proof badges?

### Slide 2

- Does the viewer understand the product in 5 seconds?
- Are dB claims removed?
- Is the pipeline truthful?

### Slide 3

- Does it show data, training, runtime and edge path?
- Does it show primary plus reference input?
- Is the hardware caveat visible?

### Slide 4

- Does it show proof and risk mitigation?
- Does it avoid overclaiming?
- Does it show the dual-mic next step?

### Slide 5

- Does it show a human communication moment?
- Is the before-after clear?
- Are benefits specific?

### Slide 6

- Does it look like an evidence board?
- Are datasets, metrics, artifacts and next phase present?
- Are huge URLs avoided?

---

## 8. Final rule

Your deck should look advanced, but not unbelievable.

The winning tone is:

```text
We built the AI engine, proved the runtime path, know the hardware gap, and have a realistic plan to finish the physical prototype.
```

That is stronger than pretending everything is already perfect.

