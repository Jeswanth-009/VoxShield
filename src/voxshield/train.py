from __future__ import annotations

import argparse
import csv
import json
import math
import random
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader, RandomSampler
from tqdm import tqdm

from .checkpoint import save_checkpoint
from .config import load_config
from .data.dataset import RandomMixDataset
from .losses import EnhancementLoss
from .model import build_model, count_parameters
from .official_gtcrn import OfficialGTCRN, load_official_weights


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _worker_seed(worker_id: int) -> None:
    seed = torch.initial_seed() % (2**32)
    np.random.seed(seed)
    random.seed(seed)


def _valid_amp_scaler_state(state: dict[str, Any] | None) -> bool:
    """Return whether a saved GradScaler state is safe to restore."""
    if not state:
        return False
    try:
        scale = float(state.get("scale", float("nan")))
    except (TypeError, ValueError):
        return False
    return math.isfinite(scale) and scale > 0.0


def _initialize_model(
    model: torch.nn.Module,
    config: dict[str, Any],
    path: str | Path,
    device: torch.device,
) -> None:
    state = torch.load(path, map_location=device, weights_only=False)
    saved_config = state.get("config", {})
    saved_architecture = saved_config.get("model", {}).get("architecture")
    current_architecture = config.get("model", {}).get("architecture")
    if saved_architecture != current_architecture:
        raise ValueError(
            f"Initialization architecture {saved_architecture!r} does not match "
            f"{current_architecture!r}"
        )
    try:
        model.load_state_dict(state["model"], strict=True)
    except (KeyError, RuntimeError) as exc:
        raise ValueError(f"Incompatible initialization checkpoint: {path}") from exc


def _initialize_fresh_model(
    model: torch.nn.Module,
    config: dict[str, Any],
    device: torch.device,
) -> str | None:
    """Load exactly one fresh-run source, preferring an explicit checkpoint."""
    initialization_path = config.get("model", {}).get("initialize_from")
    if initialization_path:
        _initialize_model(model, config, initialization_path, device)
        if config.get("model", {}).get("reset_imaginary_branch", False):
            reset = getattr(model, "reset_imaginary_branch", None)
            if not callable(reset):
                raise ValueError(
                    "model.reset_imaginary_branch requested for an unsupported model"
                )
            reset()
        return f"initialized model weights from {initialization_path}; optimizer starts fresh"
    pretrained = config.get("model", {}).get("pretrained")
    if pretrained:
        if isinstance(model, OfficialGTCRN):
            load_official_weights(model, str(pretrained))
        elif callable(getattr(model, "load_pretrained", None)):
            model.load_pretrained(str(pretrained))
        else:
            raise ValueError(f"model.pretrained is unsupported for {type(model).__name__}")
        return f"initialized pretrained model weights from {pretrained}"
    return None


def _selection_score(metrics: dict[str, float], config: dict[str, Any]) -> float:
    """Return the lower-is-better score used for best-checkpoint selection.

    Existing recipes keep selecting on total validation loss. Preservation
    fine-tuning may add explicit component weights so improving noisy examples
    cannot hide worsening clean-speech coloration.
    """
    weights = config["train"].get("selection_weights")
    if not weights:
        return float(metrics["total"])
    missing = sorted(set(weights) - set(metrics))
    if missing:
        raise ValueError(
            "train.selection_weights references missing validation metrics: "
            + ", ".join(missing)
        )
    return float(
        sum(float(weight) * float(metrics[name]) for name, weight in weights.items())
    )


