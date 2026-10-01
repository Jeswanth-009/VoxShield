"""Faithful GTCRN architecture adapted from the official MIT-licensed project.

Upstream: https://github.com/Xiaobin-Rong/gtcrn
Pinned source commit: 502ebfab64da7c4a9af78dcb9c6ceef1ebb01c73
Copyright (c) 2024 Rong Xiaobin
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn


class ERB(nn.Module):
    def __init__(
        self, low_bands: int = 65, high_bands: int = 64, nfft: int = 512,
        high_lim: int = 8000, sample_rate: int = 16000,
    ) -> None:
        super().__init__()
        filters = self._filter_banks(low_bands, high_bands, nfft, high_lim, sample_rate)
        frequencies = nfft // 2 + 1
        self.erb_subband_1 = low_bands
        self.erb_fc = nn.Linear(frequencies - low_bands, high_bands, bias=False)
        self.ierb_fc = nn.Linear(high_bands, frequencies - low_bands, bias=False)
        self.erb_fc.weight = nn.Parameter(filters, requires_grad=False)
        self.ierb_fc.weight = nn.Parameter(filters.T, requires_grad=False)

    @staticmethod
    def _hz_to_erb(frequency: float | np.ndarray) -> float | np.ndarray:
        return 21.4 * np.log10(0.00437 * frequency + 1.0)

    @staticmethod
    def _erb_to_hz(erb: float | np.ndarray) -> float | np.ndarray:
        return (10 ** (erb / 21.4) - 1.0) / 0.00437

    @classmethod
    def _filter_banks(
        cls, low_bands: int, high_bands: int, nfft: int, high_lim: int, sample_rate: int
    ) -> torch.Tensor:
        low_lim = low_bands / nfft * sample_rate
        points = np.linspace(cls._hz_to_erb(low_lim), cls._hz_to_erb(high_lim), high_bands)
        bins = np.round(cls._erb_to_hz(points) / sample_rate * nfft).astype(np.int32)
        filters = np.zeros((high_bands, nfft // 2 + 1), dtype=np.float32)
        filters[0, bins[0] : bins[1]] = (
            bins[1] - np.arange(bins[0], bins[1]) + 1e-12
        ) / (bins[1] - bins[0] + 1e-12)
        for index in range(high_bands - 2):
            filters[index + 1, bins[index] : bins[index + 1]] = (
                np.arange(bins[index], bins[index + 1]) - bins[index] + 1e-12
            ) / (bins[index + 1] - bins[index] + 1e-12)
            filters[index + 1, bins[index + 1] : bins[index + 2]] = (
                bins[index + 2] - np.arange(bins[index + 1], bins[index + 2]) + 1e-12
            ) / (bins[index + 2] - bins[index + 1] + 1e-12)
        filters[-1, bins[-2] : bins[-1] + 1] = 1.0 - filters[-2, bins[-2] : bins[-1] + 1]
        return torch.from_numpy(np.abs(filters[:, low_bands:]))

    def bm(self, value: torch.Tensor) -> torch.Tensor:
        return torch.cat(
            (value[..., : self.erb_subband_1], self.erb_fc(value[..., self.erb_subband_1 :])),
            dim=-1,
        )

    def bs(self, value: torch.Tensor) -> torch.Tensor:
        return torch.cat(
            (value[..., : self.erb_subband_1], self.ierb_fc(value[..., self.erb_subband_1 :])),
            dim=-1,
        )


class SFE(nn.Module):
    def __init__(self, kernel_size: int = 3, stride: int = 1) -> None:
        super().__init__()
        self.kernel_size = kernel_size
        self.unfold = nn.Unfold(
            kernel_size=(1, kernel_size), stride=(1, stride),
            padding=(0, (kernel_size - 1) // 2),
        )

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.unfold(value).reshape(
            value.shape[0], value.shape[1] * self.kernel_size, value.shape[2], value.shape[3]
        )


class TRA(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        self.att_gru = nn.GRU(channels, channels * 2, 1, batch_first=True)
        self.att_fc = nn.Linear(channels * 2, channels)
        self.att_act = nn.Sigmoid()

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        energy = torch.mean(value.square(), dim=-1)
        attention, _ = self.att_gru(energy.transpose(1, 2))
        attention = self.att_act(self.att_fc(attention).transpose(1, 2))[..., None]
        return value * attention


class ConvBlock(nn.Module):
    def __init__(
        self, in_channels: int, out_channels: int, kernel_size: tuple[int, int],
        stride: tuple[int, int], padding: tuple[int, int], groups: int = 1,
        use_deconv: bool = False, is_last: bool = False,
    ) -> None:
        super().__init__()
        operation = nn.ConvTranspose2d if use_deconv else nn.Conv2d
        self.conv = operation(in_channels, out_channels, kernel_size, stride, padding, groups=groups)
        self.bn = nn.BatchNorm2d(out_channels)
        self.act = nn.Tanh() if is_last else nn.PReLU()

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.act(self.bn(self.conv(value)))


class GTConvBlock(nn.Module):
    def __init__(
        self, in_channels: int, hidden_channels: int, kernel_size: tuple[int, int],
        stride: tuple[int, int], padding: tuple[int, int], dilation: tuple[int, int],
        use_deconv: bool = False,
    ) -> None:
        super().__init__()
        self.pad_size = (kernel_size[0] - 1) * dilation[0]
        operation = nn.ConvTranspose2d if use_deconv else nn.Conv2d
        self.sfe = SFE(3, 1)
        self.point_conv1 = operation(in_channels // 2 * 3, hidden_channels, 1)
        self.point_bn1 = nn.BatchNorm2d(hidden_channels)
        self.point_act = nn.PReLU()
        self.depth_conv = operation(
            hidden_channels, hidden_channels, kernel_size, stride=stride, padding=padding,
            dilation=dilation, groups=hidden_channels,
        )
        self.depth_bn = nn.BatchNorm2d(hidden_channels)
        self.depth_act = nn.PReLU()
        self.point_conv2 = operation(hidden_channels, in_channels // 2, 1)
        self.point_bn2 = nn.BatchNorm2d(in_channels // 2)
        self.tra = TRA(in_channels // 2)

    @staticmethod
    def _shuffle(left: torch.Tensor, right: torch.Tensor) -> torch.Tensor:
        value = torch.stack((left, right), dim=1).transpose(1, 2).contiguous()
        return value.reshape(value.shape[0], -1, value.shape[3], value.shape[4])

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        left, right = torch.chunk(value, chunks=2, dim=1)
        left = self.sfe(left)
        left = self.point_act(self.point_bn1(self.point_conv1(left)))
        left = F.pad(left, (0, 0, self.pad_size, 0))
        left = self.depth_act(self.depth_bn(self.depth_conv(left)))
        left = self.point_bn2(self.point_conv2(left))
        return self._shuffle(self.tra(left), right)


class GRNN(nn.Module):
    def __init__(
        self, input_size: int, hidden_size: int, num_layers: int = 1,
        batch_first: bool = True, bidirectional: bool = False,
    ) -> None:
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = bidirectional
        self.rnn1 = nn.GRU(
            input_size // 2, hidden_size // 2, num_layers,
            batch_first=batch_first, bidirectional=bidirectional,
        )
        self.rnn2 = nn.GRU(
            input_size // 2, hidden_size // 2, num_layers,
            batch_first=batch_first, bidirectional=bidirectional,
        )

    def forward(
        self, value: torch.Tensor, state: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if state is None:
            directions = 2 if self.bidirectional else 1
            state = torch.zeros(
                self.num_layers * directions, value.shape[0], self.hidden_size,
                device=value.device, dtype=value.dtype,
            )
        left, right = torch.chunk(value, chunks=2, dim=-1)
        state_left, state_right = torch.chunk(state, chunks=2, dim=-1)
        left, state_left = self.rnn1(left, state_left.contiguous())
        right, state_right = self.rnn2(right, state_right.contiguous())
        return torch.cat((left, right), dim=-1), torch.cat((state_left, state_right), dim=-1)


class DPGRNN(nn.Module):
    def __init__(self, input_size: int, width: int, hidden_size: int) -> None:
        super().__init__()
        self.width = width
        self.hidden_size = hidden_size
        self.intra_rnn = GRNN(input_size, hidden_size // 2, bidirectional=True)
        self.intra_fc = nn.Linear(hidden_size, hidden_size)
        self.intra_ln = nn.LayerNorm((width, hidden_size), eps=1e-8)
        self.inter_rnn = GRNN(input_size, hidden_size, bidirectional=False)
        self.inter_fc = nn.Linear(hidden_size, hidden_size)
        self.inter_ln = nn.LayerNorm((width, hidden_size), eps=1e-8)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        value = value.permute(0, 2, 3, 1)
        intra = value.reshape(value.shape[0] * value.shape[1], value.shape[2], value.shape[3])
        intra, _ = self.intra_rnn(intra)
        intra = self.intra_fc(intra).reshape(value.shape[0], -1, self.width, self.hidden_size)
        intra = self.intra_ln(intra) + value
        temporal = intra.permute(0, 2, 1, 3)
        inter = temporal.reshape(
            temporal.shape[0] * temporal.shape[1], temporal.shape[2], temporal.shape[3]
        )
        inter, _ = self.inter_rnn(inter)
        inter = self.inter_fc(inter).reshape(temporal.shape[0], self.width, -1, self.hidden_size)
        inter = self.inter_ln(inter.permute(0, 2, 1, 3)) + intra
        return inter.permute(0, 3, 1, 2)


class Encoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.en_convs = nn.ModuleList([
            ConvBlock(9, 16, (1, 5), (1, 2), (0, 2)),
            ConvBlock(16, 16, (1, 5), (1, 2), (0, 2), groups=2),
            GTConvBlock(16, 16, (3, 3), (1, 1), (0, 1), (1, 1)),
            GTConvBlock(16, 16, (3, 3), (1, 1), (0, 1), (2, 1)),
            GTConvBlock(16, 16, (3, 3), (1, 1), (0, 1), (5, 1)),
        ])

    def forward(self, value: torch.Tensor) -> tuple[torch.Tensor, list[torch.Tensor]]:
        outputs = []
        for layer in self.en_convs:
            value = layer(value)
            outputs.append(value)
        return value, outputs


class Decoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.de_convs = nn.ModuleList([
            GTConvBlock(16, 16, (3, 3), (1, 1), (10, 1), (5, 1), True),
            GTConvBlock(16, 16, (3, 3), (1, 1), (4, 1), (2, 1), True),
            GTConvBlock(16, 16, (3, 3), (1, 1), (2, 1), (1, 1), True),
            ConvBlock(16, 16, (1, 5), (1, 2), (0, 2), groups=2, use_deconv=True),
            ConvBlock(16, 2, (1, 5), (1, 2), (0, 2), use_deconv=True, is_last=True),
        ])

    def forward(self, value: torch.Tensor, skips: list[torch.Tensor]) -> torch.Tensor:
        for index, layer in enumerate(self.de_convs):
            value = layer(value + skips[-1 - index])
        return value


class Mask(nn.Module):
    def forward(self, mask: torch.Tensor, spectrum: torch.Tensor) -> torch.Tensor:
        real = spectrum[:, 0] * mask[:, 0] - spectrum[:, 1] * mask[:, 1]
        imag = spectrum[:, 1] * mask[:, 0] + spectrum[:, 0] * mask[:, 1]
        return torch.stack((real, imag), dim=1)


class OfficialGTCRN(nn.Module):
    """Complete official single-channel GTCRN with compatible parameter names."""

    architecture = "official_gtcrn"

    def __init__(self, n_fft: int = 512, sample_rate: int = 16000) -> None:
        super().__init__()
        if n_fft != 512 or sample_rate != 16000:
            raise ValueError("Official GTCRN requires 16 kHz audio and n_fft=512")
        self.n_fft = n_fft
        self.sample_rate = sample_rate
        self.erb = ERB(65, 64, n_fft, sample_rate // 2, sample_rate)
        self.sfe = SFE(3, 1)
        self.encoder = Encoder()
        self.dpgrnn1 = DPGRNN(16, 33, 16)
        self.dpgrnn2 = DPGRNN(16, 33, 16)
        self.decoder = Decoder()
        self.mask = Mask()

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> OfficialGTCRN:
        return cls(config["audio"]["n_fft"], config["audio"]["sample_rate"])

    def forward(self, spectrum_ri: torch.Tensor) -> torch.Tensor:
        if spectrum_ri.ndim != 4 or spectrum_ri.shape[-1] != 2:
            raise ValueError("spectrum_ri must have shape [batch, frequency, frames, 2]")
        reference = spectrum_ri
        real = spectrum_ri[..., 0].permute(0, 2, 1)
        imag = spectrum_ri[..., 1].permute(0, 2, 1)
        magnitude = torch.sqrt(real.square() + imag.square() + 1e-12)
        features = torch.stack((magnitude, real, imag), dim=1)
        features = self.sfe(self.erb.bm(features))
        features, skips = self.encoder(features)
        features = self.dpgrnn1(features)
        features = self.dpgrnn2(features)
        mask = self.erb.bs(self.decoder(features, skips))
        enhanced = self.mask(mask, reference.permute(0, 3, 2, 1))
        return enhanced.permute(0, 3, 2, 1)

    def forward_spectrum(self, spectrum: torch.Tensor) -> torch.Tensor:
        output = self.forward(torch.view_as_real(spectrum))
        return torch.view_as_complex(output.contiguous())

    def forward_audio(
        self, waveform: torch.Tensor, hop_length: int
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if hop_length != 256:
            raise ValueError("Official GTCRN pretrained weights require hop_length=256")
        window = torch.hann_window(
            self.n_fft, periodic=True, device=waveform.device, dtype=waveform.dtype
        ).sqrt()
        spectrum = torch.stft(
            waveform, self.n_fft, hop_length, self.n_fft, window,
            return_complex=True, center=True,
        )
        enhanced = self.forward_spectrum(spectrum)
        audio = torch.istft(
            enhanced, self.n_fft, hop_length, self.n_fft, window,
            center=True, length=waveform.shape[-1],
        )
        return audio, enhanced


def load_official_weights(model: OfficialGTCRN, path: str) -> None:
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    model.load_state_dict(checkpoint.get("model", checkpoint), strict=True)
