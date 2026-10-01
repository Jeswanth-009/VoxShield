"""VoxShield v10: dual-channel multi-frame deep-filter enhancement model.

v10 plan (post-v8/v9 audit): the 147k fusion model is a pointwise T-F mask —
every bin is multiplied by one complex value, so the model cannot reinforce a
harmonic across neighbouring frames, and at very low SNR its aggressive
suppression deletes speech that resembles military impulses.

v10 therefore changes the reconstruction, not merely the weights:

* **Multi-frame complex deep filtering** — the network emits a small causal
  FIR of complex coefficients per T-F unit that is applied across the last
  ``deep_filter_taps`` frames of the masked spectrum, so energy from adjacent
  frames contributes to the current estimate (the DeepFilterNet principle).
* **Separated suppression decisions** — a speech-presence estimate decides
  *whether* to attenuate, a suppression-strength estimate decides *how much*,
  and the product is bounded below by a conservative gain floor.
* **Explicit transient path** — a per-frame transient estimate relaxes noise
  suppression so impulsive events cannot pull the mask below the floor and
  delete consonant onsets.
* **Dual-channel spatial features** — the same IPD/ILD/log-ratio feature set
  as the v7/v8 fusion front-end, over an ERB sub-band representation.
* **Capacity** — roughly an order of magnitude above the fusion core
  (configurable, default ~1.1 M parameters) while remaining causal and
  streamable frame-by-frame with a packed state vector.

The temporal backbone is frequency-convolutional plus causal dual-path GRUs
(:class:`DualPathGroupedRNN` from the GTCRN lineage); convolutions act on
frequency only, so streaming state consists of the recurrent hidden states
and the deep-filter history of already-masked frames.

Initialization is behaviour-preserving: the deep-filter taps start at exactly
zero so a freshly built model computes a plain (modulated) complex mask, and
the mask heads start mildly transparent with a low noise floor.
"""

from __future__ import annotations

from typing import Any

import torch
import torch.nn.functional as F
from torch import nn

from .audio import frame_istft, frame_stft
from .model import DualPathGroupedRNN, ERBFilterBank, SubbandFeatures


def _apply_complex_mask(
    primary: torch.Tensor, mask: torch.Tensor
) -> torch.Tensor:
    """``primary`` ``(B, 2, T, F)``, ``mask`` ``(B, 2, T, F)`` -> enhanced."""
    primary_real, primary_imag = primary[:, 0], primary[:, 1]
    mask_real, mask_imag = mask[:, 0], mask[:, 1]
    enhanced_real = primary_real * mask_real - primary_imag * mask_imag
    enhanced_imag = primary_real * mask_imag + primary_imag * mask_real
    return torch.stack((enhanced_real, enhanced_imag), dim=1)


