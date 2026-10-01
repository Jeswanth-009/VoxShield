from pathlib import Path
from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(r"C:\anc")
OUT = ROOT / "output" / "documents"
OUT.mkdir(parents=True, exist_ok=True)
DOCX = OUT / "VoxShield_Final_Three_Minute_Video_Script_Expanded_Speaker_One.docx"

NAVY = "123A67"
BLUE = "1668B2"
GREEN = "009D71"
PALE_BLUE = "EAF3FB"
PALE_GREEN = "E8F6F1"
PALE_GREY = "F2F4F7"
MID_GREY = "5D6875"
BLACK = "111111"
WHITE = "FFFFFF"


def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=100, bottom=80, end=100):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def keep_with_next(paragraph, value=True):
    p_pr = paragraph._p.get_or_add_pPr()
    node = p_pr.find(qn("w:keepNext"))
    if node is None:
        node = OxmlElement("w:keepNext")
        p_pr.append(node)
    node.set(qn("w:val"), "1" if value else "0")


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Page ")
    run.font.size = Pt(8)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    paragraph._p.append(fld)


def style_doc(doc):
    sec = doc.sections[0]
    sec.top_margin = Inches(0.62)
    sec.bottom_margin = Inches(0.55)
    sec.left_margin = Inches(0.68)
    sec.right_margin = Inches(0.68)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(9.2)
    normal.font.color.rgb = RGBColor.from_string(BLACK)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.05

    for style_name, size, color in [
        ("Title", 30, BLACK),
        ("Subtitle", 13, MID_GREY),
        ("Heading 1", 18, NAVY),
        ("Heading 2", 12, BLUE),
        ("Heading 3", 10, GREEN),
    ]:
        st = styles[style_name]
        st.font.name = "Aptos Display" if style_name != "Normal" else "Aptos"
        st.font.size = Pt(size)
        st.font.color.rgb = RGBColor.from_string(color)
        st.font.bold = style_name != "Subtitle"
        st.paragraph_format.space_before = Pt(7)
        st.paragraph_format.space_after = Pt(3)
        st.paragraph_format.keep_with_next = True

    header = sec.header.paragraphs[0]
    header.text = "VOXSHIELD  |  SIH 2026  |  PS 26052"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for r in header.runs:
        r.font.name = "Aptos"
        r.font.size = Pt(8)
        r.font.bold = True
        r.font.color.rgb = RGBColor.from_string(NAVY)

    footer = sec.footer.paragraphs[0]
    footer.add_run("Team VoxShield  |  Final filming script  |  30 September 2026")
    footer.runs[0].font.size = Pt(8)
    footer.runs[0].font.color.rgb = RGBColor.from_string(MID_GREY)
    footer.add_run("                                      ")
    add_page_number(footer)


def add_label_value(doc, label, value):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(label + " ")
    r.bold = True
    r.font.color.rgb = RGBColor.from_string(NAVY)
    p.add_run(value)
    return p


def add_dialogue(doc, speaker, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.23)
    p.paragraph_format.right_indent = Inches(0.1)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(5)
    r = p.add_run(speaker.upper() + ": ")
    r.bold = True
    r.font.color.rgb = RGBColor.from_string(GREEN)
    q = p.add_run('"' + text + '"')
    q.italic = True
    q.font.size = Pt(10)
    p_pr = p._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "16")
    left.set(qn("w:space"), "8")
    left.set(qn("w:color"), GREEN)
    borders.append(left)
    p_pr.append(borders)
    return p


def add_bullets(doc, items, level=0):
    for item in items:
        p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
        p.paragraph_format.space_after = Pt(2)
        p.add_run(item)


