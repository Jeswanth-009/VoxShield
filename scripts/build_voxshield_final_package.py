from __future__ import annotations

from pathlib import Path
import textwrap
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


OUT = Path("docs/final_package")
OUT.mkdir(parents=True, exist_ok=True)


def clean(s: str) -> str:
    return textwrap.dedent(s).strip()


DOSSIER = clean(
    """
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
    """
)


TECHNICAL = clean(
    """
    # VoxShield SIH 26052 Technical Dossier

    Team Name: Team@
    Problem Statement ID: 26052

    ## Technical objective

    The technical objective is to build a real-time AI speech enhancement system for noisy defence communication. The system should suppress or reduce stationary, nonstationary and impulsive noise while preserving command speech. The intended deployment direction is edge hardware such as Raspberry Pi 5 connected to a controlled dual-microphone input path.

    ## System definition

    VoxShield consists of six major layers:

    1. data and mixture generation layer
    2. training and hard-case repair layer
    3. streaming AI enhancement model
    4. ONNX export and parity validation
    5. edge runtime and benchmark layer
    6. dashboard and evidence reporting layer

    ## Audio input model

    The model is designed around synchronized audio channels:

    - primary channel: speech plus noise near the mouth or communication source
    - reference channel: environmental noise reference

    This is important because a single Bluetooth microphone or laptop microphone array does not provide a reliable raw reference channel. Physical deployment needs a dual-microphone hardware rig with stable timing.

    ## Data sources used or planned

    | Source | Role |
    |---|---|
    | VCTK | clean speech |
    | DNS Challenge | speech/noise challenge material |
    | MAD dataset | military-like or hard acoustic material |
    | ESC-50 | environmental noise categories |
    | AudioSet targeted subset | gunshot, explosion, vehicle, engine, siren, helicopter, aircraft |
    | RIRS NOISES | room impulse responses and reverb |
    | user recordings | personal clean/noisy examples such as fan and helicopter playback |

    ## Data ingestion status

    The user has already ingested a large referenced catalog without copying audio. A later manifest included targeted AudioSet folders mapped into impulsive and nonstationary categories. The manifest counts showed more than 124,000 referenced files, with clean speech, environmental noise, impulsive noise, nonstationary noise, stationary noise and RIR categories.

    This is useful because the deck can claim a real data pipeline, not a toy dataset.

    ## Model and runtime

    The current candidate model family is a dual-channel deep-filter model exported to ONNX. The model is lightweight enough for edge testing, around 1.1M parameters in reported slides. The model runs in a frame-based streaming style at 16 kHz with a 16 ms frame duration.

    The runtime stack includes:

    - Python training and evaluation tools
    - ONNX export
    - ONNX runtime inference
    - Pi 5 benchmark
    - live console or dashboard telemetry

    ## Current strongest model candidates

    | Candidate | Strength | Limitation |
    |---|---|---|
    | v12 hard repair | strong metric candidate | older than v15 |
    | v14 realworld audioset | added more real-world targeted data | broad gate initially failed strict reliability |
    | v15 hard failure repair | broad strict gate passed, strong export and metrics | military strict gate still fails reliability thresholds |

    Recommended deck candidate: v15 for recent narrative and broad gate proof. If comparing final numbers internally, keep v12 as a backup candidate if it outperforms in selected audits.

    ## v15 export evidence

    v15 ONNX export passed parity validation. Reported values:

    - checkpoint: checkpoints_deep_filter_v15_hard_failure_repair/best.pt
    - ONNX: artifacts/voxshield-v15-hard-failure-repair-final.onnx
    - max output absolute error: about 1.82e-08
    - max state absolute error: about 4.07e-06
    - tolerance: 0.0002
    - export status: passed

    This proves the PyTorch model and ONNX export are numerically aligned enough for runtime deployment testing.

    ## v15 broad audit

    Reported v15 broad results:

    - SNR enhanced: 30.48 dB
    - SI-SNR enhanced: 30.64 dB
    - STOI enhanced: 0.938
    - PESQ enhanced: 3.94
    - pause noise attenuation: 20.24 dB
    - speech deletion rate: 0.0
    - active level error: 0.10 dB
    - strict SIH gate: passed

    This should be used in the PPT as broad controlled-audit evidence.

    ## v15 military audit

    Reported v15 military results:

    - SNR enhanced: 25.15 dB
    - SI-SNR enhanced: 25.30 dB
    - STOI enhanced: 0.915
    - PESQ enhanced: 3.63
    - pause noise attenuation: 24.58 dB
    - speech deletion rate: 0.0
    - active level error: 0.19 dB

    The quality gate did not fully pass strict military reliability because STOI target reliability and joint target reliability missed thresholds. This should not be hidden in the technical dossier. It means the average is strong, but some hard clips still fail. That is a normal engineering finding and justifies the hard-case repair roadmap.

    ## Pi 5 benchmark evidence

    Reported Pi 5 verification:

    - backend: ONNX runtime
    - frame duration: 16 ms
    - mean latency: about 5.33 ms
    - p95 latency: about 5.49 ms
    - p99 latency: about 6.05 ms
    - full pipeline p99 callback: about 6.50 ms
    - real-time factor: about 0.33
    - deadline overruns: 0
    - simulated callback drops: 0

    This is one of the strongest project facts. Use it repeatedly, but do not overstate it as full headset validation.

    ## Why live Bluetooth sounded bad

    Bluetooth headsets commonly apply their own processing and use profiles that trade bandwidth, latency and microphone quality. Laptop and Bluetooth paths may:

    - downsample or compress audio
    - apply built-in noise suppression
    - expose only mono audio
    - fail to provide a clean reference channel
    - add unpredictable latency
    - prevent raw synchronized capture

    Therefore, a bad Bluetooth demo does not automatically prove the model is useless. It proves the hardware path is wrong for validating physical cancellation.

    ## Correct hardware architecture

    Minimum next hardware rig:

    - Raspberry Pi 5
    - USB audio interface or multi-channel USB microphone device
    - primary microphone near mouth
    - reference microphone placed toward noise source
    - wired headset or speaker output
    - controlled noise playback source
    - dashboard running locally or on same network

    Avoid Bluetooth for proof demos.

    ## Evaluation metrics

    | Metric | Meaning |
    |---|---|
    | SNR | energy-level noise reduction relative to clean target |
    | SI-SNR | scale-invariant signal quality |
    | STOI | intelligibility estimate |
    | PESQ | perceptual quality estimate |
    | speech deletion rate | checks whether speech was removed |
    | active level error | checks whether speech loudness is preserved |
    | latency | real-time feasibility |

    ## Technical risks and mitigations

    | Risk | Technical reason | Mitigation |
    |---|---|---|
    | Bad live demo with laptop/Bluetooth | no synchronized raw reference | use controlled replay and wired/USB audio |
    | Model overfits synthetic mixtures | real noise differs | add field recordings and targeted hard-case repair |
    | Speech deletion | aggressive suppression can remove speech | keep STOI and speech deletion gates |
    | Impulse and rotor failures | hard transient/nonstationary noise | hard-failure dataset and loss weighting |
    | Edge CPU load | real-time deadline risk | ONNX optimization and frame-level benchmark |

    ## Next build plan

    Phase 1: freeze v15 as current demo candidate and keep v12 as backup.

    Phase 2: create a controlled demo set:

    - clean command
    - vehicle noise mix
    - rotor noise mix
    - impulse noise mix
    - fan/air noise mix
    - one user-recorded scenario

    Phase 3: build hardware rig:

    - wired mic path
    - synchronized dual input
    - Pi 5 runtime
    - dashboard

    Phase 4: record real validation clips and rerun audit.

    ## Technical conclusion

    VoxShield is not yet a fully proven physical ANC product. It is a strong AI speech enhancement prototype with a validated edge-runtime path and a clear hardware validation roadmap. This is the correct, defensible technical story.
    """
)


