from __future__ import annotations

import argparse
import json
import queue
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from .checkpoint import load_model, sha256_file, verify_onnx_pair
from .live_engine import AsyncLiveEngine
from .runtime import (
    HybridStreamingEnhancer,
    StreamingDualChannelEnhancer,
    StreamingEnhancer,
    make_onnx_frame_runner,
    make_torch_frame_runner,
)
from .telemetry import build_live_telemetry, write_atomic_json


def _device(value: str) -> int | str:
    return int(value) if value.strip().lstrip("-").isdigit() else value


def _compatible_duplex_pairs(sd, sample_rate: int, input_channels: int) -> list[str]:
    """Return concise same-host-API device pairs that accept the model format."""
    def accepts_input(index: int) -> bool:
        try:
            sd.check_input_settings(
                index, channels=input_channels, dtype="float32", samplerate=sample_rate
            )
        except (sd.PortAudioError, ValueError):
            return False
        return True

    def accepts_output(index: int) -> bool:
        try:
            sd.check_output_settings(
                index, channels=1, dtype="float32", samplerate=sample_rate
            )
        except (sd.PortAudioError, ValueError):
            return False
        return True

    devices = list(sd.query_devices())
    inputs: list[tuple[int, dict]] = []
    outputs: list[tuple[int, dict]] = []
    for index, device in enumerate(devices):
        if (
            int(device.get("max_input_channels", 0)) >= input_channels
            and accepts_input(index)
        ):
            inputs.append((index, device))
        if int(device.get("max_output_channels", 0)) >= 1 and accepts_output(index):
            outputs.append((index, device))
    ranked_pairs: list[tuple[int, str]] = []
    for input_index, input_info in inputs:
        for output_index, output_info in outputs:
            if input_info.get("hostapi") == output_info.get("hostapi"):
                input_name = str(input_info["name"])
                output_name = str(output_info["name"])
                lowered = f"{input_name} {output_name}".lower()
                score = (
                    4 * int("microphone" in input_name.lower())
                    + 4 * int("headphone" in output_name.lower())
                    + 2 * int("speaker" in output_name.lower())
                    - 3 * int("mapper" in lowered)
                    - 2 * int("primary" in lowered)
                    - 3 * int("stereo mix" in lowered)
                )
                ranked_pairs.append(
                    (
                        score,
                        (
                            f"input {input_index} ({input_name}) -> "
                            f"output {output_index} ({output_name})"
                        ),
                    )
                )
    return [text for _, text in sorted(ranked_pairs, reverse=True)[:8]]


def _validate_audio_pair(
    sd,
    input_device: int | str | None,
    output_device: int | str | None,
    *,
    sample_rate: int,
    input_channels: int,
) -> None:
    """Fail before stream startup with an actionable Windows device diagnosis."""
    try:
        input_info = sd.query_devices(input_device, "input")
        output_info = sd.query_devices(output_device, "output")
        if int(input_info.get("max_input_channels", 0)) < input_channels:
            raise ValueError(
                f"input exposes {input_info.get('max_input_channels', 0)} channel(s); "
                f"the model needs {input_channels}"
            )
        if int(output_info.get("max_output_channels", 0)) < 1:
            raise ValueError("selected output exposes no output channel")
        if input_info.get("hostapi") != output_info.get("hostapi"):
            raise ValueError("input and output use different PortAudio host APIs")
        sd.check_input_settings(
            input_device,
            channels=input_channels,
            dtype="float32",
            samplerate=sample_rate,
        )
        sd.check_output_settings(
            output_device,
            channels=1,
            dtype="float32",
            samplerate=sample_rate,
        )
    except Exception as exc:
        pairs = _compatible_duplex_pairs(sd, sample_rate, input_channels)
        suggestions = "\n  ".join(pairs) if pairs else "No compatible pair was detected."
        raise SystemExit(
            f"Audio-device preflight failed at {sample_rate} Hz: {exc}\n"
            f"Format-compatible same-backend candidates detected:\n  {suggestions}\n"
            "A Windows driver may still reject a candidate if another application owns the "
            "microphone or the endpoint was disconnected.\n"
            "Run --list-devices again after connecting/disconnecting a headset because "
            "Windows device numbers change."
        ) from exc


