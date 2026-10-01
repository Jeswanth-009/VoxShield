"""Convert user demo recordings to 16 kHz mono WAV.

Input layout:
  data/user_recordings/clean/*.m4a
  data/user_recordings/noise/*.m4a
  data/user_recordings/mixed_demo/*.m4a

Output layout:
  data/user_recordings_wav/clean/*.wav
  data/user_recordings_wav/noise/*.wav
  data/user_recordings_wav/mixed_demo/*.wav
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def convert_file(ffmpeg: str, source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(target),
    ]
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/user_recordings")
    parser.add_argument("--output", default="data/user_recordings_wav")
    args = parser.parse_args()

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg was not found on PATH. Install ffmpeg or add it to PATH.")

    input_root = Path(args.input)
    output_root = Path(args.output)
    converted = 0
    for split in ("clean", "noise", "mixed_demo"):
        for source in (input_root / split).glob("*"):
            if source.suffix.lower() not in {".m4a", ".mp3", ".wav", ".aac", ".flac"}:
                continue
            target = output_root / split / f"{source.stem}.wav"
            convert_file(ffmpeg, source, target)
            converted += 1
            print(f"{source} -> {target}")

    print(f"converted={converted} output={output_root}")


if __name__ == "__main__":
    main()
