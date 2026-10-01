from __future__ import annotations

from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

from .audio import frame_istft, frame_stft


class ERBFilterBank(nn.Module):
    """Fixed linear/ERB analysis and synthesis used by GTCRN."""

    def __init__(self, n_fft: int = 512, sample_rate: int = 16000, low_bins: int = 65, bands: int = 64) -> None:
        super().__init__()
        n_freq = n_fft // 2 + 1
        low_hz = low_bins / n_fft * sample_rate
        hz_to_erb = lambda hz: 21.4 * np.log10(0.00437 * hz + 1.0)
        erb_to_hz = lambda erb: (10.0 ** (erb / 21.4) - 1.0) / 0.00437
        points = np.linspace(hz_to_erb(low_hz), hz_to_erb(sample_rate / 2), bands)
        bins = np.round(erb_to_hz(points) / sample_rate * n_fft).astype(np.int64)
        filters = np.zeros((bands, n_freq), dtype=np.float32)
        filters[0, bins[0] : bins[1]] = (
            bins[1] - np.arange(bins[0], bins[1]) + 1e-12
        ) / (bins[1] - bins[0] + 1e-12)
        for index in range(bands - 2):
            filters[index + 1, bins[index] : bins[index + 1]] = (
                np.arange(bins[index], bins[index + 1]) - bins[index] + 1e-12
            ) / (bins[index + 1] - bins[index] + 1e-12)
            filters[index + 1, bins[index + 1] : bins[index + 2]] = (
                bins[index + 2] - np.arange(bins[index + 1], bins[index + 2]) + 1e-12
            ) / (bins[index + 2] - bins[index + 1] + 1e-12)
        filters[-1, bins[-2] : bins[-1] + 1] = 1.0 - filters[-2, bins[-2] : bins[-1] + 1]
        matrix = torch.from_numpy(np.abs(filters[:, low_bins:]))
        self.low_bins = int(low_bins)
        self.analysis = nn.Linear(n_freq - low_bins, bands, bias=False)
        self.synthesis = nn.Linear(bands, n_freq - low_bins, bias=False)
        self.analysis.weight = nn.Parameter(matrix, requires_grad=False)
        self.synthesis.weight = nn.Parameter(matrix.T, requires_grad=False)

    def compress(self, value: torch.Tensor) -> torch.Tensor:
        return torch.cat((value[..., : self.low_bins], self.analysis(value[..., self.low_bins :])), dim=-1)

    def expand(self, value: torch.Tensor) -> torch.Tensor:
        return torch.cat((value[..., : self.low_bins], self.synthesis(value[..., self.low_bins :])), dim=-1)


class SubbandFeatures(nn.Module):
    def __init__(self, width: int = 3) -> None:
        super().__init__()
        self.width = int(width)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        pad = self.width // 2
        padded = F.pad(value, (pad, pad))
        return torch.cat(
            [padded[..., offset : offset + value.shape[-1]] for offset in range(self.width)], dim=1
        )


