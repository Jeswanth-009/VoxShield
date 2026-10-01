from __future__ import annotations

from pathlib import Path
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(r"C:\anc")
OUT = ROOT / "docs" / "VoxShield_SIH_26052_Master_Document.docx"
BLACK = "000000"
NAVY = "17365D"
BLUE = "D9EAF7"
PALE = "F4F7FA"
GREY = "666666"
RED = "A61B1B"
GREEN = "17643A"


def set_repeat_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    elem = OxmlElement("w:tblHeader")
    elem.set(qn("w:val"), "true")
    tr_pr.append(elem)


def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def margins(section):
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.68)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)


def cell_text(cell, value, bold=False, color=BLACK, size=8.4, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.05
    r = p.add_run(str(value))
    r.bold = bold
    r.font.name = "Aptos"
    r._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    r._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    r.font.size = Pt(size)
    r.font.color.rgb = RGBColor.from_string(color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def add_table(doc, headers, rows, widths=None, numeric_cols=()):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.autofit = True
    set_repeat_header(t.rows[0])
    for i, h in enumerate(headers):
        cell_text(t.rows[0].cells[i], h, True, "FFFFFF", 8.3, WD_ALIGN_PARAGRAPH.CENTER)
        shade(t.rows[0].cells[i], NAVY)
    for ridx, row in enumerate(rows):
        cells = t.add_row().cells
        for i, val in enumerate(row):
            align = WD_ALIGN_PARAGRAPH.CENTER if i in numeric_cols else WD_ALIGN_PARAGRAPH.LEFT
            cell_text(cells[i], val, False, BLACK, 8.1, align)
            if ridx % 2:
                shade(cells[i], PALE)
    if widths:
        for row in t.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = Inches(width)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(1)
    return t


def para(doc, text, bold_lead=None):
    p = doc.add_paragraph()
    if bold_lead and text.startswith(bold_lead):
        p.add_run(bold_lead).bold = True
        p.add_run(text[len(bold_lead):])
    else:
        p.add_run(text)
    return p


def bullets(doc, items, level=0):
    style = "List Bullet" if level == 0 else "List Bullet 2"
    for item in items:
        doc.add_paragraph(item, style=style)


def numbered(doc, items):
    for index, item in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.18)
        p.paragraph_format.first_line_indent = Inches(-0.18)
        p.add_run(f"{index}. ").bold = True
        p.add_run(item)


def code(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.2)
    p.paragraph_format.right_indent = Inches(0.1)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(5)
    r = p.add_run(text)
    r.font.name = "Cascadia Mono"
    r._element.rPr.rFonts.set(qn("w:ascii"), "Cascadia Mono")
    r._element.rPr.rFonts.set(qn("w:hAnsi"), "Cascadia Mono")
    r.font.size = Pt(7.6)


def section_title(doc, number, title):
    doc.add_page_break()
    doc.add_heading(f"SECTION {number}  {title}", level=1)


doc = Document()
for s in doc.sections:
    margins(s)

styles = doc.styles
styles["Normal"].font.name = "Aptos"
styles["Normal"]._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
styles["Normal"]._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
styles["Normal"].font.size = Pt(9.6)
styles["Normal"].font.color.rgb = RGBColor.from_string(BLACK)
styles["Normal"].paragraph_format.space_after = Pt(5)
styles["Normal"].paragraph_format.line_spacing = 1.08
for name, size in [("Title", 30), ("Subtitle", 14), ("Heading 1", 18), ("Heading 2", 13), ("Heading 3", 10.5)]:
    style = styles[name]
    style.font.name = "Aptos Display"
    style._element.rPr.rFonts.set(qn("w:ascii"), "Aptos Display")
    style._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos Display")
    style.font.size = Pt(size)
    style.font.color.rgb = RGBColor.from_string(BLACK)
    style.font.bold = name != "Subtitle"
    style.paragraph_format.space_before = Pt(9 if name != "Title" else 0)
    style.paragraph_format.space_after = Pt(5)

# Word's built-in Title style can carry a theme border. Remove it so the cover
# relies on typography and whitespace, not a decorative rule.
title_ppr = styles["Title"]._element.get_or_add_pPr()
for border in title_ppr.findall(qn("w:pBdr")):
    title_ppr.remove(border)

section = doc.sections[0]
header = section.header.paragraphs[0]
header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
run = header.add_run("Team@  |  VoxShield  |  SIH PS 26052")
run.font.name = "Aptos"
run.font.size = Pt(7.5)
run.font.color.rgb = RGBColor.from_string(GREY)
footer = section.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = footer.add_run("Master technical and competition document  |  Evidence cut-off 28 September 2026")
run.font.name = "Aptos"
run.font.size = Pt(7.2)
run.font.color.rgb = RGBColor.from_string(GREY)

# Cover
p = doc.add_paragraph(style="Title")
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(80)
p.add_run("VoxShield SIH 26052 Master Document")
p = doc.add_paragraph(style="Subtitle")
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("AI ML enabled adaptive noise suppression for defence communication")
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(24)
r = p.add_run("Prepared by Team@")
r.bold = True
r.font.size = Pt(14)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run("Technical record  Competition evidence  Presentation source  Deployment plan")
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(45)
p.add_run("Selected baseline  v10 deep filter dual  |  Updated  28 September 2026")

doc.add_page_break()
doc.add_heading("Document purpose and factual status", level=1)
para(doc, "This master document consolidates the complete VoxShield project journey from an empty C:\\anc workspace to the current trained, exported and audited v10 system. It follows the requested nine-section SIH format and is intended to be the main factual source for the technical report, judging discussion and presentation content.")
para(doc, "The selected deployment baseline is v10 deep-filter dual. It is a 1,116,813-parameter causal dual-channel, complex-domain speech-enhancement model with a five-tap multi-frame deep-filtering output stage. The checkpoint selected at epoch 58 exports to stateful ONNX with a maximum enhanced-output absolute error of 6.10 x 10^-8 against PyTorch. On the frozen 50-file development audits, the broad set passes the strict SIH gate. The military set exceeds the mean SNR, STOI and PESQ targets and the joint-attainment target, but fails the deliberately stricter 80 percent per-file STOI-reliability requirement at 68.4 percent. Therefore the current model is strong development evidence, not defence qualification or field proof.")
para(doc, "Terms are used carefully. VoxShield currently implements real-time communication speech enhancement and noise suppression. Physical acoustic ANC that generates anti-noise into an acoustic field requires an error microphone, secondary-path identification and stable FxLMS or FxNLMS control. That physical closed loop has not been validated. The project contains adaptive-filter experiments and a roadmap, but it must not be presented as completed physical ANC.")

doc.add_heading("Executive evidence summary", level=2)
add_table(doc, ["Item", "Current factual status"], [
    ["Repository", "Built from scratch inside C:\\anc; modular data, training, evaluation, export, inference, monitoring, dashboard, tests and deployment scaffolding."],
    ["Selected model", "v10 deep-filter dual; checkpoint checkpoints_deep_filter_v10/best.pt; best epoch 58; 1,116,813 trainable parameters."],
    ["Export", "artifacts/voxshield-v10-deep-filter-final.onnx; ONNX opset 17; parity passed."],
    ["Broad audit", "23.645 dB output SNR, 0.9213 STOI, 3.7018 PESQ; strict gate passed."],
    ["Military audit", "19.455 dB output SNR, 0.8926 STOI, 3.3911 PESQ; strict gate failed only on per-file STOI reliability."],
    ["Safety", "Zero speech deletion on both frozen 50-file audits; clean-level and clean/near-clean preservation checks passed."],
    ["Rejected successor", "v10b STOI fine-tune completed and exported but was not promoted because target-attainment did not improve and military PESQ reliability fell."],
    ["Automated verification", "102 tests passed after the v10b numerical-stability repair."],
    ["Embedded status", "ONNX and Pi 5 scripts exist; final v10 has not yet been benchmarked, thermally soaked or loopback-measured on the user's Pi 5."],
])

doc.add_heading("How to read claims", level=2)
bullets(doc, [
    "Measured means a saved repository artifact supports the value.",
    "Development audit means a fixed synthetic noisy-clean validation manifest, not an independently recorded field trial.",
    "Target means the threshold stated in PS 26052 or an internal reliability requirement; it is not a measured result.",
    "Implemented means code and tests exist; it does not automatically mean target hardware validation is complete.",
    "Team input required means the repository contains no factual basis and this document intentionally leaves the field unclaimed.",
])

section_title(doc, 1, "SIH MANDATORY METADATA")
add_table(doc, ["Field", "Verified entry"], [
    ["Problem Statement ID", "26052"],
    ["Problem Statement Title", "To develop an AI/ML-enabled adaptive noise cancellation (ANC) system that effectively suppresses stationary, non-stationary, and impulsive defence noises while maintaining high speech intelligibility and real-time performance on embedded hardware."],
    ["Sponsoring Organization", "DRDO"],
    ["Department", "Department of Defence R&D"],
    ["Theme", "Miscellaneous"],
    ["Category", "Hardware"],
    ["Team Name", "Team@"],
    ["Registered Team ID", "Team input required. Insert the exact SIH registration ID before submission."],
])
doc.add_heading("Problem statement interpretation", level=2)
para(doc, "PS 26052 asks for a hybrid AI-driven ANC or noise-suppression system that handles stationary, non-stationary and impulsive defence noise, preserves speech intelligibility, operates in real time, and can be deployed to edge hardware. It explicitly describes dataset generation from clean speech plus curated defence noise at varied SNR, STFT or waveform processing, full-band and sub-band information, complex-domain processing, SI-SNR and L1/L2 or perceptual losses, augmentation, mask or direct reconstruction, optional LMS residual filtering, ONNX or TensorRT optimization, microphone/headset integration and target metrics of output SNR above 15 dB, STOI above 0.85 and PESQ above 2.5.")
doc.add_heading("Traceability from PS requirement to VoxShield", level=2)
add_table(doc, ["PS requirement", "VoxShield implementation", "Evidence status"], [
    ["Scalable noisy-clean dataset pipeline", "Recursive in-place indexing, group-aware splits, dynamic mixing and fixed audit-manifest generation.", "Implemented and tested."],
    ["Stationary, non-stationary and impulsive noise", "Explicit categories plus environmental and mixed noise; MAD military, UAV, MUSAN and ESC-50 sources.", "Implemented; field diversity still incomplete."],
    ["Full-band and sub-band features", "Causal full-band temporal modeling with ERB/sub-band context.", "Implemented in selected v10 graph."],
    ["Complex-domain phase preservation", "Complex primary/reference features, complex enhancement and signed imaginary path.", "Implemented and ONNX-validated."],
    ["SI-SNR and spectral/perceptual losses", "SI-SNR, SNR, waveform L1, compressed complex/magnitude, phase and artifact-control losses; STOI-envelope tested in v10b.", "Implemented; v10b objective rejected."],
    ["Real-time inference", "Stateful causal streaming, worker-thread processing, aligned dry fallback, health monitoring and dashboard.", "Implemented on laptop; target-hardware proof pending."],
    ["Adaptive filter", "LMS/NLMS/FxNLMS explored as an optional residual or physical-ANC path.", "Not promoted; real geometry and secondary-path tests required."],
    ["ONNX or TensorRT optimization", "FP32 ONNX export and numerical parity; INT8 tested and rejected for speed.", "ONNX complete; TensorRT is a Jetson option, not a Pi path."],
    ["Microphone and headset prototype", "Laptop mono and experimental dual-input live paths; synchronized dual-input final hardware plan.", "Engineering demo exists; final physical dual-mic prototype pending."],
    ["SNR >15 dB, STOI >0.85, PESQ >2.5", "Broad audit passes; military mean passes; military per-file STOI reliability is below internal 80% criterion.", "Partially achieved; not field-certified."],
])

section_title(doc, 2, "THE STRATEGIC FOUNDATION")
doc.add_heading("The Big Idea One Liner", level=2)
para(doc, "VoxShield is a compact, causal, defence-aware speech-enhancement system that combines a noise-reference channel, complex spectral and spatial learning, multi-frame deep filtering and fail-safe edge inference so that critical speech remains intelligible during stationary, changing and impulsive noise.")
doc.add_heading("Core Call to Action", level=2)
para(doc, "The immediate goal is approval to proceed from a validated development prototype to a controlled synchronized dual-microphone and Raspberry Pi 5 pilot. The requested technical milestone is not unrestricted field deployment. It is a measured pilot that demonstrates reproducible audio improvement, end-to-end latency, reliability, thermal behavior, power, safe bypass and performance on newly recorded target-device data.")
doc.add_heading("Target user persona profile", level=2)
add_table(doc, ["Persona", "Operational need", "VoxShield role"], [
    ["Soldier or vehicle crew member", "Understand and transmit speech near engines, rotor noise, blasts, sirens and moving platforms.", "Enhance the close-talk communication microphone before radio encoding or headset playback."],
    ["Command and control operator", "Receive intelligible speech with fewer repetitions and less listening fatigue.", "Improve upstream voice quality while preserving recognizable speaker characteristics."],
    ["Defence communications integrator", "Fit the algorithm into headset, intercom, radio or edge-compute hardware with measurable latency and fail-safe behavior.", "Use stateful ONNX, telemetry, device checks and controlled bypass."],
    ["DRDO test and evaluation engineer", "Reproduce results, inspect failures and validate under agreed acoustic and hardware conditions.", "Use frozen manifests, artifact hashes, per-category metrics, listening sets and hardware benchmark reports."],
])
doc.add_heading("Value proposition", level=2)
bullets(doc, [
    "Improves speech intelligibility while explicitly monitoring speech deletion and clean-speech regression.",
    "Targets diverse defence-relevant noise rather than only steady office noise.",
    "Runs causally with explicit recurrent state and exports to a portable ONNX representation.",
    "Keeps raw datasets in place and generates mixtures dynamically, reducing storage duplication.",
    "Treats degraded mode, bypass, telemetry and artifact traceability as first-class requirements.",
    "Exposes limitations through category, source and SNR-bin analysis instead of hiding them behind one average score.",
])

section_title(doc, 3, "PROBLEM MARKET AND COMPLEXITY VALIDATION")
doc.add_heading("Operational problem", level=2)
para(doc, "Defence speech is often mixed with broadband engine energy, rotor harmonics, wind, alarms, other speakers and short high-energy transients. When noise overlaps speech in time and frequency, simple filtering cannot separate the sources without also damaging consonants, pitch structure and speaker identity. Impulsive noise creates an additional problem: microphone or analogue-front-end clipping can permanently remove information before software receives the waveform.")
doc.add_heading("Status quo cost", level=2)
para(doc, "The repository contains no verified rupee cost, mission-loss statistic or DRDO operational incident data. A numerical status-quo cost would therefore be fabricated. The defensible impact statement is qualitative: unintelligible communication causes repeated messages, slower decisions, cognitive fatigue and increased risk of command misunderstanding. Any monetary or casualty figure must come from an authorized user study, ministry source or pilot record before inclusion.")
doc.add_heading("Why now", level=2)
bullets(doc, [
    "Compact causal neural networks can now run on edge CPUs without a cloud connection.",
    "ONNX Runtime provides a portable inference path across development and embedded targets.",
    "Public speech, environmental, military-acoustic, UAV and room-response corpora support reproducible prototype training.",
    "Edge processing supports low latency and data locality, which is preferable for sensitive communications.",
    "Modern evaluation can combine signal fidelity, intelligibility, perceptual quality, preservation and reliability instead of optimizing only one average metric.",
])
doc.add_heading("Market sizing framework", level=2)
para(doc, "No audited market report, procurement count or unit price is stored in the project. The following is a sizing method, not a claimed valuation. Team@ should populate it only from cited procurement or industry sources.")
add_table(doc, ["Layer", "Definition for VoxShield", "Required evidence before assigning value"], [
    ["TAM", "Global defence, aerospace, public-safety and high-noise industrial communication endpoints that could use embedded speech enhancement.", "Credible market report, scope definition, year, currency and device/service assumptions."],
    ["SAM", "Indian defence and mission-critical communication programs compatible with the selected headset/radio/edge architecture.", "Eligible programs, annual device volumes, integration constraints and procurement pathway."],
    ["SOM", "Realistic 3-5 year pilots and production units accessible through DRDO, integrators or licensed manufacturers.", "Named pilot pathway, qualification schedule, partner capacity and expected adoption rate."],
])
doc.add_heading("Competitor and existing-work deep dive", level=2)
add_table(doc, ["Approach", "Strength", "Critical limitation for this PS", "VoxShield response"], [
    ["Spectral subtraction and Wiener filtering", "Small, explainable and inexpensive for steady noise.", "Rapidly changing or impulsive noise causes residual musical noise and speech distortion.", "Learn time-frequency dependencies and preserve complex information; retain classical filters only as measured baselines."],
    ["LMS NLMS adaptive filtering", "Effective when a clean reference is correlated with the unwanted component and geometry is stable.", "Speech leakage, unsynchronized channels and an unknown secondary path can cancel speech or diverge.", "Reference-quality checks, synchronized-hardware requirement and separate FxNLMS physical-ANC roadmap."],
    ["Cloud denoising services", "Large models and easy updates.", "Connectivity, privacy, latency, availability and recurring-service dependence are unsuitable for many mission-critical paths.", "Local stateful ONNX inference with no cloud dependency in the audio path."],
    ["Generic consumer noise suppression", "Mature user experience for common office or call noise.", "Training domain and metrics may not cover gunshot, artillery, rotor, vehicle or extreme low-SNR defence conditions.", "Defence-aware data weighting and a separate frozen military audit."],
    ["Research models such as GTCRN UL-UNAS DeepFilterNet", "Strong published lightweight speech-enhancement ideas.", "Published results do not prove performance on Team@'s data, hardware or PS gate.", "Reproduce, audit and adapt ideas; promote only models that pass the same frozen evaluations and listening tests."],
])
doc.add_heading("Why the problem is technically difficult", level=2)
bullets(doc, [
    "Speech and noise are not cleanly separable when they occupy the same time-frequency region.",
    "At very low SNR, some speech information is absent rather than merely hidden.",
    "A high suppression score can be achieved by deleting speech; preservation metrics and listening are essential.",
    "Synthetic mixtures do not capture every microphone response, AGC, codec, limiter, reverberation, clock-drift or placement effect.",
    "Two consumer microphones on separate devices do not share a sample clock, weakening phase and spatial features.",
    "Real-time systems fail through I/O jitter and underflow even when the neural network is individually fast.",
    "A model that wins on one validation set can overfit the benchmark; an unseen test set and field recordings are required.",
])

section_title(doc, 4, "RISK MATRIX AND MITIGATION STRATEGIES")
add_table(doc, ["Risk", "Probability", "Impact", "Mitigation", "Residual status"], [
    ["Military STOI reliability remains below 80%", "High", "High", "Failure-targeted vehicle/helicopter data, real channel augmentation, bounded v11 fine-tune, untouched test set.", "Open; current value 68.4%."],
    ["Robotic or unnatural voice", "Medium", "High", "Matched-level blind listening, complex/phase losses, conservative wet mix, preservation gates and artifact taxonomy.", "Open; objective metrics alone are insufficient."],
    ["Reference microphone contains speech", "Medium", "High", "Physical placement, leakage measurement, simulated leakage training and reference-quality gate.", "Open until real synchronized hardware is tested."],
    ["Unsynchronized microphone clocks", "High with separate USB devices", "High", "Use one synchronized multi-input interface or codec for final prototype.", "Experimental laptop dual-device mode is not acceptance evidence."],
    ["Impulse clips microphone input", "Medium", "High", "Analogue headroom, limiter strategy, target-device recordings and clipping augmentation.", "Software cannot reconstruct irrecoverably saturated audio."],
    ["Pi 5 thermal throttling or underflow", "Medium", "High", "Active cooling, one-thread baseline, p50/p95/p99 benchmark, 30-60 minute soak and callback telemetry.", "Unmeasured on final v10."],
    ["Dataset leakage or licensing issue", "Medium", "High", "Group-aware splits, provenance inventory, checksum and license review; keep restricted data out of repository.", "Technical split controls exist; legal review remains required."],
    ["Model copied by a larger vendor", "Medium", "Medium", "Defence-specific failure data, evaluation discipline, deployment integration, calibration and field-feedback loop.", "No patent or exclusive-data claim is made."],
    ["Dependency failure", "Low to medium", "Medium", "Pin versions, export stable ONNX, store hashes, maintain software bypass and reproducible environment.", "Core live audio does not require a cloud API."],
    ["Metric overclaim", "Medium", "High", "Freeze manifests, state sample count, preserve reports, distinguish mean from reliability and label development versus field evidence.", "Controlled through this master document and model-card practice."],
    ["Physical ANC instability", "High before calibration", "High", "Keep speech enhancement separate; identify secondary path and test FxNLMS in controlled hardware before enabling anti-noise output.", "Physical ANC not yet completed."],
])
doc.add_heading("Market and commercial risk response", level=2)
para(doc, "The defensible moat is not a generic neural architecture. It is the combination of defence-relevant data governance, failure-driven evaluation, target-device recordings, synchronized dual-channel calibration, safe runtime behavior and evidence needed for integration. If a major vendor copies visible features, Team@ should compete through verified local performance, integration support, data provenance and rapid domain adaptation rather than unsupported claims of algorithmic exclusivity.")
doc.add_heading("Regulatory and legal response", level=2)
para(doc, "The system should default to local processing, minimal retention and controlled artifact transfer. Dataset use must follow each source license and any defence-security restrictions. Locally recorded speech requires consent, purpose limitation and an approved retention/deletion procedure. The project has no SOC 2, ISO 27001, defence certification or formal security accreditation; these must not be claimed.")

section_title(doc, 5, "PRODUCT ANATOMY AND DEEP TECHNICAL SPECIFICATIONS")
doc.add_heading("Core technology stack", level=2)
add_table(doc, ["Layer", "Current implementation"], [
    ["Languages", "Python for data, training, evaluation, inference, export, benchmarking, tests and dashboard services; PowerShell and shell scripts for workstation and Pi workflows."],
    ["ML framework", "PyTorch training and checkpointing; ONNX opset 17 export; ONNX Runtime deployment."],
    ["Audio and DSP", "16 kHz float32 mono or synchronized primary/reference audio, STFT analysis, ERB/sub-band features, complex operations, weighted overlap-add, safe conditioning."],
    ["Data storage", "Original corpora remain in place; JSONL catalogs/manifests and WAV audit pairs; local checkpoint and artifact directories. No operational database is required for the prototype."],
    ["User interface", "Local engineering dashboard and live-audio command line showing waveform, spectrum/waterfall, channel levels, correlation, mode, latency and health counters."],
    ["Deployment", "Stateful FP32 ONNX; laptop CPU/GPU development; Raspberry Pi 5 scripts; Jetson/TensorRT path documented as an alternative."],
    ["Quality assurance", "Pytest, Ruff, deterministic fixed audits, ONNX parity, metric gates, per-file/category/SNR breakdowns and saved listening audio."],
])
doc.add_heading("System architecture and data flow", level=2)
numbered(doc, [
    "Acquire a close-talk primary microphone signal containing speech plus noise and, when available, a synchronized noise-dominant reference signal.",
    "Sanitize non-finite values, convert channels to the configured 16 kHz float32 format and enforce conservative amplitude bounds without untrained filtering.",
    "Apply causal STFT analysis and form complex primary/reference spectra, magnitude, phase, inter-channel and relative-level information.",
    "Compress full-band and ERB/sub-band features so the model observes both global temporal structure and local frequency context.",
    "Process the features with a causal recurrent enhancement core carrying explicit state between frames.",
    "Predict bounded complex enhancement coefficients and five-tap multi-frame deep-filter coefficients; combine current and recent spectral frames to reconstruct speech.",
    "Use weighted overlap-add to return waveform blocks while maintaining causal streaming buffers.",
    "Apply conservative conditioning and optional dry/wet mixing. If output is late or invalid, use aligned dry audio rather than stale enhanced audio.",
    "Send audio to the selected headset/output and publish telemetry for mode, underflows, dropped input, worker failures, channel quality and latency.",
])
doc.add_heading("Selected v10 neural engine", level=2)
para(doc, "The selected v10 model is the deep_filter_dual architecture. It combines the project's dual-channel complex and ERB-aware fusion path with a substantially larger causal recurrent core and a five-tap multi-frame deep-filtering output. The larger capacity was adopted only after correcting earlier data, evaluation and runtime defects that made parameter-count conclusions unreliable. The network remains stateful and causal for frame-by-frame streaming.")
add_table(doc, ["Specification", "Value"], [
    ["Architecture identifier", "deep_filter_dual"],
    ["Trainable parameters", "1,116,813"],
    ["Selected checkpoint", "checkpoints_deep_filter_v10/best.pt"],
    ["Selected epoch", "58"],
    ["Training run", "60-epoch v10 recipe; approximately 6.42 hours reported for the completed run."],
    ["Export", "artifacts/voxshield-v10-deep-filter-final.onnx"],
    ["ONNX opset", "17"],
    ["Checkpoint SHA256", "9f6592cb999b1f8066cb0ac1bfafc4e3df06480df7dfeb84b8f5c048d3741dae"],
    ["ONNX SHA256", "fcdc680b80f2b9dcf3db9ed4f15ac083b9a518a15e4e06e2fc0683b7df44171c"],
    ["PyTorch ONNX max output error", "6.100162863731384 x 10^-8; passed at tolerance 2 x 10^-4"],
    ["PyTorch ONNX max state error", "6.256625056266785 x 10^-6"],
])
doc.add_heading("Feature and reconstruction rationale", level=2)
bullets(doc, [
    "Full-band temporal context helps identify speech and noise trajectories across frequency.",
    "ERB or sub-band context gives frequency-local detail using a perceptually motivated compact representation.",
    "Complex-domain prediction preserves and corrects phase instead of estimating magnitude alone.",
    "A signed imaginary path is essential; an earlier sign/phase defect was identified and corrected during v8 development.",
    "Multi-frame deep filtering uses neighboring causal spectral frames to model temporal structure that a single-frame mask cannot express.",
    "An explicit reference channel can contribute spatial and coherence evidence, but only when the real channels are distinct and synchronized.",
])
doc.add_heading("Training objectives", level=2)
add_table(doc, ["Loss or constraint", "Purpose"], [
    ["SI-SNR loss", "Optimize scale-invariant waveform similarity and speech separation."],
    ["Scale-sensitive SNR loss", "Prevent the model from exploiting arbitrary output scaling."],
    ["Waveform L1", "Penalize sample-domain reconstruction error."],
    ["Power-compressed complex loss", "Constrain real and imaginary spectral reconstruction while emphasizing perceptually relevant structure."],
    ["Power-compressed magnitude and multi-resolution spectral loss", "Improve spectral envelope and harmonic detail across resolutions."],
    ["Phase-consistency loss", "Reduce phase-related reconstruction artifacts."],
    ["Spectral-delta and spectral-hole penalties", "Discourage temporal discontinuities and missing speech bands associated with robotic voice."],
    ["Clean-identity loss", "Keep clean input close to unchanged output."],
    ["Speech-retention or transient-over-speech loss", "Penalize deletion when impulse or dynamic noise overlaps active speech."],
    ["STOI-envelope surrogate", "Tested in v10b to improve intelligibility reliability; numerically repaired but did not earn promotion."],
])
doc.add_heading("Dataset pipeline", level=2)
add_table(doc, ["Dataset", "Role", "Handling and limitation"], [
    ["VCTK Corpus", "Clean speech", "Recursive speaker-aware indexing; mono conversion and 16 kHz resampling at load time. Accent/language coverage is not sufficient for final Indian defence users."],
    ["MUSAN", "Stationary, ambient, music or competing-speech interference", "Category mapping by source metadata/path; license must be verified for the intended use."],
    ["ESC-50", "Environmental and event noise", "Preserve source/fold isolation; CC BY-NC terms require review for any commercial path."],
    ["MAD dataset", "Military acoustic events including gunshot, shelling, vehicle, helicopter, fighter and related labels", "Weighted in training and evaluated separately; public data is not a substitute for classified or target-device recordings."],
    ["Small UAV acoustics", "Drone and UAV rotor patterns", "Indexed in place; flight/session grouping must prevent leakage."],
    ["RIRS_NOISES", "Room impulse responses and environmental acoustics", "Used for reverberation and channel simulation; synthetic RIR application cannot validate real microphone geometry."],
])
para(doc, "The scanner accepts nested subfolders and arbitrary filenames. Known corpus adapters use metadata and path conventions where available. Audio is decoded on demand, averaged to mono when appropriate, resampled with polyphase filtering to 16 kHz and converted to float32. The mixer draws segments dynamically rather than creating a second full corpus copy.")
doc.add_heading("Mixture generation and augmentation", level=2)
bullets(doc, [
    "Noise classes: stationary, non-stationary, impulsive, environmental and mixed.",
    "Preservation cases: exact clean and near-clean examples at high SNR.",
    "SNR curriculum: broad and military ranges including difficult negative-SNR examples.",
    "Multiple noise sources and defence-source weighting for training only.",
    "Random gain, reverberation/RIR, clipping simulation, active-region selection and simulated primary/reference paths.",
    "Fixed validation pairs use stored manifests and deterministic seeds so model comparisons use identical examples.",
    "Group-aware splits reduce speaker, source, recording-session and RIR leakage; source metadata remains important because filename hashing alone cannot prove acoustic independence.",
])
doc.add_heading("Training and reproducibility", level=2)
bullets(doc, [
    "Configuration-driven recipes separate model, data, optimization, loss and output paths.",
    "Checkpointing stores model, optimizer, scheduler, scaler, epoch and best-selection state so interrupted runs can resume.",
    "Training and validation statistics are written to structured logs; best and latest checkpoints are retained.",
    "Persistent-worker epoch propagation was repaired using shared state so new deterministic mixtures appear each epoch on Windows spawn workers.",
    "Fixed validation is never silently replaced or overwritten, and invalid noisy-clean identity pairs now fail the engineering gate.",
    "Early stopping and bounded fine-tuning reduce unnecessary compute and benchmark overfitting.",
])
doc.add_heading("Model evolution and lessons learned", level=2)
add_table(doc, ["Stage", "What changed", "Observed result and decision"], [
    ["Initial tiny causal model", "Approximately 19,850 parameters; basic complex enhancement.", "Training loss improved, but evaluation SNR regressed and listening reported remaining noise and voice damage."],
    ["v3 official GTCRN", "Official-style GTCRN comparison and ONNX state export.", "Better reference baseline, but early results still did not solve preservation and military generalization."],
    ["v4 compact hybrid dual channel", "12,259-parameter causal complex plus ERB model, defence categories and preservation losses.", "Strong noisy-only improvement but clean/near-clean and impulsive gates repeatedly exposed regressions."],
    ["v5 mono corrective audit", "Corrected data defects, untrained high-pass conditioning, state leakage, invalid pairs and PESQ installation.", "Established that previous capacity conclusions were confounded; model quality still needed improvement."],
    ["v6 UL-UNAS exploration", "Upstream architecture audit and mono lightweight trials.", "Useful comparison but not automatically superior on the defence manifests."],
    ["v7 fusion dual UL-UNAS", "Primary/reference fusion, spatial features and live dashboard.", "Broad strict gate passed on a sampled set; military remained weak; laptop-array duplicate channels exposed hardware limitations."],
    ["v8 signed-phase correction", "Corrected imaginary/sign behavior and retrained.", "Large improvement versus v7; frozen military mean still around 10.6 dB output SNR, 0.817 STOI and 2.37 PESQ in the cited comparison."],
    ["v9 hard-tail fine-tune", "Focused on difficult military tails.", "Rejected because it did not improve the frozen comparison sufficiently."],
    ["v10 deep-filter dual", "Larger recurrent capacity and five-tap multi-frame deep filtering.", "Selected baseline; broad strict pass and major military gains; remaining gap is per-file STOI reliability."],
    ["v10b STOI fine-tune", "Added STOI-envelope objective and stability repairs.", "Completed but rejected; no target-rate gain and military PESQ reliability declined."],
])
doc.add_heading("v10b numerical failure and repair", level=2)
para(doc, "The v10b run initially produced finite forward losses while the AMP gradient scaler fell to zero. The root cause was the infinite derivative of sqrt(0) in inactive STOI-envelope bands and centered correlation windows. Masking after the square root was unsafe because zero multiplied by NaN can remain NaN during backpropagation. The repair clamps energies before square root, returns differentiable zero for fully inactive examples, validates saved scaler state, distinguishes recoverable AMP overflow from fatal full-precision non-finite gradients and refuses zero or non-finite scaler state before checkpointing. The repaired run completed and the full suite passed, but its frozen metrics did not justify promotion.")
doc.add_heading("Performance benchmarks", level=2)
add_table(doc, ["Frozen audit 50 files", "Output SNR", "STOI", "PESQ", "SNR target rate", "STOI target rate", "PESQ target rate", "All three", "Result"], [
    ["Broad v10", "23.645 dB", "0.9213", "3.7018", "80.0%", "82.9%", "91.4%", "74.3%", "PASS"],
    ["Broad v10b", "23.748 dB", "0.9231", "3.7272", "80.0%", "82.9%", "91.4%", "74.3%", "PASS"],
    ["Military v10", "19.455 dB", "0.8926", "3.3911", "84.2%", "68.4%", "86.8%", "60.5%", "FAIL STOI reliability"],
    ["Military v10b", "19.452 dB", "0.8956", "3.3919", "84.2%", "68.4%", "84.2%", "60.5%", "FAIL STOI reliability"],
], numeric_cols=(1,2,3,4,5,6,7))
para(doc, "The strict development gate requires mean output SNR above 15 dB, mean STOI above 0.85, mean PESQ above 2.5, speech deletion no greater than 2 percent, clean active-level error no greater than 1 dB, at least 80 percent individual attainment for each target and at least 60 percent joint attainment. Broad v10 passes. Military v10 passes the mean and joint targets but has 26 of 38 noisy clips above the STOI threshold, or 68.4 percent. Reaching 80 percent requires at least 31 of 38, approximately five additional clips.")
doc.add_heading("DNSMOS and subjective-quality evidence", level=2)
para(doc, "Optional DNSMOS evaluation was integrated as a supplementary non-intrusive quality indicator. On the shared military comparison referenced in the project status, v10 achieved approximately 2.56 DNSMOS OVRL versus 2.14 for v8. DNSMOS is not a replacement for PESQ, STOI or human listening and should not be used as a certification claim.")
doc.add_heading("Runtime and deployment behavior", level=2)
bullets(doc, [
    "The live audio callback does not wait for neural inference; a bounded worker handles frames.",
    "Late output uses the correctly aligned dry primary block to avoid discontinuity and stale speech.",
    "Non-finite output, worker failures, repeated overruns or invalid channel geometry trigger degraded or bypass mode.",
    "Dry/wet mixing allows conservative deployment when full enhancement sounds unnatural.",
    "Raw channel correlation and normalized difference help detect duplicated laptop microphone-array channels.",
    "Telemetry records submitted, enhanced and bypass blocks, output underflows, dropped input, resets and worker failures.",
])
doc.add_heading("ONNX and quantization decision", level=2)
para(doc, "FP32 ONNX is the selected deployment format. Dynamic INT8 weight quantization reduced the v10 file from 4,694,817 bytes to 3,880,831 bytes, or 82.66 percent of the FP32 size, and passed a corruption-guard tolerance. It was slower for the tested GRU-heavy frame-by-frame workload, approximately 3.42 ms versus 2.16 ms per frame in the recorded comparison. INT8 was therefore rejected rather than presented as an automatic optimization.")
doc.add_heading("APIs and third-party dependencies", level=2)
add_table(doc, ["Dependency", "Purpose", "Operational dependence"], [
    ["PyTorch", "Training, checkpointing and reference inference", "Required for training and export; not required for ONNX-only live inference."],
    ["ONNX and ONNX Runtime", "Portable graph and CPU inference", "Core deployment dependency."],
    ["NumPy SciPy SoundFile", "Signal processing, resampling and audio I/O", "Local runtime/data dependencies."],
    ["sounddevice PortAudio", "Laptop live capture and playback", "Prototype I/O; final hardware may use ALSA or a native audio service."],
    ["pystoi and PESQ 0.0.4", "Objective intelligibility and quality evaluation", "Evaluation only; not part of live audio."],
    ["speechmos DNSMOS", "Optional non-intrusive quality estimate", "Evaluation only and supplementary."],
    ["TensorBoard", "Training visualization", "Development only."],
    ["No cloud API", "The selected inference path is local", "Avoids internet dependency in the audio path."],
])
doc.add_heading("Technical defensibility", level=2)
para(doc, "The defensible engineering contribution is the integrated evidence loop: corpus-specific ingestion, group-aware and defence-weighted mixture generation, preservation-aware losses, full-band plus sub-band complex modeling, multi-frame filtering, per-source reliability gates, numerical export validation, nonblocking streaming, channel-quality diagnostics and safe degraded behavior. Individual neural layers are not claimed as proprietary inventions. The practical moat grows only after Team@ collects consented target-hardware recordings and calibration data that competitors cannot reproduce from public corpora alone.")

section_title(doc, 6, "SECURITY COMPLIANCE AND DATA GOVERNANCE")
doc.add_heading("Security architecture", level=2)
bullets(doc, [
    "Default to offline local inference; do not send live tactical audio to a cloud service.",
    "Verify checkpoint and ONNX hashes before deployment and keep the selected model/config version in session telemetry.",
    "Run the live process with least privilege and restrict write access to model, configuration and logs.",
    "Use encrypted storage and authenticated transfer for any operational recordings or model updates when required by the deployment authority.",
    "Maintain an explicit software bypass and, for safety-critical hardware, an independent hardware or system-level bypass path.",
    "Treat logs as potentially sensitive because timestamps, device names and acoustic conditions can reveal operational information.",
])
doc.add_heading("Compliance status", level=2)
add_table(doc, ["Area", "Current status", "Required before operational deployment"], [
    ["Information security certification", "None claimed", "Applicable DRDO/defence security review and organizational controls."],
    ["Dataset licensing", "Source-specific warnings documented", "Create signed inventory with dataset version, URL, license, checksum, permitted use and redistribution limits."],
    ["Human speech consent", "No project-wide consent record claimed", "Consent, purpose limitation, access control and deletion process for local recordings."],
    ["Model assurance", "Hashes, parity and tests exist", "Independent review, signed releases, SBOM and controlled update/rollback procedure."],
    ["Safety and EMC environmental qualification", "Not performed", "Hardware qualification appropriate to the intended platform and environment."],
    ["Defence certification", "Not performed", "Authority-defined evaluation on approved scenarios and equipment."],
])
doc.add_heading("Data retention and privacy policy proposal", level=2)
numbered(doc, [
    "Process live audio in memory by default and do not retain it unless a test protocol explicitly requires recording.",
    "For research captures, store the minimum audio and metadata needed for the stated experiment under a unique study identifier.",
    "Separate identity/contact records from acoustic data and restrict access by role.",
    "Record dataset origin, consent or license basis, collection date, device, room, source labels and deletion date.",
    "Delete recordings at the end of the approved retention period or on a valid withdrawal request, subject to legal/defence obligations.",
    "Do not use customer or operational audio to train a global model without explicit authorization and an approved de-identification and governance process.",
])
doc.add_heading("Isolation and availability", level=2)
para(doc, "The present prototype is file-based and single-deployment; it has no shared multi-tenant database. A production management plane should keep each deployment's models, calibration, logs and recordings logically or physically isolated. No 99.95 percent uptime SLA is claimed. Availability evidence must come from target-device soak tests, watchdog recovery, power interruption tests and hardware bypass validation.")

section_title(doc, 7, "COMMERCIALS HACKATHON SCOPE AND IMPLEMENTATION")
doc.add_heading("Pricing and unit economics", level=2)
para(doc, "The project has no approved product price, customer-acquisition history, revenue or procurement quote. A factual pricing matrix, CAC, LTV and LTV-to-CAC ratio cannot be calculated yet. For competition discussion, frame commercialization as an integration and licensing model whose price depends on hardware, qualification, customization, support and volume. Do not insert invented rupee figures.")
add_table(doc, ["Potential offering", "Scope", "Pricing basis to validate"], [
    ["Evaluation kit", "Pi 5 or equivalent edge device, audio interface, headset, selected model, dashboard and reports.", "BOM, assembly, support and pilot duration."],
    ["Integrator SDK license", "ONNX model, runtime, APIs, calibration tools and documentation for radio/headset integration.", "Per-device, per-program or annual engineering license."],
    ["Domain adaptation service", "Authorized data capture, fine-tuning, validation and model card for a target platform.", "Engineering effort, secure environment and qualification scope."],
    ["Enterprise or government support", "Controlled releases, long-term support, on-premises update service and audit assistance.", "SLA, deployment count and security obligations."],
])
doc.add_heading("Go to market channels", level=2)
bullets(doc, [
    "DRDO or defence-lab technical pilot under a controlled evaluation plan.",
    "Partnership with Indian headset, intercom, radio and rugged-compute integrators.",
    "Licensing or technology transfer after qualification, with on-premises deployment and support.",
    "Secondary regulated or high-noise markets such as aerospace ground crew, emergency response and heavy industry only after the defence core is validated.",
])
doc.add_heading("Current traction", level=2)
para(doc, "No revenue, paid user, waitlist, ministry pilot approval or client testimonial is documented. Current traction is technical: a complete repository, trained v10 checkpoint, verified ONNX export, frozen broad and military audits, saved listening files, live laptop runtime, dashboard, Pi deployment scaffolding and 102 passing tests.")
doc.add_heading("36 hour hackathon scope and feasibility", level=2)
add_table(doc, ["Can demonstrate within hackathon", "Should not be promised as completed"], [
    ["Repository walkthrough, data pipeline, model architecture and training evidence", "New full-scale training from zero during the event"],
    ["Offline before/after audio from frozen broad and military audits", "Field blast testing or classified operational evidence"],
    ["Objective report with SNR, SI-SNR, STOI, PESQ and reliability", "Certification based on a 50-file development subset"],
    ["ONNX parity, hashes and CPU benchmark", "Unmeasured Pi power, latency or thermal claims"],
    ["Headphone-based laptop live demo with safe wet mix", "Correct dual-channel proof from duplicated laptop-array channels"],
    ["Pi installation and benchmark procedure", "Physical acoustic anti-noise cancellation without secondary-path hardware"],
])
doc.add_heading("Implementation and onboarding blueprint", level=2)
add_table(doc, ["Phase", "Activities", "Exit evidence"], [
    ["1  Discovery", "Define radio/headset path, noise classes, latency budget, privacy and acceptance thresholds.", "Signed system and test requirements."],
    ["2  Hardware characterization", "Measure microphones, gain, clipping, clocking, reference leakage, sample rate and I/O latency.", "Calibration report and synchronized capture."],
    ["3  Data capture", "Collect consented speech and target noises across devices, rooms, motion and SNR.", "Provenance-controlled train/validation/untouched test partitions."],
    ["4  Adaptation", "Fine-tune from v10, run ablations and reject regressions.", "Frozen reports, hashes, listening evaluation and model card."],
    ["5  Edge integration", "Deploy FP32 ONNX, tune threads/buffers, implement watchdog and bypass.", "Pi p50/p95/p99, RTF, CPU/RAM/temp/power and soak report."],
    ["6  Controlled pilot", "Evaluate agreed scenarios and collect structured operator feedback.", "Acceptance report with failures, not only averages."],
    ["7  Qualification", "Security, environmental, safety, maintainability and production review.", "Authority-approved release decision."],
])
doc.add_heading("Anti scope for version one", level=2)
bullets(doc, [
    "No claim of cancelling acoustic sound throughout a room or vehicle cabin.",
    "No cloud speech recognition, translation or command interpretation in the core V1 path.",
    "No use of classified or personally sensitive recordings without an approved process.",
    "No universal guarantee for all weapons, vehicles, headsets, languages or SNRs.",
    "No automatic deployment of a model that fails frozen quality, preservation, listening or hardware gates.",
    "No GUI-first scope expansion until audio quality and target-hardware evidence are stable.",
])

section_title(doc, 8, "FINANCIAL MODELING TEAM AND CAPITAL STRUCTURE")
doc.add_heading("Three year financial model", level=2)
para(doc, "A factual financial projection cannot be derived from the code repository. Revenue, OpEx and profit must remain unclaimed until Team@ defines a product, pilot price, sales channel, staffing and qualification budget. Use the following model structure and show assumptions beside every number.")
add_table(doc, ["Line item", "Year 1 validation", "Year 2 pilots", "Year 3 scale"], [
    ["Gross revenue", "Team input required", "Team input required", "Team input required"],
    ["Hardware and manufacturing cost", "Team input required", "Team input required", "Team input required"],
    ["Engineering and data cost", "Team input required", "Team input required", "Team input required"],
    ["Testing certification and secure infrastructure", "Team input required", "Team input required", "Team input required"],
    ["Sales support and administration", "Team input required", "Team input required", "Team input required"],
    ["Net profit or loss", "Derived after assumptions", "Derived after assumptions", "Derived after assumptions"],
])
doc.add_heading("Resource ask and milestone tranches", level=2)
para(doc, "No approved funding ask exists. A technically grounded resource request should be milestone-based rather than a single unsupported figure.")
add_table(doc, ["Tranche", "Use", "Release condition"], [
    ["1  Evidence hardware", "Synchronized two-input interface or codec, microphones/headsets, Pi 5 cooling/power, measurement and loopback equipment.", "Approved BOM and test plan."],
    ["2  Data and model", "Controlled recordings, annotation, secure storage, failure-targeted v11 experiments and listening study.", "Provenance and consent review; untouched test set frozen."],
    ["3  Integration pilot", "Rugged packaging, radio/intercom interface, field-like controlled trials and engineering support.", "Laptop and Pi gates passed; safety bypass verified."],
    ["4  Qualification", "Security, environmental, reliability, documentation and productionization.", "Pilot acceptance and authority-defined qualification plan."],
])
doc.add_heading("Team and governance fields", level=2)
add_table(doc, ["Field", "Current factual entry"], [
    ["Team name", "Team@"],
    ["Core member names and biographies", "Team input required. Add only verified roles and two-sentence relevant expertise."],
    ["Advisors and mentors", "Team input required. Do not list a person without permission."],
    ["Cap table or equity", "Not applicable to the technical repository; team input required if a company exists."],
    ["Immediate hiring roadmap", "Recommended roles: embedded audio engineer, DSP/control engineer, ML/audio researcher, data and test engineer, hardware integration engineer, security/QA lead."],
])
doc.add_heading("Long term vision", level=2)
para(doc, "The credible long-term path is qualification as an embedded communication enhancement component that can be integrated into Indian headsets, intercoms and radios, with on-premises adaptation and audit tooling. Technology transfer, licensed integration or a strategic partnership is more realistic than claiming a specific acquirer. Physical ANC can become a separate product line only after stable secondary-path hardware validation.")

section_title(doc, 9, "MANDATORY SIH RESEARCH DATASETS AND BRAND ASSETS")
doc.add_heading("Open source and public datasets", level=2)
add_table(doc, ["Resource", "Use in project", "Governance note"], [
    ["VCTK Corpus", "Clean speech training and evaluation source", "Preserve speaker-disjoint splits and verify current license."],
    ["MUSAN", "General noise, ambient, music and competing speech", "Verify permitted use and source isolation."],
    ["ESC-50", "Environmental events", "CC BY-NC; review compatibility with future commercialization."],
    ["MAD military audio dataset", "Military-labelled gunshot, shelling, helicopter, fighter, vehicle and related noise", "Use source/session groups; public proxy does not establish battlefield coverage."],
    ["Small UAV acoustics", "UAV and rotor acoustic variation", "Preserve flight/session separation and license record."],
    ["RIRS_NOISES", "Room impulse response and noise augmentation", "Document version, source and permitted redistribution."],
])
doc.add_heading("Academic and technical foundations", level=2)
add_table(doc, ["Reference", "Relevance", "How VoxShield uses it"], [
    ["Rong et al  GTCRN  Streamable Speech Enhancement with Grouped Temporal Convolution and Recurrent Neural Network  official repository github.com/Xiaobin-Rong/gtcrn", "Lightweight causal complex speech enhancement and stateful inference.", "Used as an audited comparison and source of causal design ideas; not blindly treated as the final answer."],
    ["Rong et al  UL-UNAS  ultra-low-latency neural architecture search for speech enhancement  arXiv 2503.00340 and github.com/Xiaobin-Rong/ul-unas", "Efficient low-latency enhancement architecture.", "Explored in v6 and the dual-fusion development line."],
    ["Schroter et al  DeepFilterNet  A Low Complexity Speech Enhancement Framework for Full-Band Audio based on Deep Filtering  arXiv 2110.05588", "Multi-frame deep filtering for speech enhancement.", "Motivated the v10 five-tap causal deep-filter output; implementation remains project-specific."],
    ["Taal et al  A Short-Time Objective Intelligibility Measure for Time-Frequency Weighted Noisy Speech  ICASSP 2010", "STOI intelligibility metric.", "Used for evaluation and motivated the experimental v10b differentiable envelope objective."],
    ["ITU-T Recommendation P.862 PESQ", "Intrusive perceptual speech-quality evaluation.", "PESQ 0.0.4 is installed and validated against known samples for paired 16 kHz evaluation."],
    ["ONNX Runtime documentation  onnxruntime.ai/docs", "Portable and optimized model inference.", "Used for FP32 edge deployment and numerical parity testing."],
])
doc.add_heading("Ministry and standards alignment", level=2)
para(doc, "The project aligns technically with the requirements written in PS 26052: defence-noise categories, noisy-clean pair generation, full/sub-band and complex processing, SI-SNR and spectral/perceptual training objectives, real-time edge inference, ONNX optimization, microphone/headset integration and the stated SNR/STOI/PESQ targets. No separate DRDO manual, formal security directive or procurement standard has been supplied or verified in the repository. Team@ must add only official documents obtained through the SIH portal, DRDO sponsor or authorized mentor.")
doc.add_heading("Testimonials and case studies", level=2)
para(doc, "No verified client testimonial, operational case study or DRDO endorsement exists in the project record. Informal listening comments may guide development but must not be presented as a customer testimonial. A future case study should state device, room, noise source, SNR, participant count, protocol, before/after samples, objective results, subjective scores and limitations.")
doc.add_heading("Brand guidelines", level=2)
add_table(doc, ["Element", "Recommended controlled use"], [
    ["Name", "VoxShield"],
    ["Team", "Team@"],
    ["Primary colors", "Navy #17365D, blue #2F75B5, white #FFFFFF and neutral gray #666666."],
    ["Status colors", "Green only for passed measured gates; amber for pending or conditional; red for failed or unsafe conditions."],
    ["Typography", "Aptos or another legible sans-serif; avoid decorative military styling that reduces clarity."],
    ["Metric labeling", "Always include dataset, sample count, model version, hardware/backend and whether the value is mean or per-file reliability."],
    ["Logos", "Use official SIH/DRDO marks only according to organizer permission and supplied brand assets. No local vector package is verified by this document."],
])

# Appendices
doc.add_page_break()
doc.add_heading("APPENDIX A  Current completion and remaining plan", level=1)
add_table(doc, ["Workstream", "Approximate completion", "Reason"], [
    ["Core repository and modular software", "90-95%", "Data, training, evaluation, export, inference, monitoring, tests and docs are present."],
    ["Model research and frozen development evidence", "85-90%", "v10 is strong; military per-file STOI reliability and unseen test proof remain."],
    ["Synthetic paired evaluation", "About 90%", "Broad and military audits exist; larger untouched testing and confidence intervals remain."],
    ["Real synchronized dual-microphone proof", "30-40%", "Software path exists, but final hardware and target recordings are missing."],
    ["Raspberry Pi 5 proof", "40-50%", "Scripts exist; final v10 benchmark, thermal, power, soak and loopback evidence remain."],
    ["Physical acoustic ANC", "10-20%", "Control concepts explored; no validated secondary-path hardware loop."],
    ["Overall competition readiness", "75-80%", "Enough for a strong honest PPT and demo narrative; hardware evidence is the major gap."],
])
doc.add_heading("Prioritized next plan", level=2)
add_table(doc, ["Priority", "Action", "Acceptance criterion"], [
    ["P0", "Freeze a genuinely untouched broad and military test set from source/session-disjoint recordings.", "No model or threshold decision has used the set before final evaluation."],
    ["P0", "Review the 12 v10 military STOI failures, mainly vehicle/helicopter and roughly -13 to +6 dB.", "Each failure has verified label, clean/noisy alignment and listening diagnosis."],
    ["P0", "Add one augmentation at a time: microphone response, AGC/limiter, codec, moving source/Doppler and independent channel RIR.", "Ablation shows benefit without broad, clean or PESQ regression."],
    ["P0", "Train bounded v11 specialization from v10 rather than restarting blindly.", "Military STOI reliability >=80%, broad strict pass retained and listening not worse."],
    ["P1", "Run matched-level blinded listening for naturalness, intelligibility and artifacts.", "Predefined sample set, multiple listeners and reproducible scoring."],
    ["P1", "Acquire synchronized two-input hardware and record target-device sessions.", "Measured channel distinction, delay, leakage, clipping and metadata."],
    ["P1", "Deploy v10 FP32 ONNX to Raspberry Pi 5.", "p50/p95/p99, RTF, CPU/RAM, temperature, throttling, power, underflow and soak report."],
    ["P1", "Measure physical microphone-to-headphone latency.", "Loopback result and jitter distribution; not inferred from model timing."],
    ["P2", "Revisit FxNLMS physical ANC only with calibrated secondary path.", "Stable cancellation without speech corruption and with independent emergency bypass."],
    ["P2", "Complete legal/provenance and release documentation.", "Dataset inventory, SBOM, model card, licenses, hashes and rollback procedure."],
])

doc.add_page_break()
doc.add_heading("APPENDIX B  Demonstration and validation plan", level=1)
doc.add_heading("Reliable laptop demonstration", level=2)
numbered(doc, [
    "Use headphones to prevent acoustic feedback.",
    "List devices because Windows indices change when hardware reconnects.",
    "First play paired saved audio at matched level: noisy input, enhanced output and clean target.",
    "Show the corresponding JSON report and identify model, manifest and sample count.",
    "Run live audio with a conservative wet mix; explain normal, degraded and bypass modes.",
    "Do not call duplicated laptop-array channels a real noise-reference microphone.",
])
doc.add_heading("Raspberry Pi 5 demonstration", level=2)
numbered(doc, [
    "Install 64-bit Raspberry Pi OS, a suitable power supply and active cooling.",
    "Use a supported USB audio interface or headset. For dual-channel evidence, both inputs must share one clock.",
    "Install runtime dependencies and copy the selected FP32 ONNX, configuration and recorded hashes.",
    "Verify offline inference before opening live audio.",
    "Benchmark one ONNX thread first and record mean, p50, p95, p99, RTF, callback time, memory, CPU and temperature.",
    "Run live monitoring with headphones and confirm sustained underflows remain zero.",
    "Measure true end-to-end latency with a physical loopback, then perform a 30-60 minute thermal soak.",
])
doc.add_heading("Key PowerShell verification commands", level=2)
code(doc, 'cd C:\\anc')
code(doc, '& ".\\.venv\\Scripts\\python.exe" -m pytest -q')
code(doc, '& ".\\.venv\\Scripts\\voxshield-export.exe" --checkpoint ".\\checkpoints_deep_filter_v10\\best.pt" --output ".\\artifacts\\voxshield-v10-deep-filter-final.onnx"')
code(doc, '& ".\\.venv\\Scripts\\voxshield-evaluate.exe" --checkpoint ".\\checkpoints_deep_filter_v10\\best.pt" --onnx ".\\artifacts\\voxshield-v10-deep-filter-final.onnx" --manifest ".\\data\\mixtures\\audit_broad_val\\manifest.jsonl" --device cpu --limit 50 --strict-sih-gate --output ".\\artifacts\\v10-final-broad-50.json"')
code(doc, '& ".\\.venv\\Scripts\\voxshield-evaluate.exe" --checkpoint ".\\checkpoints_deep_filter_v10\\best.pt" --onnx ".\\artifacts\\voxshield-v10-deep-filter-final.onnx" --manifest ".\\data\\mixtures\\audit_military_val\\manifest.jsonl" --device cpu --limit 50 --strict-sih-gate --expected-noisy-categories "impulsive,nonstationary,mixed" --output ".\\artifacts\\v10-final-military-50.json"')
para(doc, "Exact live and Pi commands must be checked against the current CLI help and actual device indices immediately before the demonstration. Device numbers shown in earlier sessions are not stable identifiers.")

doc.add_page_break()
doc.add_heading("APPENDIX C  Claims permitted and prohibited", level=1)
add_table(doc, ["Safe factual claim", "Claim that must not be made yet"], [
    ["VoxShield was built from an empty project inside C:\\anc.", "The system is defence certified or field proven."],
    ["v10 is a causal dual-channel complex deep-filter model with 1,116,813 parameters.", "v10 is simply GTCRN plus UL-UNAS or a published model copied unchanged."],
    ["Broad frozen development audit passes the defined strict gate.", "All possible broad conditions are solved."],
    ["Military mean SNR/STOI/PESQ and joint attainment pass on the 50-file audit.", "Military reliability fully passes; STOI target rate is currently 68.4%."],
    ["Zero energy-threshold speech deletion was measured on the two audits.", "No word or consonant can ever be deleted."],
    ["FP32 ONNX numerically matches PyTorch within tolerance.", "INT8 is faster or selected; it was slower in the tested workload."],
    ["Pi 5 deployment scripts exist and deployment is plausible.", "Final v10 Pi latency, power and thermal targets have been measured."],
    ["A live laptop engineering demo exists.", "Laptop speaker playback is a calibrated tank, artillery or blast field test."],
    ["Reference-channel processing is implemented.", "Two arbitrary consumer microphones provide synchronized tactical spatial evidence."],
    ["Speech enhancement and noise suppression are implemented.", "Physical acoustic anti-noise ANC is complete."],
])

doc.add_page_break()
doc.add_heading("APPENDIX D  Evidence registry", level=1)
add_table(doc, ["Evidence", "Repository location", "Meaning"], [
    ["Selected checkpoint", "C:\\anc\\checkpoints_deep_filter_v10\\best.pt", "Best v10 weights selected at epoch 58."],
    ["Selected ONNX", "C:\\anc\\artifacts\\voxshield-v10-deep-filter-final.onnx", "Deployment graph."],
    ["ONNX validation", "C:\\anc\\artifacts\\voxshield-v10-deep-filter-final.validation.json", "Hashes, architecture and PyTorch parity."],
    ["Broad audit", "C:\\anc\\artifacts\\v10-final-broad-50.json", "Frozen 50-file broad metrics and gate."],
    ["Military audit", "C:\\anc\\artifacts\\v10-final-military-50.json", "Frozen 50-file military metrics and gate."],
    ["DNSMOS broad", "C:\\anc\\artifacts\\v10-final-broad-50-dnsmos.json", "Supplementary non-intrusive quality estimates."],
    ["DNSMOS military", "C:\\anc\\artifacts\\eval_temp\\v10-final-military-50-dnsmos.json", "Supplementary military quality estimates."],
    ["Rejected v10b checkpoint", "C:\\anc\\checkpoints_deep_filter_v10b_stoi\\best.pt", "Reproducible but not promoted."],
    ["v10b ONNX", "C:\\anc\\artifacts\\voxshield-v10b-stoi-final.onnx", "Rejected experiment export."],
    ["Completion record", "C:\\anc\\docs\\project-completion-status.md", "Current selection, results, defect repair and remaining work."],
    ["Corrective audit", "C:\\anc\\docs\\2026-09-audit.md", "Earlier defects, fixes, PESQ evidence and claim boundaries."],
    ["Architecture", "C:\\anc\\docs\\architecture.md", "Signal path, causality and runtime contract."],
    ["Dataset guide", "C:\\anc\\docs\\datasets.md", "Acquisition, layout, category and integrity rules."],
    ["Pi deployment", "C:\\anc\\docs\\deployment-pi5.md", "Pi installation, benchmark and live-test procedure."],
])

doc.add_page_break()
doc.add_heading("APPENDIX E  Final competition conclusion", level=1)
para(doc, "Team@ can make a technically strong and credible SIH presentation now. The project demonstrates an unusually complete data-to-edge software chain, documents failures instead of hiding them and has a selected model that passes the broad strict development gate while producing major military-domain gains. The most important remaining task is not another uncontrolled architecture change. It is to close the military per-file STOI reliability gap with failure-driven data and then prove the same artifact on synchronized microphones and Raspberry Pi 5 under a frozen, unseen evaluation protocol.")
para(doc, "The correct final status is: VoxShield is a competition-ready engineering prototype for real-time defence communication speech enhancement. It is not yet a defence-qualified product and not yet a validated physical acoustic ANC system. That distinction makes the proposal more credible, because the next milestones, hardware requirements, acceptance criteria and risks are explicit.")

doc.add_page_break()
doc.add_heading("APPENDIX F  Six slide SIH presentation source", level=1)
para(doc, "This appendix extracts presentation-ready content from the technical record. It does not replace the detailed evidence in Sections 1-9. Values are tied to the selected v10 checkpoint and frozen 50-file development audits unless explicitly marked as pending or proposed.")

doc.add_heading("Slide 1  Title and mandatory identity", level=2)
add_table(doc, ["Element", "Presentation text"], [
    ["Project", "VoxShield"],
    ["Problem statement", "AI ML enabled adaptive noise cancellation for stationary, non-stationary and impulsive defence noise with intelligible speech and edge real-time performance"],
    ["PS ID", "26052"],
    ["Organization", "DRDO  Department of Defence R&D"],
    ["Category and theme", "Hardware  Miscellaneous"],
    ["Team", "Team@"],
    ["Registration ID", "Team input required before submission"],
    ["Member names", "Team input required before submission"],
    ["Institute or college", "Team input required before submission"],
])
doc.add_heading("Slide 1 submission completion checklist", level=3)
bullets(doc, [
    "Registration ID: copy the exact identifier from the SIH portal; do not infer it from PS ID 26052.",
    "Member names: use the spelling and order registered on the SIH portal.",
    "Institute or college: use the official registered institution name and location.",
])

doc.add_heading("Slide 2  Proposed solution", level=2)
para(doc, "Headline: A causal dual-channel complex-domain speech-enhancement engine that uses full-band, ERB/sub-band and multi-frame evidence to suppress defence noise while preserving speech, then runs locally through stateful FP32 ONNX with monitored degraded and bypass modes.")
add_table(doc, ["Measured military headline", "v10 value", "PS target", "Interpretation"], [
    ["Mean output SNR", "19.455 dB", ">15 dB", "Mean target passed on the 50-file military development audit."],
    ["Mean STOI", "0.8926", ">0.85", "Mean target passed; per-file target reliability is 68.4% against the internal 80% requirement."],
    ["Mean PESQ", "3.3911", ">2.5", "Mean target passed; per-file target reliability is 86.8%."],
    ["Speech deletion rate", "0.0%", "<=2% internal gate", "Passed on the broad and military frozen audits; does not prove every phoneme is preserved."],
    ["v10 frame latency", "Pending repeatable benchmark artifact", "Real time", "Do not reuse the 2.16 ms v3 benchmark as a v10 result."],
], numeric_cols=(1,2))
doc.add_heading("Slide 2 solution bullets", level=3)
bullets(doc, [
    "Causal dual-channel neural pipeline: synchronized primary and noise-reference spectra feed the selected v10 deep-filter dual core.",
    "Complex and multi-frame processing: full-band plus ERB/sub-band context and a five-tap causal deep filter preserve phase and temporal structure.",
    "Fail-safe local deployment: stateful FP32 ONNX, dry/wet control, normal/degraded/bypass modes and runtime health telemetry.",
])
doc.add_heading("Slide 2 pipeline visual text", level=3)
para(doc, "Primary microphone plus synchronized reference microphone -> conditioning and causal STFT -> complex and ERB/spatial features -> v10 recurrent deep-filter core -> five-tap complex reconstruction -> WOLA waveform -> conservative dry/wet output and safety monitor -> headset or communication unit.")
para(doc, "Do not draw a Wiener pre-filter or LMS residual stage as part of the selected v10 production path. Classical and adaptive filters were evaluated, but the current evidence does not support claiming that three-stage chain as the promoted system.")
doc.add_heading("Slide 2 evidence badges", level=3)
bullets(doc, [
    "114,805 indexed catalog rows across speech, noise and RIR assets; this is not 114,805 defence-noise files.",
    "0.0 percent measured speech-deletion rate on the two frozen 50-file audits.",
    "FP32 ONNX parity passed with maximum enhanced-output error 6.10 x 10^-8.",
])

doc.add_page_break()
doc.add_heading("Slide 3  Technical approach", level=2)
doc.add_heading("Architecture diagram text", level=3)
code(doc, "[Primary microphone] ------\\\n                              > [Causal STFT] -> [Complex primary/reference features]\n[Reference microphone] -----/                       |\n                                                     v\n                                      [Full-band plus ERB context]\n                                                     |\n                                                     v\n                                        [Causal recurrent core]\n                                                     |\n                                                     v\n                                      [Five-tap multi-frame filter]\n                                                     |\n                                                     v\n                                [Complex reconstruction -> WOLA -> output]")
add_table(doc, ["Technical specification", "Verified value"], [
    ["Architecture", "deep_filter_dual"],
    ["Trainable parameters", "1,116,813"],
    ["Audio format", "16 kHz float32; primary plus synchronized reference for the dual path"],
    ["Streaming", "Causal stateful frame processing with explicit recurrent state"],
    ["Deep-filter context", "Five causal spectral taps"],
    ["ONNX opset", "17"],
    ["Maximum enhanced-output parity error", "6.100162863731384 x 10^-8"],
])
doc.add_heading("Verified indexed asset counts", level=3)
add_table(doc, ["Source represented in manifests v5", "Role", "Catalog rows"], [
    ["VCTK Corpus", "Clean speech", "44,242"],
    ["MAD dataset", "Military-labelled noise", "6,485"],
    ["MUSAN", "General stationary ambient music and speech interference", "2,016"],
    ["ESC-50", "Environmental events", "2,000"],
    ["Small UAV acoustics", "UAV flight recordings", "62"],
    ["Simulated RIR assets from the RIR workflow", "Room and channel responses", "60,000"],
    ["Total catalog rows", "All indexed clean noise and RIR entries", "114,805"],
], numeric_cols=(2,))
para(doc, "The 114,805 total is an audited catalog-row count, not a count of unique defence recordings. It includes 60,000 RIR entries and 44,242 clean-speech files. The data audit reported no missing catalog paths and no detected group-split leakage, while explicitly requiring manual license and acoustic-relevance review.")
doc.add_heading("Training objective summary", level=3)
para(doc, "The selected v10 recipe combines SI-SNR, scale-sensitive SNR, waveform L1, power-compressed complex and magnitude losses, multi-resolution spectral structure, phase consistency, spectral delta, spectral-hole control, clean identity and speech-retention objectives. The STOI-envelope surrogate was added only in v10b; it was numerically repaired and tested, but v10b was rejected and the STOI surrogate is not part of the selected v10 claim.")
doc.add_page_break()
doc.add_heading("Slide-ready model evolution", level=3)
add_table(doc, ["Milestone", "Approximate scale", "Technical change", "Evidence-based decision"], [
    ["v4", "12,259 parameters", "Compact causal baseline with explicit preservation training.", "Useful lightweight baseline, but impulsive-noise and clean-preservation reliability were not jointly sufficient."],
    ["v7", "About 172 thousand parameters", "Dual-channel fusion and a substantially larger recurrent model.", "Improved the dual-input path, but synchronized-hardware proof and military reliability remained open."],
    ["v8", "About 172 thousand parameters", "Corrected signed-phase and complex reconstruction behavior.", "Removed a reconstruction error source and became the direct numerical predecessor used for comparison."],
    ["v10 selected", "1,116,813 parameters", "Dual-channel full-band plus ERB features with five-tap causal complex deep filtering.", "Selected at epoch 58 because it produced the strongest frozen broad and military development evidence."],
])
doc.add_heading("Slide-ready loss groups", level=3)
add_table(doc, ["Loss group", "Implemented objectives", "Purpose"], [
    ["Waveform and scale fidelity", "SI-SNR; scale-sensitive SNR; waveform L1", "Preserve waveform alignment, level and intelligible speech structure."],
    ["Complex and spectral fidelity", "Power-compressed complex loss; power-compressed magnitude loss; multi-resolution spectral loss", "Constrain complex reconstruction, magnitude detail and resolution-dependent spectral structure."],
    ["Speech preservation", "Clean-identity loss; speech-retention or transient-over-speech loss", "Limit unnecessary processing of clean speech and reduce deletion during noise overlap."],
    ["Artifact control", "Phase-consistency loss; spectral-delta and spectral-hole penalties", "Reduce phase instability, discontinuities and robotic or hollow spectral gaps."],
])
doc.add_heading("Why alternatives were not simply stacked", level=3)
add_table(doc, ["Alternative", "Observed or researched limitation", "VoxShield decision"], [
    ["Spectral subtraction or Wiener only", "Artifacts and weak adaptation on rapidly changing or impulsive overlap.", "Keep as a baseline, not the promoted core."],
    ["LMS or NLMS only", "Requires suitable reference and geometry; speech leakage can cancel the target.", "Do not enable without synchronized hardware and measured leakage."],
    ["Published GTCRN UL-UNAS or DeepFilterNet unchanged", "Published benchmarks do not establish performance on these defence mixtures or hardware.", "Audit ideas and promote only frozen local evidence."],
    ["Cloud denoising", "Connectivity privacy availability and recurring-service dependence.", "Keep the selected audio path local and offline."],
])

doc.add_page_break()
doc.add_heading("Slide 4  Feasibility and viability", level=2)
add_table(doc, ["Area", "Current completion", "Meaning"], [
    ["Software and repository", "90-95%", "End-to-end modules, tests, export, live runtime and documentation exist."],
    ["Model and frozen evaluation", "85-90%", "v10 is selected; military STOI reliability and unseen test proof remain."],
    ["Synthetic paired evaluation", "About 90%", "Broad and military audits exist; larger independent testing remains."],
    ["Real synchronized dual-mic proof", "30-40%", "Software path exists; final hardware and recordings are missing."],
    ["Raspberry Pi 5 proof", "40-50%", "Deployment scripts exist; v10 performance, thermal, power and soak evidence remain."],
    ["Physical acoustic ANC", "10-20%", "Control concepts exist; no validated secondary-path hardware loop."],
    ["Overall competition readiness", "75-80%", "Strong honest software/model story; hardware evidence is the main gap."],
])
doc.add_heading("Provisional prototype hardware planning list", level=3)
add_table(doc, ["Item", "Purpose", "Verified project status", "Cost status"], [
    ["Raspberry Pi 5 8 GB", "Edge compute target", "User has stated a Pi 5 is available or planned; exact possession/setup must be confirmed.", "Team to enter invoice or current quote."],
    ["Official USB C power supply and active cooling", "Stable sustained Pi operation", "Required by deployment plan; purchase status not verified.", "Team to confirm."],
    ["64 GB or larger microSD", "OS runtime and artifacts", "Required; purchase status not verified.", "Team to confirm."],
    ["Synchronized two-input USB audio interface or codec", "One audio clock for primary and reference microphones", "Not yet available in the confirmed project evidence.", "Highest-priority missing hardware."],
    ["Close-talk primary microphone", "Speech-dominant input", "Consumer headset/microphones have been tested; final device not selected.", "Team to confirm."],
    ["Outward noise-reference microphone", "Noise-dominant reference input", "Final reference geometry not validated.", "Team to confirm."],
    ["USB headset or communication headset", "Safe monitored output", "Laptop headset demo has been used; final Pi device not verified.", "Team to confirm."],
    ["Loopback measurement cable or interface", "True end-to-end latency", "Not documented as available.", "Team to confirm."],
])
para(doc, "Do not present the approximately Rs 15,059 BOM or individual purchase statuses from the external review as factual until Team@ checks actual invoices, received items and compatibility. The missing synchronized audio interface is more important to the technical proof than adding an amplifier and speaker, because speaker playback can create feedback and is not needed for a headset communication demo.")
doc.add_heading("Hardware verification actions before submission", level=3)
bullets(doc, [
    "For every item, record make, model, quantity, invoice or dated quotation, received or ordered status and interface compatibility.",
    "Confirm one two-input interface or codec that captures both microphones from the same hardware clock. Two unrelated USB microphones are not an equivalent substitute.",
    "Keep the synchronized interface marked unresolved until a specific device has been received and a two-channel recording has been inspected.",
    "Add a measured v10 laptop and Raspberry Pi 5 benchmark only after saving the command, model hash, CPU settings, p50, p95, p99, RTF, callback-underflow count, temperature and test duration.",
])
doc.add_heading("Condensed implementation blueprint", level=3)
add_table(doc, ["Phase", "Work", "Exit evidence"], [
    ["1  Hardware", "Select synchronized two-input capture, microphones, headset, Pi 5 power and cooling.", "Verified BOM, compatibility record and synchronized channel capture."],
    ["2  Data capture", "Record primary and reference channels with speech, quiet, steady, non-stationary and impulsive noise cases.", "Consent and provenance record plus raw synchronized sessions."],
    ["3  Target adaptation", "Curate failure clips and run bounded adaptation without changing the frozen acceptance set.", "Improved military reliability without broad, clean-speech or PESQ regression."],
    ["4  Edge deployment", "Export the frozen model and benchmark stateful ONNX on Raspberry Pi 5.", "Parity, RTF, p50/p95/p99, callback, thermal, memory and soak report."],
    ["5  Controlled pilot", "Run headset demonstrations and controlled user evaluation on unseen recordings.", "Listening scores, operator feedback, failure log and an acceptance decision."],
])
doc.add_heading("Top risks for the slide", level=3)
bullets(doc, [
    "Military STOI reliability is 68.4 percent -> analyze the 12 failures and run a bounded failure-targeted v11 experiment without broad or PESQ regression.",
    "Unsynchronized microphone clocks invalidate stable spatial evidence -> use a single synchronized multi-input interface or codec.",
    "Pi thermal or scheduling underflow is unmeasured -> active cooling, one-thread baseline, p50/p95/p99 benchmark, physical loopback and a 30-60 minute soak.",
])
doc.add_page_break()
doc.add_heading("What can be shown and what remains pending", level=3)
add_table(doc, ["Can show now", "Pending proof"], [
    ["Repository, dataset pipeline and training history", "Genuinely unseen field-test recordings"],
    ["Offline matched noisy enhanced and clean audio", "Synchronized primary/reference target-device capture"],
    ["SNR STOI PESQ reliability and preservation reports", "v10 Raspberry Pi latency power thermal and soak results"],
    ["ONNX numerical equivalence and hashes", "Physical acoustic ANC secondary-path validation"],
    ["Headphone-based laptop engineering demo", "Defence qualification or operational endorsement"],
])

doc.add_page_break()
doc.add_heading("Slide 5  Impact and benefits", level=2)
add_table(doc, ["User", "Benefit"], [
    ["Soldier or vehicle crew", "More intelligible close-talk communication near engines, rotor noise, sirens and impulsive disturbances."],
    ["Command and control operator", "Fewer repetitions and less listening effort when receiving noisy communications."],
    ["Defence communications integrator", "Stateful portable ONNX, explicit device checks, telemetry and fail-safe behavior for headset or radio integration."],
    ["DRDO test and evaluation engineer", "Frozen manifests, artifact hashes, source/category/SNR breakdowns and saved listening evidence."],
])
doc.add_heading("Impact layers", level=3)
bullets(doc, [
    "Tactical: reduce avoidable communication errors and repetition in high-noise situations; this is a proposed benefit pending controlled user trials.",
    "Technical: local portable inference avoids a cloud dependency and includes aligned dry fallback rather than failing silently.",
    "Strategic: establishes an Indian prototype pipeline from data ingestion through edge deployment, with a measurable route to radio integration and later physical ANC research.",
])
doc.add_heading("Scalability path", level=3)
para(doc, "Evaluation kit -> integrator SDK -> authorized target-domain adaptation -> controlled pilot -> qualified embedded component. Secondary markets may include aerospace ground crew, emergency response and high-noise industry only after the defence core is validated.")
para(doc, "Credibility statement: VoxShield is a validated development prototype for communication speech enhancement. It is not yet defence-qualified, field-proven or a completed physical acoustic ANC system. The next milestone is a controlled synchronized-hardware and Raspberry Pi 5 pilot with new target-device recordings.")
doc.add_heading("Measured before and after example for the slide", level=3)
para(doc, "On the noisy-only subset of the frozen 50-file military development audit, mean SNR changed from -4.058 dB to 19.455 dB, mean STOI changed from 0.6161 to 0.8926 and mean PESQ changed from 1.1820 to 3.3911. These are aggregate synthetic-pair development results, not a single helicopter recording, an unseen field trial or a guarantee for every file. The same audit reported 68.4 percent per-file STOI target reliability, which remains the principal model gap.")
doc.add_heading("Market sizing framework for the slide", level=3)
add_table(doc, ["Layer", "Defensible framing", "Evidence required before adding a number"], [
    ["TAM", "Communication enhancement opportunities across defence, aerospace, emergency response and high-noise industry.", "A dated authoritative budget or market source, addressable equipment classes and a transparent allocation assumption."],
    ["SAM", "Indian defence communication headsets, intercoms, radios and edge-compute upgrades that can accept a local enhancement module.", "Named programs or device categories, annual procurement or installed-base evidence and an integration-scope assumption."],
    ["SOM", "A bounded pilot and integrator pathway reachable by Team@ during the first three to five years.", "Partner capacity, qualification timeline, pilot quantity, price basis and adoption-rate assumption."],
])
para(doc, "Do not use the total Indian defence budget as if it were the market size for VoxShield. It may be a context figure only when the exact fiscal year and primary government source are cited; TAM, SAM and SOM must be calculated from addressable communication equipment and explicit assumptions.")

doc.add_page_break()
doc.add_heading("Slide 6  Research references and data governance", level=2)
numbered(doc, [
    "Rong et al.  GTCRN  Streamable Speech Enhancement with Grouped Temporal Convolution and Recurrent Neural Network  github.com/Xiaobin-Rong/gtcrn.",
    "Rong et al.  UL-UNAS  Ultra-Low-Latency Neural Architecture Search for Speech Enhancement  arXiv 2503.00340  github.com/Xiaobin-Rong/ul-unas.",
    "Schroter et al.  DeepFilterNet  A Low Complexity Speech Enhancement Framework for Full-Band Audio based on Deep Filtering  arXiv 2110.05588.",
    "Taal et al.  A Short-Time Objective Intelligibility Measure for Time-Frequency Weighted Noisy Speech  ICASSP 2010.",
    "ITU-T Recommendation P.862  Perceptual Evaluation of Speech Quality.",
    "ONNX Runtime documentation  onnxruntime.ai/docs.",
    "University of Edinburgh DataShare  96 kHz CSTR VCTK Corpus record and license bundle  Open Data Commons Attribution License ODC-By 1.0  doi.org/10.7488/ds/2101.",
    "OpenSLR 17  MUSAN corpus record  Creative Commons Attribution 4.0 International  openslr.org/17.",
    "ESC-50 official repository and LICENSE  Creative Commons Attribution Non-Commercial 3.0 for ESC-50; the ESC-10 subset is CC BY  github.com/karolpiczak/ESC-50.",
    "OpenSLR 28  RIRS NOISES resource record  openslr.org/28; retain the archive license and provenance files with the project inventory.",
])
add_table(doc, ["Dataset", "Verified use", "License statement safe for the slide"], [
    ["VCTK Corpus", "Clean speech", "The official Edinburgh 96 kHz VCTK record states ODC-By 1.0, not CC BY 4.0. Confirm that the local download is this release and retain its license.txt before making the claim."],
    ["MUSAN", "General noise and interference", "OpenSLR 17 states CC BY 4.0. Preserve the OpenSLR record, attribution and exact downloaded archive checksum."],
    ["ESC-50", "Environmental events", "The official repository states CC BY-NC 3.0 for ESC-50; ESC-10 is CC BY. Non-commercial terms require legal review before commercial or production use."],
    ["MAD dataset", "Military-labelled noise", "Public availability is not the same as unrestricted production rights; record the exact source terms."],
    ["Small UAV acoustics", "UAV flight recordings", "Record the exact source page, version and terms before submission."],
    ["RIRS NOISES and RIR workflow", "Source RIR and noise material plus 60,000 indexed simulated responses", "OpenSLR 28 is the source record. Preserve the archive license/provenance material and generator settings; do not describe all 60,000 indexed entries as independent recordings."],
])
para(doc, "The project catalog records file metadata, not legal permission. The final submission should attach a license/provenance inventory with source URL, release, checksum, license text, permitted use and redistribution restrictions.")

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print(OUT)
