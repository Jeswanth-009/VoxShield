import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "C:/anc";
const SKILL_DIR = "C:/Users/jeswa/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations";
const TMP_DIR = path.join(workspaceDir, "artifacts", "slide2_best_build");
const FINAL_PPTX = path.join(workspaceDir, "docs", "VoxShield_SIH_Slide2_Best_Reference_Style.pptx");
const RUNTIME_PYTHON = "C:/Users/jeswa/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";

const { finalizePresentation } = await import(
  pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href
);

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });

const W = 1600;
const H = 900;
const font = "Aptos";
const navy = "#07345C";
const deep = "#061B2E";
const light = "#F5F7FA";
const card = "#FFFFFF";
const border = "#D6DEE8";
const text = "#172033";
const muted = "#536173";
const green = "#12B76A";
const amber = "#F59E0B";
const red = "#E5484D";
const cyan = "#0EA5E9";

const ppt = Presentation.create({ slideSize: { width: W, height: H } });
const slide = ppt.slides.add();
slide.background.fill = light;

function shape(geometry, left, top, width, height, fill = card, lineFill = border, lineWidth = 1.2) {
  return slide.shapes.add({
    geometry,
    position: { left, top, width, height },
    fill,
    line: { fill: lineFill, width: lineWidth },
  });
}

function txt(content, left, top, width, height, opts = {}) {
  const s = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  s.text = content;
  s.text.style = {
    typeface: opts.font ?? font,
    fontSize: opts.size ?? 24,
    bold: opts.bold ?? false,
    italic: opts.italic ?? false,
    color: opts.color ?? text,
    alignment: opts.align ?? "left",
    autoFit: "none",
  };
  return s;
}

function pill(content, left, top, width, height, fill, color = "#FFFFFF") {
  shape("roundRect", left, top, width, height, fill, fill, 0);
  txt(content, left, top + 7, width, height - 8, { size: 22, bold: true, color, align: "center" });
}

function sectionHeader(label, left, top, width, color) {
  shape("roundRect", left, top, width, 44, color, color, 0);
  txt(label, left + 18, top + 8, width - 36, 30, { size: 21, bold: true, color: "#FFFFFF" });
}

function smallMetric(value, label, note, left, top, width, accent) {
  shape("roundRect", left, top, width, 88, "#FFFFFF", border, 1.3);
  shape("ellipse", left + 18, top + 18, 52, 52, accent + "22", accent, 1.1);
  txt(value, left + 88, top + 14, width - 104, 34, { size: 30, bold: true, color: accent });
  txt(label, left + 88, top + 48, width - 104, 22, { size: 18, bold: true, color: text });
  txt(note, left + 88, top + 68, width - 104, 18, { size: 12.5, color: muted });
}

// Header band similar to official template but cleaner.
shape("rect", 0, 0, W, 64, "#FFFFFF", "#FFFFFF", 0);
txt("Ministry of Education", 48, 13, 240, 22, { size: 17, bold: true, color: text });
txt("Government of India", 48, 35, 240, 18, { size: 13, color: muted });
txt("SMART INDIA HACKATHON 2026", 598, 13, 404, 40, { size: 24, bold: true, color: navy, align: "center" });
txt("AICTE", 1375, 13, 170, 22, { size: 20, bold: true, color: text, align: "right" });
txt("All India Council for Technical Education", 1260, 36, 285, 18, { size: 11.5, color: muted, align: "right" });
shape("rect", 0, 64, W, 45, navy, navy, 0);
pill("Team@", 34, 72, 180, 30, "#0B477A");
txt("SIH 2026  •  PS 26052  •  Hardware", 1198, 75, 350, 28, { size: 20, bold: true, color: "#FFFFFF", align: "right" });

// Title zone.
txt("IDEA TITLE AND PROPOSED SOLUTION", 0, 126, W, 26, { size: 17, bold: true, color: muted, align: "center" });
txt("VoxShield: AI speech enhancement engine for noisy defence communication", 120, 158, 1360, 46, {
  size: 34,
  bold: true,
  color: navy,
  align: "center",
});
txt("Improves command intelligibility under vehicle, rotor, impulse and ambient noise using local real-time inference.", 205, 204, 1190, 26, {
  size: 18,
  color: muted,
  align: "center",
});