class GroupedGRU(nn.Module):
    def __init__(self, size: int, bidirectional: bool = False) -> None:
        super().__init__()
        if size % 4:
            raise ValueError("GroupedGRU size must be divisible by four")
        hidden = size // 4 if bidirectional else size // 2
        self.left = nn.GRU(size // 2, hidden, batch_first=True, bidirectional=bidirectional)
        self.right = nn.GRU(size // 2, hidden, batch_first=True, bidirectional=bidirectional)

    def forward(
        self, value: torch.Tensor, state: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        left, right = value.chunk(2, dim=-1)
        if state is None:
            left_state = right_state = None
        else:
            left_state, right_state = state.chunk(2, dim=-1)
        left, left_state = self.left(left, left_state.contiguous() if left_state is not None else None)
        right, right_state = self.right(right, right_state.contiguous() if right_state is not None else None)
        return torch.cat((left, right), dim=-1), torch.cat((left_state, right_state), dim=-1)


class DualPathGroupedRNN(nn.Module):
    """Bidirectional frequency modeling plus causal grouped temporal modeling."""

    def __init__(self, channels: int, width: int) -> None:
        super().__init__()
        self.channels = int(channels)
        self.width = int(width)
        self.intra = GroupedGRU(channels, bidirectional=True)
        self.intra_projection = nn.Linear(channels, channels)
        self.intra_norm = nn.LayerNorm((width, channels), eps=1e-8)
        self.inter = GroupedGRU(channels, bidirectional=False)
        self.inter_projection = nn.Linear(channels, channels)
        self.inter_norm = nn.LayerNorm((width, channels), eps=1e-8)

    def forward(
        self, value: torch.Tensor, state: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        batch, channels, frames, width = value.shape
        sequence = value.permute(0, 2, 3, 1)
        intra = sequence.reshape(batch * frames, width, channels)
        intra, _ = self.intra(intra)
        intra = self.intra_projection(intra).reshape(batch, frames, width, channels)
        intra = self.intra_norm(intra) + sequence
        temporal = intra.permute(0, 2, 1, 3).reshape(batch * width, frames, channels)
        packed_state = None if state is None else state.reshape(1, batch * width, channels)
        temporal, next_state = self.inter(temporal, packed_state)
        temporal = self.inter_projection(temporal).reshape(batch, width, frames, channels)
        temporal = temporal.permute(0, 2, 1, 3)
        output = self.inter_norm(temporal) + intra
        return output.permute(0, 3, 1, 2), next_state.reshape(batch, width, channels)


class GTCRN(nn.Module):
    """GTCRN-derived ultra-light causal ERB/sub-band complex-mask enhancer."""

    def __init__(
        self,
        n_fft: int = 512,
        sample_rate: int = 16000,
        channels: int = 16,
        recurrent_blocks: int = 2,
        min_mask_gain: float = 0.05,
        max_mask_gain: float = 1.25,
    ) -> None:
        super().__init__()
        if n_fft != 512 or sample_rate != 16000:
            raise ValueError("This GTCRN configuration is defined for 16 kHz audio and n_fft=512")
        self.n_fft = int(n_fft)
        self.n_freq = n_fft // 2 + 1
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self.recurrent_blocks = int(recurrent_blocks)
        self.gru_layers = self.recurrent_blocks
        self.hidden_size = self.channels
        self.min_mask_gain = float(min_mask_gain)
        self.max_mask_gain = float(max_mask_gain)
        self.erb = ERBFilterBank(n_fft, sample_rate, 65, 64)
        self.subband = SubbandFeatures(3)
        self.encoder = nn.Sequential(
            nn.Conv2d(9, channels, (1, 5), stride=(1, 2), padding=(0, 2)),
            nn.BatchNorm2d(channels),
            nn.PReLU(channels),
            nn.Conv2d(channels, channels, (1, 5), stride=(1, 2), padding=(0, 2), groups=2),
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
        self.decoder_last = nn.ConvTranspose2d(
            channels, 2, (1, 5), stride=(1, 2), padding=(0, 2)
        )
        nn.init.zeros_(self.decoder_last.weight)
        nn.init.zeros_(self.decoder_last.bias)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> GTCRN:
        return cls(
            n_fft=config["audio"]["n_fft"],
            sample_rate=config["audio"]["sample_rate"],
            **config["model"],
        )

    def initial_state(self, batch_size: int, device: torch.device | None = None) -> torch.Tensor:
        return torch.zeros(
            self.recurrent_blocks, batch_size, self.width, self.channels, device=device
        )

    def forward_ri(
        self, spectrum_ri: torch.Tensor, state: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if spectrum_ri.ndim != 4 or spectrum_ri.shape[1] != 2:
            raise ValueError("spectrum_ri must have shape [batch, 2, frequency, frames]")
        real, imag = spectrum_ri[:, 0], spectrum_ri[:, 1]
        magnitude = torch.sqrt(real.square() + imag.square() + 1e-8)
        features = torch.stack((magnitude, real, imag), dim=1).permute(0, 1, 3, 2)
        features = self.subband(self.erb.compress(features))
        features = self.encoder(features)
        states = []
        for index, block in enumerate(self.dual_path):
            block_state = None if state is None else state[index]
            features, block_state = block(features, block_state)
            states.append(block_state)
        mask = self.decoder_last(self.decoder_first(features))
        mask = self.erb.expand(mask).permute(0, 1, 3, 2)
        mask_real = 1.0 + torch.tanh(mask[:, 0])
        mask_imag = torch.tanh(mask[:, 1])
        gain = torch.sqrt(mask_real.square() + mask_imag.square() + 1e-8)
        scale = torch.clamp(self.max_mask_gain / gain, max=1.0)
        mask_real, mask_imag = mask_real * scale, mask_imag * scale
        mask_real = self.min_mask_gain + (1.0 - self.min_mask_gain) * mask_real
        mask_imag = (1.0 - self.min_mask_gain) * mask_imag
        enhanced_real = real * mask_real - imag * mask_imag
        enhanced_imag = real * mask_imag + imag * mask_real
        return torch.stack((enhanced_real, enhanced_imag), dim=1), torch.stack(states)

    def forward_spectrum(
        self, spectrum: torch.Tensor, state: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        spectrum_ri = torch.stack((spectrum.real, spectrum.imag), dim=1)
        enhanced_ri, next_state = self.forward_ri(spectrum_ri, state)
        return torch.complex(enhanced_ri[:, 0], enhanced_ri[:, 1]), next_state

    def forward_audio(
        self, waveform: torch.Tensor, hop_length: int
    ) -> tuple[torch.Tensor, torch.Tensor]:
        spectrum = frame_stft(waveform, self.n_fft, hop_length)
        enhanced, _ = self.forward_spectrum(spectrum)
        return frame_istft(enhanced, self.n_fft, hop_length, waveform.shape[-1]), enhanced

    def forward(
        self, spectrum_ri: torch.Tensor, state: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        return self.forward_ri(spectrum_ri, state)


CausalComplexMaskNet = GTCRN


def build_model(config: dict[str, Any]) -> nn.Module:
    """Build the requested architecture while keeping recipe-v2 checkpoints loadable."""
    architecture = config.get("model", {}).get("architecture", "legacy_gtcrn_derived")
    if architecture == "official_gtcrn":
        from .official_gtcrn import OfficialGTCRN

        return OfficialGTCRN.from_config(config)
    if architecture == "official_ulunas":
        from .ulunas_adapter import OfficialULUNAS

        return OfficialULUNAS.from_config(config)
    if architecture == "hybrid_dual_gtcrn":
        from .hybrid_model import HybridDualChannelGTCRN

        return HybridDualChannelGTCRN.from_config(config)
    if architecture == "fusion_dual_ulunas":
        from .fusion_model import FusionDualChannelULUNAS

        return FusionDualChannelULUNAS.from_config(config)
    if architecture == "deep_filter_dual":
        from .df_model import DeepFilterDualChannelNet

        return DeepFilterDualChannelNet.from_config(config)
    if architecture != "legacy_gtcrn_derived":
        raise ValueError(f"Unsupported model architecture: {architecture}")
    return CausalComplexMaskNet.from_config(config)


def count_parameters(model: nn.Module, trainable_only: bool = True) -> int:
    parameters = (
        (parameter for parameter in model.parameters() if parameter.requires_grad)
        if trainable_only
        else model.parameters()
    )
    return sum(parameter.numel() for parameter in parameters)
