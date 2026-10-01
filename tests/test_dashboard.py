from voxshield.dashboard import CONTROL_DEFAULTS, _read_json, _validated_control
from voxshield.dashboard_ui import HTML


def test_dashboard_control_validation_clamps_untrusted_values() -> None:
    result = _validated_control(
        {
            "wet_mix": 4.0,
            "output_gain_db": -90,
            "operator_bypass": True,
            "mute_output": True,
            "preset": "not-a-preset",
        }
    )
    assert result["wet_mix"] == 1.0
    assert result["output_gain_db"] == -18.0
    assert result["operator_bypass"] is True
    assert result["mute_output"] is True
    assert result["preset"] == "custom"
    assert result["updated_unix"] > 0


def test_dashboard_defaults_and_evidence_features_are_present() -> None:
    assert CONTROL_DEFAULTS["preset"] == "balanced"
    assert "VoxShield Console" in HTML
    assert "Controls" in HTML
    assert "Markers" in HTML
    assert "Diagnostics" in HTML
    assert "Channel check" in HTML
    assert "/api/control" in HTML
    assert "/api/marker" in HTML
    assert "SNR, STOI and PESQ" in HTML


def test_dashboard_accepts_powershell_utf8_bom(tmp_path) -> None:
    path = tmp_path / "control.json"
    path.write_text('{"wet_mix":0.61}', encoding="utf-8-sig")
    assert _read_json(path, {})["wet_mix"] == 0.61
