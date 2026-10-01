"""Fusion dual-channel UL-UNAS model tests."""

import numpy as np
import pytest
import torch

from voxshield.audio import frame_stft
from voxshield.export_onnx import fusion_export_spec
from voxshield.fusion_model import FusionDualChannelULUNAS
from voxshield.model import build_model

PRETRAINED = "external/ul-unas/checkpoints/model_trained_on_dns3.tar"


@pytest.fixture(scope="module")
def model() -> FusionDualChannelULUNAS:
    torch.manual_seed(0)
    instance = FusionDualChannelULUNAS()
    instance.load_pretrained(PRETRAINED)
    instance.eval()
    return instance


def _spectra(samples: int = 16000) -> tuple[torch.Tensor, torch.Tensor]:
    rng = np.random.default_rng(5)
    primary = (rng.normal(0.0, 0.05, samples) + 0.02 * np.sin(2 * np.pi * 220 * np.arange(samples) / 16000)).astype(np.float32)
    reference = rng.normal(0.0, 0.05, samples).astype(np.float32)
    spec_p = frame_stft(torch.from_numpy(primary), 512, 256)
    spec_r = frame_stft(torch.from_numpy(reference), 512, 256)
    return spec_p, spec_r


def test_parameter_count_is_ul_unas_scale(model: FusionDualChannelULUNAS) -> None:
    total = sum(parameter.numel() for parameter in model.parameters())
    assert 150_000 < total < 250_000
    assert model.requires_reference is True
    assert model.STATE_SIZE == model.CONV_CACHE_SIZE + model.TFA_CACHE_SIZE + model.INTER_CACHE_SIZE


def test_init_matches_pretrained_mono_mask(model: FusionDualChannelULUNAS) -> None:
    from voxshield.ulunas_adapter import OfficialULUNAS

    mono = OfficialULUNAS()
    mono.load_pretrained(PRETRAINED)
    mono.eval()
    spec, _ = _spectra(8000)
    p_ri = torch.stack((spec.real, spec.imag), dim=1).permute(0, 1, 3, 2)
    with torch.inference_mode():
        fusion_mask = model._mask(p_ri, p_ri)
        mono_mask = mono._compute_mask(p_ri)
    assert (fusion_mask[:, 0] - mono_mask[0, 0]).abs().max() < 1e-5
    assert fusion_mask[:, 1].abs().max() < 1e-5


def test_forward_audio_shapes(model: FusionDualChannelULUNAS) -> None:
    primary = (torch.rand(1, 16000) - 0.5) * 0.1
    reference = (torch.rand(1, 16000) - 0.5) * 0.1
    with torch.inference_mode():
        estimate, spectrum = model.forward_audio(primary, reference, 256)
    assert estimate.shape == primary.shape
    assert spectrum.shape[0] == 1 and spectrum.shape[1] == 257 and spectrum.shape[2] >= 63
    assert torch.isfinite(estimate).all()


def test_streaming_matches_offline(model: FusionDualChannelULUNAS) -> None:
    spec_p, spec_r = _spectra(25600)
    with torch.inference_mode():
        offline, _ = model.forward_spectrum(spec_p, spec_r)
        state = model.initial_state(1)
        p_ri = torch.stack((spec_p.real, spec_p.imag), dim=1)
        r_ri = torch.stack((spec_r.real, spec_r.imag), dim=1)
        frames = []
        for index in range(p_ri.shape[3]):
            frame, state = model.forward_ri(
                p_ri[..., index : index + 1].contiguous(),
                r_ri[..., index : index + 1].contiguous(),
                state,
            )
            frames.append(frame)
        streamed = torch.cat(frames, dim=3)[0]
    streamed_spectrum = torch.complex(streamed[0], streamed[1])
    assert (streamed_spectrum - offline[0]).abs().max() < 2e-3


def test_state_reset_is_deterministic(model: FusionDualChannelULUNAS) -> None:
    spec_p, spec_r = _spectra(5120)
    p_ri = torch.stack((spec_p.real, spec_p.imag), dim=1)
    r_ri = torch.stack((spec_r.real, spec_r.imag), dim=1)
    outputs = []
    for _ in range(2):
        model.reset() if hasattr(model, "reset") else None
        with torch.inference_mode():
            state = model.initial_state(1)
            frames = []
            for index in range(p_ri.shape[3]):
                frame, state = model.forward_ri(
                    p_ri[..., index : index + 1].contiguous(),
                    r_ri[..., index : index + 1].contiguous(),
                    state,
                )
                frames.append(frame)
        outputs.append(torch.cat(frames, dim=3))
    assert torch.equal(outputs[0], outputs[1])


def test_build_model_from_config() -> None:
    config = {
        "audio": {"n_fft": 512, "sample_rate": 16000},
        "model": {
            "architecture": "fusion_dual_ulunas",
            "initialize_from": None,
            "pretrained": None,
        },
    }
    instance = build_model(config)
    assert isinstance(instance, FusionDualChannelULUNAS)
    assert instance.requires_reference is True


def test_signed_imaginary_mask_is_zero_centred_and_bidirectional() -> None:
    instance = FusionDualChannelULUNAS(
        mask_mode="signed_imaginary", imaginary_scale=0.5
    )
    logits = torch.zeros(1, 2, 1, 129)
    mask = instance._activate_mask(logits)
    assert torch.allclose(mask[:, 0], torch.full_like(mask[:, 0], 0.5))
    assert torch.allclose(mask[:, 1], torch.zeros_like(mask[:, 1]))

    logits[:, 1] = 1.0
    positive = instance._activate_mask(logits)[:, 1]
    logits[:, 1] = -1.0
    negative = instance._activate_mask(logits)[:, 1]
    assert torch.all(positive > 0.0)
    assert torch.all(negative < 0.0)
    assert torch.allclose(positive, -negative)


def test_signed_imaginary_reset_removes_legacy_saturation() -> None:
    instance = FusionDualChannelULUNAS(mask_mode="signed_imaginary")
    with torch.no_grad():
        instance.head.weight[1].fill_(3.0)
        instance.head.bias[1].fill_(-20.0)
    instance.reset_imaginary_branch()
    assert torch.count_nonzero(instance.head.weight[1]) == 0
    assert instance.head.bias[1].item() == 0.0


def test_forward_ri_rejects_mismatched_shapes(model: FusionDualChannelULUNAS) -> None:
    primary = torch.zeros(1, 2, 257, 1)
    with pytest.raises(ValueError):
        model.forward_ri(primary, torch.zeros(1, 2, 257, 2))


def test_onnx_export_spec_matches_fusion_signature(
    model: FusionDualChannelULUNAS,
) -> None:
    inputs, input_names, output_names, dynamic_axes = fusion_export_spec(model, 257)
    primary, reference, state = inputs
    assert primary.shape == reference.shape == (1, 2, 257, 1)
    assert state.shape == (1, model.STATE_SIZE)
    assert input_names == ["primary_ri", "reference_ri", "state_in"]
    assert output_names == ["enhanced_ri", "state_out"]
    assert dynamic_axes["state_in"] == {0: "batch"}
    enhanced, next_state = model(*inputs)
    assert enhanced.shape == primary.shape
    assert next_state.shape == state.shape
