from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import torch

from .model import build_model


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_onnx_pair(checkpoint_path: str | Path, onnx_path: str | Path) -> None:
    report_path = Path(onnx_path).with_suffix(".validation.json")
    if not report_path.exists():
        raise RuntimeError(f"Missing ONNX validation report: {report_path}. Run voxshield-export.")
    import json

    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not report.get("passed"):
        raise RuntimeError("ONNX validation report is not marked as passed")
    if report.get("checkpoint_sha256") != sha256_file(checkpoint_path):
        raise RuntimeError("ONNX does not match this checkpoint (checkpoint SHA-256 mismatch)")
    if report.get("onnx_sha256") != sha256_file(onnx_path):
        raise RuntimeError("ONNX file changed after validation (ONNX SHA-256 mismatch)")


def save_checkpoint(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, temporary)
    os.replace(temporary, path)


def load_model(
    checkpoint_path: str | Path, device: str | torch.device = "cpu"
) -> tuple[torch.nn.Module, dict[str, Any], dict[str, Any]]:
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    if "config" not in checkpoint or "model" not in checkpoint:
        raise ValueError("Invalid checkpoint: expected config and model fields")
    model = build_model(checkpoint["config"])
    model.load_state_dict(checkpoint["model"])
    model.to(device).eval()
    return model, checkpoint["config"], checkpoint
