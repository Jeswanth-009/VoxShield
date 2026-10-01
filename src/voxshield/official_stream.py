"""Stateful one-STFT-frame GTCRN runtime adapted from the official MIT source."""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

from .official_gtcrn import ERB, GRNN, SFE, ConvBlock, Mask, OfficialGTCRN


class StreamConv2d(nn.Module):
    def __init__(self, channels: int, kernel: tuple[int, int], dilation: tuple[int, int]) -> None:
        super().__init__()
        self.Conv2d = nn.Conv2d(
            channels, channels, kernel, padding=(0, 1), dilation=dilation, groups=channels
        )

    def forward(
        self, value: torch.Tensor, cache: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        combined = torch.cat((cache, value), dim=2)
        return self.Conv2d(combined), combined[:, :, 1:]


class StreamConvTranspose2d(nn.Module):
    """Causal transposed convolution expressed as a weight-reversed Conv2d."""

    def __init__(
        self,
        channels: int,
        kernel: tuple[int, int],
        dilation: tuple[int, int],
    ) -> None:
        super().__init__()
        self.frequency_size = kernel[1]
        self.frequency_dilation = dilation[1]
        self.ConvTranspose2d = nn.Conv2d(
            channels,
            channels,
            kernel,
            padding=(0, 0),
            dilation=dilation,
            groups=channels,
        )

    def forward(
        self, value: torch.Tensor, cache: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        combined = torch.cat((cache, value), dim=2)
        next_cache = combined[:, :, 1:]
        padding = (self.frequency_size - 1) * self.frequency_dilation - 1
        combined = F.pad(combined, (padding, padding))
        return self.ConvTranspose2d(combined), next_cache


class StreamTRA(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        self.att_gru = nn.GRU(channels, channels * 2, 1, batch_first=True)
        self.att_fc = nn.Linear(channels * 2, channels)
        self.att_act = nn.Sigmoid()

    def forward(
        self, value: torch.Tensor, cache: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        energy = torch.mean(value.square(), dim=-1).transpose(1, 2)
        attention, cache = self.att_gru(energy, cache)
        attention = self.att_act(self.att_fc(attention).transpose(1, 2))[..., None]
        return value * attention, cache


class StreamGTConvBlock(nn.Module):
    def __init__(
        self, dilation: int, use_deconv: bool = False,
    ) -> None:
        super().__init__()
        self.sfe = SFE(3, 1)
        operation = nn.ConvTranspose2d if use_deconv else nn.Conv2d
        self.point_conv1 = operation(24, 16, 1)
        self.point_bn1 = nn.BatchNorm2d(16)
        self.point_act = nn.PReLU()
        stream_operation = StreamConvTranspose2d if use_deconv else StreamConv2d
        self.depth_conv = stream_operation(16, (3, 3), (dilation, 1))
        self.depth_bn = nn.BatchNorm2d(16)
        self.depth_act = nn.PReLU()
        self.point_conv2 = operation(16, 8, 1)
        self.point_bn2 = nn.BatchNorm2d(8)
        self.tra = StreamTRA(8)

    def forward(
        self, value: torch.Tensor, conv_cache: torch.Tensor, tra_cache: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        left, right = torch.chunk(value, 2, dim=1)
        left = self.point_act(self.point_bn1(self.point_conv1(self.sfe(left))))
        left, conv_cache = self.depth_conv(left, conv_cache)
        left = self.depth_act(self.depth_bn(left))
        left = self.point_bn2(self.point_conv2(left))
        left, tra_cache = self.tra(left, tra_cache)
        shuffled = torch.stack((left, right), dim=1).transpose(1, 2).contiguous()
        shuffled = shuffled.reshape(
            shuffled.shape[0], -1, shuffled.shape[3], shuffled.shape[4]
        )
        return shuffled, conv_cache, tra_cache


class StreamDPGRNN(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.width = 33
        self.hidden_size = 16
        self.intra_rnn = GRNN(16, 8, bidirectional=True)
        self.intra_fc = nn.Linear(16, 16)
        self.intra_ln = nn.LayerNorm((33, 16), eps=1e-8)
        self.inter_rnn = GRNN(16, 16, bidirectional=False)
        self.inter_fc = nn.Linear(16, 16)
        self.inter_ln = nn.LayerNorm((33, 16), eps=1e-8)

    def forward(
        self, value: torch.Tensor, cache: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        value = value.permute(0, 2, 3, 1)
        intra = value.reshape(value.shape[0] * value.shape[1], value.shape[2], 16)
        intra, _ = self.intra_rnn(intra)
        intra = self.intra_fc(intra).reshape(value.shape[0], -1, 33, 16)
        intra = self.intra_ln(intra) + value
        temporal = intra.permute(0, 2, 1, 3)
        inter = temporal.reshape(temporal.shape[0] * 33, temporal.shape[2], 16)
        inter, cache = self.inter_rnn(inter, cache)
        inter = self.inter_fc(inter).reshape(temporal.shape[0], 33, -1, 16)
        inter = self.inter_ln(inter.permute(0, 2, 1, 3)) + intra
        return inter.permute(0, 3, 1, 2), cache


class StreamEncoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.en_convs = nn.ModuleList([
            ConvBlock(9, 16, (1, 5), (1, 2), (0, 2)),
            ConvBlock(16, 16, (1, 5), (1, 2), (0, 2), groups=2),
            StreamGTConvBlock(1), StreamGTConvBlock(2), StreamGTConvBlock(5),
        ])

    def forward(
        self, value: torch.Tensor, conv: torch.Tensor, tra: torch.Tensor
    ) -> tuple[torch.Tensor, list[torch.Tensor], torch.Tensor, torch.Tensor]:
        skips = []
        for layer in self.en_convs[:2]:
            value = layer(value)
            skips.append(value)
        next_conv, next_tra = [], []
        starts = (0, 2, 6)
        ends = (2, 6, 16)
        for index, layer in enumerate(self.en_convs[2:]):
            value, cache, attention = layer(
                value, conv[:, :, starts[index] : ends[index]], tra[index]
            )
            next_conv.append(cache)
            next_tra.append(attention)
            skips.append(value)
        return value, skips, torch.cat(next_conv, dim=2), torch.stack(next_tra)


class StreamDecoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.de_convs = nn.ModuleList([
            StreamGTConvBlock(5, True), StreamGTConvBlock(2, True),
            StreamGTConvBlock(1, True),
            ConvBlock(16, 16, (1, 5), (1, 2), (0, 2), groups=2, use_deconv=True),
            ConvBlock(16, 2, (1, 5), (1, 2), (0, 2), use_deconv=True, is_last=True),
        ])

    def forward(
        self, value: torch.Tensor, skips: list[torch.Tensor],
        conv: torch.Tensor, tra: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        next_conv: list[torch.Tensor] = [
            conv[:, :, :2], conv[:, :, 2:6], conv[:, :, 6:16]
        ]
        next_tra: list[torch.Tensor] = []
        cache_indices = (2, 1, 0)
        for index, layer in enumerate(self.de_convs[:3]):
            cache_index = cache_indices[index]
            value, cache, attention = layer(
                value + skips[-1 - index], next_conv[cache_index], tra[index]
            )
            next_conv[cache_index] = cache
            next_tra.append(attention)
        for index, layer in enumerate(self.de_convs[3:], start=3):
            value = layer(value + skips[-1 - index])
        return value, torch.cat(next_conv, dim=2), torch.stack(next_tra)


class StreamGTCRN(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.erb = ERB(65, 64)
        self.sfe = SFE(3, 1)
        self.encoder = StreamEncoder()
        self.dpgrnn1 = StreamDPGRNN()
        self.dpgrnn2 = StreamDPGRNN()
        self.decoder = StreamDecoder()
        self.mask = Mask()

    @staticmethod
    def initial_states(
        batch_size: int, device: torch.device
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return (
            torch.zeros(2, batch_size, 16, 16, 33, device=device),
            torch.zeros(2, 3, 1, batch_size, 16, device=device),
            torch.zeros(2, 1, batch_size * 33, 16, device=device),
        )

    def forward(
        self, spectrum: torch.Tensor, conv: torch.Tensor,
        tra: torch.Tensor, inter: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        reference = spectrum
        real = spectrum[..., 0].permute(0, 2, 1)
        imag = spectrum[..., 1].permute(0, 2, 1)
        magnitude = torch.sqrt(real.square() + imag.square() + 1e-12)
        features = self.sfe(self.erb.bm(torch.stack((magnitude, real, imag), dim=1)))
        features, skips, encoder_conv, encoder_tra = self.encoder(
            features, conv[0], tra[0]
        )
        features, inter_1 = self.dpgrnn1(features, inter[0])
        features, inter_2 = self.dpgrnn2(features, inter[1])
        mask, decoder_conv, decoder_tra = self.decoder(
            features, skips, conv[1], tra[1]
        )
        mask = self.erb.bs(mask)
        enhanced = self.mask(mask, reference.permute(0, 3, 2, 1)).permute(0, 3, 2, 1)
        return (
            enhanced,
            torch.stack((encoder_conv, decoder_conv)),
            torch.stack((encoder_tra, decoder_tra)),
            torch.stack((inter_1, inter_2)),
        )


def convert_to_stream(stream: StreamGTCRN, offline: OfficialGTCRN) -> None:
    source = offline.state_dict()
    converted = stream.state_dict()
    for key in converted:
        source_key = key.replace("Conv2d.", "").replace("ConvTranspose2d.", "")
        if source_key not in source:
            raise KeyError(f"No offline GTCRN tensor for stream tensor {key}")
        tensor = source[source_key]
        if "ConvTranspose2d." in key and key.endswith("weight"):
            if converted[key].shape != tensor.shape:
                tensor = tensor.permute(1, 0, 2, 3)
            tensor = torch.flip(tensor, dims=(-2, -1))
        converted[key] = tensor
    stream.load_state_dict(converted, strict=True)
