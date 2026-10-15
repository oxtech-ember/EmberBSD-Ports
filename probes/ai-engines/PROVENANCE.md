# AI engine source and patch provenance

The current source profile uses **ONNX Runtime 1.31.0** and the
[canonical package patches and feature file](../onnxruntime/PROVENANCE.md).
Its updated runtime archive is pinned in [sources.tsv](sources.tsv).
The table and local adaptation descriptions below preserve the historical
**1.30.0** run in [NATIVE.md](NATIVE.md). The old ONNX patch copies are not
applied by the current builder. The historical 1.30.0 runtime archive SHA256
is `f6681ecbddf53898adf0cc9e8e9e84657485b84d2eca3c8aa353de6d7dd417ef`.

Checked against official upstream release metadata on **2026-10-07**.
The immutable archives and SHA256 values are in [sources.tsv](sources.tsv).
Original licenses, author names and source identifiers are unchanged.
Our shell/C/C++ helpers are [MIT-licensed](LICENSE) and AI-assisted.
Local ONNX Runtime changes preserve the patched files' licenses: MIT, except
the Apache-2.0 `threadpool.cc`; the added `netbsd_cpu.h` helper is MIT.
The RNNoise patch retains its upstream author and license.
The local ONNX Runtime patches have not been submitted upstream.

