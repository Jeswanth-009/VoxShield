import numpy as np
import torch

from voxshield.metrics import pause_noise_attenuation
from voxshield.official_gtcrn import OfficialGTCRN
from voxshield.official_stream import StreamGTCRN, convert_to_stream


def test_official_stream_matches_full_sequence() -> None:
    torch.manual_seed(9)
    offline = OfficialGTCRN().eval()
    stream = StreamGTCRN().eval()
    convert_to_stream(stream, offline)
    value = torch.randn(1, 257, 5, 2) * 0.05
    with torch.inference_mode():
        expected = offline(value)
        conv, tra, inter = stream.initial_states(1, torch.device("cpu"))
        pieces = []
        for frame in value.split(1, dim=2):
            output, conv, tra, inter = stream(frame, conv, tra, inter)
            pieces.append(output)
    assert torch.allclose(expected, torch.cat(pieces, dim=2), atol=1e-3, rtol=1e-3)


def test_pause_noise_attenuation_detects_reduction() -> None:
    clean = np.zeros(3200, dtype=np.float32)
    clean[960:2240] = 0.2
    rng = np.random.default_rng(4)
    noise = rng.normal(0.0, 0.05, len(clean)).astype(np.float32)
    attenuation = pause_noise_attenuation(clean, clean + noise, clean + noise * 0.1)
    assert attenuation is not None
    assert attenuation > 19.0
