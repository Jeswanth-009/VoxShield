# VoxShield SIH PPT Reference Style Rebuild Manual

This is the corrected direction after seeing the latest slide. The current slide is visually polished, but it is too cinematic. It feels like a defence game poster or product trailer, not like the SIH finalist references. The finalist decks are usually not dark cinematic hero posters. They are structured evidence slides: clean header, dense but readable diagrams, compact cards, prototype screenshots, workflow arrows, tables, implementation details, and proof blocks.

The new design direction should be:

> Technical finalist board, not cinematic battlefield poster.

---

## 1. What to stop doing immediately

### Stop using cinematic battlefield backgrounds

Remove:

- dramatic soldier face
- helicopter/tank background
- smoky battlefield scene
- dark war-game lighting
- huge cinematic title treatment

Why: it makes the work look fictional. The references feel like real submissions because they use diagrams, screenshots, icons, tables, system maps, prototype blocks, and implementation details.

### Stop using huge “VoxShield” branding on every slide

The product name should appear, but not dominate the slide like a movie title. In the reference decks, the idea name is usually visible, but the slide content is the hero.

Use product branding only as:

- small logo/title strip
- top-left product mark
- one central system block

Not as:

- giant 25 percent slide title
- glowing wordmark
- cinematic headline

### Stop using neon cyber UI everywhere

Use subtle colors, not full neon.

Current problem:

- glowing green borders
- huge red/green waveforms
- dark sci-fi cards
- dramatic proof cards

Better:

- white/light background or very light grey
- navy section headers
- green only for validated proof
- amber only for risks/next steps
- simple icon line style
- real dashboard screenshot or simple wireframe, not fake glowing UI

### Stop using “mission-ready” and “protected communication” as if finished

Use:

```text
AI speech enhancement engine
```

```text
Edge-ready prototype path
```

```text
Controlled replay demo
```

```text
Next: synchronized dual-mic hardware validation
```

Avoid:

```text
Mission-ready speech
```

```text
Full adaptive noise cancellation
```

```text
Battlefield-ready headset
```

---

## 2. What the reference decks actually do

From the finalist references, the common pattern is:

### Pattern 1: Structured slide boards

They divide slides into clear blocks:

- Problem
- Solution
- Workflow
- Architecture
- Feasibility
- Impact
- References

They do not use one big cinematic scene.

### Pattern 2: Dense but controlled content

They often have a lot of information, but it is organized through:

- numbered flow
- mini tables
- architecture diagrams
- colored cards
- icons
- screenshots
- implementation blocks

The density looks intentional.

### Pattern 3: Real-world proof

They show:

- prototype image
- workflow
- technology stack
- result/metrics
- implementation timeline
- cost/viability
- references

For VoxShield, proof is stronger than cinematic visuals. Your best assets are:

- v15 broad strict gate passed
- Pi 5 benchmark
- ONNX export passed
- model/evaluation pipeline
- dashboard concept
- failure analysis
- honest hardware roadmap

### Pattern 4: Human problem plus technical system

They do not only show technology. They show who uses it and why.

For VoxShield:

- operator
- noisy environment
- hidden command words
- local processing
- edge device
- dashboard
- dual mic hardware path

---

## 3. Correct visual style

### Overall style

Use:

> Clean defence-tech infographic.

Not:

> cinematic military poster.

### Background

Use one of these:

Option A, safest:

- white or very light grey background
- navy headers
- dark blue cards
- green highlights

Option B, still modern:

- light grey canvas
- central dark architecture panel
- white surrounding cards

Option C, if you want dark:

- mostly dark navy
- no photo background
- flat infographic blocks
- very limited glow

Best recommendation:

Use a light or semi-light slide for slides 2 to 6. Keep dark only for small system blocks. This will look much more like the references.

### Color palette

Use:

- Navy: `#08345C`
- Deep navy: `#061B2E`
- Light background: `#F5F7FA`
- Card white: `#FFFFFF`
- Border grey: `#D6DEE8`
- Green proof: `#12B76A`
- Amber next step: `#F59E0B`
- Red problem: `#E5484D`
- Body text: `#172033`

Avoid:

- neon green everywhere
- red waveforms everywhere
- fully black slide backgrounds
- photographic battle backgrounds

### Typography

Use:

- main slide heading: 28 to 34 pt
- section labels: 14 to 18 pt
- card text: 9.5 to 12 pt
- metric numbers: 20 to 26 pt

