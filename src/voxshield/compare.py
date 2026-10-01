"""Compare evaluation reports without hiding metric trade-offs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

OBJECTIVES = {
    "snr_improvement": 1,
    "si_snr_improvement": 1,
    "stoi_enhanced": 1,
    "pesq_enhanced": 1,
    "speech_deletion_rate": -1,
    "clean_active_level_error_db": -1,
}


def _record_id_hash(report: dict[str, Any]) -> str:
    identifiers = [str(record.get("id")) for record in report.get("records", [])]
    return hashlib.sha256("\n".join(identifiers).encode()).hexdigest()


def _candidate(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    report = json.loads(source.read_text(encoding="utf-8"))
    noisy = report.get("noisy_only_summary", {})
    clean = report.get("clean_and_near_clean_summary", {})
    strict = report.get("quality_gate", {}).get("strict_sih_gate", {})
    values = {
        "snr_improvement": noisy.get("snr_improvement"),
        "si_snr_improvement": noisy.get("si_snr_improvement"),
        "stoi_enhanced": noisy.get("stoi_enhanced"),
        "pesq_enhanced": noisy.get("pesq_enhanced"),
        "speech_deletion_rate": noisy.get("speech_deletion_rate"),
        "clean_active_level_error_db": clean.get("active_level_error_db"),
    }
    return {
        "name": source.stem,
        "report": str(source),
        "count": report.get("count"),
        "record_id_sha256": _record_id_hash(report),
        "manifest_sha256": report.get("provenance", {}).get("manifest_sha256"),
        "quality_gate_passed": bool(report.get("quality_gate", {}).get("passed")),
        "strict_gate_requested": bool(strict.get("requested")),
        "strict_gate_passed": bool(strict.get("passed")),
        "metrics": values,
    }


def _dominates(first: dict[str, Any], second: dict[str, Any], metrics: list[str]) -> bool:
    never_worse = True
    strictly_better = False
    for metric in metrics:
        direction = OBJECTIVES[metric]
        first_value = direction * float(first["metrics"][metric])
        second_value = direction * float(second["metrics"][metric])
        never_worse &= first_value >= second_value
        strictly_better |= first_value > second_value
    return never_worse and strictly_better


def compare_reports(paths: list[str | Path], require_strict_gate: bool = False) -> dict[str, Any]:
    if len(paths) < 2:
        raise ValueError("at least two reports are required")
    candidates = [_candidate(path) for path in paths]
    counts = {candidate["count"] for candidate in candidates}
    record_hashes = {candidate["record_id_sha256"] for candidate in candidates}
    manifest_hashes = {
        candidate["manifest_sha256"]
        for candidate in candidates
        if candidate["manifest_sha256"] is not None
    }
    if len(counts) != 1 or len(record_hashes) != 1:
        raise ValueError("reports do not contain the same evaluated record IDs")
    if len(manifest_hashes) > 1:
        raise ValueError("reports were generated from different manifests")
    comparable_metrics = [
        metric
        for metric in OBJECTIVES
        if all(candidate["metrics"][metric] is not None for candidate in candidates)
    ]
    eligible = [
        candidate
        for candidate in candidates
        if candidate["quality_gate_passed"]
        and (not require_strict_gate or candidate["strict_gate_passed"])
    ]
    pareto = [
        candidate
        for candidate in eligible
        if not any(
            _dominates(other, candidate, comparable_metrics)
            for other in eligible
            if other is not candidate
        )
    ]
    winner = pareto[0]["name"] if len(pareto) == 1 and comparable_metrics else None
    warnings = []
    if len(manifest_hashes) == 0:
        warnings.append("legacy reports lack manifest hashes; record IDs were used for matching")
    missing_metrics = [metric for metric in OBJECTIVES if metric not in comparable_metrics]
    if missing_metrics:
        warnings.append(f"metrics excluded because they are missing: {', '.join(missing_metrics)}")
    if not eligible:
        warnings.append("no candidate passed the required quality gate")
    elif winner is None:
        warnings.append("no unique winner: candidates have non-dominated metric trade-offs")
    return {
        "same_evaluation_records": True,
        "required_strict_gate": require_strict_gate,
        "comparable_metrics": comparable_metrics,
        "candidates": candidates,
        "pareto_front": [candidate["name"] for candidate in pareto],
        "unique_winner": winner,
        "warnings": warnings,
        "note": "A unique numerical winner still requires matched listening and runtime tests.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare matched VoxShield evaluation reports")
    parser.add_argument("reports", nargs="+")
    parser.add_argument("--output", default="artifacts/model-comparison.json")
    parser.add_argument("--require-strict-gate", action="store_true")
    parser.add_argument("--fail-without-winner", action="store_true")
    args = parser.parse_args()
    try:
        result = compare_reports(args.reports, require_strict_gate=args.require_strict_gate)
    except ValueError as exc:
        parser.error(str(exc))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if args.fail_without_winner and result["unique_winner"] is None:
        raise SystemExit("No unique gate-passing winner")


if __name__ == "__main__":
    main()
