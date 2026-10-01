# VoxShield v4 complete rebuild plan

The eventual operator interface is specified in [ui-spec.md](ui-spec.md). A read-only local
spectrum/waterfall engineering monitor is implemented; control functions remain deliberately
downstream of objective, listening, real-time, and fail-safe gates.

VoxShield v4 separates communication speech enhancement from physical active
noise control.  The former runs as a causal dual-channel neural pipeline on a
laptop and Raspberry Pi 5.  The latter is an FxNLMS control loop using an
external reference microphone, an in-ear error microphone and the headphone
driver.  A speech denoiser alone must not be described as physical ANC.

## Non-destructive migration

- Keep `checkpoints_v3`, `runs_v3` and v3 release artifacts as a frozen baseline.
- New training writes only to `checkpoints_v4` and `runs_v4`.
- Existing source datasets remain indexed in place; large datasets are never
  copied merely to rearrange folders.
- Final test manifests are frozen before hyper-parameter tuning.

## Work packages

1. **Data integrity:** hash-aware indexing, speaker/noise/session-disjoint
   splits, licence inventory and duplicate detection.
2. **Multichannel synthesis:** primary/reference channels, independent acoustic
   paths, timing/gain mismatch, speech leakage, self-noise, clipping, radio
   coloration and transient-over-speech sampling.
3. **Target recordings:** synchronized primary/reference/error microphones on
   the final interface and headset, with isolated source signals retained.
4. **Models:** classical Wiener/NLMS baselines, single-channel GTCRN/UL-UNAS
   baselines, and the v4 dual-channel causal complex-mask model.
5. **Training:** broad pretraining, defence curriculum, transient hard cases,
   clean preservation, target-hardware fine-tuning and compression.
6. **Evaluation:** per-noise and per-SNR SNR/SI-SNR/STOI/PESQ/DNSMOS, ASR WER,
   clean preservation, speech-deletion rate and listening tests.
7. **Native runtime:** synchronized audio, stateful resampling, lock-free audio
   callback, persistent ONNX state, limiter, watchdog and cross-faded bypass.
8. **Pi 5:** Raspberry Pi OS Lite 64-bit, ALSA, ONNX Runtime ARM64, thread and
   affinity tuning, quantization, thermal/latency/xrun soak tests.
9. **Physical ANC:** secondary-path measurement, bounded FxNLMS, feedback
   protection, error-microphone validation and hardware bypass.

## Required hardware

- Raspberry Pi 5, official 27 W supply and active cooling.
- One synchronized USB audio interface.  Two inputs are enough for neural
  enhancement; at least three synchronized inputs and two outputs are required
  for primary, reference, error and anti-noise paths.
- Close-talk boom microphone, outward reference microphone, in-ear error
  microphone and a closed-back communications headset.
- Safe calibrated test loudspeaker, SPL meter and loopback cable.
- A DSP/MCU is recommended for the final sample-by-sample FxNLMS loop; the Pi
  supervises ANC and runs the neural communication path.

## Release gates

- No speaker, original noise, session, room or device leakage across splits.
- Overall output SNR > 15 dB, STOI > 0.85 and PESQ > 2.5 on the declared test
  distribution, with per-category results published.
- Every defence-noise category improves SNR and SI-SNR.
- Clean STOI loss <= 0.01 and output level error <= 1 dB.
- No catastrophic 50--100 ms active-speech erasures during transients.
- ONNX and PyTorch agree within a declared tolerance.
- Communication end-to-end latency <= 50 ms, inference p99 below one hop,
  and zero xruns in a two-hour Pi soak test.
- All real target-hardware and human listening gates pass before the model is
  called complete.

## Current implementation status

The repository now contains simulated synchronized reference channels,
transient/speech overlap sampling, a dual-channel causal model, identity-safe
initialization, clean-identity and short-time speech-retention losses, stateful
dual-input streaming, dual-input ONNX validation, strict evaluation gates,
capture diagnostics, an offline FxNLMS simulator, and a Pareto model-comparison
gate. Training is divided into broad, defence-weighted and target-hardware
stages with fresh optimizer state at stage boundaries. An evidence-triggered
preservation correction adds preservation-SNR, spectral identity, spectral
delta and phase consistency before defence fine-tuning.

Drone recordings and simulated RIRs are indexed. Still outstanding are real
target-device recordings, completion of v4 training, matched listening tests,
a native lock-free production runtime,
actual Pi 5 soak/thermal measurements, physical secondary-path calibration,
and hardware fail-safe validation. None of those are implied by software smoke
tests.
