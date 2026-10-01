"""Evaluate the official H-GTCRN checkpoint on a VoxShield paired manifest.

This is an offline research oracle, not the deployable VoxShield runtime.  The
official front-end performs iterative FD-WPE + AuxIVA and therefore cannot be
presented as a 16 ms streaming implementation without a separate online IVA
port and latency benchmark.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from voxshield.audio import read_audio
from voxshield.metrics import optional_metrics, si_snr, snr


def load_official_model(root: Path, variant: str, device: torch.device) -> torch.nn.Module:
    folder = "masking_on_noisy" if variant == "noisy" else "masking_on_iva"
    checkpoint = "best_model_0121.tar" if variant == "noisy" else "best_model_0110.tar"
    source = root / folder / "gtcrn_iva.py"
    spec = importlib.util.spec_from_file_location(f"hgtcrn_{variant}", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    model = module.GTCRN_IVA().to(device)
    payload = torch.load(root / folder / checkpoint, map_location=device, weights_only=False)
    model.load_state_dict(payload["model"], strict=True)
    return model.eval()


def mean(records: list[dict], key: str) -> float | None:
    values = [r[key] for r in records if r.get(key) is not None and np.isfinite(r[key])]
    return float(np.mean(values)) if values else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--official-root", default="external/h-gtcrn")
    parser.add_argument("--variant", choices=("noisy", "iva"), default="noisy")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output", required=True)
    parser.add_argument("--save-audio")
    args = parser.parse_args()

    device = torch.device(args.device)
    model = load_official_model(Path(args.official_root), args.variant, device)
    rows = [json.loads(line) for line in Path(args.manifest).read_text(encoding="utf-8").splitlines()]
    rows = rows[: args.limit] if args.limit else rows
    audio_dir = Path(args.save_audio) if args.save_audio else None
    if audio_dir:
        audio_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    for row in rows:
        clean = read_audio(Path(args.data_root) / row["clean"], 16000)
        noisy = read_audio(Path(args.data_root) / row["noisy"], 16000)
        reference = read_audio(Path(args.data_root) / row["reference"], 16000)
        length = min(len(clean), len(noisy), len(reference))
        channels = np.stack((noisy[:length], reference[:length]), axis=0)
        with torch.inference_mode():
            enhanced = model(torch.from_numpy(channels).unsqueeze(0).to(device))
        enhanced_np = enhanced.detach().cpu().numpy().reshape(-1)[:length]
        extra = optional_metrics(clean[:length], enhanced_np, 16000)
        record = {
            "id": row["id"],
            "category": row["category"],
            "noise_source_label": row.get("noise_source_label"),
            "snr_enhanced": snr(clean[:length], enhanced_np),
            "si_snr_enhanced": si_snr(clean[:length], enhanced_np),
            "stoi_enhanced": extra.get("stoi"),
            "pesq_enhanced": extra.get("pesq"),
        }
        records.append(record)
        if audio_dir:
            sf.write(audio_dir / f"{row['id']}_hgtcrn_{args.variant}.wav", enhanced_np, 16000)
    keys = ("snr_enhanced", "si_snr_enhanced", "stoi_enhanced", "pesq_enhanced")
    result = {
        "warning": (
            "Offline official H-GTCRN oracle only. Its iterative FD-WPE/AuxIVA front-end "
            "has not been converted or validated as VoxShield streaming inference."
        ),
        "variant": args.variant,
        "count": len(records),
        "summary": {key: mean(records, key) for key in keys},
        "target_attainment": {
            "snr": mean([{"v": float(r["snr_enhanced"] >= 15.0)} for r in records], "v"),
            "stoi": mean([{"v": float(r["stoi_enhanced"] >= 0.85)} for r in records], "v"),
            "pesq": mean([{"v": float(r["pesq_enhanced"] >= 2.5)} for r in records], "v"),
            "all_three": mean(
                [
                    {
                        "v": float(
                            r["snr_enhanced"] >= 15.0
                            and r["stoi_enhanced"] >= 0.85
                            and r["pesq_enhanced"] >= 2.5
                        )
                    }
                    for r in records
                ],
                "v",
            ),
        },
        "records": records,
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"] | {"target_attainment": result["target_attainment"]}, indent=2))


if __name__ == "__main__":
    main()