def _run_epoch(
    model: torch.nn.Module,
    loader: DataLoader,
    criterion: EnhancementLoss,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None,
    scaler: torch.amp.GradScaler,
    config: dict[str, Any],
) -> dict[str, float]:
    training = optimizer is not None
    model.train(training)
    if training and config["train"].get("freeze_batch_norm_stats", False):
        for module in model.modules():
            if isinstance(module, torch.nn.modules.batchnorm._BatchNorm):
                module.eval()
    totals: dict[str, float] = {}
    batches = 0
    progress = tqdm(loader, desc="train" if training else "valid", leave=False)
    for batch in progress:
        mixture = batch["mixture"].to(device, non_blocking=True)
        clean = batch["clean"].to(device, non_blocking=True)
        reference = batch.get("reference")
        if reference is not None:
            reference = reference.to(device, non_blocking=True)
        preservation_mask = torch.tensor(
            [
                str(category) == "clean" or str(category).startswith("near_clean:")
                for category in batch["category"]
            ],
            dtype=torch.bool,
            device=device,
        )
        if training:
            optimizer.zero_grad(set_to_none=True)
        with torch.set_grad_enabled(training):
            with torch.autocast(
                device_type=device.type,
                enabled=bool(config["train"]["amp"] and device.type == "cuda"),
            ):
                if getattr(model, "requires_reference", False):
                    if reference is None:
                        raise ValueError(
                            "The selected model requires reference audio; enable data.multichannel"
                        )
                    estimate, estimate_spectrum = model.forward_audio(
                        mixture, reference, config["audio"]["hop_length"]
                    )
                else:
                    estimate, estimate_spectrum = model.forward_audio(
                        mixture, config["audio"]["hop_length"]
                    )
                loss, components = criterion(
                    estimate,
                    clean,
                    estimate_spectrum,
                    mixture_audio=mixture,
                    preservation_mask=preservation_mask,
                )
            if not torch.isfinite(loss):
                raise FloatingPointError("Non-finite training loss; checkpoint was not updated")
            if training:
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                gradient_norm = torch.nn.utils.clip_grad_norm_(
                    model.parameters(), config["train"]["grad_clip_norm"]
                )
                # In full precision, a non-finite gradient is a real failure.
                # Under AMP it can be a recoverable overflow: GradScaler must
                # be allowed to skip the optimizer step and lower its scale.
                if not torch.isfinite(gradient_norm) and not scaler.is_enabled():
                    raise FloatingPointError(
                        "Non-finite gradient norm; optimizer step and checkpoint were skipped"
                    )
                scaler.step(optimizer)
                scaler.update()
                if scaler.is_enabled():
                    scale = float(scaler.get_scale())
                    if not math.isfinite(scale) or scale <= 0.0:
                        raise FloatingPointError(
                            "AMP gradient scale became non-finite or zero; "
                            "checkpoint was not updated. Resume with AMP disabled."
                        )
        batches += 1
        for name, value in components.items():
            totals[name] = totals.get(name, 0.0) + float(value.detach())
        progress.set_postfix(loss=f"{float(loss.detach()):.3f}")
    if batches == 0:
        raise RuntimeError("DataLoader yielded no batches")
    return {name: value / batches for name, value in totals.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train VoxShield")
    parser.add_argument("--config", default="configs/base.yaml")
    parser.add_argument("--resume", default=None)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.resume:
        config["train"]["resume"] = args.resume
        config.setdefault("model", {})["initialize_from"] = None
    _seed_everything(int(config["seed"]))
    device = torch.device(args.device)
    model = build_model(config).to(device)
    initialization_path = config.get("model", {}).get("initialize_from")
    if initialization_path and config["train"].get("resume"):
        raise ValueError("model.initialize_from and train.resume are mutually exclusive")
    if not config["train"].get("resume"):
        initialization_message = _initialize_fresh_model(model, config, device)
        if initialization_message:
            print(initialization_message)
    criterion = EnhancementLoss(config).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config["train"]["learning_rate"],
        weight_decay=config["train"]["weight_decay"],
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, factor=0.5, patience=4)
    scaler = torch.amp.GradScaler("cuda", enabled=config["train"]["amp"] and device.type == "cuda")
    start_epoch, global_step = 0, 0
    best_loss, best_selection_score = float("inf"), float("inf")
    resume_path = config["train"].get("resume")
    if resume_path:
        state = torch.load(resume_path, map_location=device, weights_only=False)
        saved_recipe = int(state.get("config", {}).get("recipe_version", 1))
        current_recipe = int(config.get("recipe_version", 1))
        if saved_recipe != current_recipe:
            raise ValueError(
                f"Checkpoint recipe v{saved_recipe} is incompatible with config recipe "
                f"v{current_recipe}; start a fresh run instead of resuming it"
            )
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        scheduler.load_state_dict(state["scheduler"])
        saved_scaler = state.get("scaler")
        if scaler.is_enabled() and saved_scaler:
            if _valid_amp_scaler_state(saved_scaler):
                scaler.load_state_dict(saved_scaler)
            else:
                print(
                    "warning: checkpoint AMP scaler is invalid; using a fresh scaler. "
                    "For a stability-sensitive resume, set train.amp=false."
                )
        start_epoch = int(state["epoch"]) + 1
        global_step = int(state.get("global_step", 0))
        best_loss = float(state.get("best_val_loss", best_loss))
        best_selection_score = float(
            state.get("best_selection_score", best_loss)
        )
        epochs_without_improvement = int(state.get("epochs_without_improvement", 0))
    else:
        epochs_without_improvement = 0
    train_set = RandomMixDataset(config, "train")
    val_set = RandomMixDataset(config, "val")
    generator = torch.Generator().manual_seed(int(config["seed"]))
    num_workers = int(config["train"]["num_workers"])
    loader_options = {
        "batch_size": config["train"]["batch_size"],
        "num_workers": num_workers,
        "pin_memory": device.type == "cuda",
        "worker_init_fn": _worker_seed,
        "generator": torch.Generator().manual_seed(int(config["seed"]) + 1_000_000),
        "persistent_workers": bool(
            num_workers > 0 and config["train"].get("persistent_workers", True)
        ),
    }
    train_loader = DataLoader(
        train_set, sampler=RandomSampler(train_set, generator=generator),
        drop_last=True, **loader_options
    )
    val_loader = DataLoader(val_set, shuffle=False, drop_last=False, **loader_options)
    checkpoint_dir = Path(config["train"]["checkpoint_dir"])
    run_dir = Path(config["train"]["run_dir"])
    run_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = run_dir / "metrics.jsonl"
    csv_path = run_dir / "metrics.csv"
    try:
        from torch.utils.tensorboard import SummaryWriter

        tensorboard = SummaryWriter(run_dir / "tensorboard")
    except ImportError:
        tensorboard = None
    print(f"device={device} parameters={count_parameters(model):,}")
    if config["train"].get("freeze_batch_norm_stats", False):
        print("pretrained BatchNorm running statistics are frozen during fine-tuning")
    for epoch in range(start_epoch, int(config["train"]["epochs"])):
        # Epoch-local ordering is reproducible after an epoch-boundary resume.
        generator.manual_seed(int(config["seed"]) + epoch)
        _seed_everything(int(config["seed"]) + epoch)
        train_set.set_epoch(epoch)
        val_set.set_epoch(0)
        started = time.time()
        train_metrics = _run_epoch(model, train_loader, criterion, device, optimizer, scaler, config)
        global_step += len(train_loader)
        should_validate = (epoch + 1) % int(config["train"]["validate_every"]) == 0
        val_metrics = (
            _run_epoch(model, val_loader, criterion, device, None, scaler, config)
            if should_validate
            else {}
        )
        selection_score = (
            _selection_score(val_metrics, config) if val_metrics else None
        )
        if val_metrics:
            scheduler.step(
                selection_score
                if config["train"].get("scheduler_metric") == "selection_score"
                else val_metrics["total"]
            )
        record = {
            "epoch": epoch,
            "seconds": time.time() - started,
            "learning_rate": optimizer.param_groups[0]["lr"],
            "train": train_metrics,
            "validation": val_metrics,
            "selection_score": selection_score,
        }
        with metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        metric_names = tuple(sorted(set(train_metrics) | set(val_metrics)))
        csv_row = {
            "epoch": epoch,
            "seconds": record["seconds"],
            "learning_rate": record["learning_rate"],
            "selection_score": selection_score,
            **{f"train_{key}": train_metrics.get(key) for key in metric_names},
            **{f"val_{key}": val_metrics.get(key) for key in metric_names},
        }
        write_header = not csv_path.exists()
        with csv_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(csv_row))
            if write_header:
                writer.writeheader()
            writer.writerow(csv_row)
        if tensorboard is not None:
            for split, values in (("train", train_metrics), ("validation", val_metrics)):
                for name, value in values.items():
                    tensorboard.add_scalar(f"{split}/{name}", value, epoch)
            tensorboard.add_scalar("train/learning_rate", record["learning_rate"], epoch)
            if selection_score is not None:
                tensorboard.add_scalar("validation/selection_score", selection_score, epoch)
        min_delta = float(config["train"].get("early_stopping_min_delta", 0.0))
        if val_metrics:
            best_loss = min(best_loss, float(val_metrics["total"]))
        improved = bool(
            selection_score is not None
            and selection_score < best_selection_score - min_delta
        )
        if improved:
            best_selection_score = float(selection_score)
            epochs_without_improvement = 0
        elif val_metrics:
            epochs_without_improvement += 1
        payload = {
            "format_version": 1,
            "epoch": epoch,
            "global_step": global_step,
            "best_val_loss": best_loss,
            "best_selection_score": best_selection_score,
            "epochs_without_improvement": epochs_without_improvement,
            "config": config,
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(),
            "scaler": scaler.state_dict(),
        }
        save_checkpoint(checkpoint_dir / "last.pt", payload)
        if improved:
            save_checkpoint(checkpoint_dir / "best.pt", payload)
        print(json.dumps(record))
        patience = config["train"].get("early_stopping_patience")
        if patience and epochs_without_improvement >= int(patience):
            print(
                f"early stopping: validation did not improve for "
                f"{epochs_without_improvement} validation runs"
            )
            break
    if tensorboard is not None:
        tensorboard.close()


if __name__ == "__main__":
    main()
