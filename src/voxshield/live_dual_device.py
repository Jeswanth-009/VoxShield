"""Experimental two-endpoint laptop demo with acoustic delay calibration.

This module intentionally lives outside the production single-stream runtime.
Separate PortAudio input streams are not guaranteed to share a hardware clock,
but the Realtek headset and laptop-array endpoints can be useful for a bounded
engineering demonstration when their measured alignment remains stable.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from .checkpoint import load_model, sha256_file, verify_onnx_pair
from .diagnostics import _lag_and_correlation
from .live_engine import AsyncLiveEngine
from .runtime import (
    HybridStreamingEnhancer,
    StreamingDualChannelEnhancer,
    make_onnx_frame_runner,
    make_torch_frame_runner,
)
from .telemetry import build_live_telemetry, write_atomic_json


def _device(value: str) -> int | str:
    return int(value) if value.strip().lstrip("-").isdigit() else value


class SampleDelay:
    """Causal fixed sample delay that supports arbitrary block sizes."""

    def __init__(self, samples: int) -> None:
        if samples < 0:
            raise ValueError("delay must be non-negative")
        self.samples = int(samples)
        self._buffer = np.zeros(self.samples, dtype=np.float32)

    def process(self, block: np.ndarray) -> np.ndarray:
        value = np.asarray(block, dtype=np.float32).reshape(-1)
        if not self.samples:
            return value.copy()
        combined = np.concatenate((self._buffer, value))
        output = combined[: len(value)].copy()
        self._buffer = combined[len(value) :]
        return output


def _read_channel(stream, frames: int, channel: int) -> tuple[np.ndarray, bool]:
    audio, overflowed = stream.read(frames)
    return np.asarray(audio[:, channel], dtype=np.float32).copy(), bool(overflowed)


def _controlled_demo_primary(
    primary: np.ndarray,
    reference: np.ndarray,
    reference_mix: float,
) -> np.ndarray:
    """Create a disclosed speech+noise primary for a split-device demonstration.

    The production topology expects the primary capsule to contain speech plus
    environmental noise.  A Bluetooth speech microphone can suppress that
    environmental noise before PortAudio receives it, while the laptop array
    still captures it.  This optional engineering-demo path electronically adds
    a bounded copy of the reference to the primary so Dry and Enhance operate on
    the same observable noisy input.  It must never be described as field capture.
    """
    gain = float(np.clip(reference_mix, 0.0, 1.0))
    voice = np.asarray(primary, dtype=np.float32).reshape(-1)
    noise = np.asarray(reference, dtype=np.float32).reshape(-1)
    if voice.shape != noise.shape:
        raise ValueError("primary and reference blocks must have the same shape")
    return np.clip(voice + gain * noise, -0.98, 0.98).astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Experimental synchronized laptop dual-device VoxShield demo"
    )
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--onnx", default=None)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--primary-device", type=_device, required=True)
    parser.add_argument("--reference-device", type=_device, required=True)
    parser.add_argument("--output-device", type=_device, required=True)
    parser.add_argument("--primary-channel", type=int, default=0)
    parser.add_argument("--reference-channel", type=int, default=0)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--queue-blocks", type=int, default=16)
    parser.add_argument("--playout-extra-blocks", type=int, default=2)
    parser.add_argument("--wet-mix", type=float, default=0.65)
    parser.add_argument("--calibration-seconds", type=float, default=4.0)
    parser.add_argument("--maximum-calibration-lag-ms", type=float, default=200.0)
    parser.add_argument("--minimum-calibration-correlation", type=float, default=0.08)
    parser.add_argument("--manual-reference-offset-ms", type=float, default=0.0)
    parser.add_argument(
        "--controlled-reference-mix",
        type=float,
        default=0.0,
        help=(
            "Electronically add this reference fraction to the primary for a disclosed "
            "controlled demo (0 disables; not production capture)"
        ),
    )
    parser.add_argument("--lms", action="store_true")
    parser.add_argument("--telemetry-file", default=None)
    parser.add_argument("--control-file", default=None)
    parser.add_argument("--session-report", default=None)
    parser.add_argument("--duration-seconds", type=float, default=None)
    args = parser.parse_args()

    if args.primary_device == args.reference_device:
        parser.error("primary and reference devices must be different endpoints")
    if args.primary_channel < 0 or args.reference_channel < 0:
        parser.error("channel indices cannot be negative")
    if not 0.0 <= args.wet_mix <= 1.0:
        parser.error("--wet-mix must be between 0 and 1")
    if not 0.0 <= args.controlled_reference_mix <= 1.0:
        parser.error("--controlled-reference-mix must be between 0 and 1")
    if args.calibration_seconds < 1.0:
        parser.error("--calibration-seconds must be at least 1")
    if args.duration_seconds is not None and args.duration_seconds <= 0:
        parser.error("--duration-seconds must be positive")

    try:
        import sounddevice as sd
    except ImportError as exc:
        raise SystemExit("Install live audio support with: pip install -e .[live]") from exc

    model, config, _ = load_model(args.checkpoint, args.device if not args.onnx else "cpu")
    if not getattr(model, "requires_reference", False):
        raise SystemExit("The experimental dual-device path requires a dual-channel model.")
    if args.onnx:
        verify_onnx_pair(args.checkpoint, args.onnx)
    runner = (
        make_onnx_frame_runner(model, args.onnx, args.threads)
        if args.onnx
        else make_torch_frame_runner(model, args.device)
    )
    audio = config["audio"]
    runtime = dict(config["runtime"])
    runtime["wet_mix"] = args.wet_mix
    if args.lms:
        stream = HybridStreamingEnhancer(
            runner,
            sample_rate=audio["sample_rate"],
            n_fft=audio["n_fft"],
            hop_length=audio["hop_length"],
            neural_dual_channel=True,
            **runtime,
        )
    else:
        stream = StreamingDualChannelEnhancer(
            runner,
            sample_rate=audio["sample_rate"],
            n_fft=audio["n_fft"],
            hop_length=audio["hop_length"],
            **runtime,
        )
    engine = AsyncLiveEngine(
        stream,
        audio["hop_length"],
        queue_blocks=args.queue_blocks,
        playout_extra_blocks=args.playout_extra_blocks,
    )

    sample_rate = int(audio["sample_rate"])
    hop = int(audio["hop_length"])
    primary_channels = args.primary_channel + 1
    reference_channels = args.reference_channel + 1
    calibration_blocks = max(1, round(args.calibration_seconds * sample_rate / hop))
    capture_overflows = 0
    output_underflows = 0
    started = time.monotonic()
    last_telemetry = 0.0
    calibration_lag = 0
    calibration_correlation = 0.0
    control_signature: tuple[int, int] | None = None
    operator_control: dict[str, object] = {
        "wet_mix": float(args.wet_mix),
        "effective_wet_mix": 0.0,
        "output_gain_db": 0.0,
        "operator_bypass": False,
        "mute_output": False,
        "preset": "custom",
        "operating_mode": "auto",
    }
    reference_gate: dict[str, object] = {
        "healthy": False,
        "state": "checking",
        "reason": "waiting for calibrated reference audio",
        "reference_rms_dbfs": -120.0,
        "correlation": 0.0,
        "good_frames": 0,
        "bad_frames": 0,
        "_smoothed_power": 0.0,
    }

    def set_wet_mix(value: float) -> None:
        target = getattr(stream, "inner", stream)
        target.wet_mix = float(np.clip(value, 0.0, 1.0))

    def refresh_controls() -> None:
        nonlocal control_signature
        if not args.control_file:
            return
        path = Path(args.control_file)
        try:
            stat = path.stat()
            signature = (stat.st_mtime_ns, stat.st_size)
            if signature == control_signature:
                return
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            mode = str(value.get("operating_mode", "auto"))
            if mode not in {"dry", "enhanced", "auto"}:
                mode = "auto"
            operator_control.update(
                {
                    "wet_mix": float(np.clip(float(value.get("wet_mix", args.wet_mix)), 0.0, 1.0)),
                    "output_gain_db": float(np.clip(float(value.get("output_gain_db", 0.0)), -18.0, 6.0)),
                    "operator_bypass": bool(value.get("operator_bypass", False)),
                    "mute_output": bool(value.get("mute_output", False)),
                    "preset": str(value.get("preset", "custom")),
                    "operating_mode": mode,
                }
            )
            control_signature = signature
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass

    def update_gate(primary: np.ndarray, reference: np.ndarray) -> None:
        p = primary.astype(np.float64) - float(np.mean(primary))
        r = reference.astype(np.float64) - float(np.mean(reference))
        p_rms = float(np.sqrt(np.mean(p**2)))
        r_rms = float(np.sqrt(np.mean(r**2)))
        ref_db = float(20.0 * np.log10(max(r_rms, 1e-12)))
        instant_power = r_rms * r_rms
        previous_power = float(reference_gate.get("_smoothed_power", 0.0))
        smoothing = 0.35 if instant_power >= previous_power else 0.015
        smoothed_power = previous_power + smoothing * (instant_power - previous_power)
        reference_gate["_smoothed_power"] = smoothed_power
        smoothed_ref_db = float(10.0 * np.log10(max(smoothed_power, 1e-24)))
        denominator = float(np.linalg.norm(p) * np.linalg.norm(r))
        correlation = float(np.dot(p, r) / denominator) if denominator > 1e-12 else 0.0
        difference = float(np.sqrt(np.mean((p - r) ** 2)) / max(p_rms + r_rms, 1e-12))
        if smoothed_ref_db < -60.0:
            good, reason = False, "reference microphone is too quiet"
        elif ref_db > -3.0 or bool(np.any(np.abs(reference) >= 0.98)):
            good, reason = False, "reference microphone is clipping"
        elif abs(correlation) >= 0.985 and difference <= 0.08:
            good, reason = False, "primary and reference appear duplicated"
        else:
            good, reason = True, "reference signal is active and distinct"
        if good:
            reference_gate["good_frames"] = int(reference_gate["good_frames"]) + 1
            reference_gate["bad_frames"] = 0
            if int(reference_gate["good_frames"]) >= 8:
                reference_gate["healthy"] = True
        else:
            reference_gate["bad_frames"] = int(reference_gate["bad_frames"]) + 1
            reference_gate["good_frames"] = 0
            # Allow short gaps in impulsive/real-world noise. At a 16 ms block,
            # 125 frames is a two-second release rather than a flickering gate.
            if int(reference_gate["bad_frames"]) >= 125:
                reference_gate["healthy"] = False
        if bool(reference_gate["healthy"]) and not good:
            reason = "reference hold active; waiting for the next noise burst"
        reference_gate.update(
            {
                "state": "ready" if reference_gate["healthy"] else "not_ready",
                "reason": reason,
                "reference_rms_dbfs": ref_db,
                "smoothed_reference_rms_dbfs": smoothed_ref_db,
                "correlation": correlation,
            }
        )

    def apply_mode() -> None:
        mode = str(operator_control["operating_mode"])
        requested = float(operator_control["wet_mix"])
        if bool(operator_control["operator_bypass"]) or mode == "dry":
            effective = 0.0
        elif mode == "enhanced":
            effective = requested
        else:
            effective = requested if bool(reference_gate["healthy"]) else 0.0
        set_wet_mix(effective)
        operator_control["effective_wet_mix"] = effective
        operator_control["reference_gate"] = dict(reference_gate)

    print("Use headphones. Keep the earphone microphone close to your mouth.")
    if args.controlled_reference_mix > 0.0:
        print(
            "CONTROLLED ELECTRONIC MIX ENABLED: "
            f"primary = JBL voice + {args.controlled_reference_mix:.2f} * reference noise. "
            "Dry/bypass monitors this combined test input; this is not production capture."
        )
    print(
        f"Calibration will capture {args.calibration_seconds:.1f} seconds. "
        "Play the gun/noise sound from the phone near the laptop reference microphone "
        "and remain silent until calibration completes."
    )

    primary_info = sd.query_devices(args.primary_device)
    reference_info = sd.query_devices(args.reference_device)
    if primary_info["max_input_channels"] < primary_channels:
        raise SystemExit("Primary device does not expose the requested channel.")
    if reference_info["max_input_channels"] < reference_channels:
        raise SystemExit("Reference device does not expose the requested channel.")

    try:
        with (
            sd.InputStream(
                samplerate=sample_rate,
                blocksize=hop,
                channels=primary_channels,
                dtype="float32",
                device=args.primary_device,
                latency="high",
            ) as primary_stream,
            sd.InputStream(
                samplerate=sample_rate,
                blocksize=hop,
                channels=reference_channels,
                dtype="float32",
                device=args.reference_device,
                latency="high",
            ) as reference_stream,
            sd.OutputStream(
                samplerate=sample_rate,
                blocksize=hop,
                channels=1,
                dtype="float32",
                device=args.output_device,
                latency="high",
            ) as output_stream,
        ):
            primary_calibration: list[np.ndarray] = []
            reference_calibration: list[np.ndarray] = []
            for _ in range(calibration_blocks):
                primary, primary_overflow = _read_channel(
                    primary_stream, hop, args.primary_channel
                )
                reference, reference_overflow = _read_channel(
                    reference_stream, hop, args.reference_channel
                )
                capture_overflows += int(primary_overflow) + int(reference_overflow)
                primary_calibration.append(primary)
                reference_calibration.append(reference)
                output_underflows += int(
                    output_stream.write(np.zeros((hop, 1), dtype=np.float32))
                )

            primary_probe = np.concatenate(primary_calibration)
            reference_probe = np.concatenate(reference_calibration)
            calibration_lag, calibration_correlation = _lag_and_correlation(
                primary_probe,
                reference_probe,
                sample_rate,
                args.maximum_calibration_lag_ms,
            )
            if abs(calibration_correlation) < args.minimum_calibration_correlation:
                calibration_lag = round(
                    sample_rate * args.manual_reference_offset_ms / 1000.0
                )
                print(
                    "Calibration correlation was inconclusive; using manual offset "
                    f"{args.manual_reference_offset_ms:.2f} ms."
                )
            primary_delay = SampleDelay(max(0, -calibration_lag))
            reference_delay = SampleDelay(max(0, calibration_lag))
            added_alignment_ms = 1000.0 * abs(calibration_lag) / sample_rate
            print(
                "Calibration complete: "
                f"lag={calibration_lag} samples ({1000 * calibration_lag / sample_rate:.2f} ms), "
                f"correlation={calibration_correlation:.3f}, "
                f"added alignment delay={added_alignment_ms:.2f} ms."
            )
            print("Live dual-device enhancement started. Press Ctrl+C to stop.")
            started = time.monotonic()
            refresh_controls()
            while True:
                if (
                    args.duration_seconds is not None
                    and time.monotonic() - started >= args.duration_seconds
                ):
                    break
                primary, primary_overflow = _read_channel(
                    primary_stream, hop, args.primary_channel
                )
                reference, reference_overflow = _read_channel(
                    reference_stream, hop, args.reference_channel
                )
                capture_overflows += int(primary_overflow) + int(reference_overflow)
                aligned_primary = primary_delay.process(primary)
                aligned_reference = reference_delay.process(reference)
                test_primary = _controlled_demo_primary(
                    aligned_primary,
                    aligned_reference,
                    args.controlled_reference_mix,
                )
                refresh_controls()
                update_gate(aligned_primary, aligned_reference)
                apply_mode()
                output = engine.submit_and_render(test_primary, aligned_reference)
                gain = 0.0 if bool(operator_control["mute_output"]) else 10.0 ** (
                    float(operator_control["output_gain_db"]) / 20.0
                )
                output = np.clip(output * gain, -0.98, 0.98).astype(np.float32)
                output_underflows += int(output_stream.write(output[:, None]))
                now = time.monotonic()
                if args.telemetry_file and now - last_telemetry >= 0.1:
                    runtime_status = stream.monitor.status.__dict__.copy()
                    runtime_status.update(
                        {
                            "calibration_lag_samples": calibration_lag,
                            "calibration_lag_ms": 1000.0 * calibration_lag / sample_rate,
                            "calibration_correlation": calibration_correlation,
                            "capture_overflows": capture_overflows,
                            "output_underflows": output_underflows,
                            "experimental_dual_device": True,
                        }
                    )
                    try:
                        write_atomic_json(
                            args.telemetry_file,
                            build_live_telemetry(
                                test_primary,
                                aligned_reference,
                                output,
                                sample_rate=sample_rate,
                                n_fft=audio["n_fft"],
                                runtime_status=runtime_status,
                                engine_stats=engine.snapshot(),
                                wet_mix=stream.wet_mix,
                                hop_length=hop,
                                playout_latency_ms=1000.0 * engine.added_latency_samples / sample_rate,
                                session_elapsed_seconds=now - started,
                                operator_control=operator_control,
                                model_info={
                                    "architecture": config["model"]["architecture"],
                                    "backend": "onnxruntime" if args.onnx else "pytorch",
                                    "onnx_sha256": sha256_file(args.onnx) if args.onnx else None,
                                    "input_device": f"voice: {primary_info['name']} | reference: {reference_info['name']}",
                                    "output_device": str(sd.query_devices(args.output_device)["name"]),
                                    "primary_channel": int(args.primary_channel),
                                    "reference_channel": int(args.reference_channel),
                                    "capture_topology": "calibrated Windows dual-device demo",
                                    "controlled_reference_mix": float(
                                        args.controlled_reference_mix
                                    ),
                                },
                            ),
                        )
                    except OSError:
                        # Windows browsers, antivirus and indexers can briefly deny
                        # replacement of the JSON file. Telemetry is best effort and
                        # must never stop the real-time audio loop.
                        pass
                    last_telemetry = now
    except KeyboardInterrupt:
        print("stopped")
    finally:
        engine.close()
        report = {
            "experimental_dual_device": True,
            "checkpoint": str(Path(args.checkpoint).resolve()),
            "checkpoint_sha256": sha256_file(args.checkpoint),
            "onnx": str(Path(args.onnx).resolve()) if args.onnx else None,
            "onnx_sha256": sha256_file(args.onnx) if args.onnx else None,
            "primary_device": str(args.primary_device),
            "reference_device": str(args.reference_device),
            "output_device": str(args.output_device),
            "controlled_reference_mix": float(args.controlled_reference_mix),
            "calibration_lag_samples": calibration_lag,
            "calibration_lag_ms": 1000.0 * calibration_lag / sample_rate,
            "calibration_correlation": calibration_correlation,
            "capture_overflows": capture_overflows,
            "output_underflows": output_underflows,
            "engine": engine.snapshot(),
            "runtime": stream.monitor.status.__dict__.copy(),
            "note": (
                "Controlled electronic speech+reference mixture using separate Windows endpoints; "
                "not acoustic field capture or final synchronized-hardware evidence."
                if args.controlled_reference_mix > 0.0
                else "Engineering demo using separate Windows endpoints; not final synchronized-hardware evidence."
            ),
        }
        if args.session_report:
            write_atomic_json(args.session_report, report)
            print(f"session report: {args.session_report}")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