def add_timing_table(doc):
    rows = [
        ("0:00-0:12", "Hook", "P1", "Noise, hand reveal, one-line problem"),
        ("0:12-1:02", "Problem and journey", "P1", "PS scope, constraints, design evolution"),
        ("1:02-1:29", "Architecture", "P2", "Dual input, causal enhancement, safeguards"),
        ("1:29-2:05", "Live demo", "P2", "Bypass first, then enhancement, honest telemetry"),
        ("2:05-2:27", "Evidence", "P2", "Audits and measured metrics"),
        ("2:27-2:46", "Edge proof", "P2", "Raspberry Pi 5 execution"),
        ("2:46-3:23", "Impact and close", "P1", "What exists, roadmap, final promise"),
    ]
    table = doc.add_table(rows=1, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    for i, name in enumerate(("Time", "Beat", "Lead", "What the judge sees")):
        cell = hdr.cells[i]
        cell.text = name
        shade(cell, NAVY)
        for r in cell.paragraphs[0].runs:
            r.font.bold = True
            r.font.color.rgb = RGBColor.from_string(WHITE)
    for idx, row in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = value
            set_cell_margins(cells[i])
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if idx % 2 == 0:
                shade(cells[i], PALE_BLUE)
        cells[0].width = Inches(1.05)
        cells[1].width = Inches(1.35)
        cells[2].width = Inches(0.55)
        cells[3].width = Inches(4.2)
    doc.add_paragraph()


def add_segment(doc, number, timing, title, lead, goal, dialogue, visuals, performance=None, edit=None):
    h = doc.add_heading(f"{number}. {title}", level=1)
    keep_with_next(h)
    add_label_value(doc, "TIMING", timing)
    add_label_value(doc, "LEAD", lead)
    add_label_value(doc, "PURPOSE", goal)
    if performance:
        add_label_value(doc, "PERFORMANCE", performance)
    add_dialogue(doc, lead, dialogue)
    doc.add_heading("Camera, screen and edit cues", level=2)
    add_bullets(doc, visuals)
    if edit:
        doc.add_heading("Editor note", level=3)
        p = doc.add_paragraph(edit)
        p.paragraph_format.left_indent = Inches(0.2)


def add_performance_beat(doc, timecode, intention, action, delivery, dialogue, screen=None):
    h = doc.add_heading(f"{timecode}  {intention}", level=2)
    keep_with_next(h)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("FACE AND BODY  ")
    r.bold = True
    r.font.color.rgb = RGBColor.from_string(NAVY)
    p.add_run(action)
    keep_with_next(p)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run("VOICE  ")
    r.bold = True
    r.font.color.rgb = RGBColor.from_string(NAVY)
    p.add_run(delivery)
    keep_with_next(p)
    dialogue_p = add_dialogue(doc, "Person 1", dialogue)
    keep_with_next(dialogue_p)
    if screen:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.23)
        p.paragraph_format.space_after = Pt(5)
        r = p.add_run("ON SCREEN  ")
        r.bold = True
        r.font.color.rgb = RGBColor.from_string(GREEN)
        p.add_run(screen)


doc = Document()
style_doc(doc)

# Cover
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(74)
r = p.add_run("VoxShield")
r.font.name = "Aptos Display"
r.font.size = Pt(42)
r.font.bold = True
r.font.color.rgb = RGBColor.from_string(NAVY)
r2 = p.add_run("  VIDEO SCRIPT")
r2.font.name = "Aptos Display"
r2.font.size = Pt(25)
r2.font.bold = True
r2.font.color.rgb = RGBColor.from_string(GREEN)

p = doc.add_paragraph("A cinematic-technical three-minute story for SIH 2026")
p.style = doc.styles["Subtitle"]
p.alignment = WD_ALIGN_PARAGRAPH.CENTER

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(22)
r = p.add_run("Problem Statement 26052  |  Defence & National Security  |  Hardware")
r.bold = True
r.font.size = Pt(11)
r.font.color.rgb = RGBColor.from_string(NAVY)

doc.add_paragraph()
table = doc.add_table(rows=4, cols=2)
table.alignment = WD_TABLE_ALIGNMENT.CENTER
table.style = "Table Grid"
meta = [
    ("Narrative split", "Person 1: mission story and close  |  Person 2: architecture, demo and evidence"),
    ("Creative ratio", "Approximately 40% cinematic storytelling, 60% technical proof"),
    ("Recording target", "Capture 3:25-3:40, then edit to 2:55-3:05"),
    ("Demonstration rule", "Show real signals, state limitations, and never replace evidence with animation"),
]
for i, (a, b) in enumerate(meta):
    table.cell(i, 0).text = a
    table.cell(i, 1).text = b
    shade(table.cell(i, 0), NAVY)
    shade(table.cell(i, 1), PALE_GREY if i % 2 == 0 else WHITE)
    for r in table.cell(i, 0).paragraphs[0].runs:
        r.font.bold = True
        r.font.color.rgb = RGBColor.from_string(WHITE)
    for c in table.rows[i].cells:
        set_cell_margins(c, 110, 130, 110, 130)

p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(42)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("FINAL PRODUCTION MASTER  |  30 SEPTEMBER 2026")
r.font.size = Pt(9)
r.font.bold = True
r.font.color.rgb = RGBColor.from_string(MID_GREY)

doc.add_page_break()

doc.add_heading("Director's Brief", level=1)
doc.add_paragraph(
    "The video must feel like a real engineering demonstration with a controlled cinematic opening. "
    "The emotional hook earns attention; the technical sequence earns trust. The story is not that all "
    "battlefield noise has already been solved. The story is that the team identified a demanding real-time "
    "communication problem, built a working edge prototype, measured it, learned where laboratory success "
    "does not automatically transfer, and designed the next hardware validation step."
)

