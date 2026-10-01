from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.io import savemat

from voxshield.convert_uav import _ranked_splits, convert_recording
from voxshield.data.ingest import detect_adapter


def test_convert_uav_selects_documented_channel_and_resamples(tmp_path: Path) -> None:
    sample_rate = 20000
    samples = 2000
    time = np.arange(samples) / sample_rate
    pressure = np.stack(
        [
            np.sin(2 * np.pi * 440 * time),
            np.sin(2 * np.pi * 880 * time),
            np.sin(2 * np.pi * 1200 * time),
            np.zeros(samples),
        ],
        axis=1,
    )
    source = tmp_path / "cub_flyover_001.mat"
    savemat(
        source,
        {"acoustics": {"incident_pascals": pressure, "utc_time": time + 1000.0}},
    )
    output = tmp_path / "derived" / "train" / "uav_cub_flyover_001.wav"
    result = convert_recording(source, output, 16000)
    audio, actual_rate = sf.read(output, dtype="float32")
    assert actual_rate == 16000
    assert 1595 <= len(audio) <= 1605
    assert result["selected_microphone_one_based"] == 1
    (tmp_path / "derived" / "uav-conversion.json").write_text("{}")
    assert detect_adapter(tmp_path / "derived") == "uav"


def test_uav_ranked_splits_are_complete_and_disjoint(tmp_path: Path) -> None:
    files = [tmp_path / f"flight_{index:03d}.mat" for index in range(20)]
    splits = _ranked_splits(files, 1337)
    assert set(splits) == set(files)
    assert list(splits.values()).count("train") == 16
    assert list(splits.values()).count("val") == 2
    assert list(splits.values()).count("test") == 2
