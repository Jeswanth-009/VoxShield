from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | Path) -> dict[str, Any]:
    path = Path(path).resolve()
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    base_name = config.pop("base", None)
    if base_name:
        base = load_config(path.parent / base_name)
        config = _merge(base, config)
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    missing = [name for name in ("audio", "model", "runtime") if name not in config]
    if missing:
        raise ValueError(f"Missing config sections: {', '.join(missing)}")
    audio = config["audio"]
    if audio["n_fft"] <= audio["hop_length"] or audio["n_fft"] % 2:
        raise ValueError("n_fft must be even and greater than hop_length")
    if audio["sample_rate"] <= 0 or audio["hop_length"] <= 0:
        raise ValueError("sample_rate and hop_length must be positive")
    if (
        config["model"].get("architecture") == "official_gtcrn"
        and (audio["sample_rate"] != 16000 or audio["n_fft"] != 512 or audio["hop_length"] != 256)
    ):
        raise ValueError(
            "official_gtcrn requires sample_rate=16000, n_fft=512, hop_length=256"
        )
    if (
        config["model"].get("architecture") == "official_ulunas"
        and (audio["sample_rate"] != 16000 or audio["n_fft"] != 512 or audio["hop_length"] != 256)
    ):
        raise ValueError(
            "official_ulunas requires sample_rate=16000, n_fft=512, hop_length=256"
        )
    data = config.get("data", {})
    if config["model"].get("architecture") == "hybrid_dual_gtcrn":
        if audio["sample_rate"] != 16000 or audio["n_fft"] != 512:
            raise ValueError("hybrid_dual_gtcrn requires sample_rate=16000 and n_fft=512")
        if not data.get("multichannel", False):
            raise ValueError("hybrid_dual_gtcrn requires data.multichannel=true")
    clean_probability = float(data.get("clean_probability", 0.0))
    near_clean_probability = float(data.get("near_clean_probability", 0.0))
    if clean_probability < 0 or near_clean_probability < 0:
        raise ValueError("clean and near-clean probabilities cannot be negative")
    if clean_probability + near_clean_probability >= 1.0:
        raise ValueError("clean and near-clean probabilities must leave some noisy examples")
    delay = data.get("interchannel_delay_samples", (-16, 16))
    if len(delay) != 2 or int(delay[0]) > int(delay[1]):
        raise ValueError("interchannel_delay_samples must be [minimum, maximum]")
    for field in ("category_weights", "noise_dataset_weights", "noise_label_weights"):
        for name, value in data.get(field, {}).items():
            if float(value) <= 0.0:
                raise ValueError(f"{field}.{name} must be positive")
