# Native AArch64 acceptance

This is the historical ONNX Runtime **1.30.0** source-probe record.
The current build uses the [canonical 1.31.0 provider](../onnxruntime/README.md).
The original measurements and output hashes below remain unchanged.

Validated on **2026-10-07 (UTC+03:00)** in a disposable VM. This is an
installed C/C++ source-probe result, not a binary distribution or board claim.
Source versions, licenses, immutable archives and adaptation provenance are
in [PROVENANCE.md](PROVENANCE.md). The recipe and contracts are owned by
EmberBSD-Ports.

## Platform and build

- NetBSD 11.0 AArch64 userland with the EmberBSD `EMBER64` kernel from
  source revision `b4f718dabd085ed117a24f84d8558e4a43091dc0`.
- QEMU's actual `-kernel` boot image SHA256:
  `49395ea85b1c31e8c9eb41dce5bb29c2636ecc1c17785370375a7fb517cc8d2a`.
- Initial RNNoise/ncnn builds: one vCPU, 3 GiB RAM, one build job.
  ORT started there, then continued with two vCPUs, 4 GiB RAM and two jobs.
  Final acceptance used the latter VM; ordinary inference used one thread.
- GCC 12.5.0 (`nb3 20260326`), CMake 4.3.3, Ninja 1.13.2,
  Python 3.13.14 for upstream generators, pkg-config 2.5.1.
- Release C++20 CPU shared-library profile, installed Eigen 5.0.1;
  contrib/ML operators, training, Python bindings, telemetry, cpuinfo,
  XNNPACK, KleidiAI, SVE and accelerator providers disabled.
  The installed provider registry contained only `CPUExecutionProvider`.

ORT completed through native fixes and Ninja continuations. No clean-build
duration is reported. CMake regeneration after adding the required CPU helper
also rebuilt internal dependencies: Ninja reported changed command lines.
The selected profile remained unchanged; inspected ORT and protobuf commands
use C++20. The recipe explicitly sets it to match those final commands.
Warnings remain errors and the shared-library link retains `--no-undefined`.

The largest recorded build-stage maximum RSS was **2,732,124 KiB**.
`time -l` reports a process maximum, not the sum of parallel workers.
One observation showed compiler RSS values of 2,366,612 and 830,824 KiB
simultaneously. No OOM occurred. Use 4 GiB RAM and `JOBS=1` for headroom.
Final work tree: **1,810,632 KiB**, including archives, sources and build
products; private installation: **45,832 KiB**. These are measured sizes,
not upper bounds for another configuration or toolchain.

## Acceptance results

The installed CMake/pkg-config consumers built with `-Wall -Wextra -Werror`.
All **7/7 CTests passed** in 0.61 seconds:

| Contract | Result |
|---|---|
| ONNX Runtime 1.30.0 | Exact Add/Relu values over 100 runs; malformed model, wrong shape and missing input rejected |
| ncnn 20260526 | Exact Add/Relu and dense-weight results; 100 runs; malformed graph and unknown blobs rejected |
| RNNoise 0.2 | 144,000 input/output samples; finite output/probability; streaming continuity; silence tail; incomplete and NaN inputs rejected |
| Silero VAD 6.2.3 | 1,008,000 samples; 1,969 frames; arbitrary chunk continuity; final padding; silence boundaries; PCM/rate errors rejected |
| Silero invalid model | Rejected non-model input |
| Silero invalid WAV | Rejected malformed audio input |
| Build guards | Existing work preserved; invalid job count rejected; all 15 corrupt archive cases rejected before extraction |

Silero reported 1,450 speech frames, first 1.024 s and last 61.024 s at the
fixed 0.5 frame threshold. These are contract outputs for the pinned fixture,
not speech-detection accuracy measurements.

Two source-header contracts passed: BFloat16 NaN/infinity/finite/zero
conversion, and 1,000 current-CPU readings each from main and worker threads.
The optional CPU-ID test also followed worker affinity from CPU 0 to CPU 1.
The optional installed ORT test created two intra-op threads, verified the
actual worker masks through `pthread_getaffinity_np`, checked the graph's
exact output and observed no runtime error logs. Both affinity checks ran
with permission to bind threads. Permission-denied behavior is not a PASS.

`ldd` resolved every engine from the private installation. Other dependencies
were NetBSD base libraries: libc, libm, libpthread, librt, libstdc++, libgcc_s,
libexecinfo and libelf. No missing library was reported. ORT emitted
`Unknown CPU vendor. cpuinfo_vendor value: 0` with cpuinfo disabled; no
vendor-specific tuning is established by these checks.

| Standalone contract | Wall time | Maximum RSS | VM |
|---|---:|---:|---|
| RNNoise | 0.03 s | 5,044 KiB | 1 vCPU / 3 GiB |
| ncnn | below 0.01 s timer resolution | 3,720 KiB | 1 vCPU / 3 GiB |
| ONNX Runtime | 0.01 s | 19,132 KiB | 2 vCPU / 4 GiB |
| Silero | 0.40 s | 65,160 KiB | 2 vCPU / 4 GiB |
| ORT affinity | 0.01 s | 17,740 KiB | 2 vCPU / 4 GiB |

These short VM measurements are not physical-board performance, sustained
load, real-time audio, denoising quality or multi-core throughput results.
FP16 Conv numerical behavior and model-package/GQA semantics were not
separately exercised; their portability regressions are compilation/linkage.

## Captured installed outputs

SHA256 values identify the actual unstripped outputs from this run. They do
not promise byte-identical results across build paths or toolchains.

| File | SHA256 |
|---|---|
| `libonnxruntime.so.1.30.0` | `5db7fc7b74a0af4801581b7ca2dc8d2f6c147c3c01e2adc674650e409c9a38e3` |
| `libonnxruntime_providers_shared.so` | `87e57fd08e99ab34f3dca86fe5f59291f5aa60b8af67ba4f8390a75f4135e545` |
| `libncnn.so.1.0.20260526` | `fee12034c1446a8b6b8222a22492a85967b6d20e60ed392f4fedb61e706edf90` |
| `librnnoise.so.4.1` | `8ff27ed2f5a4f0598b1df4386dea345b6fccd42d82a9bdf8fcbff23c2116af57` |
| `silero_vad.onnx` | `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3` |
| `silero-test.wav` | `89f17d9c94c4b31eb320f424628bcbc920abaddbee6e2760fd868bfb1d9a2e47` |