// Main cards.
const y = 258;
const cardH = 405;
const leftX = 40;
const midX = 420;
const rightX = 1218;
shape("roundRect", leftX, y, 340, cardH, "#FFFFFF", "#F3B4B7", 1.6);
shape("roundRect", midX, y, 758, cardH, "#FFFFFF", "#A6C8EA", 1.6);
shape("roundRect", rightX, y, 342, cardH, "#FFFFFF", "#A6E5C3", 1.6);
sectionHeader("1  Problem context", leftX + 16, y + 16, 308, red);
sectionHeader("2  Proposed system workflow", midX + 18, y + 16, 722, navy);
sectionHeader("3  Prototype outputs", rightX + 16, y + 16, 310, green);

// Left rows
const problemRows = [
  ["Vehicle and engine noise", "Masks low-frequency speech cues"],
  ["Rotor and wind noise", "Creates modulated nonstationary noise"],
  ["Impulse noise", "Can hide short command words"],
  ["Ambient field noise", "Reduces communication intelligibility"],
];
for (let i = 0; i < problemRows.length; i++) {
  const top = y + 80 + i * 72;
  shape("roundRect", leftX + 22, top, 296, 58, i % 2 === 0 ? "#FFF8F8" : "#FFFFFF", "#EBC2C4", 1);
  shape("ellipse", leftX + 38, top + 13, 32, 32, "#FEE2E2", red, 1);
  txt(String(i + 1), leftX + 38, top + 17, 32, 20, { size: 15, bold: true, color: red, align: "center" });
  txt(problemRows[i][0], leftX + 84, top + 10, 220, 18, { size: 14.5, bold: true, color: text });
  txt(problemRows[i][1], leftX + 84, top + 30, 220, 18, { size: 12.5, color: muted });
}
shape("roundRect", leftX + 22, y + 374, 296, 52, "#FFF1F2", "#FDA4AF", 1);
txt("Result", leftX + 42, y + 384, 64, 18, { size: 14, bold: true, color: red });
txt("Command words can get masked in high-noise communication.", leftX + 98, y + 381, 205, 34, { size: 13.5, color: text });

// Middle workflow.
txt("System idea: use a reference-noise path plus speech-preserving enhancement, then expose runtime health for the operator.", midX + 36, y + 72, 680, 30, { size: 15.5, color: muted });
const steps = [
  ["Primary mic", "Speech near mouth"],
  ["Reference mic", "Environment noise"],
  ["Streaming model", "Dual-channel deep filter"],
  ["Retention guard", "Checks speech deletion risk"],
  ["Enhanced output", "Audio plus telemetry"],
];
const stepW = 126;
const gap = 18;
let sx = midX + 36;
for (let i = 0; i < steps.length; i++) {
  const top = y + 135;
  shape("roundRect", sx, top, stepW, 132, "#F8FBFF", "#BBD4EF", 1.2);
  shape("ellipse", sx + 42, top + 13, 42, 42, i < 2 ? "#DBEAFE" : i === 4 ? "#D1FAE5" : "#E0F2FE", i < 2 ? cyan : i === 4 ? green : navy, 1.2);
  txt(String(i + 1), sx + 42, top + 22, 42, 20, { size: 15, bold: true, color: i === 4 ? green : navy, align: "center" });
  txt(steps[i][0], sx + 10, top + 64, stepW - 20, 20, { size: 14, bold: true, color: text, align: "center" });
  txt(steps[i][1], sx + 10, top + 88, stepW - 20, 34, { size: 11.5, color: muted, align: "center" });
  if (i < steps.length - 1) {
    shape("rightArrow", sx + stepW + 3, top + 49, gap + 8, 34, "#8BB9E8", "#8BB9E8", 0);
  }
  sx += stepW + gap + 8;
}