doc.add_heading("Narrative arc", level=2)
add_bullets(doc, [
    "Disruption: noise masks a critical instruction.",
    "Intent: protect speech without depending on cloud connectivity.",
    "Engineering journey: move from broad noise cancellation ideas to a bounded-latency dual-input system.",
    "Proof: run a live A/B demonstration, expose telemetry, and show measured audit results.",
    "Credibility: clearly separate validated software and edge execution from the synchronized headset hardware still in progress.",
    "Mission: retrofit existing communication chains and continue toward field-grade validation.",
])

doc.add_heading("Timing map", level=2)
add_timing_table(doc)

doc.add_heading("Non-negotiable truth labels", level=2)
add_bullets(doc, [
    "Use 'engineering demonstration' for the split Windows microphone setup.",
    "Use 'validated on synthetic and curated replay audits' for the reported quality metrics.",
    "Use 'Raspberry Pi 5 benchmark' for the 5.33 ms mean inference figure.",
    "Use 'synchronized dual-microphone hardware in progress' for the planned common-clock headset rig.",
    "Do not say 'battlefield proven', 'deployment ready', or 'works in every noise condition'.",
])

doc.add_page_break()

add_segment(
    doc, "1", "0:00-0:12", "Cold open: the cost of masked speech", "Person 1",
    "Create immediate stakes, then reveal the human speaker.",
    "Sorry for that. But in a defence environment, nobody gets to pause the engine, rotor, wind or blast before giving a critical command. When noise masks even one word, the problem is not comfort. It is communication failure.",
    [
        "Start on a black screen. Play a sharp but safe two-second burst of rotor, engine and radio-static sound.",
        "A hand covers the lens. At 0:02 the hand pulls away, revealing Person 1 in a clean medium shot.",
        "On 'one word', flash a subtitle fragment: HOLD POSITION / LEFT FLANK / MOVE NOW.",
        "Reduce the noise bed under dialogue; do not make the spoken words difficult to understand.",
    ],
    "Controlled, serious and direct. Pause briefly after 'communication failure'.",
    "Keep the hook under 12 seconds. The reveal must feel deliberate, not like a social-media prank."
)

add_segment(
    doc, "2", "0:12-1:02", "Problem interpretation and design journey", "Person 1",
    "Give Person 1 enough substance to establish the problem, constraints and evolution of the solution.",
    "When we first read this problem statement, our first thought was an inline audio optimizer: something that could sit inside an existing communication chain and clean speech locally. But the real requirement was harder. Defence noise is not one sound. It can be stationary engine rumble, changing rotor and wind patterns, or sudden impulsive events. The system also has to be causal, work without cloud access, stay within a small frame deadline and fail safely instead of muting the operator. So we treated latency, speech preservation, edge deployment and evidence as first-class requirements. We explored adaptive cancellation, compact GTCRN-style enhancement and UL-UNAS-based dual-channel processing. Those experiments taught us the central lesson: architecture alone is not enough when microphones are unsynchronized or when training mixtures do not match the real acoustic path. VoxShield therefore evolved into a complete pipeline - controlled data ingestion, a causal dual-input deep-filter engine, ONNX export, runtime safeguards, objective audits, live telemetry and Raspberry Pi validation.",
    [
        "Use a clean left-to-right timeline: Inline optimizer -> model experiments -> dual-input engine -> measured edge prototype.",
        "Beside the noise categories, show four restrained icons: engine, rotor, blast and wind. Avoid cinematic battlefield composites.",
        "Animate the four requirements one at a time: OFFLINE, LOW LATENCY, SPEECH SAFE, FAIL SAFE.",
        "Show one short repository montage: manifests, training console, exported ONNX file and Pi benchmark JSON.",
    ],
    "Speak as a builder explaining decisions, not as a salesperson listing features.",
    "If time is tight, remove the sentence beginning 'We explored...' but retain the lesson about synchronization and domain match."
)

doc.add_page_break()

add_segment(
    doc, "3", "1:02-1:29", "Technical architecture", "Person 2",
    "Explain the signal path clearly before touching the live controls.",
    "This is the current VoxShield prototype. A primary channel carries speech plus noise, while a reference channel measures the surrounding acoustic field. Audio is framed causally at 16 kilohertz and processed by our dual-input deep-filter model. The runtime keeps recurrent state across frames, exports through ONNX for portable inference, and includes aligned dry fallback, queue protection and telemetry. The dashboard does not invent results. It visualizes the two captured inputs, the processed output, inference time and runtime health.",
    [
        "Person 2 stands beside the laptop and Raspberry Pi. Cut between the speaker and a screen capture of the dashboard.",
        "Overlay a simple four-stage topology: Primary + Reference -> Causal STFT -> Dual-input Deep Filter -> Output + Telemetry.",
        "Display a small honesty label: WINDOWS SPLIT-DEVICE ENGINEERING DEMO; COMMON-CLOCK RIG IN PROGRESS.",
        "On 'recurrent state', show only a subtle state-loop icon; do not overload the screen with a neural-network diagram.",
    ],
    "Use measured, technical language. Point at the physical Pi when saying 'portable inference'."
)

