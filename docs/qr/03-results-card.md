# 03 — VoxShield v15 results card

**Model:** causal dual-input `deep_filter_dual`, v15 hard-failure repair. **Evaluation:** ONNX Runtime on two fixed 50-clip audits. These are controlled/synthetic paired tests, not military field recordings or a human listening study.

| Fixed audit | Clips | Enhanced SNR | SNR gain over noisy | Enhanced STOI | Enhanced PESQ | Speech-deletion metric | Strict gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| [Broad validation](../../release/v15/broad-50.json) | 50 | 30.48 dB | +10.07 dB | 0.938 | 3.94 | 0.0 | **Pass** |
| [Military-focused validation](../../release/v15/military-50.json) | 50 | 25.15 dB | +14.05 dB | 0.915 | 3.63 | 0.0 | **Fail** |

**Why can the second row have high averages but fail?** The strict gate checks how many *individual clips* meet targets, not only the means. In the military-focused set, STOI target reliability and the combined target reliability are below threshold. A mean of 0.915 STOI does not mean every command is intelligible. The recorded `speech_deletion_rate` is an automated metric on these paired clips, not proof that no word is ever lost in a live conversation.

### Verification chain

1. The selected [checkpoint](../../release/v15/best.pt) has SHA-256 `9af778772b9a4c531106cd244f56bcb326f1b00056a67762b1dca790d5799629`.
2. The selected [ONNX graph](../../release/v15/voxshield-v15.onnx) has SHA-256 `33e352558a33670dfd65e6412c89c13f50b94140721672c09c9ae43701bc4307`.
3. The [export validation](../../release/v15/voxshield-v15.validation.json) passed numerical parity against PyTorch at a `0.0002` tolerance. Parity proves that the graph matches the checkpoint, **not** that it removes noise in every environment.
4. The two linked JSON audits contain per-clip records, source labels, aggregate values, gate thresholds and checks. Source WAVs are not redistributed in the repository, so the exact old audit cannot be rerun from a fresh clone alone.

### What was actually measured on Raspberry Pi 5?

An **earlier v10**, not v15, 8 GB Pi run processed 10,000 frames of 16 ms. Reported model timing was **5.33 ms mean** and **6.05 ms p99**, with zero model deadline overruns and zero simulated callback drops. Full-pipeline p99 callback time was 6.50 ms. Those numbers do **not** measure the microphone-to-earphone loop and must not be labelled v15 Pi performance. A version-matched v15 Pi report is still needed.

### Exact sentence for a judge

> “Our v15 ONNX model passes the broad 50-clip strict audit and improves the military-focused set on average. The military strict reliability gate still fails on some hard cases. The current JBL/laptop demonstration is a real software run, but synchronized headset and physical-latency validation are the next engineering steps.”

**Do not claim:** battlefield validation, MIL-STD certification, 0% deletion in every real session, v15 Pi timing from the v10 benchmark, or a sourced hardware cost advantage without a sourced bill of materials.
