"""Evidence-based release readiness for communication enhancement and physical ANC."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _gate(passed: bool, evidence: Path | None, detail: str) -> dict[str, Any]:
    return {
        "passed": bool(passed),
        "evidence": str(evidence) if evidence is not None else None,
        "detail": detail,
    }


def build_readiness(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    artifacts = root / "artifacts"
    audit_path = artifacts / "data-audit-v4.json"
    evaluation_path = artifacts / "v4-final-test.json"
    benchmark_path = artifacts / "pi5-v4-benchmark.json"
    soak_path = artifacts / "pi5-soak.json"
    listening_path = artifacts / "listening-test.json"
    loopback_path = artifacts / "physical-loopback.json"
    anc_path = artifacts / "physical-anc-test.json"
    audit = _read_json(audit_path)
    evaluation = _read_json(evaluation_path)
    benchmark = _read_json(benchmark_path)
    soak = _read_json(soak_path)
    listening = _read_json(listening_path)
    loopback = _read_json(loopback_path)
    anc_test = _read_json(anc_path)
    strict = (
        evaluation.get("quality_gate", {}).get("strict_sih_gate", {})
        if evaluation
        else {}
    )
    benchmark_passed = bool(
        benchmark
        and benchmark.get("p99_latency_ms") is not None
        and benchmark.get("frame_duration_ms") is not None
        and float(benchmark["p99_latency_ms"]) < float(benchmark["frame_duration_ms"])
        and int(benchmark.get("runtime_deadline_overruns", -1)) == 0
        and int(benchmark.get("dropped_or_underflowed_audio_callbacks", -1)) == 0
    )
    loopback_passed = bool(
        loopback
        and loopback.get("measured_end_to_end_latency_ms") is not None
        and float(loopback["measured_end_to_end_latency_ms"]) <= 50.0
    )
    communication_gates = {
        "dataset": _gate(
            bool(audit and audit.get("ready")),
            audit_path,
            "Requires valid leak-free splits plus the declared defence labels and RIR coverage.",
        ),
        "stage1_checkpoint": _gate(
            (root / "checkpoints_v4_stage1" / "best.pt").exists(),
            root / "checkpoints_v4_stage1" / "best.pt",
            "Broad pretraining checkpoint.",
        ),
        "stage2_checkpoint": _gate(
            (root / "checkpoints_v4_stage2" / "best.pt").exists(),
            root / "checkpoints_v4_stage2" / "best.pt",
            "Defence-weighted checkpoint.",
        ),
        "stage3_checkpoint": _gate(
            (root / "checkpoints_v4_stage3" / "best.pt").exists(),
            root / "checkpoints_v4_stage3" / "best.pt",
            "Target-hardware checkpoint.",
        ),
        "validated_onnx": _gate(
            bool(
                (artifacts / "voxshield-v4-final.onnx").exists()
                and (artifacts / "voxshield-v4-final.validation.json").exists()
                and (_read_json(artifacts / "voxshield-v4-final.validation.json") or {}).get(
                    "passed"
                )
            ),
            artifacts / "voxshield-v4-final.validation.json",
            "ONNX must match the final checkpoint and pass numerical validation.",
        ),
        "strict_quality": _gate(
            bool(
                evaluation
                and evaluation.get("quality_gate", {}).get("passed")
                and strict.get("requested")
                and strict.get("passed")
            ),
            evaluation_path,
            "Requires held-out SNR, STOI, PESQ, category, and speech-preservation gates.",
        ),
        "pi_frame_deadline": _gate(
            benchmark_passed,
            benchmark_path,
            "Pi p99 inference must remain below one hop with no runtime drops or overruns.",
        ),
        "physical_loopback_latency": _gate(
            loopback_passed,
            loopback_path,
            "Measured microphone-to-output loopback latency must be at most 50 ms.",
        ),
        "pi_two_hour_soak": _gate(
            bool(
                soak
                and float(soak.get("duration_seconds", 0.0)) >= 7200.0
                and int(soak.get("xruns", -1)) == 0
                and int(soak.get("invalid_model_bypasses", -1)) == 0
                and int(soak.get("output_underflows", -1)) == 0
                and int(soak.get("dropped_input_blocks", -1)) == 0
                and int(soak.get("worker_failures", -1)) == 0
                and soak.get("thermal_throttling") is False
            ),
            soak_path,
            "Two hours, zero xruns/underflows/drops/failures, and no thermal throttling.",
        ),
        "matched_listening_test": _gate(
            bool(listening and listening.get("passed")),
            listening_path,
            "Blind or randomized matched listening must confirm intelligibility and preservation.",
        ),
    }
    communication_ready = all(value["passed"] for value in communication_gates.values())
    physical_gates = {
        "communication_release": _gate(
            communication_ready,
            None,
            "Physical ANC builds on a completed communication enhancement release.",
        ),
        "secondary_path_calibrated": _gate(
            bool(anc_test and anc_test.get("secondary_path_calibrated")),
            anc_path,
            "Requires measured headset/loudspeaker-to-error-microphone path.",
        ),
        "physical_anc_test": _gate(
            bool(
                anc_test
                and anc_test.get("passed")
                and anc_test.get("stable")
                and float(anc_test.get("maximum_safe_output", 0.0)) > 0.0
            ),
            anc_path,
            "Requires stable measured attenuation within declared safe output limits.",
        ),
        "hardware_bypass": _gate(
            bool(anc_test and anc_test.get("hardware_bypass_verified")),
            anc_path,
            "Bypass must work after process crash, Pi failure, USB loss, and power loss.",
        ),
    }
    physical_ready = all(value["passed"] for value in physical_gates.values())
    return {
        "project_root": str(root),
        "communication_enhancement": {
            "ready": communication_ready,
            "gates": communication_gates,
        },
        "physical_anc": {"ready": physical_ready, "gates": physical_gates},
        "truthful_status": (
            "physical_anc_ready"
            if physical_ready
            else "communication_ready"
            if communication_ready
            else "research_and_validation"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Report evidence-based VoxShield readiness")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output", default="artifacts/readiness.json")
    parser.add_argument(
        "--require",
        choices=("communication", "physical-anc"),
        default=None,
        help="Return a failure code unless this release level is ready",
    )
    args = parser.parse_args()
    result = build_readiness(args.project_root)
    output = Path(args.project_root) / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if args.require == "communication" and not result["communication_enhancement"]["ready"]:
        raise SystemExit("Communication enhancement release gates are incomplete")
    if args.require == "physical-anc" and not result["physical_anc"]["ready"]:
        raise SystemExit("Physical ANC release gates are incomplete")


if __name__ == "__main__":
    main()
