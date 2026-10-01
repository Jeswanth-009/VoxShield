from __future__ import annotations

import argparse
import json
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from tqdm import tqdm

from .audio import read_audio
from .checkpoint import load_model, sha256_file
from .infer import build_stream, enhance_file
from .metrics import (
    active_level_error_db,
    optional_dnsmos,
    optional_metrics,
    pause_noise_attenuation,
    si_snr,
    snr,
    speech_deletion_rate,
)


def _mean(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None and np.isfinite(value)]
    return float(np.mean(valid)) if valid else None


def _distribution(values: list[float | None]) -> dict[str, float | int | None]:
    """Expose the weak tail so a good mean cannot hide bad examples."""
    valid = np.asarray(
        [value for value in values if value is not None and np.isfinite(value)],
        dtype=np.float64,
    )
    if not valid.size:
        return {"count": 0, "minimum": None, "p05": None, "p10": None,
                "median": None, "p90": None, "maximum": None}
    return {
        "count": int(valid.size),
        "minimum": float(np.min(valid)),
        "p05": float(np.percentile(valid, 5)),
        "p10": float(np.percentile(valid, 10)),
        "median": float(np.median(valid)),
        "p90": float(np.percentile(valid, 90)),
        "maximum": float(np.max(valid)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate fixed paired mixtures")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--manifest", default="data/mixtures/test_v2/manifest.jsonl")
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--onnx", default=None)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument(
        "--cascade-passes",
        type=int,
        default=1,
        help="Apply independent streaming model instances sequentially (diagnostic; default: 1)",
    )
    parser.add_argument("--require-pesq", action="store_true")
    parser.add_argument(
        "--dnsmos",
        action="store_true",
        help="Also score DNSMOS/P.835 (no-reference SIG/BAK/OVRL) on noisy and "
        "enhanced audio; requires the optional speechmos package",
    )
    parser.add_argument("--legacy-dc-blocker", action="store_true",
                        help="Reproduce the old output high-pass filter for an ablation")
    parser.add_argument(
        "--lms",
        action="store_true",
        help="Evaluate the full hybrid chain: NormalizedLMS pre-cancellation "
        "from the reference channel, then the neural model on the residual",
    )
    parser.add_argument("--lms-taps", type=int, default=128)
    parser.add_argument("--lms-step-size", type=float, default=0.05)
    parser.add_argument(
        "--wet-mix",
        type=float,
        default=None,
        help=(
            "Override the checkpoint runtime wet mix for a controlled evaluation "
            "(0=dry aligned input, 1=fully enhanced)"
        ),
    )
    parser.add_argument("--output", default="artifacts/evaluation.json")
    parser.add_argument("--save-audio", default=None)
    parser.add_argument(
        "--save-audio-limit",
        type=int,
        default=None,
        help="Save only the first N enhanced examples while still evaluating the full manifest",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Evaluate only the first N rows for a quick engineering gate",
    )
    parser.add_argument(
        "--fail-on-regression", action="store_true",
        help="Return a failure code unless the noisy-example quality gate passes",
    )
    parser.add_argument(
        "--strict-sih-gate",
        action="store_true",
        help="Require the stated SNR/STOI/PESQ targets plus voice-preservation limits",
    )
    parser.add_argument(
        "--minimum-individual-target-rate",
        type=float,
        default=0.80,
        help=(
            "With --strict-sih-gate, require at least this fraction of noisy clips "
            "to meet each SNR/STOI/PESQ target (default: 0.80)"
        ),
    )
    parser.add_argument(
        "--minimum-all-target-rate",
        type=float,
        default=0.60,
        help=(
            "With --strict-sih-gate, require at least this fraction of noisy clips "
            "to meet SNR, STOI and PESQ simultaneously (default: 0.60)"
        ),
    )
    parser.add_argument(
        "--expected-noisy-categories",
        default="stationary,nonstationary,impulsive,environmental,mixed",
        help="Comma-separated categories required by this evaluation gate",
    )
    args = parser.parse_args()
    if args.threads < 1:
        parser.error("--threads must be positive")
    if args.cascade_passes < 1:
        parser.error("--cascade-passes must be positive")
    torch.set_num_threads(args.threads)
    if args.require_pesq or args.strict_sih_gate:
        try:
            from pesq import pesq  # noqa: F401
        except ImportError as exc:
            raise SystemExit("PESQ is required but cannot be imported in this environment") from exc
    if args.wet_mix is not None and not 0.0 <= args.wet_mix <= 1.0:
        parser.error("--wet-mix must be between 0 and 1")
    for name in ("minimum_individual_target_rate", "minimum_all_target_rate"):
        if not 0.0 <= getattr(args, name) <= 1.0:
            parser.error(f"--{name.replace('_', '-')} must be between 0 and 1")
    _, config, _ = load_model(args.checkpoint, "cpu")
    sample_rate = config["audio"]["sample_rate"]
    root = Path(args.data_root)
    rows = [json.loads(line) for line in Path(args.manifest).read_text(encoding="utf-8").splitlines() if line]
    if args.limit is not None:
        rows = rows[: args.limit]
    if not rows:
        raise SystemExit("Evaluation manifest is empty. Generate fixed mixtures first.")
    records = []
    data_issues = []
    summary_values: dict[str, list[float | None]] = defaultdict(list)
    audio_dir = Path(args.save_audio) if args.save_audio else None
    streams = []
    for _ in range(args.cascade_passes):
        stream, _ = build_stream(
            args.checkpoint,
            args.onnx,
            args.device,
            wet_mix=args.wet_mix,
            use_lms=args.lms,
            lms_taps=args.lms_taps,
            lms_step_size=args.lms_step_size,
        )
        stream.conditioner.dc_blocker = args.legacy_dc_blocker
        streams.append(stream)
    stream = streams[-1]
    temporary_root = Path("artifacts") / "eval_tmp"
    temporary_root.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.mkdtemp(prefix="voxshield-eval-", dir=str(temporary_root.resolve()))
    for index, row in enumerate(tqdm(rows, desc="evaluate")):
            keep_audio = audio_dir is not None and (
                args.save_audio_limit is None or index < args.save_audio_limit
            )
            output_path = (audio_dir if keep_audio else Path(temporary)) / f"{row['id']}.wav"
            pass_input = root / row["noisy"]
            runtime_info = None
            for pass_index, pass_stream in enumerate(streams):
                pass_output = (
                    output_path
                    if pass_index == len(streams) - 1
                    else Path(temporary) / f"{row['id']}.pass-{pass_index + 1}.wav"
                )
                runtime_info = enhance_file(
                    pass_input, pass_output, args.checkpoint, args.device,
                    args.onnx, stream=pass_stream, config=config,
                    reference_path=(root / row["reference"] if row.get("reference") else None),
                )
                pass_input = pass_output
            clean = read_audio(root / row["clean"], sample_rate)
            noisy = read_audio(root / row["noisy"], sample_rate)
            enhanced = read_audio(output_path, sample_rate)
            if len(clean) != len(noisy) or len(clean) != len(enhanced):
                raise ValueError(f"Unaligned lengths for {row['id']}")
            if row.get('category') not in {'clean', 'near_clean'} and np.array_equal(clean, noisy):
                data_issues.append({'id': row['id'], 'reason': 'noisy_pair_contains_no_noise'})
            if any(pass_stream.monitor.status.failures for pass_stream in streams):
                raise RuntimeError(f"Model failure/bypass while evaluating {row['id']}: {runtime_info}")
            noisy_perceptual = optional_metrics(clean, noisy, sample_rate)
            enhanced_perceptual = optional_metrics(clean, enhanced, sample_rate)
            dnsmos_scores: dict[str, float | None] = {}
            if args.dnsmos:
                noisy_ovrl = optional_dnsmos(noisy, sample_rate)["dnsmos_ovrl"]
                enhanced_dnsmos = optional_dnsmos(enhanced, sample_rate)
                dnsmos_scores = {
                    "dnsmos_noisy": noisy_ovrl,
                    "dnsmos_sig": enhanced_dnsmos["dnsmos_sig"],
                    "dnsmos_bak": enhanced_dnsmos["dnsmos_bak"],
                    "dnsmos_ovrl": enhanced_dnsmos["dnsmos_ovrl"],
                }
                if enhanced_dnsmos["dnsmos_ovrl"] is not None and noisy_ovrl is not None:
                    dnsmos_scores["dnsmos_ovrl_improvement"] = (
                        enhanced_dnsmos["dnsmos_ovrl"] - noisy_ovrl
                    )
            if args.require_pesq and (
                noisy_perceptual['pesq'] is None or enhanced_perceptual['pesq'] is None
            ):
                raise RuntimeError(f"PESQ could not score {row['id']}; inspect this recording")
            scores = {
                "id": row["id"],
                "category": row.get("category", "unknown"),
                "noise_dataset": row.get("noise_dataset"),
                "noise_source_label": row.get("noise_source_label"),
                "second_noise_source_label": row.get("second_noise_source_label"),
                "input_snr_db": float(row.get("snr_db", snr(clean, noisy))),
                "snr_noisy": snr(clean, noisy),
                "snr_enhanced": snr(clean, enhanced),
                "si_snr_noisy": si_snr(clean, noisy),
                "si_snr_enhanced": si_snr(clean, enhanced),
                "stoi_noisy": noisy_perceptual["stoi"],
                "stoi_enhanced": enhanced_perceptual["stoi"],
                "pesq_noisy": noisy_perceptual["pesq"],
                "pesq_enhanced": enhanced_perceptual["pesq"],
                "pause_noise_attenuation_db": pause_noise_attenuation(
                    clean, noisy, enhanced
                ),
                "speech_deletion_rate": speech_deletion_rate(clean, enhanced),
                "active_level_error_db": active_level_error_db(clean, enhanced),
            }
            scores["snr_improvement"] = scores["snr_enhanced"] - scores["snr_noisy"]
            scores["si_snr_improvement"] = scores["si_snr_enhanced"] - scores["si_snr_noisy"]
            scores["stoi_improvement"] = (
                scores["stoi_enhanced"] - scores["stoi_noisy"]
                if scores["stoi_enhanced"] is not None and scores["stoi_noisy"] is not None
                else None
            )
            scores["pesq_improvement"] = (
                scores["pesq_enhanced"] - scores["pesq_noisy"]
                if scores["pesq_enhanced"] is not None and scores["pesq_noisy"] is not None
                else None
            )
            scores.update(dnsmos_scores)
            records.append(scores)
            for name, value in scores.items():
                if name not in (
                    "id", "category", "noise_dataset", "noise_source_label",
                    "second_noise_source_label",
                ):
                    summary_values[name].append(value)
    noisy_records = [
        record for record in records if record["category"] not in {"clean", "near_clean"}
    ]
    preservation_records = [
        record for record in records if record["category"] in {"clean", "near_clean"}
    ]

    def summarize(selected: list[dict]) -> dict[str, float | None]:
        return {
            name: _mean([record[name] for record in selected])
            for name in summary_values
        }

    noisy_summary = summarize(noisy_records)
    preservation_summary = summarize(preservation_records)
    noisy_distributions = {
        name: _distribution([record[name] for record in noisy_records])
        for name in (
            "snr_enhanced",
            "si_snr_enhanced",
            "stoi_enhanced",
            "pesq_enhanced",
            "speech_deletion_rate",
            "active_level_error_db",
        )
    }
    target_attainment = {
        "output_snr_at_least_15_db": _mean(
            [float(record["snr_enhanced"] >= 15.0) for record in noisy_records]
        ),
        "stoi_at_least_0_85": _mean(
            [
                float(record["stoi_enhanced"] >= 0.85)
                for record in noisy_records
                if record["stoi_enhanced"] is not None
            ]
        ),
        "pesq_at_least_2_5": _mean(
            [
                float(record["pesq_enhanced"] >= 2.5)
                for record in noisy_records
                if record["pesq_enhanced"] is not None
            ]
        ),
        "all_three_targets": _mean(
            [
                float(
                    record["snr_enhanced"] >= 15.0
                    and record["stoi_enhanced"] is not None
                    and record["stoi_enhanced"] >= 0.85
                    and record["pesq_enhanced"] is not None
                    and record["pesq_enhanced"] >= 2.5
                )
                for record in noisy_records
            ]
        ),
    }
    required = {
        "snr_improvement": 1.0,
        "si_snr_improvement": 1.0,
        "stoi_improvement": -0.01,
        "pause_noise_attenuation_db": 3.0,
    }
    checks = {
        name: noisy_summary.get(name) is not None
        and float(noisy_summary[name]) >= threshold
        for name, threshold in required.items()
    }
    checks["speech_not_deleted"] = bool(
        noisy_summary.get("speech_deletion_rate") is not None
        and float(noisy_summary["speech_deletion_rate"]) <= 0.02
    )
    checks["valid_dataset_pairs"] = not data_issues
    expected_noisy_categories = {
        item.strip() for item in args.expected_noisy_categories.split(",") if item.strip()
    }
    if not expected_noisy_categories:
        raise SystemExit("--expected-noisy-categories must contain at least one category")
    noisy_category_checks = {}
    for category in sorted(expected_noisy_categories):
        category_records = [record for record in noisy_records if record["category"] == category]
        category_snr = _mean([record["snr_improvement"] for record in category_records])
        category_si_snr = _mean(
            [record["si_snr_improvement"] for record in category_records]
        )
        noisy_category_checks[category] = bool(
            category_snr is not None
            and category_si_snr is not None
            and category_snr >= -1.0
            and category_si_snr >= -1.0
        )
    preservation_category_checks = {}
    for category in ("clean", "near_clean"):
        category_records = [
            record for record in preservation_records if record["category"] == category
        ]
        enhanced_snr = _mean([record["snr_enhanced"] for record in category_records])
        stoi_delta = _mean([record["stoi_improvement"] for record in category_records])
        preservation_category_checks[category] = bool(
            enhanced_snr is not None
            and enhanced_snr >= 20.0
            and stoi_delta is not None
            and stoi_delta >= -0.01
        )
    checks["no_noisy_category_regression"] = bool(noisy_category_checks) and all(
        noisy_category_checks.values()
    )
    checks["clean_and_near_clean_preserved"] = bool(
        preservation_category_checks
    ) and all(preservation_category_checks.values())
    strict_thresholds = {
        "output_snr_db": 15.0,
        "stoi": 0.85,
        "pesq": 2.5,
        "maximum_speech_deletion_rate": 0.02,
        "maximum_clean_level_error_db": 1.0,
        "minimum_individual_target_rate": args.minimum_individual_target_rate,
        "minimum_all_target_rate": args.minimum_all_target_rate,
    }
    strict_checks = {
        "pesq_complete": all(
            record["pesq_enhanced"] is not None and record["pesq_noisy"] is not None
            for record in records
        ),
        "output_snr": noisy_summary.get("snr_enhanced") is not None
        and float(noisy_summary["snr_enhanced"]) >= strict_thresholds["output_snr_db"],
        "stoi": noisy_summary.get("stoi_enhanced") is not None
        and float(noisy_summary["stoi_enhanced"]) >= strict_thresholds["stoi"],
        "pesq": noisy_summary.get("pesq_enhanced") is not None
        and float(noisy_summary["pesq_enhanced"]) >= strict_thresholds["pesq"],
        "speech_deletion_rate": noisy_summary.get("speech_deletion_rate") is not None
        and float(noisy_summary["speech_deletion_rate"])
        <= strict_thresholds["maximum_speech_deletion_rate"],
        "clean_level_error": preservation_summary.get("active_level_error_db") is not None
        and float(preservation_summary["active_level_error_db"])
        <= strict_thresholds["maximum_clean_level_error_db"],
        "snr_target_reliability": target_attainment["output_snr_at_least_15_db"]
        is not None
        and float(target_attainment["output_snr_at_least_15_db"])
        >= strict_thresholds["minimum_individual_target_rate"],
        "stoi_target_reliability": target_attainment["stoi_at_least_0_85"] is not None
        and float(target_attainment["stoi_at_least_0_85"])
        >= strict_thresholds["minimum_individual_target_rate"],
        "pesq_target_reliability": target_attainment["pesq_at_least_2_5"] is not None
        and float(target_attainment["pesq_at_least_2_5"])
        >= strict_thresholds["minimum_individual_target_rate"],
        "joint_target_reliability": target_attainment["all_three_targets"] is not None
        and float(target_attainment["all_three_targets"])
        >= strict_thresholds["minimum_all_target_rate"],
    }
    strict_passed = all(strict_checks.values())
    quality_gate = {
        "passed": bool(noisy_records)
        and all(checks.values())
        and (not args.strict_sih_gate or strict_passed),
        "thresholds": required,
        "checks": checks,
        "noisy_category_checks": noisy_category_checks,
        "preservation_category_checks": preservation_category_checks,
        "additional_thresholds": {
            "each_noisy_category_snr_and_si_snr_improvement_db": -1.0,
            "each_preservation_category_enhanced_snr_db": 20.0,
            "each_preservation_category_stoi_improvement": -0.01,
        },
        "strict_sih_gate": {
            "requested": args.strict_sih_gate,
            "passed": strict_passed,
            "thresholds": strict_thresholds,
            "checks": strict_checks,
            "warning": (
                "PESQ must be installed and computed; missing metrics fail this gate. "
                "Both mean scores and per-clip target-attainment rates are required."
            ),
        },
        "note": "This automatic gate complements, but cannot replace, listening tests.",
    }
    result = {
        "provenance": {
            "checkpoint": str(Path(args.checkpoint).resolve()),
            "checkpoint_sha256": sha256_file(args.checkpoint),
            "onnx": str(Path(args.onnx).resolve()) if args.onnx else None,
            "onnx_sha256": sha256_file(args.onnx) if args.onnx else None,
            "manifest": str(Path(args.manifest).resolve()),
            "manifest_sha256": sha256_file(args.manifest),
            "architecture": config["model"]["architecture"],
            "device": args.device,
            "limit": args.limit,
            "wet_mix": stream.wet_mix,
            "output_dc_blocker": stream.conditioner.dc_blocker,
            "torch_threads": args.threads,
            "cascade_passes": args.cascade_passes,
            "cascade_algorithmic_latency_ms": (
                args.cascade_passes * 1000.0 * stream.algorithmic_latency_samples / sample_rate
            ),
            "evaluator_revision": "2026-09-worker-runtime-audit",
        },
        "count": len(records),
        "dataset_issues": data_issues,
        "category_counts": {
            category: sum(record["category"] == category for record in records)
            for category in sorted({record["category"] for record in records})
        },
        "summary": {name: _mean(values) for name, values in summary_values.items()},
        "noisy_only_summary": noisy_summary,
        "noisy_only_distributions": noisy_distributions,
        "noisy_only_target_attainment_rate": target_attainment,
        "clean_and_near_clean_summary": preservation_summary,
        "quality_gate": quality_gate,
        "by_category": {
            category: {
                name: _mean([record[name] for record in records if record["category"] == category])
                for name in summary_values
            }
            for category in sorted({record["category"] for record in records})
        },
        "by_category_and_snr_bin": {
            f"{category}@{snr_bin:+d}dB": {
                name: _mean(
                    [
                        record[name]
                        for record in records
                        if record["category"] == category
                        and int(round(record["input_snr_db"] / 5.0) * 5) == snr_bin
                    ]
                )
                for name in summary_values
                if name != "input_snr_db"
            }
            for category, snr_bin in sorted(
                {
                    (record["category"], int(round(record["input_snr_db"] / 5.0) * 5))
                    for record in records
                }
            )
        },
        "by_noise_source_label": {
            label: {
                name: _mean(
                    [
                        record[name]
                        for record in records
                        if record.get("noise_source_label") == label
                        or record.get("second_noise_source_label") == label
                    ]
                )
                for name in summary_values
            }
            for label in sorted(
                {
                    str(label)
                    for record in records
                    for label in (
                        record.get("noise_source_label"),
                        record.get("second_noise_source_label"),
                    )
                    if label is not None
                }
            )
        },
        "records": records,
        "notes": {
            "stoi_unavailable": all(record["stoi_enhanced"] is None for record in records),
            "pesq_unavailable": all(record["pesq_enhanced"] is None for record in records),
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
    print(json.dumps({"noisy_only": noisy_summary, "quality_gate": quality_gate}, indent=2))
    if args.fail_on_regression and not quality_gate["passed"]:
        raise SystemExit("Quality gate failed; do not continue a long training run")


if __name__ == "__main__":
    main()
