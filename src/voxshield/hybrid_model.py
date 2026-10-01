"""Causal dual-channel complex-mask model for VoxShield v4.

The model consumes a close-talk primary microphone and a synchronized external
reference microphone.  It intentionally keeps the compact ERB/sub-band and
dual-path recurrent building blocks used by the existing embedded model while
adding spatial/cross-channel evidence.  It is not a physical anti-noise
controller; the FxNLMS earcup loop is a separate subsystem.
"""

from __future__ import annotations

from typing import Any

import torch
from torch import nn

from .audio import frame_istft, frame_stft
from .model import DualPathGroupedRNN, ERBFilterBank, SubbandFeatures


class HybridDualChannelGTCRN(nn.Module):
    """Ultra-light causal dual-channel enhancer with complex reconstruction."""

    requires_reference = True

    def __init__(
        self,
        n_fft: int = 512,
        sample_rate: int = 16000,
        channels: int = 16,
        recurrent_blocks: int = 2,
        min_mask_gain: float = 0.08,
        max_mask_gain: float = 1.20,
        preserve_bias: float = 2.0,
    ) -> None:
        super().__init__()
        if n_fft != 512 or sample_rate != 16000:
            raise ValueError("hybrid_dual_gtcrn currently requires 16 kHz audio and n_fft=512")
        if channels % 4:
            raise ValueError("channels must be divisible by four")
        self.n_fft = int(n_fft)
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self.recurrent_blocks = int(recurrent_blocks)
        self.min_mask_gain = float(min_mask_gain)
        self.max_mask_gain = float(max_mask_gain)
        self.preserve_bias = float(preserve_bias)
        self.erb = ERBFilterBank(n_fft, sample_rate, 65, 64)
        self.subband = SubbandFeatures(3)

        # Nine base features (27 after 3-bin sub-band unfolding): primary and
        # reference magnitude/real/imag, phase difference, and log-level ratio.
        self.encoder = nn.Sequential(
            nn.Conv2d(27, channels, (1, 5), stride=(1, 2), padding=(0, 2)),
            nn.BatchNorm2d(channels),
            nn.PReLU(channels),
            nn.Conv2d(
                channels,
                channels,
                (1, 5),
                stride=(1, 2),
                padding=(0, 2),
                groups=2,
            ),
            nn.BatchNorm2d(channels),
            nn.PReLU(channels),
        )
        self.width = 33
        self.dual_path = nn.ModuleList(
            [DualPathGroupedRNN(channels, self.width) for _ in range(recurrent_blocks)]
        )
        self.decoder_first = nn.Sequential(
            nn.ConvTranspose2d(
                channels,
                channels,
                (1, 5),
                stride=(1, 2),
                padding=(0, 2),
                groups=2,
            ),
            nn.BatchNorm2d(channels),
            nn.PReLU(channels),
        )
        # real mask residual, imaginary mask, conservative enhancement gate
        self.decoder_last = nn.ConvTranspose2d(
            channels, 3, (1, 5), stride=(1, 2), padding=(0, 2)
        )
        nn.init.zeros_(self.decoder_last.weight)
        nn.init.zeros_(self.decoder_last.bias)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> HybridDualChannelGTCRN:
        options = dict(config["model"])
        options.pop("architecture", None)
        options.pop("pretrained", None)
        options.pop("initialize_from", None)
        return cls(
            n_fft=config["audio"]["n_fft"],
            sample_rate=config["audio"]["sample_rate"],
            **options,
        )

    def initial_state(
        self, batch_size: int, device: torch.device | None = None
    ) -> torch.Tensor:
        return torch.zeros(
            self.recurrent_blocks,
            batch_size,
            self.width,
            self.channels,
            device=device,
        )

    @staticmethod
    def _features(primary_ri: torch.Tensor, reference_ri: torch.Tensor) -> torch.Tensor:
        primary_real, primary_imag = primary_ri[:, 0], primary_ri[:, 1]
        reference_real, reference_imag = reference_ri[:, 0], reference_ri[:, 1]
        primary_mag = torch.sqrt(primary_real.square() + primary_imag.square() + 1e-8)
        reference_mag = torch.sqrt(reference_real.square() + reference_imag.square() + 1e-8)
        denominator = (primary_mag * reference_mag).clamp_min(1e-6)
        phase_cos = (
            primary_real * reference_real + primary_imag * reference_imag
        ) / denominator
        phase_sin = (
            primary_imag * reference_real - primary_real * reference_imag
        ) / denominator
        log_ratio = (torch.log1p(primary_mag) - torch.log1p(reference_mag)).clamp(-5.0, 5.0)
        return torch.stack(
            (
                primary_mag,
                primary_real,
                primary_imag,
                reference_mag,
                reference_real,
                reference_imag,
                phase_cos,
                phase_sin,
                log_ratio,
            ),
            dim=1,
        ).permute(0, 1, 3, 2)

    def forward_ri(
        self,
        primary_ri: torch.Tensor,
        reference_ri: torch.Tensor,
        state: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        expected = "[batch, 2, frequency, frames]"
        if primary_ri.ndim != 4 or primary_ri.shape[1] != 2:
            raise ValueError(f"primary_ri must have shape {expected}")
        if reference_ri.shape != primary_ri.shape:
            raise ValueError("reference_ri must have the same shape as primary_ri")

        features = self.subband(self.erb.compress(self._features(primary_ri, reference_ri)))
        features = self.encoder(features)
        states = []
        for index, block in enumerate(self.dual_path):
            block_state = None if state is None else state[index]
            features, block_state = block(features, block_state)
            states.append(block_state)

        controls = self.decoder_last(self.decoder_first(features))
        controls = self.erb.expand(controls).permute(0, 1, 3, 2)
        mask_real = 1.0 + torch.tanh(controls[:, 0])
        mask_imag = torch.tanh(controls[:, 1])
        magnitude = torch.sqrt(mask_real.square() + mask_imag.square() + 1e-8)
        bounded = magnitude.clamp(self.min_mask_gain, self.max_mask_gain)
        scale = bounded / magnitude.clamp_min(1e-8)
        mask_real, mask_imag = mask_real * scale, mask_imag * scale

        primary_real, primary_imag = primary_ri[:, 0], primary_ri[:, 1]
        enhanced_real = primary_real * mask_real - primary_imag * mask_imag
        enhanced_imag = primary_real * mask_imag + primary_imag * mask_real
        enhanced = torch.stack((enhanced_real, enhanced_imag), dim=1)

        # Learned conservative gate.  A fresh model is exactly identity because
        # the mask decoder starts at (1 + 0j), independent of the gate value.
        gate = torch.sigmoid(controls[:, 2:3] + self.preserve_bias)
        output = gate * enhanced + (1.0 - gate) * primary_ri
        return output, torch.stack(states)

    def forward_spectrum(
        self,
        primary: torch.Tensor,
        reference: torch.Tensor,
        state: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        primary_ri = torch.stack((primary.real, primary.imag), dim=1)
        reference_ri = torch.stack((reference.real, reference.imag), dim=1)
        output_ri, next_state = self.forward_ri(primary_ri, reference_ri, state)
        return torch.complex(output_ri[:, 0], output_ri[:, 1]), next_state

    def forward_audio(
        self,
        primary: torch.Tensor,
        reference: torch.Tensor,
        hop_length: int,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        primary_spectrum = frame_stft(primary, self.n_fft, hop_length)
        reference_spectrum = frame_stft(reference, self.n_fft, hop_length)
        enhanced, _ = self.forward_spectrum(primary_spectrum, reference_spectrum)
        return frame_istft(enhanced, self.n_fft, hop_length, primary.shape[-1]), enhanced

    def forward(
        self,
        primary_ri: torch.Tensor,
        reference_ri: torch.Tensor,
        state: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        return self.forward_ri(primary_ri, reference_ri, state)
