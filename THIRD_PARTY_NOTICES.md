# Third-party research and implementation notice

The VoxShield GTCRN-derived architecture is informed by the official implementation of:

> Xiaobin Rong, Teng Zhang, and Yuxuan Hu, “GTCRN: A Speech Enhancement Model Requiring
> Ultralow Computational Resources,” ICASSP 2024.

Official project: https://github.com/Xiaobin-Rong/gtcrn

VoxShield recipe v3 adapts the complete architecture and streaming design from
the official repository pinned at commit
`502ebfab64da7c4a9af78dcb9c6ceef1ebb01c73`. The upstream DNS3 and VCTK-DEMAND
checkpoints are retained under `external/gtcrn_official/checkpoints` for
reproducible initialization and comparison. Final VoxShield checkpoints must be
fine-tuned and evaluated on the user-supplied data.

The upstream implementation is distributed under the MIT License. VoxShield does not claim
upstream benchmark results as its own results.

Copyright (c) 2024 Rong Xiaobin

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the “Software”), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT
OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
