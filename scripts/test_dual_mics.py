"""Open two Windows microphone endpoints concurrently and show independent levels."""

from __future__ import annotations

import argparse
import threading
import time

import numpy as np


def _device(value: str) -> int | str:
    return int(value) if value.strip().lstrip("-").isdigit() else value


def _dbfs(value: np.ndarray) -> tuple[float, float]:
    audio = np.asarray(value, dtype=np.float64).reshape(-1)
    rms = float(np.sqrt(np.mean(audio**2))) if len(audio) else 0.0
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    return float(20.0 * np.log10(max(rms, 1e-12))), peak


def _bar(db: float, width: int = 30) -> str:
    amount = int(np.clip((db + 72.0) / 72.0, 0.0, 1.0) * width)
    return "#" * amount + "." * (width - amount)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-device", type=_device, default=1)
    parser.add_argument("--reference-device", type=_device, default=2)
    parser.add_argument("--primary-channel", type=int, default=0)
    parser.add_argument("--reference-channel", type=int, default=0)
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--duration", type=float, default=12.0)
    args = parser.parse_args()

    import sounddevice as sd

    if args.primary_device == args.reference_device:
        parser.error("primary and reference devices must be different")
    latest = {
        "primary": np.zeros(256, dtype=np.float32),
        "reference": np.zeros(256, dtype=np.float32),
    }
    status_text = {"primary": "", "reference": ""}
    lock = threading.Lock()

    def callback_for(name: str, channel: int):
        def callback(indata, frames, time_info, status):
            del frames, time_info
            with lock:
                latest[name] = np.asarray(indata[:, channel], dtype=np.float32).copy()
                status_text[name] = str(status) if status else ""

        return callback

    primary_info = sd.query_devices(args.primary_device, "input")
    reference_info = sd.query_devices(args.reference_device, "input")
    print(f"PRIMARY   {args.primary_device}: {primary_info['name']}")
    print(f"REFERENCE {args.reference_device}: {reference_info['name']}")
    print("Speak into the JBL microphone while playing noise near the laptop microphone.")
    print("Both bars should move differently. Avoid ENV clipping and a >20 dB level gap.")
    print("Target while noise plays: VOICE about -35 to -20 dBFS, ENV about -25 to -10 dBFS.")
    print("Press Ctrl+C to stop.\n")

    with (
        sd.InputStream(
            device=args.primary_device,
            samplerate=args.sample_rate,
            blocksize=256,
            channels=args.primary_channel + 1,
            dtype="float32",
            latency="high",
            callback=callback_for("primary", args.primary_channel),
        ),
        sd.InputStream(
            device=args.reference_device,
            samplerate=args.sample_rate,
            blocksize=256,
            channels=args.reference_channel + 1,
            dtype="float32",
            latency="high",
            callback=callback_for("reference", args.reference_channel),
        ),
    ):
        started = time.monotonic()
        try:
            while time.monotonic() - started < args.duration:
                time.sleep(0.25)
                with lock:
                    primary = latest["primary"].copy()
                    reference = latest["reference"].copy()
                    primary_status = status_text["primary"]
                    reference_status = status_text["reference"]
                p_db, p_peak = _dbfs(primary)
                r_db, r_peak = _dbfs(reference)
                level_gap_db = r_db - p_db
                if r_peak >= 0.98 or r_db >= -3.0:
                    verdict = "BAD: ENV CLIPPING - lower phone volume or move it away from laptop"
                elif r_db < -60.0:
                    verdict = "BAD: ENV TOO QUIET"
                elif p_db < -48.0:
                    verdict = "BAD: PRIMARY TOO QUIET - noise must also reach JBL"
                elif level_gap_db > 20.0:
                    verdict = "ADJUST: move phone toward JBL / away from laptop"
                elif level_gap_db < -6.0:
                    verdict = "ADJUST: reference should hear noise more strongly"
                else:
                    verdict = "USABLE LEVEL BALANCE"
                print(
                    f"VOICE {p_db:6.1f} dB [{_bar(p_db)}] peak={p_peak:.3f}  |  "
                    f"ENV {r_db:6.1f} dB [{_bar(r_db)}] peak={r_peak:.3f}  |  "
                    f"gap={level_gap_db:+5.1f} dB  {verdict}"
                )
                if primary_status or reference_status:
                    print(f"  status: voice={primary_status or 'ok'} env={reference_status or 'ok'}")
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