class DeepFilterDualChannelNet(nn.Module):
    """Causal dual-channel enhancer with a multi-frame complex deep-filter
    head. ``requires_reference = True``; streams per-frame via
    :meth:`forward_ri` with a packed state vector (deep-filter history first,
    then the recurrent hidden states)."""

    requires_reference = True
    architecture = "deep_filter_dual"

    def __init__(
        self,
        n_fft: int = 512,
        sample_rate: int = 16000,
        channels: int = 160,
        recurrent_blocks: int = 4,
        deep_filter_taps: int = 5,
        df_scale: float = 0.5,
        imaginary_scale: float = 0.5,
        min_mask_gain: float = 0.03,
        transient_gate: float = 0.5,
    ) -> None:
        super().__init__()
        if n_fft != 512 or sample_rate != 16000:
            raise ValueError("deep_filter_dual requires 16 kHz audio and n_fft=512")
        if channels % 4:
            raise ValueError("channels must be divisible by four (grouped GRUs)")
        if deep_filter_taps < 1:
            raise ValueError("deep_filter_taps must be at least one")
        if recurrent_blocks < 1:
            raise ValueError("recurrent_blocks must be at least one")
        if df_scale <= 0.0:
            raise ValueError("df_scale must be positive")
        if imaginary_scale <= 0.0:
            raise ValueError("imaginary_scale must be positive")
        if not 0.0 <= min_mask_gain < 1.0:
            raise ValueError("min_mask_gain must be in [0, 1)")
        if not 0.0 <= transient_gate <= 1.0:
            raise ValueError("transient_gate must be in [0, 1]")

        self.n_fft = int(n_fft)
        self.n_freq = n_fft // 2 + 1
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self.recurrent_blocks = int(recurrent_blocks)
        self.deep_filter_taps = int(deep_filter_taps)
        self.history_taps = self.deep_filter_taps - 1
        self.df_scale = float(df_scale)
        self.imaginary_scale = float(imaginary_scale)
        self.min_mask_gain = float(min_mask_gain)
        self.transient_gate = float(transient_gate)
        self.width = 33  # 129 ERB bins -> 65 -> 33 through two stride-2 convs

        self.erb = ERBFilterBank(n_fft, sample_rate, 65, 64)
        self.subband = SubbandFeatures(3)
        feature_channels = 7 * self.subband.width  # 7 spatial/spectral features

        self.enc1 = nn.Conv2d(feature_channels, channels, (1, 5), stride=(1, 2), padding=(0, 2))
        self.enc1_bn = nn.BatchNorm2d(channels)
        self.enc1_act = nn.PReLU(channels)
        self.enc2 = nn.Conv2d(channels, channels, (1, 5), stride=(1, 2), padding=(0, 2), groups=2)
        self.enc2_bn = nn.BatchNorm2d(channels)
        self.enc2_act = nn.PReLU(channels)

        self.dual_path = nn.ModuleList(
            DualPathGroupedRNN(channels, self.width) for _ in range(self.recurrent_blocks)
        )

        self.dec1 = nn.ConvTranspose2d(
            channels, channels, (1, 5), stride=(1, 2), padding=(0, 2), groups=2
        )
        self.dec1_bn = nn.BatchNorm2d(channels)
        self.dec1_act = nn.PReLU(channels)
        self.dec2 = nn.ConvTranspose2d(channels, channels, (1, 5), stride=(1, 2), padding=(0, 2))
        self.dec2_bn = nn.BatchNorm2d(channels)
        self.dec2_act = nn.PReLU(channels)
        self.skip_proj = nn.Conv2d(feature_channels, channels, kernel_size=1)

        # gain head: [real transparency, imaginary phase correction] (v8 lesson:
        # the imaginary branch must be signed and zero-centred, never sigmoid).
        self.gain_head = nn.Conv2d(channels, 2, kernel_size=1)
        self.spp_head = nn.Conv2d(channels, 1, kernel_size=1)
        self.suppression_head = nn.Conv2d(channels, 1, kernel_size=1)
        self.transient_head = nn.Conv2d(channels, 1, kernel_size=1)
        self.df_head = nn.Conv2d(channels, 2 * self.history_taps, kernel_size=1)

        with torch.no_grad():
            self.gain_head.bias.zero_()
            self.gain_head.bias[0] = 1.5  # sigmoid(1.5) ~ 0.82 speech transparency
            self.spp_head.bias.fill_(1.5)  # starts mostly speech-present
            self.suppression_head.bias.fill_(-1.5)  # starts gently suppressing
            self.transient_head.bias.fill_(-1.5)
            nn.init.zeros_(self.df_head.weight)
            nn.init.zeros_(self.df_head.bias)

        self.DF_STATE_SIZE = 2 * self.history_taps * self.n_freq
        self.RNN_STATE_SIZE = self.recurrent_blocks * self.width * self.channels
        self.STATE_SIZE = self.DF_STATE_SIZE + self.RNN_STATE_SIZE

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> DeepFilterDualChannelNet:
        options = dict(config["model"])
        options.pop("architecture", None)
        options.pop("pretrained", None)
        options.pop("initialize_from", None)
        options.pop("reset_imaginary_branch", None)
        # Inherited chains carry legacy keys for other architectures; drop them.
        known = {
            "channels",
            "recurrent_blocks",
            "deep_filter_taps",
            "df_scale",
            "imaginary_scale",
            "min_mask_gain",
            "transient_gate",
        }
        options = {key: value for key, value in options.items() if key in known}
        return cls(
            n_fft=config["audio"]["n_fft"],
            sample_rate=config["audio"]["sample_rate"],
            **options,
        )

    # ------------------------------------------------------------------
    # Features, heads and the deep filter
    # ------------------------------------------------------------------

    def _features(self, primary: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
        """``(B, 2, T, F)`` spectra -> ``(B, 7, T, F)`` spatial features."""
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
        return torch.cat(
            (log_p, log_r, cos_ipd, sin_ipd, log_ratio, primary_real, primary_imag), dim=1
        )

    def _heads(self, features: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Decoded features -> ERB-domain ``(mask, deep-filter coefficients)``.

        The mask real part combines a speech-transparency gain and a noise
        suppression gain, arbitrated by the speech-presence estimate and
        bounded below by ``min_mask_gain``; a detected transient relaxes the
        suppression so impulsive events cannot delete speech.  The deep-filter
        coefficients are zero-centred tanh-bounded corrections.
        """
        gain_logits = self.gain_head(features)
        transparency = torch.sigmoid(gain_logits[:, 0:1])
        imaginary = self.imaginary_scale * torch.tanh(gain_logits[:, 1:2])
        spp = torch.sigmoid(self.spp_head(features))
        suppression = torch.sigmoid(self.suppression_head(features))
        transient = torch.sigmoid(self.transient_head(features))
        noise_gain = self.min_mask_gain + (1.0 - self.min_mask_gain) * suppression * (
            1.0 - self.transient_gate * transient
        )
        real = transparency * spp + noise_gain * (1.0 - spp)
        mask_erb = torch.cat((real, imaginary), dim=1)
        df_erb = self.df_scale * torch.tanh(self.df_head(features))
        return mask_erb, df_erb

    def _backbone(self, features: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """ERB features -> ``(decoded, encoder_tap_65, encoder_tap_33)``."""
        e1 = self.enc1_act(self.enc1_bn(self.enc1(features)))
        e2 = self.enc2_act(self.enc2_bn(self.enc2(e1)))
        h = e2
        for block in self.dual_path:
            h, _ = block(h, None)
        d1 = self.dec1_act(self.dec1_bn(self.dec1(h + e2)))
        d2 = self.dec2_act(self.dec2_bn(self.dec2(d1 + e1)))
        return d2 + self.skip_proj(features), e1, e2

    @staticmethod
    def _apply_deep_filter(
        masked: torch.Tensor, coefficients: torch.Tensor
    ) -> torch.Tensor:
        """Causal multi-frame complex filtering of the masked spectrum.

        ``masked`` ``(B, 2, T, F)`` and ``coefficients`` ``(B, 2*K, T, F)``
        (ordered ``c1_re, c1_im, c2_re, ...``) produce
        ``y[t] = m[t] + sum_k c_k[t] * m[t-k]``; history beyond the sequence
        is zero, matching the zero-initialised streaming state.
        """
        taps = coefficients.shape[1] // 2
        if taps == 0:
            return masked
        padded = F.pad(masked, (0, 0, taps, 0))  # left-pad the time dimension
        windows = padded.unfold(2, taps + 1, 1)  # (B, 2, T, F, taps+1); [..., j] = m[t+j-taps]
        output = masked
        for tap in range(1, taps + 1):
            window_index = taps - tap
            c_re = coefficients[:, 2 * tap - 2 : 2 * tap - 1]
            c_im = coefficients[:, 2 * tap - 1 : 2 * tap]
            w_re = windows[:, 0:1, :, :, window_index]
            w_im = windows[:, 1:2, :, :, window_index]
            output = output + torch.cat(
                (c_re * w_re - c_im * w_im, c_re * w_im + c_im * w_re), dim=1
            )
        return output

    def _enhance_spectra_ri(
        self, primary: torch.Tensor, reference: torch.Tensor
    ) -> torch.Tensor:
        """Full-sequence ``(B, 2, T, F)`` real/imag in -> ``(B, 2, T, F)`` out."""
        features = self.subband(self.erb.compress(self._features(primary, reference)))
        decoded, _, _ = self._backbone(features)
        mask_erb, df_erb = self._heads(decoded)
        mask = self.erb.expand(mask_erb)
        df_full = self.erb.expand(df_erb)
        masked = _apply_complex_mask(primary, mask)
        return self._apply_deep_filter(masked, df_full)

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
        del state  # the full-sequence path starts from zero history internally
        p_ri = torch.stack((primary.real, primary.imag), dim=1).permute(0, 1, 3, 2)
        r_ri = torch.stack((reference.real, reference.imag), dim=1).permute(0, 1, 3, 2)
        enhanced = self._enhance_spectra_ri(p_ri, r_ri)
        enhanced = enhanced.permute(0, 1, 3, 2)  # (B, 2, F, T)
        enhanced_spectrum = torch.complex(enhanced[:, 0], enhanced[:, 1])  # (B, F, T)
        return enhanced_spectrum, None

    def forward_audio(
        self,
        primary: torch.Tensor,
        reference: torch.Tensor,
        hop_length: int,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if hop_length < 1 or hop_length > self.n_fft:
            raise ValueError("hop_length must be in [1, n_fft]")
        primary_spectrum = frame_stft(primary, self.n_fft, hop_length)
        reference_spectrum = frame_stft(reference, self.n_fft, hop_length)
        enhanced, _ = self.forward_spectrum(primary_spectrum, reference_spectrum)
        return frame_istft(enhanced, self.n_fft, hop_length, primary.shape[-1]), enhanced

    # ------------------------------------------------------------------
    # Streaming interface: per-frame RI spectra + packed state vector
    # ------------------------------------------------------------------

    def initial_state(
        self, batch_size: int = 1, device: torch.device | None = None
    ) -> torch.Tensor:
        return torch.zeros(batch_size, self.STATE_SIZE, device=device)

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
        if primary_ri.shape[3] != 1:
            raise ValueError("streaming forward_ri processes exactly one frame per call")
        if state is None or state.shape[0] != primary_ri.shape[0] or state.shape[1] != self.STATE_SIZE:
            state = self.initial_state(primary_ri.shape[0], primary_ri.device)

        primary = primary_ri.permute(0, 1, 3, 2).contiguous()  # (B, 2, T=1, F)
        reference = reference_ri.permute(0, 1, 3, 2).contiguous()
        features = self.subband(self.erb.compress(self._features(primary, reference)))

        if self.history_taps:
            df_history = state[:, : self.DF_STATE_SIZE].reshape(
                -1, 2 * self.history_taps, self.n_freq
            )
        else:
            df_history = None  # pure pointwise mask; no deep-filter state
        block_state_size = self.width * self.channels
        rnn_states = [
            state[
                :,
                self.DF_STATE_SIZE
                + block * block_state_size : self.DF_STATE_SIZE
                + (block + 1) * block_state_size,
            ].reshape(-1, self.width, self.channels)
            for block in range(self.recurrent_blocks)
        ]

        e1 = self.enc1_act(self.enc1_bn(self.enc1(features)))
        e2 = self.enc2_act(self.enc2_bn(self.enc2(e1)))
        h = e2
        for index, block in enumerate(self.dual_path):
            h, rnn_states[index] = block(h, rnn_states[index])
        d1 = self.dec1_act(self.dec1_bn(self.dec1(h + e2)))
        d2 = self.dec2_act(self.dec2_bn(self.dec2(d1 + e1)))
        mask_erb, df_erb = self._heads(d2 + self.skip_proj(features))

        mask = self.erb.expand(mask_erb)  # (B, 2, 1, F)
        masked = _apply_complex_mask(primary, mask)
        if self.history_taps:
            df_full = self.erb.expand(df_erb)  # (B, 2*K, 1, F)
            enhanced_real = masked[:, 0:1]
            enhanced_imag = masked[:, 1:2]
            for tap in range(1, self.history_taps + 1):
                c_re = df_full[:, 2 * tap - 2 : 2 * tap - 1]  # (B, 1, 1, F)
                c_im = df_full[:, 2 * tap - 1 : 2 * tap]
                h_re = df_history[:, 2 * tap - 2 : 2 * tap - 1]  # (B, 1, F)
                h_im = df_history[:, 2 * tap - 1 : 2 * tap]
                enhanced_real = enhanced_real + c_re * h_re - c_im * h_im
                enhanced_imag = enhanced_imag + c_re * h_im + c_im * h_re
            enhanced = torch.cat((enhanced_real, enhanced_imag), dim=1)
        else:
            enhanced = masked

        newest = masked.reshape(-1, 2 * self.n_freq)  # [re(F), im(F)] of frame t
        if self.history_taps:
            trimmed = state[:, : 2 * (self.history_taps - 1) * self.n_freq]
            next_df_history = torch.cat((newest, trimmed), dim=1)
        else:
            next_df_history = state[:, :0]
        next_rnn = torch.cat(
            [block_state.reshape(-1, self.width * self.channels) for block_state in rnn_states],
            dim=1,
        )
        next_state = torch.cat((next_df_history, next_rnn), dim=1)

        enhanced_ri = enhanced.permute(0, 1, 3, 2).contiguous()  # (B, 2, F, 1)
        return enhanced_ri, next_state

    def forward(  # type: ignore[override]
        self,
        primary_ri: torch.Tensor,
        reference_ri: torch.Tensor,
        state: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        return self.forward_ri(primary_ri, reference_ri, state)
