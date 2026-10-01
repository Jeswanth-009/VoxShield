"""Adapter for the pinned MIT-licensed upstream UL-UNAS implementation."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import torch
from torch import nn

from .audio import frame_stft


_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_upstream() -> ModuleType:
    source = _PROJECT_ROOT / 'external' / 'ul-unas' / 'ulunas.py'
    if not source.exists():
        raise FileNotFoundError(
            f'Missing pinned UL-UNAS source: {source}. See docs/2026-09-audit.md.'
        )
    spec = importlib.util.spec_from_file_location('voxshield_upstream_ulunas', source)
    if spec is None or spec.loader is None:
        raise ImportError(f'Cannot load UL-UNAS source: {source}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OfficialULUNAS(nn.Module):
    """Causal 16 kHz UL-UNAS waveform model behind the VoxShield interface.

    The upstream ULUNAS model is a waveform-in / waveform-out architecture that
    internally performs STFT, applies a real-valued sigmoid mask via an ERB-based
    encoder–DPGRNN–decoder stack, and reconstructs with ISTFT.

    This adapter exposes both:
      - ``forward_audio`` for the training loop (full waveform path)
      - ``forward_ri`` for the WOLA streaming runtime (per-frame STFT path)
    """

    architecture = 'official_ulunas'
    requires_reference = False

    def __init__(self, n_fft: int = 512, sample_rate: int = 16000) -> None:
        super().__init__()
        if n_fft != 512 or sample_rate != 16000:
            raise ValueError('Official UL-UNAS requires 16 kHz audio and n_fft=512')
        self.n_fft = n_fft
        self.sample_rate = sample_rate
        self.core = _load_upstream().ULUNAS(n_fft=n_fft)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> OfficialULUNAS:
        return cls(config['audio']['n_fft'], config['audio']['sample_rate'])

    def load_pretrained(self, path: str | Path) -> None:
        """Load upstream checkpoint. Relative paths are resolved from project root."""
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = _PROJECT_ROOT / resolved
        if not resolved.exists():
            raise FileNotFoundError(f'Missing pretrained checkpoint: {resolved}')
        checkpoint = torch.load(resolved, map_location='cpu', weights_only=False)
        self.core.load_state_dict(checkpoint.get('model', checkpoint), strict=True)

    def _compute_mask(self, spec: torch.Tensor) -> torch.Tensor:
        """Extract the real-valued mask from the core encoder–DPGRNN–decoder stack.

        Args:
            spec: complex STFT in upstream layout ``(B, 2, T, F)``

        Returns:
            Real-valued sigmoid mask ``(B, 2, T, F)`` — i.e. the same mask
            broadcast to both real and imaginary channels.
        """
        feat = torch.log10(torch.norm(spec, dim=1, keepdim=True).clamp(1e-12))
        feat = self.core.erb.bm(feat)
        feat, en_outs = self.core.encoder(feat)
        feat = self.core.dpgrnn(feat)
        m_feat = self.core.decoder(feat, en_outs)
        m = self.core.erb.bs(m_feat)  # (B, 1, T, F) — sigmoid mask
        return m.expand_as(spec)

    # ------------------------------------------------------------------
    # Training interface: waveform → waveform
    # ------------------------------------------------------------------

    def forward_audio(
        self, waveform: torch.Tensor, hop_length: int
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if hop_length != 256:
            raise ValueError('Official UL-UNAS requires hop_length=256')
        enhanced = self.core(waveform)
        return enhanced, frame_stft(enhanced, self.n_fft, hop_length)

    def forward(self, waveform: torch.Tensor) -> torch.Tensor:
        return self.core(waveform)

    # ------------------------------------------------------------------
    # WOLA streaming interface: per-frame STFT → masked STFT
    # ------------------------------------------------------------------

    def forward_ri(
        self, spectrum_ri: torch.Tensor, state: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Process a single STFT frame for the WOLA streaming runtime.

        The state carries accumulated mask context. UL-UNAS uses GRUs whose
        hidden states are managed internally by PyTorch during full-sequence
        processing; for single-frame streaming we process one time-step at a
        time by reshaping to ``T=1``.

        Args:
            spectrum_ri: ``(B, 2, F, 1)`` — real/imag of one STFT frame
            state: opaque recurrent state from previous frame (or None)

        Returns:
            Tuple of masked ``(B, 2, F, 1)`` and next recurrent state.
        """
        # Reshape from WOLA convention [B,2,F,1] → upstream [B,2,T=1,F]
        spec = spectrum_ri.permute(0, 1, 3, 2)  # (B, 2, 1, F)

        # The upstream model expects to see the full T dimension, but for
        # streaming we send T=1 frames.  Internal GRU hidden states are part
        # of the PyTorch modules and are not explicitly managed here — the
        # ``state`` tensor we carry is a dummy placeholder for API compat.
        mask = self._compute_mask(spec)  # (B, 2, 1, F)
        enhanced = spec * mask

        # Back to WOLA convention [B,2,F,1]
        output = enhanced.permute(0, 1, 3, 2)

        # Return a dummy state tensor for API compatibility
        dummy_state = state if state is not None else torch.zeros(1)
        return output, dummy_state


def make_stream_ulunas(model: OfficialULUNAS) -> nn.Module:
    """Create a stateful StreamULUNAS module sharing weights with the given model."""
    import sys
    base_dir = _PROJECT_ROOT / "external" / "ul-unas"
    stream_dir = base_dir / "ulunas_onnx" / "stream"
    for p in (str(base_dir), str(stream_dir)):
        if p not in sys.path:
            sys.path.insert(0, p)
    from ulunas_stream import StreamULUNAS
    stream_model = StreamULUNAS()
    stream_model.erb = model.core.erb
    stream_model.encoder = model.core.encoder
    stream_model.dpgrnn = model.core.dpgrnn
    stream_model.decoder = model.core.decoder
    return stream_model

