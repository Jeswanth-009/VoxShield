import json
from unittest.mock import patch

import numpy as np

from voxshield.telemetry import build_live_telemetry, write_atomic_json


def test_live_telemetry_is_finite_and_atomic(tmp_path) -> None:
    time = np.arange(512, dtype=np.float32) / 16000
    primary = 0.1 * np.sin(2 * np.pi * 440 * time)
    reference = 0.05 * np.sin(2 * np.pi * 900 * time)
    result = build_live_telemetry(
        primary,
        reference,
        primary,
        sample_rate=16000,
        n_fft=512,
        runtime_status={"mode": "normal"},
        engine_stats={"output_underflows": 0},
    )
    assert len(result["frequency_hz"]) == 257
    assert max(result["spectrum_dbfs"]["primary"]) <= 0
    assert len(result["waveform"]["primary"]) == 192
    assert result["channel_relationship"]["status"] == "distinct"
    assert result["signal_analysis"]["speech_activity"] is True
    assert set(result["signal_analysis"]["band_energy_percent"]) == {
        "sub_bass",
        "speech_low",
        "speech_core",
        "speech_high",
        "presence",
        "air",
    }
    path = tmp_path / "telemetry.json"
    write_atomic_json(path, result)
    assert json.loads(path.read_text())["runtime"]["mode"] == "normal"


def test_telemetry_detects_duplicated_channels() -> None:
    rng = np.random.default_rng(91)
    duplicated = rng.normal(0.0, 0.05, 512).astype(np.float32)
    result = build_live_telemetry(
        duplicated,
        duplicated.copy(),
        duplicated,
        sample_rate=16000,
        n_fft=512,
        runtime_status={"mode": "normal"},
        engine_stats={},
        wet_mix=0.9,
    )
    assert result["channel_relationship"]["status"] == "duplicated"
    assert result["channel_relationship"]["zero_lag_correlation"] > 0.999
    assert result["wet_mix"] == 0.9


def test_mono_telemetry_marks_reference_unavailable() -> None:
    primary = np.ones(256, dtype=np.float32) * 0.01
    result = build_live_telemetry(
        primary,
        None,
        primary,
        sample_rate=16000,
        n_fft=512,
        runtime_status={"mode": "normal"},
        engine_stats={},
    )
    assert result["channel_relationship"]["status"] == "unavailable"


def test_atomic_telemetry_retries_transient_windows_lock(tmp_path) -> None:
    path = tmp_path / "telemetry.json"
    real_replace = __import__("os").replace
    attempts = 0

    def flaky_replace(source, target):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise PermissionError("simulated destination lock")
        return real_replace(source, target)

    with patch("voxshield.telemetry.os.replace", side_effect=flaky_replace):
        write_atomic_json(path, {"status": "normal"})
    assert attempts == 3
    assert json.loads(path.read_text()) == {"status": "normal"}


def test_live_telemetry_reports_runtime_and_model_context() -> None:
    audio = np.ones(512, dtype=np.float32) * 0.01
    result = build_live_telemetry(
        audio,
        audio * 0.3,
        audio * 0.5,
        sample_rate=16000,
        n_fft=512,
        hop_length=256,
        playout_latency_ms=32.0,
        session_elapsed_seconds=12.5,
        operator_control={"preset": "balanced", "effective_wet_mix": 0.82},
        model_info={"architecture": "deep_filter_dual", "backend": "onnxruntime"},
        runtime_status={"mode": "normal", "last_inference_ms": 1.6},
        engine_stats={"submitted_blocks": 10},
    )
    assert result["runtime"]["frame_rtf"] == 0.1
    assert result["playout_latency_ms"] == 32.0
    assert result["session_elapsed_seconds"] == 12.5
    assert result["operator_control"]["effective_wet_mix"] == 0.82
    assert result["model"]["architecture"] == "deep_filter_dual"