add_segment(
    doc, "4", "1:29-2:05", "Live A/B demonstration", "Person 2",
    "Let judges hear a before/after comparison while seeing independent microphone activity and honest telemetry.",
    "First, I am selecting operator bypass. You can hear the monitored input before enhancement, while the voice and environment traces move independently. Now I enable VoxShield. The same spoken line continues, but the enhancement path suppresses the correlated background while preserving the command. The live panel also reports mode, inference time, overruns and stream health, so a clean output is not accepted without runtime evidence.",
    [
        "Before recording, verify that the JBL microphone is the primary input, the laptop array is the reference input and the JBL headphones are the output.",
        "Play a repeatable noise sample from the phone near the laptop reference microphone. Keep the JBL microphone close to Person 2's mouth.",
        "Speak the same command twice: 'Hold position. Left flank clear. Move on my mark.'",
        "Begin in bypass for at least three seconds. Show both input waveforms and the mode badge in the same frame.",
        "Switch to enhancement without cutting the video. Hold the dashboard shot long enough for the viewer to see the state change.",
        "Use a controlled reference mix only as a disclosed demonstration aid. Do not label it raw acoustic capture.",
    ],
    "Do not shout over the noise. The contrast should come from the signal path, not from changing delivery.",
    "Capture system audio directly for the final edit. A camera microphone recording headphone leakage will not provide a fair A/B comparison."
)

doc.add_page_break()

add_segment(
    doc, "5", "2:05-2:27", "Measured evidence", "Person 2",
    "Convert the demonstration into defensible proof without implying field validation.",
    "The live clip is only one example, so we also run repeatable audits. On our v15 broad fifty-clip audit, the exported ONNX model passed the strict gate with 30.48 decibels enhanced SNR, 0.938 STOI, 3.94 PESQ and zero measured speech deletion. A harder military-focused audit improved strongly on average, but still missed the reliability gate on some clips. We keep that failure visible because it defines the next training and hardware work.",
    [
        "Show a four-number results strip for the broad audit, each labelled V15 BROAD / 50 CLIPS / SYNTHETIC-CURATED REPLAY.",
        "Then show the military audit as AMBER, not green: average enhanced SNR 25.15 dB, STOI 0.915, PESQ 3.63; reliability gate not passed.",
        "Add a one-line caption: MEANS ARE STRONG; WORST-CASE RELIABILITY REMAINS OPEN.",
        "Briefly show paired noisy and enhanced spectrograms from a real saved evaluation record.",
    ],
    "Slow down on the limitation sentence. This is where credibility is won.",
    "Never crop out the audit name, clip count or gate status."
)

add_segment(
    doc, "6", "2:27-2:46", "Raspberry Pi 5 edge proof", "Person 2",
    "Show that the runtime meets its frame budget on the target edge class.",
    "For edge feasibility, the model was exported to ONNX and benchmarked on a Raspberry Pi 5 with eight gigabytes of memory. Across ten thousand sixteen-millisecond frames, mean inference was 5.33 milliseconds, p99 was 6.05 milliseconds and there were zero deadline overruns. That is execution headroom for a real-time pipeline; physical end-to-end headset latency will still be measured on the synchronized prototype.",
    [
        "Film the actual Pi 5, power connection and terminal. Avoid using a stock Raspberry Pi image.",
        "Overlay the benchmark JSON values: 10,000 frames; 5.33 ms mean; 6.05 ms p99; 0 overruns; 16 ms frame.",
        "Show the ONNX filename and validation status for one second, then return to the Pi shot.",
    ],
    "Touch or point to the Pi only once. Let the verified numbers carry the claim."
)

doc.add_page_break()

add_segment(
    doc, "7", "2:46-3:23", "Impact, honest status and close", "Person 1",
    "Bring Person 1 back with a meaningful summary, retrofit path and precise next step.",
    "What we have built is more than a model checkpoint. It is a reproducible data pipeline, a streaming dual-input engine, a validated ONNX artifact, objective audit reports, runtime monitoring, a live operator dashboard and a Raspberry Pi deployment path. The prototype is designed as a local retrofit layer for existing wired communication chains, so it can work without cloud connectivity. Today, the software pipeline and edge timing are validated, while the common-clock dual-microphone headset is still the critical hardware integration step. Our next phase is clear: synchronized stereo capture, physical loopback latency, recordings from the target headset geometry, hard-case retraining, and acoustic, thermal and long-duration tests. VoxShield is our attempt to make sure that when the environment gets louder, the command does not disappear.",
    [
        "Return to the original clean medium shot. Keep the Pi and laptop visible but secondary.",
        "Build a concise stack beside Person 1: DATA -> ENGINE -> ONNX -> AUDITS -> PI -> HEADSET RIG NEXT.",
        "On the final sentence, cut to the same command subtitle from the opening, now complete and clean.",
        "End on the VoxShield wordmark, team name, PS 26052 and QR code. Hold for at least three seconds.",
    ],
    "The ending should sound resolved, not exaggerated. Look directly into the lens for the final sentence.",
    "If the final cut must be exactly three minutes, use the cut plan on the next page."
)

