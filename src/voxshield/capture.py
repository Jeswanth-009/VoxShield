"""Capture and inspect synchronized primary/reference microphone audio."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from .audio import sanitize_audio
from .diagnostics import dual_channel_diagnostics, read_dual_channel_file


def _device(value: str) -> int | str:
    return int(value) if value.strip().lstrip("-").isdigit() else value


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-._")
    return cleaned or "capture"


def _write_capture(
    output_root: Path,
    name: str,
    selected: np.ndarray,
    sample_rate: int,
    metadata: dict[str, Any],
) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    session = output_root / f"{timestamp}-{_slug(name)}"
    suffix = 1
    while session.exists():
        session = output_root / f"{timestamp}-{_slug(name)}-{suffix:02d}"
        suffix += 1
    session.mkdir(parents=True)
    selected = sanitize_audio(selected)
    sf.write(str(session / "synchronized.wav"), selected, sample_rate, subtype="PCM_24")
    sf.write(str(session / "primary.wav"), selected[:, 0], sample_rate, subtype="PCM_24")
    sf.write(str(session / "reference.wav"), selected[:, 1], sample_rate, subtype="PCM_24")
    (session / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return session


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record or inspect synchronized two-channel VoxShield audio"
    )
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--analyze", default=None, help="Analyze an existing multichannel file")
    parser.add_argument("--input-device", type=_device, default=None)
    parser.add_argument("--primary-channel", type=int, default=0)
    parser.add_argument("--reference-channel", type=int, default=1)
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--output-dir", default="data/captures")
    parser.add_argument("--name", default="field")
    parser.add_argument(
        "--label",
        default="unlabeled",
        help="Human label such as tank_idle, rotor, speech_only, or mixed",
    )
    args = parser.parse_args()
    if args.primary_channel < 0 or args.reference_channel < 0:
        parser.error("channel indices cannot be negative")
    if args.primary_channel == args.reference_channel:
        parser.error("primary and reference channels must be different")
    if args.sample_rate <= 0 or args.seconds <= 0:
        parser.error("sample rate and duration must be positive")
    if args.analyze:
        primary, reference, sample_rate = read_dual_channel_file(
            args.analyze,
            primary_channel=args.primary_channel,
            reference_channel=args.reference_channel,
        )
        print(json.dumps(dual_channel_diagnostics(primary, reference, sample_rate), indent=2))
        return
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise SystemExit("Install live audio support with: pip install -e .[live]") from exc
    if args.list_devices:
        print(sd.query_devices())
        return
    input_channels = max(args.primary_channel, args.reference_channel) + 1
    frames = round(args.seconds * args.sample_rate)
    device_info = sd.query_devices(args.input_device, "input")
    if int(device_info["max_input_channels"]) < input_channels:
        parser.error(
            f"selected device exposes {device_info['max_input_channels']} input channels; "
            f"{input_channels} are required"
        )
    print(
        f"Recording {args.seconds:.1f}s at {args.sample_rate} Hz from one synchronized device. "
        "Do not change device settings during capture."
    )
    recorded = sd.rec(
        frames,
        samplerate=args.sample_rate,
        channels=input_channels,
        dtype="float32",
        device=args.input_device,
        blocking=True,
    )
    selected = np.column_stack(
        (recorded[:, args.primary_channel], recorded[:, args.reference_channel])
    ).astype(np.float32)
    diagnostics = dual_channel_diagnostics(selected[:, 0], selected[:, 1], args.sample_rate)
    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "name": args.name,
        "label": args.label,
        "device": {key: device_info[key] for key in device_info},
        "sample_rate": args.sample_rate,
        "input_channels_requested": input_channels,
        "primary_source_channel": args.primary_channel,
        "reference_source_channel": args.reference_channel,
        "diagnostics": diagnostics,
        "usage": "research_capture_not_a_quality_claim",
    }
    session = _write_capture(
        Path(args.output_dir), args.name, selected, args.sample_rate, metadata
    )
    print(json.dumps({"session": str(session), "diagnostics": diagnostics}, indent=2))


if __name__ == "__main__":
    main()