Use bold only for:

- section names
- metric values
- product name

Do not bold entire paragraphs.

---

## 4. Correct Slide 2 rebuild

Your slide 2 should look like an SIH finalist “idea and proposed solution” slide, not a hero poster.

## Slide 2 title

At top in the SIH template title area:

```text
Idea title and proposed solution
```

Below that, small product heading:

```text
VoxShield: AI speech enhancement engine for noisy defence communication
```

Do not make “VoxShield” huge. Make it 30 to 34 pt, not 60+ pt.

## Slide 2 structure

Use a clean 4-block layout:

```text
┌────────────────────────────────────────────────────────────┐
│ Small product heading and one-line value proposition        │
├───────────────┬──────────────────────────────┬─────────────┤
│ Problem       │ Proposed system workflow      │ Outputs     │
│ context       │                              │             │
├───────────────┴──────────────────────────────┴─────────────┤
│ Why this is different / proof strip                         │
└────────────────────────────────────────────────────────────┘
```

### Top area

Height: 15 percent of slide.

Text:

```text
VoxShield: AI speech enhancement engine for noisy defence communication
```

Subtitle:

```text
Improves command intelligibility under vehicle, rotor, impulse and ambient noise using local real-time inference.
```

This is serious and factual.

### Left block: Problem context

Width: 25 percent.

Use a white card with red header.

Header:

```text
Problem context
```

Inside, use 4 compact rows:

```text
Vehicle and engine noise
Masks low-frequency speech cues
```

```text
Rotor and wind noise
Creates modulated nonstationary noise
```

```text
Impulse noise
Can hide short command words
```

```text
Ambient field noise
Reduces intelligibility during communication
```

Use simple line icons only. No military photos here.

### Middle block: Proposed system workflow

Width: 50 percent.

This should be the main visual.

Use a clean numbered workflow:

```text
1. Primary speech input
2. Reference noise input
3. Streaming AI enhancement
4. Speech preservation check
5. Enhanced audio and telemetry
```

Make it look like a process diagram, not a sci-fi engine.

Recommended shape:

Five rectangular steps connected by arrows:

```text
Primary mic + reference mic
        ↓
Frame and normalize
        ↓
Dual-channel deep filter
        ↓
Speech retention guard
        ↓
Enhanced speech + dashboard telemetry
```

Under the workflow, add a small note:

```text
Designed for synchronized dual-microphone hardware. Current demo uses controlled replay and Pi 5 runtime validation.
```

This note is important because it makes the slide believable.

### Right block: Outputs

Width: 25 percent.

Use a white card with green header.

Header:

```text
Prototype outputs
```

Inside:

```text
Enhanced speech
Clearer command audio
```

```text
Runtime telemetry
Latency, bypass and health state
```

```text
Evidence report
SNR, STOI, PESQ and speech deletion
```

```text
Edge deployment path
ONNX model and Pi 5 benchmark
```

Use icons, not waveforms.

### Bottom strip: Why it is different

Height: 18 percent.

Use 4 proof cards:

```text
Speech preserving
0.0 speech deletion in reported audits
```

```text
Edge feasible
Pi 5 mean latency 5.33 ms
```

```text
Model validated
v15 broad strict gate passed
```

```text
Hardware-aware
Next step is synchronized dual mic validation
```

Use green for first three, amber for hardware-aware.

## Slide 2 exact wireframe

```text
┌────────────────────────────────────────────────────────────────────┐
│ IDEA TITLE AND PROPOSED SOLUTION                                   │
│ VoxShield: AI speech enhancement engine for noisy defence comms     │
│ Improves command intelligibility using local real-time inference    │
├─────────────────┬──────────────────────────────────┬───────────────┤
│ PROBLEM CONTEXT │ PROPOSED SYSTEM WORKFLOW          │ OUTPUTS       │
│                 │                                  │               │
│ Vehicle noise   │ 1 Primary mic                     │ Enhanced      │
│ Rotor noise     │ 2 Reference mic                    │ speech        │
│ Impulse noise   │ 3 Streaming AI model               │ Telemetry     │
│ Ambient noise   │ 4 Speech retention check           │ Evidence      │
│                 │ 5 Enhanced output                  │ Edge path     │
│                 │                                  │               │
│                 │ Note: dual-mic hardware path       │               │
├─────────────────┴──────────────────────────────────┴───────────────┤
│ Speech preserving | Edge feasible | Model validated | Hardware aware│
└────────────────────────────────────────────────────────────────────┘
```