doc.add_heading("End card content", level=2)
add_bullets(doc, [
    "VoxShield - Local, causal speech enhancement for noisy defence communication",
    "Working prototype | Measured audits | Raspberry Pi 5 validated | Synchronized headset rig in progress",
    "QR destination: one clean evidence hub containing the demo, architecture, audit summaries, benchmark report, limitations and team contact",
])

doc.add_page_break()

doc.add_heading("Speaker One Performance Master", level=1)
doc.add_paragraph(
    "This is the detailed performance version for Person 1. It divides the opening and closing into short beats so the speaker knows what to say, what to do with the face and hands, where to look, and when the editor should change the picture. Person 1 is the human anchor of the film: calm under pressure, technically aware, and honest about the prototype's present status."
)

doc.add_heading("Character and physical baseline", level=2)
add_bullets(doc, [
    "Expression: serious and alert in the opening; curious and analytical during the design journey; quietly confident in the close.",
    "Posture: feet stable, shoulders relaxed, chin level. Do not sway, pace continuously or fold the arms.",
    "Eye line: look into the camera for the problem and final promise. Look briefly toward graphics or hardware only when referring to them.",
    "Hands: keep them around waist to chest height. Use one purposeful gesture for each major idea, then return to a neutral position.",
    "Voice: begin slightly subdued after the noise burst, become conversational while explaining the journey, and finish slower and firmer.",
    "Reaction style: do not act frightened by the opening noise. Show a half-second of interruption, regain control, then address the viewer.",
])

doc.add_heading("Speaker One Opening Rehearsal", level=1)

add_performance_beat(
    doc, "0:00-0:02", "The interruption",
    "The screen is black. Person 1's hand already covers the lens. Hold completely still; there is no visible acting yet.",
    "No dialogue. Let the noise burst create the interruption.",
    "",
    "BLACK SCREEN. A short mix of rotor, engine and radio static begins, controlled below clipping."
)

add_performance_beat(
    doc, "0:02-0:05", "Recover control",
    "Pull the hand away in one smooth motion. Blink once, take a small breath and settle the shoulders. Give a brief apologetic look, not a smile.",
    "Say the first three words softly and naturally. Pause for half a beat after them.",
    "Sorry for that.",
    "As the hand moves, cut the noise bed down by about 8 to 10 dB. No title yet."
)

add_performance_beat(
    doc, "0:05-0:12", "Turn disturbance into the problem",
    "Look directly into the lens. On 'nobody gets to pause', open one palm slightly toward the camera. On 'communication failure', stop the gesture and hold eye contact.",
    "Measured and firm. Stress 'critical command' and 'one word'. Leave a short pause before the last sentence.",
    "But in a defence environment, nobody gets to pause the engine, rotor, wind or blast before giving a critical command. When noise masks even one word, the problem is not comfort. It is communication failure.",
    "Flash HOLD POSITION, LEFT FLANK and MOVE NOW one at a time. Briefly distort or mask one key word, then restore it."
)

add_performance_beat(
    doc, "0:12-0:20", "Explain the first idea",
    "Relax the face slightly and turn the torso ten degrees toward the architecture graphic. Use a small horizontal hand movement to suggest something inserted into an existing chain.",
    "Shift from dramatic to conversational. Sound like you are explaining the team's first whiteboard decision.",
    "When we first read this problem statement, our first thought was an inline audio optimizer - something that could sit inside an existing communication chain and clean speech locally.",
    "Show a simple radio chain. Animate a small VOXSHIELD block being inserted between microphone and receiver."
)

add_performance_beat(
    doc, "0:20-0:31", "Show why the problem is harder",
    "Face the camera again. Count the three noise families with restrained finger cues: one, two, three. Keep the hand below shoulder height.",
    "Slightly faster, but articulate the category names. Drop the voice on 'not one sound' so the line feels like a discovery.",
    "But the real requirement was harder. Defence noise is not one sound. It can be stationary engine rumble, changing rotor and wind patterns, or sudden impulsive events such as gunfire and blasts.",
    "Use real, restrained icons or short waveform snippets for stationary, nonstationary and impulsive noise."
)

