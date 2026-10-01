# VoxShield operator UI specification

The supplied dark spectrum/waterfall screenshots are the visual reference, not a literal RF
interface. VoxShield works at 16 kHz, so all frequency displays cover 0--8 kHz and all labels
refer to audio channels and enhancement state.

## Primary screen

1. A top status strip shows `NORMAL`, `DEGRADED`, or `BYPASS`; active backend (ONNX/PyTorch),
   sample rate, block size, end-to-end latency estimate, real-time factor, callback overruns,
   and reference-channel health.
2. A spectrum plot shows primary/noisy, reference, and enhanced traces with selectable overlays.
   It must use dBFS, not arbitrary RF reference levels.
3. A scrolling spectrogram/waterfall shows either the enhanced signal or a synchronized
   noisy-versus-enhanced split. It covers 0--8 kHz and has a fixed, documented colour scale so
   screenshots remain comparable.
4. A compact control panel provides input/output device selection, primary/reference channel
   selection, start/stop, safe output gain, monitor mute, record test, and software bypass.
   Bypass must remain immediately available even if model inference fails.
5. Quality telemetry displays speech-preservation risk, primary/reference RMS and clipping,
   estimated noise attenuation during pauses, and a clear warning when the reference microphone
   contains excessive target-speech leakage.

## Safety and truthfulness

- The UI must never label a run as `ANC active` unless an error microphone, calibrated secondary
  path, and physical FxNLMS control loop are actually running. Neural communication enhancement
  is labelled `Speech enhancement`.
- The displayed SNR/STOI/PESQ values are available only for evaluation files with a known clean
  target. Live audio may show signal levels and engineering telemetry, not fabricated quality
  metrics.
- Runtime failure, stale audio, NaN/Inf output, repeated deadline misses, channel loss, or severe
  clipping automatically enters degraded/bypass mode and explains the reason.
- Output is conservatively limited and fades between enhanced and bypass paths to avoid clicks.

## Implementation order

The first UI implementation should be a laptop engineering console driven by the existing live
runtime/health API. A lightweight Pi 5 view can follow after the headless ONNX service passes the
two-hour soak test. The UI must not own DSP state; closing it must not crash or corrupt the audio
service.