## What this fixes

This makes the slide:

- less cinematic
- more like finalist references
- easier to judge in 5 seconds
- more factual
- less likely to be questioned
- more aligned with your actual project

---

## 5. Design comparison: wrong vs right

| Current direction | Correct reference-style direction |
|---|---|
| cinematic defence background | clean technical infographic |
| giant product title | normal product heading |
| glowing AI engine | workflow diagram |
| red/green waveforms everywhere | one or zero waveforms |
| dramatic mission wording | factual prototype wording |
| proof mixed into same poster | proof strip with compact cards |
| looks like generated product ad | looks like SIH engineering submission |

---

## 6. Correct all six slides in reference style

### Slide 1: Title

Use a clean title slide.

Do not use a battlefield image full bleed.

Recommended:

- white SIH header
- left product name and metadata
- right simple system visual: headset, edge device, waveform
- bottom proof badges

Look:

> Official, polished, not cinematic.

### Slide 2: Idea and proposed solution

Use the 4-block layout described above.

Look:

> Product concept and workflow.

### Slide 3: Technical approach

Use a detailed architecture diagram.

Blocks:

- data sources
- mixture generator
- model training
- ONNX export
- runtime
- dashboard
- Pi 5

Look:

> Engineering system map.

### Slide 4: Feasibility and viability

Use proof plus risk mitigation.

Blocks:

- validated now
- benchmark results
- deployment hardware
- risk mitigation
- cost/parts estimate if available

Look:

> Readiness board.

### Slide 5: Impact and benefits

Use before/after communication example and beneficiary map.

Blocks:

- command hidden by noise
- enhanced command
- defence/rescue/industrial users
- local processing benefits

Look:

> Human impact with technical proof.

### Slide 6: Research and references

Use evidence board.

Blocks:

- datasets
- metrics
- artifacts
- next phase
- references/QR

Look:

> Evidence and credibility.

---

## 7. Exact style to copy from references

Copy these patterns:

- use many small evidence blocks
- use numbered diagrams
- use clean tables
- use icons with labels
- use real proof cards
- use implementation roadmap
- use references as evidence chips

Do not copy:

- their exact content
- their exact colors if unrelated
- random decorative images

For VoxShield, the best borrowed style is:

> CoalWorks architecture density plus Mindsmiths feasibility clarity plus EarthBenders polished cards.

That means:

- structured
- evidence-heavy
- diagram-first
- not cinematic

---

## 8. PowerPoint build steps for the corrected Slide 2

### Step 1: Remove the cinematic image

Delete:

- soldier background
- helicopter/tank background
- dark photo overlay

Replace with:

- light grey background `#F5F7FA`
- optional faint waveform line at 5 percent opacity

### Step 2: Reduce title size

Use:

```text
VoxShield: AI speech enhancement engine for noisy defence communication
```

Font:

- 30 to 34 pt
- navy
- bold only on “VoxShield”

Subtitle:

- 14 to 16 pt
- grey/navy

### Step 3: Create three main columns

Column widths:

- left: 25 percent
- middle: 50 percent
- right: 25 percent

Margins:

- 0.25 inch between columns
- keep card padding

### Step 4: Left problem card

White card.

Header red:

```text
Problem context
```

Add 4 rows with icons and two-line text.

No photos.

### Step 5: Middle workflow card

White or very light blue card.

Header navy:

```text
Proposed system workflow
```

Add five numbered blocks.

Use arrow connectors.

Place a tiny amber note at bottom:

```text
Next hardware phase: synchronized dual-microphone validation
```

### Step 6: Right outputs card

White card.

Header green:

```text
Prototype outputs
```

Add four output rows.

No waveform.

### Step 7: Bottom proof strip

Four proof cards.

Keep them small.

Cards:

```text
0.0 speech deletion
5.33 ms Pi 5 latency
v15 broad gate passed
Dual-mic hardware next
```

### Step 8: Footer

Use official SIH footer:

```text
Team@ | Problem Statement ID: 26052 | Theme: Defence and National Security | PS Category: Hardware
```

Keep it simple.

---

## 9. Final visual target

If someone sees the corrected slide, they should say:

> This looks like a serious SIH technical proposal.

Not:

> This looks like a generated defence product poster.

The corrected slide should be slightly less “wow” at first glance, but much more credible. That is what you need for SIH judging.

