"""V10 deep-filter dual-channel model tests."""

import numpy as np
import pytest
import torch

from voxshield.audio import frame_stft
from voxshield.df_model import DeepFilterDualChannelNet
from voxshield.export_onnx import fusion_export_spec
from voxshield.model import build_model


@pytest.fixture(scope="module")
def model() -> DeepFilterDualChannelNet:
    torch.manual_seed(0)
    instance = DeepFilterDualChannelNet()
    instance.eval()
    return instance


def _spectra(samples: int = 16000) -> tuple[torch.Tensor, torch.Tensor]:
    rng = np.random.default_rng(5)
    primary = (
        rng.normal(0.0, 0.05, samples)
        + 0.02 * np.sin(2 * np.pi * 220 * np.arange(samples) / 16000)
    ).astype(np.float32)
    reference = rng.normal(0.0, 0.05, samples).astype(np.float32)
    spec_p = frame_stft(torch.from_numpy(primary), 512, 256)
    spec_r = frame_stft(torch.from_numpy(reference), 512, 256)
    return spec_p, spec_r


def test_parameter_count_is_mid_scale(model: DeepFilterDualChannelNet) -> None:
    trainable = sum(
        parameter.numel()
        for parameter in model.parameters()
        if parameter.requires_grad
    )
    # v10 plan: roughly an order of magnitude above the 147k fusion core,
    # but still a candidate for later distillation.
    assert 500_000 < trainable < 1_500_000
    assert model.requires_reference is True
    assert model.STATE_SIZE == model.DF_STATE_SIZE + model.RNN_STATE_SIZE


def test_forward_audio_shapes(model: DeepFilterDualChannelNet) -> None:
    primary = (torch.rand(1, 16000) - 0.5) * 0.1
    reference = (torch.rand(1, 16000) - 0.5) * 0.1
    with torch.inference_mode():
        estimate, spectrum = model.forward_audio(primary, reference, 256)
    assert estimate.shape == primary.shape
    assert spectrum.shape[0] == 1 and spectrum.shape[1] == 257 and spectrum.shape[2] >= 63
    assert torch.isfinite(estimate).all()


def test_streaming_matches_offline(model: DeepFilterDualChannelNet) -> None:
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


def test_deep_filter_tap_ordering_and_zero_history() -> None:
    """Tap k must apply to frame t-k, with zeros before the sequence start."""
    torch.manual_seed(3)
    masked = torch.randn(2, 2, 6, 5)
    coefficients = torch.randn(2, 4, 6, 5) * 0.3  # two complex taps
    output = DeepFilterDualChannelNet._apply_deep_filter(masked, coefficients)
    reference = masked.clone()
    for t in range(6):
        for k in (1, 2):
            c_re, c_im = coefficients[:, 2 * k - 2, t], coefficients[:, 2 * k - 1, t]
            if t - k >= 0:
                w_re, w_im = masked[:, 0, t - k], masked[:, 1, t - k]
            else:
                w_re = w_im = torch.zeros_like(c_re)
            reference[:, 0, t] += c_re * w_re - c_im * w_im
            reference[:, 1, t] += c_re * w_im + c_im * w_re
    assert torch.allclose(output, reference, atol=1e-5)


def test_pointwise_mask_when_no_history_taps() -> None:
    instance = DeepFilterDualChannelNet(channels=32, recurrent_blocks=1, deep_filter_taps=1)
    masked = torch.randn(1, 2, 4, 9)
    coefficients = torch.zeros(1, 0, 4, 9)
    assert torch.equal(
        DeepFilterDualChannelNet._apply_deep_filter(masked, coefficients), masked
    )


def test_head_outputs_are_bounded_and_signed(model: DeepFilterDualChannelNet) -> None:
    torch.manual_seed(0)
    features = torch.randn(2, model.channels, 3, 129)
    mask_erb, df_erb = model._heads(features)
    real, imaginary = mask_erb[:, 0], mask_erb[:, 1]
    assert (real >= model.min_mask_gain - 1e-6).all() and (real <= 1.0 + 1e-6).all()
    # v8 lesson: the imaginary branch must be signed and zero-centred.
    assert (imaginary.abs() <= model.imaginary_scale + 1e-6).all()
    assert (df_erb.abs() <= model.df_scale + 1e-6).all()


