# Architecture and training rationale

## Neural cores

V3 remains a frozen single-channel comparison using the complete official GTCRN architecture,
adapted under its MIT license and pinned at upstream commit
`502ebfab64da7c4a9af78dcb9c6ceef1ebb01c73`.

V4 is a separate causal, synchronized dual-channel model. It analyzes complex primary and
reference spectra, ERB/sub-band context, inter-channel phase, and relative level. A recurrent
causal core predicts a bounded complex ratio mask plus a conservative identity gate. Zeroed mask
heads make a newly initialized network an identity mapping instead of an arbitrary speech
destroyer. The reference input is required; two unrelated USB microphones are not accepted as a
synchronized pair.

## Signal path

1. Sanitize and resample the synchronized primary/reference channels to 16 kHz float32.
2. Analyze 512-sample frames with a square-root Hann window and 128-sample hop.
3. Form primary/reference complex, magnitude, phase and relative-level features; then apply
   ERB/sub-band feature extraction.
4. Run the causal dual-channel recurrent core and bounded mask/identity heads.
5. Apply the complex mask to the primary spectrum and reconstruct with weighted overlap-add.
6. Remove DC and enforce the conservative output limit.
7. Run inference on a bounded worker, never inside the PortAudio callback. A late output is
   discarded and replaced with the corresponding delayed dry primary block.
8. On invalid output or repeated deadline misses, enter aligned degraded/bypass mode.

V4 WOLA buffering is 384 samples (24 ms at 16 kHz); live worker playout adds 128 samples (8 ms)
by default. Audio drivers and hardware add more latency, so only a physical loopback measurement
can determine end-to-end latency.

## Objectives and mixture curriculum

V4 combines SI-SNR, scale-sensitive SNR, power-compressed spectral/complex, waveform,
clean-identity and short-time speech-retention losses. The last two explicitly penalize the voice
deletion observed under tank/impulse overlap. The mixer supplies exact-clean and 25--40 dB
near-clean pairs alongside stationary, non-stationary, impulsive, environmental, and mixed noise.
Training reads source files dynamically; it does not materialize a huge mixture corpus.

Training has three optimizer-separated stages: broad pretraining, defence-weighted fine-tuning,
and target-hardware fine-tuning. MAD/source-label oversampling applies only to training;
validation stays on the frozen broad distribution. A stage loads model weights from the prior
best checkpoint but starts a fresh lower-rate optimizer, while `--resume` remains reserved for
continuing an interrupted stage exactly.

## Causality contract

Temporal processing is causal and carries explicit recurrent state. Tests compare full-sequence
and one-frame stateful output. The dual-input ONNX export validates enhanced output and recurrent
state against PyTorch.

The live health monitor can use dry bypass for safety, but offline evaluation disables deadline
bypass so a slow workstation call can never silently turn an enhanced test file into noisy input.