def _pi_health() -> dict[str, object]:
    result: dict[str, object] = {
        "thermal_throttling": None,
        "throttled_bits": None,
        "temperature_c": None,
    }
    thermal_path = Path("/sys/class/thermal/thermal_zone0/temp")
    if thermal_path.exists():
        try:
            result["temperature_c"] = float(thermal_path.read_text().strip()) / 1000.0
        except (OSError, ValueError):
            pass
    try:
        completed = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        raw = completed.stdout.strip().split("=")[-1]
        bits = int(raw, 16)
        result["throttled_bits"] = bits
        result["thermal_throttling"] = bool(bits & ((1 << 2) | (1 << 18)))
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        pass
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run live VoxShield audio enhancement")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--onnx", default=None)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--input-device", type=_device, default=None)
    parser.add_argument("--output-device", type=_device, default=None)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--queue-blocks", type=int, default=8)
    parser.add_argument("--playout-extra-blocks", type=int, default=1)
    parser.add_argument("--telemetry-file", default=None)
    parser.add_argument("--control-file", default=None, help="Dashboard operator-control JSON")
    parser.add_argument("--telemetry-interval", type=float, default=0.10)
    parser.add_argument("--duration-seconds", type=float, default=None)
    parser.add_argument("--session-report", default=None)
    parser.add_argument("--primary-channel", type=int, default=0)
    parser.add_argument(
        "--reference-channel",
        type=int,
        default=1,
        help="Input channel on the same synchronized interface (v4 only)",
    )
    parser.add_argument(
        "--wet-mix",
        type=float,
        default=None,
        help="Enhanced fraction from 0 to 1; lower values preserve more aligned input",
    )
    parser.add_argument(
        "--lms",
        action="store_true",
        help="Enable the hybrid chain: NormalizedLMS pre-cancellation from the "
        "reference channel, then the neural model on the residual. Requires a "
        "2-channel input interface.",
    )
    parser.add_argument("--lms-taps", type=int, default=128)
    parser.add_argument("--lms-step-size", type=float, default=0.05)
    parser.add_argument("--list-devices", action="store_true")
    args = parser.parse_args()
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise SystemExit("Install live audio support with: pip install -e .[live]") from exc
    if args.list_devices:
        print(sd.query_devices())
        return
    model, config, _ = load_model(args.checkpoint, args.device if not args.onnx else "cpu")
    if args.onnx:
        verify_onnx_pair(args.checkpoint, args.onnx)
    audio = config["audio"]
    dual_channel = bool(getattr(model, "requires_reference", False))
    if args.primary_channel < 0 or args.reference_channel < 0:
        parser.error("input channel indices cannot be negative")
    if dual_channel and args.primary_channel == args.reference_channel:
        parser.error("primary and reference channels must be different")
    input_channels = (
        max(args.primary_channel, args.reference_channel) + 1
        if dual_channel
        else args.primary_channel + 1
    )
    _validate_audio_pair(
        sd,
        args.input_device,
        args.output_device,
        sample_rate=audio["sample_rate"],
        input_channels=input_channels,
    )
    runner = (
        make_onnx_frame_runner(model, args.onnx, args.threads)
        if args.onnx
        else make_torch_frame_runner(model, args.device)
    )
    runtime = dict(config["runtime"])
    if args.wet_mix is not None:
        if not 0.0 <= args.wet_mix <= 1.0:
            parser.error("--wet-mix must be between 0 and 1")
        runtime["wet_mix"] = args.wet_mix
    stream_class = (
        StreamingDualChannelEnhancer
        if getattr(model, "requires_reference", False)
        else StreamingEnhancer
    )
    if args.lms:
        stream = HybridStreamingEnhancer(
            runner,
            sample_rate=audio["sample_rate"],
            n_fft=audio["n_fft"],
            hop_length=audio["hop_length"],
            neural_dual_channel=bool(getattr(model, "requires_reference", False)),
            lms_taps=args.lms_taps,
            lms_step_size=args.lms_step_size,
            **runtime,
        )
    else:
        stream = stream_class(
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
    events: queue.SimpleQueue[str] = queue.SimpleQueue()
    operator_control: dict[str, object] = {
        "wet_mix": float(stream.wet_mix), "effective_wet_mix": float(stream.wet_mix),
        "output_gain_db": 0.0, "operator_bypass": False, "mute_output": False,
        "preset": "custom", "operating_mode": "auto",
        "reference_gate": {
            "healthy": False,
            "state": "checking",
            "reason": "waiting for synchronized reference audio",
            "reference_rms_dbfs": -120.0,
            "correlation": 0.0,
        },
    }
    reference_gate = {
        "healthy": False,
        "good_frames": 0,
        "bad_frames": 0,
        "state": "checking",
        "reason": "waiting for synchronized reference audio",
        "reference_rms_dbfs": -120.0,
        "correlation": 0.0,
        "_smoothed_power": 0.0,
    }
    try:
        input_info = sd.query_devices(args.input_device, "input")
        output_info = sd.query_devices(args.output_device, "output")
        input_name = str(input_info.get("name", args.input_device or "system default"))
        output_name = str(output_info.get("name", args.output_device or "system default"))
    except (sd.PortAudioError, ValueError, TypeError):
        input_name = str(args.input_device or "system default")
        output_name = str(args.output_device or "system default")
    model_info = {
        "architecture": config["model"]["architecture"],
        "backend": "onnxruntime" if args.onnx else "pytorch",
        "onnx_sha256": sha256_file(args.onnx) if args.onnx else None,
        "input_device": input_name,
        "output_device": output_name,
        "primary_channel": int(args.primary_channel),
        "reference_channel": int(args.reference_channel) if dual_channel else None,
        "capture_topology": "synchronized dual-channel" if dual_channel else "single-channel",
    }
    control_signature: tuple[int, int] | None = None

    def set_wet_mix(value: float) -> None:
        target = getattr(stream, "inner", stream)
        target.wet_mix = float(np.clip(value, 0.0, 1.0))

    def update_reference_gate(primary: np.ndarray, reference: np.ndarray | None) -> None:
        """Debounced reference-health gate used by Auto mode.

        A healthy reference must be active, non-clipping, and meaningfully different
        from the speech microphone.  This is deliberately a deployment/readiness
        check, not a claim that two unsynchronised Windows devices are phase aligned.
        """
        if reference is None:
            good = False
            reason = "reference microphone unavailable"
            ref_db = -120.0
            correlation = 0.0
        else:
            p = np.asarray(primary, dtype=np.float64)
            r = np.asarray(reference, dtype=np.float64)
            p -= float(np.mean(p))
            r -= float(np.mean(r))
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
            difference = float(
                np.sqrt(np.mean((p - r) ** 2)) / max(p_rms + r_rms, 1e-12)
            )
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
            if int(reference_gate["bad_frames"]) >= 125:
                reference_gate["healthy"] = False
        if bool(reference_gate["healthy"]) and not good:
            reason = "reference hold active; waiting for the next noise burst"
        reference_gate.update({
            "state": "ready" if reference_gate["healthy"] else "not_ready",
            "reason": reason,
            "reference_rms_dbfs": ref_db,
            "smoothed_reference_rms_dbfs": locals().get("smoothed_ref_db", ref_db),
            "correlation": correlation,
        })

    def apply_operating_mode() -> None:
        requested = float(operator_control.get("wet_mix", stream.wet_mix))
        mode = str(operator_control.get("operating_mode", "auto"))
        bypass = bool(operator_control.get("operator_bypass", False))
        if bypass or mode == "dry":
            effective = 0.0
        elif mode == "enhanced":
            effective = requested
        else:
            effective = requested if bool(reference_gate["healthy"]) else 0.0
        set_wet_mix(effective)
        operator_control["effective_wet_mix"] = effective
        operator_control["reference_gate"] = dict(reference_gate)

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
            # Windows PowerShell 5.1 writes ``-Encoding utf8`` with a BOM.
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            requested = float(np.clip(float(value.get("wet_mix", stream.wet_mix)), 0.0, 1.0))
            bypass = bool(value.get("operator_bypass", False))
            operating_mode = str(value.get("operating_mode", "auto"))
            if operating_mode not in {"dry", "enhanced", "auto"}:
                operating_mode = "auto"
            operator_control.update({
                "wet_mix": requested,
                "output_gain_db": float(np.clip(float(value.get("output_gain_db", 0.0)), -18.0, 6.0)),
                "operator_bypass": bypass,
                "mute_output": bool(value.get("mute_output", False)),
                "preset": str(value.get("preset", "custom")),
                "operating_mode": operating_mode,
            })
            apply_operating_mode()
            control_signature = signature
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            events.put(f"operator control ignored: {exc}")
    last_mode = stream.monitor.status.mode
    dual_channel = bool(
        getattr(stream, "consumes_reference", isinstance(stream, StreamingDualChannelEnhancer))
    )
    if args.telemetry_interval <= 0:
        parser.error("--telemetry-interval must be positive")
    if args.duration_seconds is not None and args.duration_seconds <= 0:
        parser.error("--duration-seconds must be positive")
    telemetry_blocks: queue.Queue[tuple[np.ndarray, np.ndarray | None, np.ndarray]] = (
        queue.Queue(maxsize=4)
    )

    def callback(indata, outdata, frames, time_info, status):
        nonlocal last_mode
        if status:
            stream.monitor.observe_audio_status(status)
            events.put(str(status))
        try:
            primary_block = np.asarray(indata[:, args.primary_channel], dtype=np.float32)
            reference_block = (
                np.asarray(indata[:, args.reference_channel], dtype=np.float32)
                if dual_channel
                else None
            )
            update_reference_gate(primary_block, reference_block)
            apply_operating_mode()
            output = engine.submit_and_render(
                primary_block,
                reference_block,
            )
        except Exception as exc:  # noqa: BLE001 - callback must always provide safe audio
            output = np.asarray(indata[:, args.primary_channel], dtype=np.float32)
            events.put(f"live engine callback fallback: {exc}")
        if len(output) < frames:
            output = np.pad(output, (0, frames - len(output)))
        gain = 0.0 if operator_control["mute_output"] else 10.0 ** (
            float(operator_control["output_gain_db"]) / 20.0
        )
        output = np.clip(output[:frames] * gain, -0.98, 0.98).astype(np.float32)
        outdata[:, 0] = output
        if args.telemetry_file:
            item = (
                primary_block.copy(),
                reference_block.copy() if reference_block is not None else None,
                np.asarray(output[:frames], dtype=np.float32).copy(),
            )
            try:
                telemetry_blocks.put_nowait(item)
            except queue.Full:
                try:
                    telemetry_blocks.get_nowait()
                except queue.Empty:
                    pass
                try:
                    telemetry_blocks.put_nowait(item)
                except queue.Full:
                    pass
        mode = stream.monitor.status.mode
        if mode != last_mode:
            events.put(json.dumps(stream.monitor.status.__dict__))
            last_mode = mode

    print(
        f"Live enhancement: {audio['sample_rate']} Hz, {audio['hop_length']} samples/block, "
        f"live playout latency={1000 * engine.added_latency_samples / audio['sample_rate']:.1f} ms, "
        f"wet_mix={stream.wet_mix:.2f}, inputs={'primary+reference' if dual_channel else 'primary'}"
    )
    print("Press Ctrl+C to stop. Runtime health changes are printed below.")
    started = time.monotonic()
    refresh_controls()
    last_telemetry = 0.0
    telemetry_warning_active = False
    try:
        with sd.Stream(
            samplerate=audio["sample_rate"],
            blocksize=audio["hop_length"],
            channels=(input_channels, 1),
            dtype="float32",
            device=(args.input_device, args.output_device),
            callback=callback,
        ):
            while True:
                now = time.monotonic()
                refresh_controls()
                if args.duration_seconds is not None and now - started >= args.duration_seconds:
                    print("requested duration completed")
                    break
                try:
                    print(events.get(timeout=0.1), file=sys.stderr)
                except queue.Empty:
                    pass
                if args.telemetry_file and now - last_telemetry >= args.telemetry_interval:
                    latest = None
                    while True:
                        try:
                            latest = telemetry_blocks.get_nowait()
                        except queue.Empty:
                            break
                    if latest is not None:
                        primary, reference, enhanced = latest
                        try:
                            write_atomic_json(
                                args.telemetry_file,
                                build_live_telemetry(
                                    primary,
                                    reference,
                                    enhanced,
                                    sample_rate=audio["sample_rate"],
                                    n_fft=audio["n_fft"],
                                    runtime_status=stream.monitor.status.__dict__.copy(),
                                    engine_stats=engine.snapshot(),
                                    wet_mix=stream.wet_mix,
                                    hop_length=audio["hop_length"],
                                    playout_latency_ms=1000 * engine.added_latency_samples / audio["sample_rate"],
                                    session_elapsed_seconds=now - started,
                                    operator_control=operator_control,
                                    model_info=model_info,
                                ),
                            )
                            telemetry_warning_active = False
                        except OSError as exc:
                            if not telemetry_warning_active:
                                events.put(f"telemetry temporarily unavailable: {exc}")
                                telemetry_warning_active = True
                        last_telemetry = now
    except KeyboardInterrupt:
        print("stopped")
    except sd.PortAudioError as exc:
        raise SystemExit(
            f"Windows could not open the selected live audio stream: {exc}\n"
            "Close applications using the microphone, reconnect the headset, run "
            "--list-devices again, and select current input/output IDs from the same backend."
        ) from exc
    finally:
        engine.close()
        elapsed = time.monotonic() - started
        engine_stats = engine.snapshot()
        print(f"live engine: {json.dumps(engine_stats)}")
        if args.session_report:
            pi_health = _pi_health()
            status = stream.monitor.status.__dict__.copy()
            report = {
                "checkpoint": str(Path(args.checkpoint).resolve()),
                "checkpoint_sha256": sha256_file(args.checkpoint),
                "onnx": str(Path(args.onnx).resolve()) if args.onnx else None,
                "onnx_sha256": sha256_file(args.onnx) if args.onnx else None,
                "architecture": config["model"]["architecture"],
                "input_channels": 2 if dual_channel else 1,
                "duration_seconds": elapsed,
                "sample_rate": audio["sample_rate"],
                "hop_length": audio["hop_length"],
                "playout_latency_ms": 1000
                * engine.added_latency_samples
                / audio["sample_rate"],
                "engine": engine_stats,
                "runtime": status,
                "xruns": int(status.get("audio_status_events", 0)),
                "invalid_model_bypasses": int(status.get("failures", 0)),
                "output_underflows": int(engine_stats.get("output_underflows", 0)),
                "dropped_input_blocks": int(
                    engine_stats.get("dropped_input_blocks", 0)
                ),
                "worker_failures": int(engine_stats.get("worker_failures", 0)),
                **pi_health,
            }
            write_atomic_json(args.session_report, report)
            print(f"session report: {args.session_report}")


if __name__ == "__main__":
    main()
