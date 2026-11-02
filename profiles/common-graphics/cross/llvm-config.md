# Target LLVM metadata for cross builds

Cross packages need a build-host `llvm-config` that reports the installed
EmberBSD target LLVM package. The host LLVM helper describes the wrong ABI, and
the target executable cannot run on the build host.

The common graphics cross profile includes
[`lang/llvm/cross-llvm-config.mk`](../../../pkgsrc/lang/llvm/cross-llvm-config.mk).
Its `pre-configure` target runs the single supported producer from installed
`llvm` and `llvm-devel` package metadata. It uses the selected native LLVM
compiler and Support, TargetParser and Demangle archives. It needs neither the
LLVM source archive nor target/native LLVM CMake build trees. Normal package
builds, including Mesa, invoke this automatically.

The producer validates the installed version, target triple, assertion/RTTI
settings, target library and `/usr/pkg` prefix. It rejects native compiler,
linker or LLVM inputs outside the selected host prefix, as well as metadata
that retains temporary source/build paths. The output lives under the package
work root and is regenerated when installed metadata or selected native inputs
change. It is build metadata, not a target package or a second LLVM provider.

For direct diagnosis, the current CLI is:

```sh
EMBERBSD_HOST_PREFIX=/absolute/host-pkg-llvm \
EMBERBSD_NATIVE_LD=/absolute/host-pkg-llvm/bin/ld.lld \
NATIVE_CXX=/absolute/host-pkg-llvm/bin/clang++ \
/absolute/host-pkg-llvm/bin/python3.15 -B \
    /absolute/pkgsrc/lang/llvm/files/cross-llvm-config.py \
    /absolute/work/llvm-config/helper/bin/llvm-config \
    /absolute/work/llvm-config /absolute/pkgsrc /absolute/sysroot
```

The `CONFIG` argument must be `WORK/helper/bin/llvm-config`; the wrapper
serializes generation for that work root and reuses it only while its installed
inputs match. To validate an existing helper against the currently installed
sysroot without rebuilding it:

```sh
/absolute/host-pkg-llvm/bin/python3.15 -B \
    /absolute/pkgsrc/lang/llvm/files/cross-llvm-config.py \
    --validate /absolute/work/llvm-config/helper/bin/llvm-config \
    /absolute/sysroot
```

A helper tied to an earlier sysroot prefix is rejected. Run the producer again
with the new sysroot to create a helper for its installed prefix. Do not copy a
helper between sysroots or substitute a host `llvm-config`.

The focused regression is
`profiles/common-build-tools/tests/llvm-config-installed-metadata.py`. It checks
metadata normalization and rejects wrong versions, targets, prefixes,
relocation and a native compiler outside the selected prefix. It also verifies
that changing installed metadata changes the producer cache identity. The
normal pkgsrc `pre-configure` path remains the production integration check.

`adapt-llvm-config.py` is a separate compatibility adapter for an existing
upstream-built helper; it is not part of this producer or the normal pkgsrc
path. Its admission checks are covered by the `llvm-admission` tests.