add_performance_beat(
    doc, "0:31-0:42", "Define the engineering constraints",
    "Stand square to camera. Mark each requirement with one compact downward hand beat. Do not point at the viewer.",
    "Use an even technical cadence. Pause briefly between the four requirements so captions can land.",
    "The system also has to be causal, work without cloud access, stay inside a small frame deadline, preserve the operator's words and fail safely instead of going silent.",
    "Reveal labels sequentially: OFFLINE, CAUSAL, BOUNDED LATENCY, SPEECH SAFE, FAIL SAFE."
)

doc.add_heading("Speaker One Opening Rehearsal Continued", level=1)

add_performance_beat(
    doc, "0:42-0:52", "Explain the team's learning",
    "Glance toward the experiment timeline, then return to the lens. Use an open hand rather than a victory gesture; this section is about learning, not claiming success.",
    "Warm, reflective tone. Slow down for 'architecture alone is not enough'.",
    "We explored adaptive cancellation, compact GTCRN-style enhancement and UL-UNAS-based dual-channel processing. Those experiments taught us that architecture alone is not enough when microphones are unsynchronized or when training mixtures do not match the real acoustic path.",
    "Show the three experiment labels, then highlight SYNC and DOMAIN MATCH as the two lessons."
)

add_performance_beat(
    doc, "0:52-1:02", "Reveal the complete system and hand off",
    "Move half a step sideways so the pipeline graphic has room. Sweep one hand once from left to right as the stages appear. At the final phrase, turn the eyes toward Person 2 and give a small nod.",
    "Build energy through the pipeline list. Finish cleanly; do not trail off while Person 2 prepares to speak.",
    "That is why VoxShield became a complete engineering pipeline: controlled data ingestion, a causal dual-input deep-filter engine, ONNX deployment, runtime safeguards, objective audits, live telemetry and Raspberry Pi validation. Here is how the current prototype works.",
    "Build the stack: DATA -> DUAL INPUT -> DEEP FILTER -> ONNX -> SAFETY -> AUDITS -> PI 5. Cut to Person 2 on the final sentence."
)

doc.add_heading("Handoff to Person Two", level=2)
add_bullets(doc, [
    "Person 1 must finish the sentence before turning the head. Turning too early makes the ending sound uncertain.",
    "Person 2 should already be framed in the next shot, not walk into position after the handoff.",
    "Use a straight cut or a short audio-led cut. Avoid a dramatic whoosh transition.",
    "Person 1 remains silent until the closing section; do not insert reaction shots that imply agreement with a metric that has not yet appeared.",
])

doc.add_page_break()

doc.add_heading("Speaker One Closing Rehearsal", level=1)

add_performance_beat(
    doc, "2:46-2:55", "Return with substance",
    "Re-enter in the same position and framing used after the opening reveal. Begin with hands neutral. On 'more than a model checkpoint', lift one open palm slightly.",
    "Confident but not celebratory. The first line should answer the judge's unspoken question: what did the team actually build?",
    "What we have built is more than a model checkpoint. It is a reproducible data pipeline, a streaming dual-input engine, a validated ONNX artifact, objective audit reports, runtime monitoring, a live operator dashboard and a Raspberry Pi deployment path.",
    "Show the six deliverables as compact verified items. Use repository screenshots and actual files, not decorative mockups."
)

add_performance_beat(
    doc, "2:55-3:03", "State the practical value",
    "Turn the body slightly toward the Pi and cable path, but keep the eyes mostly on the camera. Use a short connecting gesture between the visible hardware items.",
    "Clear and practical. Stress 'local retrofit layer' and 'without cloud connectivity'.",
    "The prototype is designed as a local retrofit layer for existing wired communication chains, so it can process speech close to the operator without depending on cloud connectivity.",
    "Animate a restrained existing-radio -> VoxShield edge module -> headset path. Label it PROPOSED RETROFIT PATH."
)

add_performance_beat(
    doc, "3:03-3:11", "Name the present boundary",
    "Bring both hands back to neutral. Keep the face open and matter-of-fact. Do not look down or smile apologetically when stating the limitation.",
    "Slow down and use a lower pitch. This sentence must sound like engineering control, not a confession.",
    "Today, the software pipeline and Raspberry Pi timing are validated. The common-clock dual-microphone headset and physical end-to-end audio path are still the critical hardware integration steps.",
    "Split the screen: VALIDATED NOW in green; NEXT HARDWARE VALIDATION in amber."
)

add_performance_beat(
    doc, "3:11-3:18", "Make the next phase concrete",
    "Use one compact forward hand movement on 'next phase'. Keep the list to a single breath; do not count every item on the fingers.",
    "Slightly faster, purposeful and specific.",
    "Our next phase is synchronized stereo capture, physical loopback latency measurement, target-headset recordings, hard-case retraining, and acoustic, thermal and long-duration testing.",
    "Build a five-step roadmap ending in FIELD EVALUATION. Do not label the current prototype field-ready."
)

