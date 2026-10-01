from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import numpy as np
import torch

from .checkpoint import load_model, save_checkpoint
from .config import load_config
from .losses import EnhancementLoss
from .model import build_model, count_parameters
from .official_gtcrn import OfficialGTCRN, load_official_weights
from .runtime import StreamingEnhancer, make_torch_frame_runner


def main() -> None:
    parser = argparse.ArgumentParser(description="Data-free one-step VoxShield smoke test")
    parser.add_argument("--config", default="configs/base.yaml")
    args = parser.parse_args()
    torch.manual_seed(7)
    config = load_config(args.config)
    model = build_model(config)
    if isinstance(model, OfficialGTCRN) and config.get("model", {}).get("pretrained"):
        load_official_weights(model, config["model"]["pretrained"])
    criterion = EnhancementLoss(config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    length = config["audio"]["n_fft"] * 8
    clean = torch.randn(1, length) * 0.03
    mixture = clean + torch.randn_like(clean) * 0.01
    estimate, spectrum = model.forward_audio(mixture, config["audio"]["hop_length"])
    loss, components = criterion(estimate, clean, spectrum)
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    optimizer.step()
    if not torch.isfinite(loss):
        raise SystemExit("non-finite loss")
    with tempfile.TemporaryDirectory() as temporary:
        checkpoint = Path(temporary) / "smoke.pt"
        save_checkpoint(
            checkpoint,
            {
                "format_version": 1,
                "epoch": 0,
                "global_step": 1,
                "config": config,
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
            },
        )
        restored, restored_config, _ = load_model(checkpoint)
        stream = StreamingEnhancer(
            make_torch_frame_runner(restored),
            sample_rate=restored_config["audio"]["sample_rate"],
            n_fft=restored_config["audio"]["n_fft"],
            hop_length=restored_config["audio"]["hop_length"],
            deadline_fraction=1000.0,
        )
        source = mixture.squeeze(0).numpy()
        chunks = [stream.process(source[index : index + 173]) for index in range(0, len(source), 173)]
        chunks.append(stream.flush())
        output = np.concatenate(chunks)
    if len(output) != length or not np.isfinite(output).all():
        raise SystemExit("streaming checkpoint round-trip failed")
    print(
        json.dumps(
            {
                "passed": True,
                "trainable_parameters": count_parameters(model),
                "one_step_loss": float(loss.detach()),
                "components": {name: float(value.detach()) for name, value in components.items()},
                "streamed_samples": len(output),
                "note": "Synthetic plumbing check only; this is not a quality metric.",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
