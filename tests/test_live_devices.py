from unittest.mock import Mock

import pytest

from voxshield.live import _compatible_duplex_pairs, _validate_audio_pair


def _fake_sounddevice():
    devices = [
        {"index": 0, "name": "Two-channel mic", "hostapi": 1,
         "max_input_channels": 2, "max_output_channels": 0},
        {"index": 1, "name": "Headphones", "hostapi": 1,
         "max_input_channels": 0, "max_output_channels": 2},
        {"index": 2, "name": "Wrong-backend output", "hostapi": 2,
         "max_input_channels": 0, "max_output_channels": 2},
    ]
    sd = Mock()

    def query(device=None, kind=None):
        if device is None and kind is None:
            return devices
        info = devices[int(device)]
        if kind == "input" and info["max_input_channels"] == 0:
            raise ValueError("not an input device")
        if kind == "output" and info["max_output_channels"] == 0:
            raise ValueError("not an output device")
        return info

    sd.query_devices.side_effect = query
    return sd


def test_audio_pair_preflight_accepts_same_backend_pair() -> None:
    sd = _fake_sounddevice()
    _validate_audio_pair(sd, 0, 1, sample_rate=16000, input_channels=2)
    sd.check_input_settings.assert_called_once()
    sd.check_output_settings.assert_called_once()


def test_audio_pair_preflight_explains_reversed_devices() -> None:
    sd = _fake_sounddevice()
    with pytest.raises(SystemExit, match="Format-compatible same-backend candidates detected"):
        _validate_audio_pair(sd, 1, 0, sample_rate=16000, input_channels=2)
    assert _compatible_duplex_pairs(sd, 16000, 2) == [
        "input 0 (Two-channel mic) -> output 1 (Headphones)"
    ]