add_performance_beat(
    doc, "3:18-3:23", "Finish on the mission",
    "Lower the hands completely. Look directly into the lens. Hold still for one full second after the final word so the editor has a clean ending.",
    "Slow, firm and quiet. Stress 'louder' and 'command'. Do not add 'thank you' immediately afterward.",
    "VoxShield is our attempt to make sure that when the environment gets louder, the command does not disappear.",
    "Return to the complete command from the opening, then dissolve to the end card and QR code."
)

doc.add_page_break()

doc.add_heading("Speaker One Reaction and Gesture Rules", level=1)
add_bullets(doc, [
    "Opening reaction: interrupted for half a second, then composed. Never perform panic or fake hearing pain.",
    "Problem statements: eyebrows slightly engaged, direct eye contact, minimal movement.",
    "Technical explanation: relaxed forehead, occasional small nod, open palms. Avoid pointing, chopping motions and constant hand movement.",
    "Limitations: neutral face and steady eye contact. Honesty should look deliberate, not embarrassed.",
    "Final promise: no smile until after the last spoken word. A small natural smile may appear during the silent end-card hold.",
    "If a line is forgotten, stop, reset to neutral and repeat the whole beat. Do not splice in the middle of a technical term.",
])

doc.add_heading("Speaker One Voice Curve", level=2)
add_bullets(doc, [
    "0:02-0:12: low, controlled urgency.",
    "0:12-0:31: conversational discovery.",
    "0:31-0:42: precise technical cadence.",
    "0:42-1:02: reflective learning that builds into a confident handoff.",
    "2:46-3:03: confident inventory and practical value.",
    "3:03-3:18: slower honesty, then purposeful roadmap.",
    "3:18-3:23: quiet, memorable final line followed by a one-second hold.",
])

doc.add_heading("Speaker One Rehearsal Method", level=2)
add_bullets(doc, [
    "First pass: read only the dialogue until every technical term sounds natural.",
    "Second pass: add pauses and emphasis, but keep both hands still.",
    "Third pass: add only the gestures written for each beat. Remove any repeated or nervous movement.",
    "Fourth pass: rehearse with the actual graphics and handoff timing so eye movement matches the edit.",
    "Final pass: record from the real camera position and review once with sound muted to check posture, expression and eye line.",
])

doc.add_heading("Speaker One Take Checklist", level=2)
add_bullets(doc, [
    "The hand leaves the lens smoothly and does not block the face after the reveal.",
    "The opening apology is brief; the speaker does not smile during the problem statement.",
    "Each requirement receives one gesture at most.",
    "The turn toward Person 2 happens after the handoff sentence is complete.",
    "The limitation is delivered with steady eye contact and no embarrassed reaction.",
    "The final line is followed by one full second of stillness.",
])

doc.add_page_break()

doc.add_heading("Evidence and Caption Sheet", level=1)
doc.add_paragraph("Use these exact labels in overlays, charts, the dashboard recording and QR evidence hub.")

metrics = [
    ("V15 broad audit", "50 clips", "Enhanced SNR 30.48 dB", "STOI 0.938", "PESQ 3.94", "Strict gate: PASS"),
    ("V15 military audit", "50 clips", "Enhanced SNR 25.15 dB", "STOI 0.915", "PESQ 3.63", "Reliability gate: NOT PASSED"),
    ("Pi 5 benchmark", "10,000 frames", "Mean 5.33 ms", "p99 6.05 ms", "16 ms frame", "Deadline overruns: 0"),
]
table = doc.add_table(rows=1, cols=6)
table.style = "Table Grid"
table.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, t in enumerate(("Evidence", "Scope", "Metric 1", "Metric 2", "Metric 3", "Status")):
    table.cell(0, i).text = t
    shade(table.cell(0, i), NAVY)
    for r in table.cell(0, i).paragraphs[0].runs:
        r.font.bold = True
        r.font.color.rgb = RGBColor.from_string(WHITE)
set_repeat_table_header(table.rows[0])
for ridx, row in enumerate(metrics):
    cells = table.add_row().cells
    for i, t in enumerate(row):
        cells[i].text = t
        set_cell_margins(cells[i], 75, 70, 75, 70)
        if ridx % 2 == 0:
            shade(cells[i], PALE_BLUE)
    if "NOT" in row[-1]:
        shade(cells[-1], "FFF1D6")
    else:
        shade(cells[-1], PALE_GREEN)

doc.add_heading("Recommended QR evidence hub", level=2)
add_bullets(doc, [
    "A 60-90 second uncut A/B demonstration with system audio.",
    "One-page architecture diagram that labels the current split-device demo and the planned common-clock rig separately.",
    "Broad and military audit summaries, including thresholds, clip counts, pass/fail status and downloadable JSON reports.",
    "Raspberry Pi 5 benchmark report and short terminal capture.",
    "Model card: sample rate, causal framing, input assumptions, known failure modes and intended use.",
    "Reproducibility page: checkpoint and ONNX hashes, command list, environment versions and dataset provenance summary.",
    "Limitations and roadmap: synchronization, acoustic path mismatch, device DSP, physical loopback latency and field recordings.",
    "Team roles, contact details and a dated changelog.",
])

