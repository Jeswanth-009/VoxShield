# VoxShield model card — fill this for every promoted model

Do not replace this template with claims until the run has completed. Keep one completed copy next
to each released ONNX model.

## Identity

- Model/run name:
- Training commit:
- Checkpoint SHA-256:
- ONNX SHA-256 and validation report:
- Training dates and hardware:

## Real training data

- Clean-speech sources, releases, licenses, hours, languages, speaker counts:
- Noise sources, releases, licenses, hours per category:
- Target-device/field recordings and collection conditions:
- RIR sources:
- Train/validation/test source-disjoint policy:
- Known demographic, language, microphone, and environment gaps:

## Training

- Configuration file and any overrides:
- Epoch selected and reason:
- Training/validation curves reviewed for overfitting:
- Failed/interrupted runs and changes made:

## Held-out quality

Report SNR, SI-SNR, STOI, and PESQ by noise category and SNR bin. Add representative listening-test
results from multiple people and note speech distortion, musical noise, transient smearing, and
failure cases. Never copy numbers from the GTCRN paper or a different dataset/model.

## System validation

- Pi 5 ONNX frame latency/RTF/RAM/CPU and temperature under a sustained run:
- Physical loopback end-to-end latency:
- Audio callback underflow/overflow count:
- Bypass/degraded-mode fault-injection results:
- Microphone/interface/radio models, gains, sample format, and isolation:

## Promotion decision

- Accepted limitations:
- Rejected use cases:
- Reviewer/date:
- Deployment approval:

