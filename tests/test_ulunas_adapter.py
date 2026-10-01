import torch
from voxshield.ulunas_adapter import OfficialULUNAS, _PROJECT_ROOT


def test_ulunas_adapter_loads_pretrained_and_preserves_length():
    model = OfficialULUNAS().eval()
    # Use absolute path resolved from project root so the test works from any cwd
    checkpoint = _PROJECT_ROOT / 'external' / 'ul-unas' / 'checkpoints' / 'model_trained_on_dns3.tar'
    model.load_pretrained(checkpoint)
    waveform = torch.randn(1, 4096) * 0.01
    with torch.inference_mode():
        output, spectrum = model.forward_audio(waveform, 256)
    assert output.shape == waveform.shape
    assert spectrum.shape[-2] == 257
    assert sum(parameter.numel() for parameter in model.parameters()) == 171328


def test_ulunas_forward_ri_single_frame():
    """Verify the per-frame STFT interface used by the WOLA streaming runtime."""
    model = OfficialULUNAS().eval()
    checkpoint = _PROJECT_ROOT / 'external' / 'ul-unas' / 'checkpoints' / 'model_trained_on_dns3.tar'
    model.load_pretrained(checkpoint)
    # Simulate a single STFT frame: [batch=1, real/imag=2, freq=257, time=1]
    spectrum_ri = torch.randn(1, 2, 257, 1) * 0.01
    with torch.inference_mode():
        output, state = model.forward_ri(spectrum_ri, None)
    assert output.shape == spectrum_ri.shape, f"Expected {spectrum_ri.shape}, got {output.shape}"
    assert torch.isfinite(output).all()


def test_ulunas_frame_runner_integration():
    """Verify ULUNASTorchFrameRunner works through the runtime factory."""
    from voxshield.runtime import make_torch_frame_runner
    import numpy as np

    model = OfficialULUNAS().eval()
    checkpoint = _PROJECT_ROOT / 'external' / 'ul-unas' / 'checkpoints' / 'model_trained_on_dns3.tar'
    model.load_pretrained(checkpoint)
    runner = make_torch_frame_runner(model, 'cpu')
    # Single STFT frame: [batch=1, 2, 257, 1]
    spectrum_ri = np.random.randn(1, 2, 257, 1).astype(np.float32) * 0.01
    output = runner.enhance(spectrum_ri)
    assert output.shape == spectrum_ri.shape
    assert np.isfinite(output).all()
    # Reset should work without error
    runner.reset()