doc.add_heading("Mandatory lower-third labels", level=2)
add_bullets(doc, [
    "ENGINEERING DEMONSTRATION - SEPARATE WINDOWS AUDIO ENDPOINTS",
    "CONTROLLED REFERENCE MIX ACTIVE (only when it is actually active)",
    "V15 BROAD AUDIT - 50 SYNTHETIC/CURATED REPLAY CLIPS",
    "RASPBERRY PI 5 BENCHMARK - MODEL TIMING, NOT PHYSICAL AUDIO I/O LATENCY",
])

doc.add_page_break()

doc.add_heading("Recording Runbook", level=1)
doc.add_heading("Before filming", level=2)
add_bullets(doc, [
    "Charge the JBL headset, phone, laptop and Raspberry Pi power bank; disable notifications on all devices.",
    "Use a quiet room for dialogue and record the cinematic noise as a separate controlled layer.",
    "Frame both speakers consistently: eye line near the upper third, soft front light, uncluttered technical background.",
    "Record each person's full section twice: one natural take and one faster safety take.",
    "Screen-record the dashboard at native resolution and capture its audio output directly.",
    "Run the dual-microphone test first and confirm that VOICE and ENV bars react independently.",
    "Verify bypass audibly before filming the enhancement transition.",
    "Record five seconds of room tone and a clean shot of the Pi, cables, laptop, phone noise source and dashboard.",
])

doc.add_heading("Live demo sequence", level=2)
steps = [
    "Start the verified v15 dashboard command with the confirmed device IDs.",
    "During calibration, remain silent and play the chosen noise near the laptop reference microphone.",
    "Confirm that calibration completes and telemetry begins updating.",
    "Select operator bypass and record at least three seconds of the command plus background.",
    "Switch to enhancement in the same continuous recording and repeat the command at the same mouth-to-mic distance.",
    "Show the runtime mode, last inference time, overruns, underflows and two distinct input traces.",
    "Stop cleanly and preserve the session report, telemetry JSON and screen recording used in the edit.",
]
for i, item in enumerate(steps, 1):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(3)
    p.add_run(item)

doc.add_heading("Edit discipline", level=2)
add_bullets(doc, [
    "Use one visual idea per shot. Avoid full-screen text walls.",
    "Keep proof captions on screen long enough to read: at least 1.5 seconds for a short metric, 3 seconds for a limitation.",
    "Use waveform motion only from captured audio. Decorative waveform loops should never be presented as live data.",
    "Normalize narration consistently. Preserve a clear audible difference in the A/B segment without artificially muting bypass.",
    "Use subtle cuts, simple line animations and one consistent navy-green visual system. Avoid cinematic battlefield stock footage after the opening.",
    "Add subtitles throughout; judges may watch without sound.",
])

doc.add_heading("Strict three-minute cut plan", level=2)
cut_table = doc.add_table(rows=1, cols=3)
cut_table.style = "Table Grid"
cut_table.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, t in enumerate(("Priority", "Safe cut", "Time recovered")):
    cut_table.cell(0, i).text = t
    shade(cut_table.cell(0, i), NAVY)
    for r in cut_table.cell(0, i).paragraphs[0].runs:
        r.font.bold = True
        r.font.color.rgb = RGBColor.from_string(WHITE)
cuts = [
    ("1", "Remove the architecture-history sentence naming GTCRN and UL-UNAS.", "8-10 s"),
    ("2", "Shorten the repository montage and remove its spoken inventory.", "5-7 s"),
    ("3", "Compress the Pi explanation to mean, frame budget and zero overruns.", "5-6 s"),
    ("4", "Move detailed roadmap labels to silent end-card animation.", "4-6 s"),
]
for idx, row in enumerate(cuts):
    cells = cut_table.add_row().cells
    for i, t in enumerate(row):
        cells[i].text = t
        set_cell_margins(cells[i])
        if idx % 2 == 0:
            shade(cells[i], PALE_GREY)

doc.add_heading("Final pre-submission check", level=2)
add_bullets(doc, [
    "Final duration is within the portal limit.",
    "Every metric has a scope label and every limitation remains visible.",
    "The bypass and enhanced samples come from the same continuous setup.",
    "The Raspberry Pi shown is the device used for the benchmark.",
    "QR code resolves on a phone without login and the evidence hub works on mobile.",
    "Team name, PS ID and contact details match the submitted presentation.",
])

doc.save(DOCX)
print(DOCX)
