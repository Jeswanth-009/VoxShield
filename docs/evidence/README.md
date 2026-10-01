# Release evidence files

These templates define the human and hardware evidence that software cannot fabricate. Copy a
template into `artifacts/`, replace every `null`/placeholder with measured information, and keep
the raw recordings, photographs, logs, and test protocol beside it. Never set `passed: true`
unless the recorded protocol was actually completed.

| Final file | Created by | What it proves |
| --- | --- | --- |
| `artifacts/data-audit-v4.json` | `voxshield-data audit` | Corpus coverage, paths and split integrity |
| `artifacts/v4-final-test.json` | `voxshield-evaluate --strict-sih-gate` | Held-out objective quality and preservation |
| `artifacts/pi5-v4-benchmark.json` | `voxshield-benchmark` on the Pi | Frame timing, RTF and memory on target hardware |
| `artifacts/pi5-soak.json` | `voxshield-live --duration-seconds 7200 --session-report ...` | Two-hour live runtime health and Pi thermal state |
| `artifacts/physical-loopback.json` | Manual loopback test | Measured microphone-to-output latency |
| `artifacts/listening-test.json` | Human listening protocol | Speech quality, intelligibility and transient preservation |
| `artifacts/physical-anc-test.json` | Calibrated headset/fixture test | Secondary-path calibration, stable attenuation and hardware bypass |

Run `voxshield-readiness --project-root . --output artifacts/readiness.json` after adding evidence.
It reports communication enhancement and physical ANC separately. Missing data is a failed gate,
not a zero or an assumed pass.

