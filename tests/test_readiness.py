import json

from voxshield.readiness import build_readiness


def test_readiness_refuses_missing_evidence(tmp_path) -> None:
    result = build_readiness(tmp_path)
    assert result["truthful_status"] == "research_and_validation"
    assert not result["communication_enhancement"]["ready"]
    assert not result["physical_anc"]["ready"]


def test_readiness_accepts_complete_communication_evidence(tmp_path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    for stage in (1, 2, 3):
        checkpoint = tmp_path / f"checkpoints_v4_stage{stage}" / "best.pt"
        checkpoint.parent.mkdir()
        checkpoint.write_bytes(b"checkpoint")
    (artifacts / "data-audit-v4.json").write_text(json.dumps({"ready": True}))
    (artifacts / "voxshield-v4-final.onnx").write_bytes(b"onnx")
    (artifacts / "voxshield-v4-final.validation.json").write_text(
        json.dumps({"passed": True})
    )
    (artifacts / "v4-final-test.json").write_text(
        json.dumps(
            {
                "quality_gate": {
                    "passed": True,
                    "strict_sih_gate": {"requested": True, "passed": True},
                }
            }
        )
    )
    (artifacts / "pi5-v4-benchmark.json").write_text(
        json.dumps(
            {
                "p99_latency_ms": 2.0,
                "frame_duration_ms": 8.0,
                "runtime_deadline_overruns": 0,
                "dropped_or_underflowed_audio_callbacks": 0,
            }
        )
    )
    (artifacts / "physical-loopback.json").write_text(
        json.dumps({"measured_end_to_end_latency_ms": 42.0})
    )
    (artifacts / "pi5-soak.json").write_text(
        json.dumps(
            {
                "duration_seconds": 7200,
                "xruns": 0,
                "invalid_model_bypasses": 0,
                "output_underflows": 0,
                "dropped_input_blocks": 0,
                "worker_failures": 0,
                "thermal_throttling": False,
            }
        )
    )
    (artifacts / "listening-test.json").write_text(json.dumps({"passed": True}))
    result = build_readiness(tmp_path)
    assert result["communication_enhancement"]["ready"]
    assert not result["physical_anc"]["ready"]
    assert result["truthful_status"] == "communication_ready"
