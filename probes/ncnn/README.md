# Installed ncnn CPU runtime

This profile provides Tencent **ncnn 20260526** with GCC 16.2.0.
The shared C/C++ API executes a small convolutional network in AArch64 EmberBSD.
Independent scalar calculations check every logit and probability.
The [Examples application](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/ai/ncnn-cpu)
owns the model generator and end-user programs.

The ordinary [pkgsrc recipe](../../pkgsrc/local-ai/ncnn) owns the shared SDK.
Source pins are in [sources.tsv](sources.tsv) and the installed
[SOURCE](../../pkgsrc/local-ai/ncnn/files/SOURCE) receipt.
The release remains the latest stable upstream release checked on 2026-10-15.
Its revision is `e54f7b1f88434e1d844ea0551b880a1cfb079ce1`.
See [VALIDATION.md](VALIDATION.md) for evidence and limits.

## Profile

The profile installs headers, `libncnn.so.1`, CMake exports and `ncnn.pc`.
AArch64 uses baseline ARMv8-A NEON. The native x86-64 memory control uses SSE2.
Runtime ISA dispatch, later ARM/x86 extensions, OpenMP, Vulkan, tools,
benchmarks, examples and Python bindings are disabled.
POSIX synchronization remains enabled. Operator loops run serially.
Two application threads are tested with separate network instances.
Upstream Release optimization flags remain enabled.
No source generator needs Python for this selection.

Six canonical [patches](../../pkgsrc/local-ai/ncnn/patches) fix CPU discovery,
first-use synchronization, C wrapper allocation failures, retained matrix
weights, callback failures and strict C type visibility.
[Patch provenance](tests/upstream/PATCHES.md) describes their contracts.
These are local AI-assisted adaptations, not accepted upstream patches.
Original Tencent and third-party notices remain in the installed package.

## Cross build

Use a coherent EmberBSD sysroot and GCC16 target libraries.
Do not replace the fork's base with upstream NetBSD release sets.
The build requires CMake, Ninja, GNU patch, curl, tar and SHA tools.
Run on a Linux x86-64 host with GCC 16.2.0 available for native controls.
The script requires new absolute output paths without whitespace.

```sh
sh probes/ncnn/build-runtime.sh cross /absolute/gcc16-toolchain \
  /absolute/emberbsd-sysroot /absolute/archives /absolute/ncnn-cross
```

The installed target SDK is `ncnn-cross/stage/usr/pkg`.
The script verifies the source archive and applies the canonical patches.
It retains the toolchain file, compilation database and build logs.
`JOBS=2` is the default. Four total jobs fit the accepted cloud host.
Use `native /absolute/native-gcc16-prefix` as the first two arguments for
the Linux control. Its installed prefix is `NEW_OUTPUT/install`.

For ordinary native pkgsrc builds, export the pinned tree with
`scripts/prepare-pkgsrc.sh` and build `local-ai/ncnn` with the GCC16 profile.
The recorded cloud acceptance creates a real package from the cross stage.
It does not establish a complete native pkgsrc bootstrap.

## Installed consumers and tests

CMake uses `find_package(ncnn 20260526 EXACT CONFIG REQUIRED)`.
The runtime and pkg-config version string is `1.0.20260526`.
The CMake imported target supplies flat includes such as `<c_api.h>`.
The pkg-config include root supports `<ncnn/c_api.h>`.
The complete C example also builds with actual pkg-config flags.
Neither normal application includes runtime source-tree headers.

- [Unchanged upstream tests and CPU controls](tests/upstream/README.md).
- [C API allocation, lifetime and callback controls](tests/c-api-allocations/README.md).
- [Strict C headers and C/C++ layout controls](tests/c-api-header/README.md).

On an EmberBSD AArch64 guest with matching GCC16 libraries and pkgtools,
`run-target.sh PACKAGES TESTS NEW_RESULTS` installs the cross package,
executes the installed applications and controls, removes it, reinstalls it
and checks the results again. Stage the documented test executables and model
files below `TESTS`; install the two example applications under `/usr/pkg/bin`.
Keep the independent checker separate from the ncnn runtime.

NetBSD affinity, heterogeneous core topology and optional ARM feature discovery
remain unsupported. Mapped-file loading remains unsupported on NetBSD;
the tested path uses ordinary file loading.
The fixed wrapper handles failed C allocations. Later C++ `new` failures
retain upstream exception behavior. Arbitrary untrusted models, every operator,
accuracy, real-time performance, boards, training and accelerators are unverified.
