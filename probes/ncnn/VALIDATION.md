# ncnn GCC16 CPU validation

The accepted release is **20260526**, published on 2026-05-26.
The latest stable upstream release was checked on 2026-10-15.
Revision: `e54f7b1f88434e1d844ea0551b880a1cfb079ce1`.
Source archive SHA256:
`da1ade826bc22858a9fb87ae052789bbd614d042b3ec2c22e6544ca83db6bc04`.
The six canonical patches reconstruct both complete production source trees
exactly: 4,068 entries, with matching bytes, types, modes and links.

## Installed EmberBSD package

GCC 16.2.0 cross-builds a shared baseline AArch64 NEON runtime.
The kernel, base and sysroot come from EmberBSD revision
`267ee85eee1027198175809a8b7b0572df36ad1e`.
The ABI triplet is `aarch64--netbsd`; C++ uses `libstdc++.so.7`.
The acceptance VM has two Cortex-A72 CPUs and 2 GiB RAM under QEMU TCG.
It uses a standalone 256-MiB FFSv2 image and no target compiler.

The guest creates `ncnn-20260526.tgz` with real pkgtools from the cross stage.
It installs the package, checks all 39 files and symlinks, runs the tests,
removes it, checks header/library/metadata removal, reinstalls it and repeats
the installed consumers. All payload bytes, modes and links match the stage.
The GCC16 runtime is already installed in the image.
This proves cross-package acceptance, not a full native pkgsrc build.
The first accepted run shut down and unmounted cleanly at about 183 seconds.
This is scenario duration, not a performance measurement.

## Neural-network answers

The installed C and C++ examples load a six-layer FP32 CNN:
5x5x2 input, valid 3x3 convolution with three outputs, ReLU, global average
pooling, a three-output dense layer and softmax.
Its weights are original deterministic synthetic data, not a trained model.
Graph SHA256: `a2894f77214ce944ffd876f1135e3226a7c02bba11d714cb8aaa4bf75cad19c7`.
The 284-byte weight file SHA256 is
`bf046c98094830b862f22d50ce881cd10dd5299d5ec52cd921b7deb62ab98e2d`.

- Seeds 0, 17 and 1023 use 1/3/32 inputs and 1/100/4 repetitions.
  Each API produces 429 rows per installation, with six scalar outputs per row.
- A separate scalar double-precision program checks every logit, probability,
  row identity, order and count at tolerance `1e-5`, scaled above magnitude one.
  It does not include ncnn headers, link ncnn or read the generated weights.
  The host independently checks the exported guest CSVs.
- C and C++ CSVs match. A third complete C consumer compiled with the actual
  installed `ncnn.pc` flags matches the CMake C consumer.
  Outputs also match after package reinstallation.
- Both wrappers reject missing/malformed graphs, missing/truncated/nonfinite
  weights, unknown blobs and invalid numeric bounds while preserving output.
  The direct C API separately rejects bad graph magic, absent graph/weights
  and truncated weights. Wrapper validation is not an arbitrary-model guarantee.
- Two application threads create and destroy 16 independent networks and
  compare 128 inference runs, 768 scalar values, against sequential results.
  This prewarmed control checks lifetimes and consistency.
  It does not replace the separate first-use race regression.

## Upstream and source regressions

Eight unchanged upstream programs pass against the installed shared runtime:
C API, ParamDict, expression, ReLU, pooling, InnerProduct, softmax and convolution.
Upstream `testutil.cpp` compares optimized operators to reference implementations.
The convolution program covers 360 shape/kernel configurations before its
per-option variants. These programs do not represent every ncnn operator.

Actual baseline and final `cpu.cpp` controls run in the two-CPU guest.
The baseline reports one CPU and fails the comparison; the fixed source
reports two and passes. Affinity remains an explicit unsupported failure.
Eight simultaneous first callers exercise the real `pthread_once` path.
On native Linux, DRD finds 16,441 baseline errors in 76 contexts and zero
unsuppressed errors after the fix. Shipped default suppressions remain enabled;
no custom suppression or annotation is used.
Raw Helgrind retains seven reports in one glibc pthread_once publication context.
A real-primitive control documents that tool limit. Helgrind is not declared clean.

Actual `c_api.cpp` controls cover 13 direct wrapper allocation failures.
The original crashes are detected in child processes. The fixed factories
return null, release preallocated layers, or log failed void registration
without modifying its list. Registration rejection and retry are checked.
Later C++ allocation exceptions retain upstream policy.

The original matrix-array adapter retains a destroyed local vector.
Memcheck detects the first-load use-after-free. The fixed adapter retains
six arrays and validates 48 values after original handles are destroyed.
1D/2D/3D, empty/exhausted arrays and user callback dispatch pass.
Eighteen callback controls check nonzero status, partial outputs, null weights,
missing outputs and zero-sized arrays. Thirteen original callback failures
are detected as crashes or changed destination outputs.

Strict GCC16 C11 through actual pkg-config includes exposes exactly four
ignored type-visibility errors in the original header. The fixed C header
and both C++ headers compile strictly. All four types retain identical sizes,
alignments and field offsets: 248 serialized ABI bytes.
Native output, AArch64 object data and three running target layout programs agree.
Function visibility remains public with `-fvisibility=hidden`.

## Native memory and source analysis

The Linux x86-64 control uses the same patches and a baseline SSE2 backend.
Native CTest groups pass 3/3 application, 10/10 upstream/CPU and 5/5 C API tests.
There are 45 strict Memcheck processes: 28 example scenarios, three header
layout programs and 14 upstream/CPU/C API/pkg-config programs.
Every accepted process has zero errors and no heap blocks remaining at exit.
No custom Memcheck suppression is used. Intentional baseline failures are
separate negative controls and are not described as clean memory checks.
Native memory results are separate from actual EmberBSD execution.

Cppcheck 2.17.1, Clang Static Analyzer 19.1.7 and GCC16 path analysis use
recorded source/header/macro hashes and actual target compilation databases.
All 28 upstream/final runtime Clang contexts complete with zero stale inputs.
The final CPU/C API analysis has no finding. Inherited generic/ARM convolution
dead stores remain documented. Partial Cppcheck removes all 60 repeated OOM
warnings and the callback null-output warning after the patches.
Inherited raw-storage views and allocator pointer-size notices remain diagnosed.

Full C++ Cppcheck imports/preprocessed inputs fail on GCC16 type_traits syntax.
Its raw database import omits system headers; its experimental Clang AST
import fails on scratch-space locations. Those are incomplete analysis paths.
The examples and header controls also pass 22 Clang contexts and eight C
GCC16 path-analysis contexts. Complete C-header Cppcheck preserves inherited
inline-helper style notices; C++ array/type_traits parsing remains incomplete.
There is no claim of globally clean source analysis.

CPU inference in this VM does not establish model accuracy, live capture,
parallel operator throughput, hardware acceleration, physical-board behavior
or real-time constraints. NetBSD mmap loading, affinity, heterogeneous topology
and optional ARM feature discovery remain unsupported.