PPT = clean(
    """
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
    """
)


FILES = [
    ("VoxShield_SIH_26052_Judging_Dossier", DOSSIER),
    ("VoxShield_SIH_26052_Technical_Dossier", TECHNICAL),
    ("VoxShield_SIH_26052_PPT_PDF_Blueprint", PPT),
]


def md_to_story(text: str):
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="DocTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#061B2E"),
            alignment=TA_CENTER,
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1x",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#07345C"),
            spaceBefore=14,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2x",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#172033"),
            spaceBefore=10,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Bodyx",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=12.2,
            textColor=colors.HexColor("#172033"),
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Bulletx",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.1,
            leading=12,
            leftIndent=14,
            firstLineIndent=-8,
            spaceAfter=3,
        )
    )
    story = []
    lines = text.splitlines()
    para_buf = []
    table_buf = []
    in_table = False

    def flush_para():
        nonlocal para_buf
        if para_buf:
            p = " ".join(x.strip() for x in para_buf).strip()
            if p:
                story.append(Paragraph(p, styles["Bodyx"]))
            para_buf = []

    def flush_table():
        nonlocal table_buf, in_table
        if table_buf:
            rows = []
            for row in table_buf:
                parts = [c.strip() for c in row.strip().strip("|").split("|")]
                if all(re.fullmatch(r":?-{3,}:?", c or "") for c in parts):
                    continue
                rows.append([Paragraph(c, styles["Bodyx"]) for c in parts])
            if rows:
                col_count = max(len(r) for r in rows)
                for r in rows:
                    while len(r) < col_count:
                        r.append(Paragraph("", styles["Bodyx"]))
                tbl = Table(rows, repeatRows=1, hAlign="LEFT")
                tbl.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#07345C")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D6DEE8")),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 5),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ]
                    )
                )
                story.append(tbl)
                story.append(Spacer(1, 8))
        table_buf = []
        in_table = False

    for line in lines:
        raw = line.rstrip()
        if raw.startswith("|") and raw.endswith("|"):
            flush_para()
            in_table = True
            table_buf.append(raw)
            continue
        if in_table:
            flush_table()
        if not raw.strip():
            flush_para()
            continue
        if raw.startswith("# "):
            flush_para()
            story.append(Paragraph(raw[2:].strip(), styles["DocTitle"]))
        elif raw.startswith("## "):
            flush_para()
            story.append(Paragraph(raw[3:].strip(), styles["H1x"]))
        elif raw.startswith("### "):
            flush_para()
            story.append(Paragraph(raw[4:].strip(), styles["H2x"]))
        elif raw.startswith("- "):
            flush_para()
            story.append(Paragraph("• " + raw[2:].strip(), styles["Bulletx"]))
        elif re.match(r"^\d+\. ", raw):
            flush_para()
            story.append(Paragraph(raw.strip(), styles["Bulletx"]))
        elif raw.startswith("```"):
            flush_para()
        else:
            para_buf.append(raw)
    flush_para()
    flush_table()
    return story


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#536173"))
    canvas.drawString(0.72 * inch, 0.42 * inch, "VoxShield SIH 26052 | Team@")
    canvas.drawRightString(A4[0] - 0.72 * inch, 0.42 * inch, f"Page {doc.page}")
    canvas.restoreState()


for stem, content in FILES:
    md_path = OUT / f"{stem}.md"
    pdf_path = OUT / f"{stem}.pdf"
    md_path.write_text(content + "\n", encoding="utf-8")
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=0.72 * inch,
        leftMargin=0.72 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=stem,
    )
    story = md_to_story(content)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(pdf_path)