// Middle lower detail boxes
shape("roundRect", midX + 36, y + 298, 325, 78, "#F8FBFF", "#D6DEE8", 1);
txt("Validated software path", midX + 56, y + 310, 280, 20, { size: 15, bold: true, color: navy });
txt("ONNX export, offline audits, failure analysis and controlled replay demo.", midX + 56, y + 335, 280, 28, { size: 12.7, color: muted });
shape("roundRect", midX + 382, y + 298, 340, 78, "#FFFBEB", "#FCD34D", 1);
txt("Hardware note", midX + 402, y + 310, 280, 20, { size: 15, bold: true, color: "#92400E" });
txt("True physical validation needs synchronized raw dual-microphone capture.", midX + 402, y + 335, 295, 28, { size: 12.7, color: "#713F12" });

// Right output rows.
const outs = [
  ["Enhanced speech", "Clearer command audio"],
  ["Runtime telemetry", "Latency, bypass and health state"],
  ["Evidence report", "SNR, STOI, PESQ and deletion"],
  ["Edge deployment path", "ONNX model and Pi 5 benchmark"],
];
for (let i = 0; i < outs.length; i++) {
  const top = y + 82 + i * 68;
  shape("roundRect", rightX + 22, top, 298, 54, i % 2 === 0 ? "#F7FEFA" : "#FFFFFF", "#B6E8CA", 1);
  shape("ellipse", rightX + 38, top + 12, 30, 30, "#DCFCE7", green, 1);
  txt("✓", rightX + 38, top + 13, 30, 20, { size: 15, bold: true, color: green, align: "center" });
  txt(outs[i][0], rightX + 82, top + 9, 220, 18, { size: 14.5, bold: true, color: text });
  txt(outs[i][1], rightX + 82, top + 29, 220, 18, { size: 12.4, color: muted });
}
shape("roundRect", rightX + 22, y + 374, 298, 52, "#ECFDF5", "#86EFAC", 1);
txt("Output is a prototype evidence path, not a claimed field-ready headset.", rightX + 44, y + 386, 255, 26, { size: 13, bold: true, color: "#065F46", align: "center" });

// Bottom proof strip.
txt("Proof strip", 44, 686, 130, 24, { size: 16, bold: true, color: navy });
shape("line", 152, 699, 1380, 1, "none", "#CBD5E1", 1);
smallMetric("30.48 dB", "SNR", "v15 broad strict", 58, 726, 350, green);
smallMetric("5.33 ms", "Latency", "Pi 5 mean for 16 ms frame", 438, 726, 350, cyan);
smallMetric("0.0", "Speech deletion", "reported audits", 818, 726, 350, green);
smallMetric("Next", "Dual-mic validation", "synchronized raw capture", 1198, 726, 350, amber);

// Footer.
shape("rect", 0, 858, W, 42, "#FFFFFF", "#FFFFFF", 0);
shape("line", 0, 858, W, 1, "none", "#CBD5E1", 1);
txt("Team@", 48, 872, 130, 18, { size: 14, color: navy });
txt("Problem Statement ID: 26052", 420, 872, 260, 18, { size: 14, color: text });
txt("Theme: Defence and National Security", 730, 872, 320, 18, { size: 14, color: text });
txt("PS Category: Hardware", 1100, 872, 240, 18, { size: 14, color: text });
txt("2/6", 1505, 872, 55, 18, { size: 16, bold: true, color: navy, align: "right" });

slide.speakerNotes.textFrame.setText(
  "Slide 2 generated for VoxShield SIH PS 26052. Factual metrics are from the user's reported v15 and Pi 5 evidence: v15 broad SNR 30.48 dB, Pi 5 mean latency 5.33 ms, speech deletion 0.0 in reported audits. Hardware note included to avoid overclaiming physical ANC before synchronized dual-mic validation."
);

const candidatePath = path.join(TMP_DIR, "candidate.pptx");
await (await PresentationFile.exportPptx(ppt)).save(candidatePath);
const preview = await slide.export({ format: "png", scale: 1 });
await fs.writeFile(path.join(TMP_DIR, "slide2-preview.png"), new Uint8Array(await preview.arrayBuffer()));

const result = await finalizePresentation({
  explicitTotalSlideCount: 1,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "14400000,8100000", "--validate-heading-fit"],
  requiredNativeTableOwnerSlides: [],
  fontPolicy: { basis: "design", families: [font] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(TMP_DIR, "validation.json"),
});

console.log(JSON.stringify({ final: FINAL_PPTX, preview: path.join(TMP_DIR, "slide2-preview.png"), result }, null, 2));
