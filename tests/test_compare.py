import json

import pytest

from voxshield.compare import compare_reports


def _report(scale: float, identifiers: list[str]) -> dict:
    return {
        "count": len(identifiers),
        "noisy_only_summary": {
            "snr_improvement": 3.0 * scale,
            "si_snr_improvement": 2.0 * scale,
            "stoi_enhanced": 0.8 + 0.05 * scale,
            "pesq_enhanced": 2.0 + 0.5 * scale,
            "speech_deletion_rate": 0.02 / scale,
        },
        "clean_and_near_clean_summary": {"active_level_error_db": 0.5 / scale},
        "quality_gate": {
            "passed": True,
            "strict_sih_gate": {"requested": True, "passed": True},
        },
        "records": [{"id": identifier} for identifier in identifiers],
    }


def test_compare_reports_selects_only_dominating_candidate(tmp_path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(json.dumps(_report(2.0, ["a", "b"])), encoding="utf-8")
    second.write_text(json.dumps(_report(1.0, ["a", "b"])), encoding="utf-8")
    result = compare_reports([first, second], require_strict_gate=True)
    assert result["unique_winner"] == "first"


def test_compare_reports_rejects_different_examples(tmp_path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(json.dumps(_report(1.0, ["a"])), encoding="utf-8")
    second.write_text(json.dumps(_report(1.0, ["b"])), encoding="utf-8")
    with pytest.raises(ValueError, match="same evaluated record IDs"):
        compare_reports([first, second])