| Component | Official release | Revision | License |
|---|---|---|---|
| ONNX Runtime | [1.30.0](https://github.com/microsoft/onnxruntime/releases/tag/v1.30.0) | `f2c39fe2f838cf35ce7da92824f5a5e3ee6e88a7` | MIT, with `ThirdPartyNotices.txt` |
| ncnn | [20260526](https://github.com/Tencent/ncnn/releases/tag/20260526) | `e54f7b1f88434e1d844ea0551b880a1cfb079ce1` | BSD-3-Clause plus notices in `LICENSE.txt` |
| RNNoise | [0.2](https://github.com/xiph/rnnoise/releases/tag/v0.2) | `904a876dce1f9ab8860c0a5000ed151f9f6eef58` | BSD-3-Clause, `COPYING` |
| Silero VAD | [6.2.3](https://github.com/snakers4/silero-vad/releases/tag/v6.2.3) | `5cd7945676eb32225748052e2e6a0580e4686a08` | MIT, Silero Team |
| Eigen | [5.0.1](https://gitlab.com/libeigen/eigen/-/releases/5.0.1) | release archive pinned by SHA256 | MPL-2.0 and `COPYING*` notices |

RNNoise 0.2 remains the latest tagged upstream release at this check. Its
release archive includes `src/rnnoise_data.c`; this recipe neither trains a
model nor downloads separate weights. Silero's `silero_vad.onnx` and
`tests/data/test.wav` come unchanged from its release archive. Their individual
hashes are in [models.tsv](models.tsv). The VAD state/context protocol follows
the upstream ONNX wrapper; the new C++ contract is written for this probe.

## ONNX Runtime dependencies

[dependencies.tsv](dependencies.tsv) adds SHA256 checks to the selected
upstream `cmake/deps.txt` inputs. Their upstream SHA1 values were also verified
when preparing the manifest. The CPU profile consumes Abseil 20250814.0,
protobuf 33.6, ONNX 1.22.0, date 3.0.1, FlatBuffers 23.5.26, JSON 3.11.3,
Microsoft GSL 4.2.1, Boost mp11 1.82.0, RE2 2024-07-02 and SafeInt 3.0.28.
These are ONNX Runtime's internal source dependencies; the public installed
interface remains its C/C++ API. No second system protobuf, interpreter,
FlatBuffers or Eigen package is installed. Eigen 5.0.1 is shared in version
with the robotics profile instead of the older upstream Eigen archive.

Upstream ONNX Runtime applies its own compatibility patches to these sources.
Those patches remain under their original paths in the pinned source archive.
The installed `ThirdPartyNotices.txt` and copied dependency license files keep
this attribution. This profile does not claim that every internal upstream
component is independently the latest release.

## RNNoise upstream backport

[rnnoise-upstream-arm-build.patch](patches/rnnoise-upstream-arm-build.patch)
is the unchanged upstream commit
[372f7b4b76cde4ca1ec4605353dd17898a99de38](https://github.com/xiph/rnnoise/commit/372f7b4b76cde4ca1ec4605353dd17898a99de38),
by Timothy B. Terriberry, 2024-04-15. Patch SHA256:
`c491dfba7784ba027f7293259652053bb63bc834aae693269e4b5cf1dda54b05`.
It was committed after the 0.2 release. It replaces the missing Opus header
and macros with RNNoise equivalents and fixes related x86 includes.
The unpatched release fails compiling its NEON code. Native compiler evidence
records the missing header; the patched ARM64 library and 144,000-sample
installed consumer passed in the EMBER64 VM.
This is an accepted upstream fix backported unchanged, not a new local fix.

## Historical 1.30.0 local adaptation

[onnxruntime-netbsd-affinity.patch](patches/onnxruntime-netbsd-affinity.patch)
uses NetBSD's dynamically allocated `cpuset_t` and `pthread_setaffinity_np`
instead of Linux `cpu_set_t`, `CPU_SET` and `SYS_gettid`. It checks allocation,
CPU IDs and affinity errors, preserves error logging, and destroys the set.
Other platforms retain their existing path. The basis is NetBSD's
[cpuset(3)](https://man.netbsd.org/cpuset.3) and
[affinity(3)](https://man.netbsd.org/affinity.3) interfaces.
Unprivileged affinity may be denied by system policy; the standard test
uses one explicit inference thread and does not change that policy.
The separate optional test passed with two vCPUs and permission to bind
threads: ORT's worker masks matched CPU 0 and CPU 1, with correct inference
results. This validates the adaptation's successful affinity path, not
multi-core inference throughput or every failure branch.

[onnxruntime-netbsd-thread-id.patch](patches/onnxruntime-netbsd-thread-id.patch)
uses NetBSD `_lwp_self()` for logging thread IDs instead of Linux
`SYS_gettid`. A native compiler probe confirms that `SYS_gettid` is absent,
while the native LWP call compiles and returns a positive thread ID.
The public logging API and behavior on other systems remain unchanged.

[onnxruntime-netbsd-isnan.patch](patches/onnxruntime-netbsd-isnan.patch)
uses the standard C++ `std::isnan` name for NetBSD's BFloat16 constructor.
The native build fails because `::isnan` is unavailable in this C++ context.
A source-header contract checks NaN, infinity, a negative finite value and
zero; it fails to compile before the patch. Other platforms retain their
existing host/device path.

[onnxruntime-netbsd-cpu-id.patch](patches/onnxruntime-netbsd-cpu-id.patch)
uses NetBSD's [_lwp_ctl(2)](https://man.netbsd.org/_lwp_ctl.2) communication
area for the profiling CPU identifier. Linux `sched_getcpu()` is unavailable.
The kernel supplies the current CPU in `lc_curcpu`; API failure returns -1,
preserving the unknown/error value. A source-header contract checks 1,000
current-CPU readings each in the main thread and a worker.

[onnxruntime-installed-eigen.patch](patches/onnxruntime-installed-eigen.patch)
restores the intended use of the existing preinstalled-Eigen build option.
The unpatched option is declared but does not alter dependency selection.
The patch selects the installed Eigen CMake package and avoids downloading
or exposing another Eigen version. It is a build integration change, not
an algorithm or Eigen source change.

[onnxruntime-single-pointer-assign.patch](patches/onnxruntime-single-pointer-assign.patch)
expresses single output/device pointers with `vector::assign(count, value)`
rather than a one-element array range or initializer list. These forms
produce the same one-element vectors. GCC 12.5 at `-O3` diagnoses the original
inlined range copies with `-Warray-bounds`. The actual translation units fail
before this patch and compile after it; warning-as-error checks remain enabled.
This is compiler compatibility, not validation of the GroupQueryAttention
graph rewrite or model-package device selection.

[onnxruntime-cpu-fused-helper.patch](patches/onnxruntime-cpu-fused-helper.patch)
keeps the existing `fused_activation.cc` helper in the CPU library when contrib
operators are disabled. Standard CPU FP16 Conv calls this helper too; the
unpatched profile fails its strict final link with an undefined
`GetFusedActivationAttr`. This source file registers no contrib operators.
Its implementation and standard operators remain unchanged, and
`--no-undefined` stays enabled. FP16 numerical behavior is not separately
validated by the float32 inference contracts.

## Evidence boundary

Archive hashes, model/fixture hashes and shell syntax have been checked.
[NATIVE.md](NATIVE.md) records native builds, installed linkage, seven CTest
contracts, source-header regressions and the optional affinity checks in an
AArch64 EMBER64 VM. All inference uses CPU execution. Physical boards,
accelerators, live audio, quality evaluation and sustained operation remain
unverified.