def test_fresh_model_starts_as_plain_mask(model: DeepFilterDualChannelNet) -> None:
    """Deep-filter taps start at zero, so fresh output equals the masked input."""
    assert torch.count_nonzero(model.df_head.weight) == 0
    assert torch.count_nonzero(model.df_head.bias) == 0
    spec_p, spec_r = _spectra(5120)
    p_ri = torch.stack((spec_p.real, spec_p.imag), dim=1).permute(0, 1, 3, 2)
    r_ri = torch.stack((spec_r.real, spec_r.imag), dim=1).permute(0, 1, 3, 2)
    with torch.inference_mode():
        features = model.subband(model.erb.compress(model._features(p_ri, r_ri)))
        decoded, _, _ = model._backbone(features)
        mask_erb, df_erb = model._heads(decoded)
        mask = model.erb.expand(mask_erb)
        from voxshield.df_model import _apply_complex_mask

        pointwise = _apply_complex_mask(p_ri, mask)
        full = model._enhance_spectra_ri(p_ri, r_ri)
    assert torch.count_nonzero(df_erb) == 0
    assert torch.allclose(full, pointwise, atol=1e-6)


def test_streaming_history_carries_energy_across_frames() -> None:
    """A silent frame following an active one must still receive deep-filter
    energy from the packed history — proves the state wiring end to end."""
    instance = DeepFilterDualChannelNet(
        channels=32, recurrent_blocks=1, deep_filter_taps=3
    )
    instance.eval()
    with torch.no_grad():
        instance.df_head.weight.fill_(0.05)
        instance.df_head.bias.fill_(0.1)
    frequency = 257
    active = torch.randn(1, 2, frequency, 1) * 0.1
    silence = torch.zeros(1, 2, frequency, 1)
    with torch.inference_mode():
        state = instance.initial_state(1)
        _, state = instance.forward_ri(active, active, state)
        from_silence, _ = instance.forward_ri(silence, silence, state)
    assert from_silence.abs().max() > 0.0


def test_state_reset_is_deterministic(model: DeepFilterDualChannelNet) -> None:
    spec_p, spec_r = _spectra(5120)
    p_ri = torch.stack((spec_p.real, spec_p.imag), dim=1)
    r_ri = torch.stack((spec_r.real, spec_r.imag), dim=1)
    outputs = []
    for _ in range(2):
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


def test_forward_ri_rejects_mismatched_and_multi_frame() -> None:
    instance = DeepFilterDualChannelNet(channels=32, recurrent_blocks=1)
    primary = torch.zeros(1, 2, 257, 1)
    with pytest.raises(ValueError):
        instance.forward_ri(primary, torch.zeros(1, 2, 257, 2))
    with pytest.raises(ValueError):
        instance.forward_ri(torch.zeros(1, 2, 257, 4), torch.zeros(1, 2, 257, 4))


def test_build_model_from_config_drops_legacy_keys() -> None:
    config = {
        "audio": {"n_fft": 512, "sample_rate": 16000},
        "model": {
            "architecture": "deep_filter_dual",
            "initialize_from": None,
            "pretrained": None,
            "reset_imaginary_branch": None,
            # legacy keys inherited from fusion/hybrid chains must be ignored
            "mask_mode": "signed_imaginary",
            "feature_channels": 5,
            "min_mask_gain": 0.05,
        },
    }
    instance = build_model(config)
    assert isinstance(instance, DeepFilterDualChannelNet)
    assert instance.requires_reference is True
    assert instance.min_mask_gain == 0.05


def test_onnx_export_spec_matches_signature() -> None:
    instance = DeepFilterDualChannelNet(
        channels=32, recurrent_blocks=1, deep_filter_taps=3
    )
    inputs, input_names, output_names, dynamic_axes = fusion_export_spec(instance, 257)
    primary, reference, state = inputs
    assert primary.shape == reference.shape == (1, 2, 257, 1)
    assert state.shape == (1, instance.STATE_SIZE)
    assert input_names == ["primary_ri", "reference_ri", "state_in"]
    assert output_names == ["enhanced_ri", "state_out"]
    assert dynamic_axes["state_in"] == {0: "batch"}
    enhanced, next_state = instance(*inputs)
    assert enhanced.shape == primary.shape
    assert next_state.shape == state.shape


def test_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError):
        DeepFilterDualChannelNet(channels=30)  # not divisible by four
    with pytest.raises(ValueError):
        DeepFilterDualChannelNet(n_fft=1024)
    with pytest.raises(ValueError):
        DeepFilterDualChannelNet(deep_filter_taps=0)
    with pytest.raises(ValueError):
        DeepFilterDualChannelNet(min_mask_gain=1.0)
