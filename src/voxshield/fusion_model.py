"""VoxShield-Fusion: dual-channel spatial front-end + UL-UNAS attention core.

Architecture (problem-statement workstream 2):

* **Input** — dual-channel STFT (primary + reference microphone), upstream
  layout ``(B, 2, T, F)``.
* **Spatial features** — five ERB-banded channels: primary log-magnitude,
  reference log-magnitude, inter-channel phase difference (cos/sin of the
  normalized cross-spectrum), and log-magnitude ratio.
* **Temporal core** — the pinned upstream UL-UNAS encoder / DPGRNN / decoder
  with its causal CTFA attention blocks (weights initialised from the
  upstream DNS3 checkpoint).
* **Output head** — a 2-channel complex ratio mask ``(Mr, Mi)`` applied as a
  complex multiplication, replacing the upstream real sigmoid mask so phase
  is corrected directly.

Initialization is behaviour-preserving: the encoder's first convolution is
widened to accept the five feature channels with the pretrained weights
copied into the primary log-magnitude channel and zeros elsewhere, and the
imaginary mask branch starts strongly negative (``Mi ~= 0``), so a freshly
built fusion model computes exactly what the pretrained mono UL-UNAS
computes. Training then learns to exploit the spatial channels and the
imaginary mask.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import torch
import torch.nn.functional as F
from torch import nn

from .audio import frame_istft, frame_stft

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_STREAM_MODULE_PATH = _PROJECT_ROOT / "external" / "ul-unas" / "ulunas_onnx" / "stream"


def _load_upstream_ulunas() -> Any:
    import importlib.util

    source = _PROJECT_ROOT / "external" / "ul-unas" / "ulunas.py"
    if not source.exists():
        raise FileNotFoundError(f"Missing pinned UL-UNAS source: {source}")
    spec = importlib.util.spec_from_file_location("voxshield_fusion_upstream_ulunas", source)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load UL-UNAS source: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_stream_module() -> Any:
    import importlib.util
    import sys

    base_dir = _PROJECT_ROOT / "external" / "ul-unas"
    stream_dir = base_dir / "ulunas_onnx" / "stream"
    for path in (str(base_dir), str(stream_dir)):
        if path not in sys.path:
            sys.path.insert(0, path)
    source = stream_dir / "ulunas_stream.py"
    spec = importlib.util.spec_from_file_location("voxshield_fusion_ulunas_stream", source)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load StreamULUNAS source: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _stream_temporal_conv(x: torch.Tensor, conv: nn.Module, cache: torch.Tensor):
    """Causal single-step temporal convolution with a left context cache."""
    inp = torch.cat([cache, x], dim=2)
    if isinstance(conv, nn.ConvTranspose2d):
        kernel_t = conv.kernel_size[0]
        padded = F.pad(inp, (0, 0, kernel_t - 1, 0))
        y = conv(padded)[:, :, -1:, :]
    else:
        y = conv(inp)
    new_cache = inp[:, :, 1:, :]
    return y, new_cache


def _stream_ctfa(ctfa: nn.Module, x: torch.Tensor, hidden_cache: torch.Tensor):
    zt = torch.mean(x.pow(2), dim=-1)
    at, hidden_cache = ctfa.ta_gru(zt.transpose(1, 2), hidden_cache)
    at = torch.sigmoid(ctfa.ta_fc(at).transpose(1, 2))
    af = torch.sigmoid(ctfa.fa(x))
    y = at[..., None] * x * af[:, None]
    return y, hidden_cache


def _stream_xconv(block: nn.Module, x: torch.Tensor, conv_cache: torch.Tensor, tfa_cache: torch.Tensor):
    x, conv_cache = _stream_temporal_conv(x, block.ops[1], conv_cache)
    x = block.ops[2](x)
    x = block.ops[3](x)
    x, tfa_cache = _stream_ctfa(block.ops[4], x, tfa_cache)
    x = block.ops[5](x)
    return x, conv_cache, tfa_cache


def _stream_xdws(block: nn.Module, x: torch.Tensor, tfa_cache: torch.Tensor, conv_cache: torch.Tensor | None = None):
    h = block.pconv(x)
    if conv_cache is None:
        h = block.dconv[0](h)
        h = block.dconv[1](h)
    else:
        h, conv_cache = _stream_temporal_conv(h, block.dconv[1], conv_cache)
    h = block.dconv[2](h)
    h = block.dconv[3](h)
    h, tfa_cache = _stream_ctfa(block.dconv[4], h, tfa_cache)
    return h, conv_cache, tfa_cache


def _stream_xmb(block: nn.Module, x: torch.Tensor, tfa_cache: torch.Tensor, conv_cache: torch.Tensor | None = None):
    residual = x
    x = block.pconv1(x)
    if conv_cache is None:
        x = block.dconv(x)
    else:
        x, conv_cache = _stream_temporal_conv(x, block.dconv[1], conv_cache)
        x = block.dconv[2](x)
        x = block.dconv[3](x)
    x = block.pconv2[0](x)
    x = block.pconv2[1](x)
    x, tfa_cache = _stream_ctfa(block.pconv2[2], x, tfa_cache)
    if x.shape == residual.shape:
        x = x + residual
    x = block.shuffle(x)
    return x, conv_cache, tfa_cache


def _stream_dpgrnn(block: nn.Module, x: torch.Tensor, inter_cache: torch.Tensor):
    x = x.permute(0, 2, 3, 1)  # (B,T,F,C)

    intra_x = x.reshape(x.shape[0] * x.shape[1], x.shape[2], x.shape[3])
    intra_x = block.intra_rnn(intra_x)[0]
    intra_x = block.intra_fc(intra_x)
    intra_x = intra_x.reshape(x.shape[0], -1, block.width, block.input_size)
    intra_x = block.intra_ln(intra_x)
    intra_out = x + intra_x

    x = intra_out.permute(0, 2, 1, 3)  # (B,F,T,C)
    inter_x = x.reshape(x.shape[0] * x.shape[1], x.shape[2], x.shape[3])
    inter_x, inter_cache = block.inter_rnn(inter_x, inter_cache)
    inter_x = block.inter_fc(inter_x)
    inter_x = inter_x.reshape(x.shape[0], block.width, -1, block.input_size)
    inter_x = inter_x.permute(0, 2, 1, 3)  # (B,T,F,C)
    inter_x = block.inter_ln(inter_x)
    inter_out = intra_out + inter_x

    dual_out = inter_out.permute(0, 3, 1, 2)  # (B,C,T,F)
    return dual_out, inter_cache


class FusionDualChannelULUNAS(nn.Module):
    """Dual-channel fusion of spatial features, UL-UNAS attention core, and a
    complex ratio mask. ``requires_reference = True``; streams per-frame via
    :meth:`forward_ri` with a packed cache state."""

    requires_reference = True
    architecture = "fusion_dual_ulunas"

    # Keep these constants local so importing runtime.py for other architectures
    # does not require the optional pinned UL-UNAS checkout to be present.
    _UPSTREAM_CONV_SHAPES: ClassVar[list] = [
        (1, 2, 129),
        (24, 1, 65),
        (24, 1, 33),
        (24, 1, 33),
        (12, 1, 33),
        (12, 2, 65),
    ]
    _TFA_HIDDEN: ClassVar[list] = [24, 48, 48, 64, 32, 64, 48, 48, 24, 2]
    _INTER_SHAPES: ClassVar[list] = [(33, 16), (33, 16)]

    def __init__(
        self,
        n_fft: int = 512,
        sample_rate: int = 16000,
        feature_channels: int = 5,
        imaginary_bias: float = -20.0,
        mask_mode: str = "legacy_sigmoid",
        imaginary_scale: float = 1.0,
    ) -> None:
        super().__init__()
        if n_fft != 512 or sample_rate != 16000:
            raise ValueError("fusion_dual_ulunas requires 16 kHz audio and n_fft=512")
        if feature_channels < 1:
            raise ValueError("feature_channels must be positive")
        self.n_fft = int(n_fft)
        self.sample_rate = int(sample_rate)
        self.feature_channels = int(feature_channels)
        self.imaginary_bias = float(imaginary_bias)
        if mask_mode not in {"legacy_sigmoid", "signed_imaginary"}:
            raise ValueError(f"unsupported complex-mask mode: {mask_mode}")
        if imaginary_scale <= 0.0:
            raise ValueError("imaginary_scale must be positive")
        self.mask_mode = str(mask_mode)
        self.imaginary_scale = float(imaginary_scale)

        core = _load_upstream_ulunas().ULUNAS(n_fft=n_fft)
        self.erb = core.erb
        self.encoder = core.encoder
        self.dpgrnn = core.dpgrnn
        self.decoder = core.decoder

        # Widen the first encoder convolution to consume every feature channel.
        # The pretrained weights occupy the primary log-magnitude channel and
        # the spatial channels start at exactly zero contribution.
        first_block = self.encoder.en_convs[0]
        first_conv = first_block.ops[1]
        if not isinstance(first_conv, nn.Conv2d):
            raise TypeError("unexpected first encoder layer; upstream layout changed")
        widened = nn.Conv2d(
            feature_channels,
            first_conv.out_channels,
            first_conv.kernel_size,
            stride=first_conv.stride,
            padding=first_conv.padding,
            groups=first_conv.groups,
            bias=first_conv.bias is not None,
        )
        with torch.no_grad():
            widened.weight.zero_()
            widened.weight[:, : first_conv.in_channels] = first_conv.weight
            if first_conv.bias is not None:
                widened.bias.copy_(first_conv.bias)
        first_block.ops[1] = widened

        # The first block's left-context cache widens with its input channels;
        # every later cache keeps the upstream geometry.
        self._conv_shapes = [
            (self.feature_channels,) + tuple(self._UPSTREAM_CONV_SHAPES[0])[1:]
        ] + self._UPSTREAM_CONV_SHAPES[1:]
        self.CONV_CACHE_SIZE = sum(
            int(torch.tensor(shape).prod().item()) for shape in self._conv_shapes
        )
        self.TFA_CACHE_SIZE = sum(self._TFA_HIDDEN)
        self.INTER_CACHE_SIZE = sum(
            int(torch.tensor(shape).prod().item()) for shape in self._INTER_SHAPES
        )
        self.STATE_SIZE = self.CONV_CACHE_SIZE + self.TFA_CACHE_SIZE + self.INTER_CACHE_SIZE

        # Complex mask head on the pre-sigmoid decoder output: the real branch
        # starts as the identity (pretrained magnitude mask) and the imaginary
        # branch starts at Mi ~= sigmoid(imaginary_bias) ~= 0.
        self.head = nn.Conv2d(1, 2, kernel_size=1)
        with torch.no_grad():
            self.head.weight.zero_()
            self.head.weight[0, 0] = 1.0
            self.head.bias.zero_()
            self.head.bias[1] = self.imaginary_bias

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> FusionDualChannelULUNAS:
        options = dict(config["model"])
        options.pop("architecture", None)
        options.pop("pretrained", None)
        options.pop("initialize_from", None)
        options.pop("reset_imaginary_branch", None)
        # Inherited chains carry legacy keys for other architectures
        # (channels, recurrent_blocks, min/max_mask_gain, ...); drop them.
        known = {
            "feature_channels",
            "imaginary_bias",
            "mask_mode",
            "imaginary_scale",
        }
        options = {key: value for key, value in options.items() if key in known}
        return cls(
            n_fft=config["audio"]["n_fft"],
            sample_rate=config["audio"]["sample_rate"],
            **options,
        )

    def reset_imaginary_branch(self) -> None:
        """Reset the phase branch at a trainable zero correction."""
        if self.mask_mode != "signed_imaginary":
            raise RuntimeError("imaginary reset is only valid for signed_imaginary mode")
        with torch.no_grad():
            self.head.weight[1].zero_()
            self.head.bias[1].zero_()

    def _activate_mask(self, logits: torch.Tensor) -> torch.Tensor:
        """Convert the two head logits into a bounded complex mask."""
        real = torch.sigmoid(logits[:, 0:1])
        if self.mask_mode == "legacy_sigmoid":
            imaginary = torch.sigmoid(logits[:, 1:2])
        else:
            imaginary = self.imaginary_scale * torch.tanh(logits[:, 1:2])
        return torch.cat((real, imaginary), dim=1)

    def load_pretrained(self, path: str | Path) -> None:
        """Load the upstream DNS3 checkpoint into the shared core modules.

        The checkpoint's first encoder convolution is narrower than this
        model's widened version, so the state is loaded into a pristine
        upstream instance first and then transferred module-by-module: every
        core module wholesale, and the widened convolution with the pretrained
        weights copied into the primary channel and zeros elsewhere. The
        complex-mask head is intentionally left at its initialization.
        """
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = _PROJECT_ROOT / resolved
        if not resolved.exists():
            raise FileNotFoundError(f"Missing pretrained checkpoint: {resolved}")
        checkpoint = torch.load(resolved, map_location="cpu", weights_only=False)
        state = checkpoint.get("model", checkpoint)
        upstream = _load_upstream_ulunas().ULUNAS(n_fft=self.n_fft)
        upstream.load_state_dict(state, strict=True)

        self.erb.load_state_dict(upstream.erb.state_dict())
        self.dpgrnn.load_state_dict(upstream.dpgrnn.state_dict())
        self.decoder.load_state_dict(upstream.decoder.state_dict())
        for index in range(1, len(self.encoder.en_convs)):
            self.encoder.en_convs[index].load_state_dict(
                upstream.encoder.en_convs[index].state_dict()
            )
        first_block = self.encoder.en_convs[0]
        upstream_first = upstream.encoder.en_convs[0]
        for op_index, (mine, theirs) in enumerate(zip(first_block.ops, upstream_first.ops)):
            if op_index == 1:
                continue  # the widened convolution is handled below
            mine.load_state_dict(theirs.state_dict())
        widened_conv = first_block.ops[1]
        pretrained_conv = upstream_first.ops[1]
        with torch.no_grad():
            widened_conv.weight.zero_()
            widened_conv.weight[:, : pretrained_conv.in_channels] = pretrained_conv.weight
            if pretrained_conv.bias is not None:
                widened_conv.bias.copy_(pretrained_conv.bias)

    # ------------------------------------------------------------------
    # Features and masks
    # ------------------------------------------------------------------

    def _features(self, primary: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
        """``(B, 2, T, F)`` spectra -> ``(B, C, T, 129)`` ERB-banded features."""
        p_mag = torch.norm(primary, dim=1, keepdim=True).clamp(1e-12)
        r_mag = torch.norm(reference, dim=1, keepdim=True).clamp(1e-12)
        log_p = torch.log10(p_mag)
        log_r = torch.log10(r_mag)
        primary_real, primary_imag = primary[:, 0:1], primary[:, 1:2]
        reference_real, reference_imag = reference[:, 0:1], reference[:, 1:2]
        denominator = (p_mag * r_mag).clamp_min(1e-12)
        cos_ipd = (primary_real * reference_real + primary_imag * reference_imag) / denominator
        sin_ipd = (primary_imag * reference_real - primary_real * reference_imag) / denominator
        log_ratio = (log_p - log_r).clamp(-5.0, 5.0)
        features = torch.cat((log_p, log_r, cos_ipd, sin_ipd, log_ratio), dim=1)
        if self.feature_channels == 1:
            return self.erb.bm(log_p)
        return self.erb.bm(features)

    def _mask(self, primary: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
        """Full-sequence complex ratio mask: ``(B, 2, T, F)``."""
        feat = self._features(primary, reference)
        feat, en_outs = self.encoder(feat)
        feat = self.dpgrnn(feat)
        x = feat
        blocks = self.decoder.de_convs
        for index in range(len(blocks)):
            x = blocks[index](x + en_outs[len(blocks) - index - 1])
        mask_erb = self._activate_mask(self.head(x))
        return self.erb.bs(mask_erb)

    @staticmethod
    def _apply_complex_mask(
        primary: torch.Tensor, mask: torch.Tensor
    ) -> torch.Tensor:
        """``primary`` ``(B, 2, T, F)``, ``mask`` ``(B, 2, T, F)`` -> enhanced."""
        primary_real, primary_imag = primary[:, 0], primary[:, 1]
        mask_real, mask_imag = mask[:, 0], mask[:, 1]
        enhanced_real = primary_real * mask_real - primary_imag * mask_imag
        enhanced_imag = primary_real * mask_imag + primary_imag * mask_real
        return torch.stack((enhanced_real, enhanced_imag), dim=1)

    # ------------------------------------------------------------------
    # Training interface: dual waveform -> enhanced waveform
    # ------------------------------------------------------------------

    def forward_spectrum(
        self,
        primary: torch.Tensor,
        reference: torch.Tensor,
        state: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        """Complex spectra ``(B, F, T)`` -> enhanced spectrum + (unused) state."""
        del state  # full-sequence path manages recurrent state internally
        p_ri = torch.stack((primary.real, primary.imag), dim=1).permute(0, 1, 3, 2)
        r_ri = torch.stack((reference.real, reference.imag), dim=1).permute(0, 1, 3, 2)
        mask = self._mask(p_ri, r_ri)
        enhanced = self._apply_complex_mask(p_ri, mask)  # (B, 2, T, F)
        enhanced = enhanced.permute(0, 1, 3, 2)  # (B, 2, F, T)
        enhanced_spectrum = torch.complex(enhanced[:, 0], enhanced[:, 1])  # (B, F, T)
        return enhanced_spectrum, None

    def forward_audio(
        self,
        primary: torch.Tensor,
        reference: torch.Tensor,
        hop_length: int,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if hop_length != 256:
            raise ValueError("fusion_dual_ulunas requires hop_length=256")
        primary_spectrum = frame_stft(primary, self.n_fft, hop_length)
        reference_spectrum = frame_stft(reference, self.n_fft, hop_length)
        enhanced, _ = self.forward_spectrum(primary_spectrum, reference_spectrum)
        return frame_istft(enhanced, self.n_fft, hop_length, primary.shape[-1]), enhanced

    # ------------------------------------------------------------------
    # WOLA streaming interface: per-frame RI spectra + packed cache state
    # ------------------------------------------------------------------

    def initial_state(
        self, batch_size: int = 1, device: torch.device | None = None
    ) -> torch.Tensor:
        return torch.zeros(batch_size, self.STATE_SIZE, device=device)

    def _unpack_state(self, state: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        conv_cache = state[:, : self.CONV_CACHE_SIZE]
        tfa_cache = state[:, self.CONV_CACHE_SIZE : self.CONV_CACHE_SIZE + self.TFA_CACHE_SIZE]
        inter_cache = state[:, self.CONV_CACHE_SIZE + self.TFA_CACHE_SIZE :]
        return (
            conv_cache.contiguous(),
            tfa_cache.contiguous(),
            inter_cache.contiguous(),
        )

    def _pack_state(
        self,
        conv_caches: list[torch.Tensor],
        tfa_caches: list[torch.Tensor],
        inter_caches: list[torch.Tensor],
    ) -> torch.Tensor:
        conv = torch.cat([cache.reshape(cache.shape[0], -1) for cache in conv_caches], dim=1)
        tfa = torch.cat([cache.reshape(cache.shape[1], -1) for cache in tfa_caches], dim=1)
        inter = torch.cat([cache.reshape(cache.shape[0], -1) for cache in inter_caches], dim=1)
        return torch.cat((conv, tfa, inter), dim=1)

    def forward_ri(
        self,
        primary_ri: torch.Tensor,
        reference_ri: torch.Tensor,
        state: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """WOLA frame path. Inputs ``(B, 2, F, 1)``, state ``(B, STATE_SIZE)``."""
        if primary_ri.ndim != 4 or primary_ri.shape[1] != 2:
            raise ValueError("primary_ri must have shape [batch, 2, frequency, frames]")
        if reference_ri.shape != primary_ri.shape:
            raise ValueError("reference_ri must have the same shape as primary_ri")
        if state is None or state.shape[0] != primary_ri.shape[0] or state.shape[1] != self.STATE_SIZE:
            state = self.initial_state(primary_ri.shape[0], primary_ri.device)

        primary = primary_ri.permute(0, 1, 3, 2).contiguous()  # (B,2,T=1,F)
        reference = reference_ri.permute(0, 1, 3, 2).contiguous()
        feat = self._features(primary, reference)  # (B, C, 1, 129)

        conv_cache, tfa_cache, inter_cache = self._unpack_state(state)
        conv_caches = self._unpack_conv_cache(conv_cache)
        tfa_caches = self._unpack_tfa_cache(tfa_cache)
        inter_caches = self._unpack_inter_cache(inter_cache)

        en_outs = []
        feat, conv_caches[0], tfa_caches[0] = _stream_xconv(
            self.encoder.en_convs[0], feat, conv_caches[0], tfa_caches[0]
        )
        en_outs.append(feat)
        feat, conv_caches[1], tfa_caches[1] = _stream_xmb(
            self.encoder.en_convs[1], feat, tfa_caches[1], conv_caches[1]
        )
        en_outs.append(feat)
        feat, conv_caches[2], tfa_caches[2] = _stream_xdws(
            self.encoder.en_convs[2], feat, tfa_caches[2], conv_caches[2]
        )
        en_outs.append(feat)
        feat, _, tfa_caches[3] = _stream_xmb(self.encoder.en_convs[3], feat, tfa_caches[3])
        en_outs.append(feat)
        feat, _, tfa_caches[4] = _stream_xdws(self.encoder.en_convs[4], feat, tfa_caches[4])
        en_outs.append(feat)

        feat, inter_caches[0] = _stream_dpgrnn(self.dpgrnn[0], feat, inter_caches[0])
        feat, inter_caches[1] = _stream_dpgrnn(self.dpgrnn[1], feat, inter_caches[1])

        feat, _, tfa_caches[5] = _stream_xdws(
            self.decoder.de_convs[0], feat + en_outs[4], tfa_caches[5]
        )
        feat, _, tfa_caches[6] = _stream_xmb(
            self.decoder.de_convs[1], feat + en_outs[3], tfa_caches[6]
        )
        feat, conv_caches[3], tfa_caches[7] = _stream_xdws(
            self.decoder.de_convs[2], feat + en_outs[2], tfa_caches[7], conv_caches[3]
        )
        feat, conv_caches[4], tfa_caches[8] = _stream_xmb(
            self.decoder.de_convs[3], feat + en_outs[1], tfa_caches[8], conv_caches[4]
        )
        feat, conv_caches[5], tfa_caches[9] = _stream_xconv(
            self.decoder.de_convs[4], feat + en_outs[0], conv_caches[5], tfa_caches[9]
        )

        mask_erb = self._activate_mask(self.head(feat))  # (B, 2, 1, 129)
        mask = self.erb.bs(mask_erb)  # (B, 2, 1, F)
        enhanced = self._apply_complex_mask(primary, mask)  # (B, 2, 1, F)
        enhanced_ri = enhanced.permute(0, 1, 3, 2).contiguous()  # (B, 2, F, 1)

        next_state = self._pack_state(conv_caches, tfa_caches, inter_caches)
        return enhanced_ri, next_state

    # cache pack/unpack mirroring the pinned StreamULUNAS helpers, with
    # explicit contiguity so arbitrary batch sizes work
    def _unpack_conv_cache(self, conv_cache: torch.Tensor) -> list[torch.Tensor]:
        caches = []
        offset = 0
        for shape in self._conv_shapes:
            count = 1
            for dim in shape:
                count *= dim
            caches.append(conv_cache[:, offset : offset + count].reshape(-1, *shape))
            offset += count
        return caches

    def _unpack_tfa_cache(self, tfa_cache: torch.Tensor) -> list[torch.Tensor]:
        batch = tfa_cache.shape[0]
        caches = []
        offset = 0
        for hidden in self._TFA_HIDDEN:
            caches.append(tfa_cache[:, offset : offset + hidden].reshape(1, batch, hidden))
            offset += hidden
        return caches

    def _unpack_inter_cache(self, inter_cache: torch.Tensor) -> list[torch.Tensor]:
        caches = []
        offset = 0
        for shape in self._INTER_SHAPES:
            count = 1
            for dim in shape:
                count *= dim
            caches.append(inter_cache[:, offset : offset + count].reshape(-1, *shape))
            offset += count
        return caches

    def forward(  # type: ignore[override]
        self,
        primary_ri: torch.Tensor,
        reference_ri: torch.Tensor,
        state: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        return self.forward_ri(primary_ri, reference_ri, state)
