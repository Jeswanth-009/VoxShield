# 05 — Judge's proof pack and evidence status

This index separates **downloadable proof that exists now** from **measurements still required**. Open the one-page [results card](03-results-card.md) and [architecture sheet](04-architecture-sheet.md) first; use the files below for verification.

## Available now

| Evidence | File | What it verifies |
| --- | --- | --- |
| Source and repeatable setup | [README](../../README.md), [package metadata](../../pyproject.toml), [tests](../../tests/) | What the software implements and how to run it |
| v15 checkpoint | [best.pt](../../release/v15/best.pt) | The selected model weights; SHA-256 is in the results card |
| v15 export | [voxshield-v15.onnx](../../release/v15/voxshield-v15.onnx) | Deployable graph paired with the checkpoint |
| Export parity | [validation JSON](../../release/v15/voxshield-v15.validation.json) | PyTorch/ONNX numerical comparison and file hashes |
| Fixed broad audit | [broad-50.json](../../release/v15/broad-50.json) | 50 per-clip records, summary, thresholds and **passing** strict gate |
| Fixed military-focused audit | [military-50.json](../../release/v15/military-50.json) | 50 per-clip records, summary and **failing** strict reliability gate |
| Windows live path | [demo helper](../../scripts/run_v15_jbl_dashboard_demo.ps1), [dual-device runtime](../../src/voxshield/live_dual_device.py) | Actual device capture, controls, inference and session-report generation |
| Raspberry Pi setup | [Pi scripts](../../scripts/pi/), [deployment notes](../../docs/deployment-pi5.md) | Historical **v10** install/benchmark procedure, not v15 hardware verification |
| Third-party attribution | [notices](../../THIRD_PARTY_NOTICES.md), [data guide](../../data/README.md) | Origin of upstream code and dataset handling |

The current automated suite collects **110 tests** and passed in the local publication run on 1 October 2026. This sentence is not a downloadable test log. If the slide quotes a test count, export a dated CI/JUnit report for the **same Git commit** and link it here.

## Add after each measurement is actually made

| Missing item | Minimum contents before publishing |
| --- | --- |
| **Continuous live demo MP4** | Screen, real JBL output audio, visible Dry/Enhanced selection, device IDs/names, controlled-mix value, model hash and uncut transition; follow [recording guide](02-listen-and-record.md). |
| **Matched listening audio** | Noisy, enhanced and optional clean target for each clip; identical duration and playback gain, exact clip ID, source attribution/licence, explicit “synthetic audit” or “own live recording” label. |
| **v15 Pi 5 benchmark JSON** | Same v15 checkpoint/ONNX hashes, Pi model/RAM, OS, frame count, mean/p95/p99, CPU, temperature, overruns and output drops. Do not reuse the v10 number. |
| **Physical loopback latency** | Test wiring, input/output device, sample rate, repeated trials, p50/p95/p99 end-to-end latency and raw capture. A model frame time alone does not meet this requirement. |
| **Shared-clock headset test** | Two capsules into one ADC clock, acoustic geometry, measured channel leakage/alignment, live session report and A/B recording. Not present in the JBL/laptop setup. |
| **Human listening/command test** | Blinded protocol, participant count, sentence set, raw/noisy/enhanced order, word accuracy or preference outcome and failure cases. |
| **Prototype BOM and comparison** | Component part numbers, dated supplier quotes, assembly/power costs and a like-for-like basis for any foreign-system price comparison. No unsupported ₹ cost or percentage claim. |
| **Ruggedization / MIL-STD evidence** | Exact test method, accredited or documented lab, fixture, conditions and result. Until then, label as a *target*, never compliance. |

The [evidence templates](../../docs/evidence/README.md) are starting points only; blank templates are **not** completed proof. Datasets and personal recordings are deliberately not uploaded. The published 50-clip JSON files report the experiment, but without the licensed source WAVs they are not a self-contained, exact rerun package.

## Five-second judge route

1. **Watch/hear** the continuous live clip once it exists.
2. **Check** the two audit rows and note that one strict gate fails.
3. **Open** the ONNX validation and model hashes if they want to verify the release.
4. **See** the remaining hardware/field milestones without confusing them with completed work.
