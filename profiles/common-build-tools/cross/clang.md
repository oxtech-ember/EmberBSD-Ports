# Cross-building the current Clang package

The Clang 23.1.4 recipe uses target LLVM headers, libraries and CMake exports
from the common EmberBSD sysroot. Only generators and build interpreters run
on the development host. This path supports the complete QtTools dependency;
it does not replace QDoc or remove Qt Designer from the package.

## Matching host tools

First build the native LLVM tools with `build-llvm-native.py`, as described in
[the LLVM family](../llvm-family.md#cross-build-and-accepted-core). Then build
only the matching native Clang generator from the same verified archive:

```sh
export EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK
HOST_PYTHON=/absolute/host-python3.15 JOBS=3 \
    python3 -B profiles/common-build-tools/cross/build-clang-native.py \
    /absolute/llvm-project-23.1.4.src.tar.xz /absolute/native-llvm \
    /absolute/new-clang-host-work /absolute/cmake /absolute/ninja
```

The script verifies the source SHA256 and native LLVM version, and records
inputs and output hashes. Reusing native LLVM avoids building another LLVM
library stack. Disabling tests in this generator-only build does not change
the target package's tests, static archives or supported backends.

Add these inputs to the private MAKECONF used with the
[common cross configuration](README.md):

```make
EMBERBSD_LLVM_NATIVE_TOOLS=/absolute/native-llvm/bin
EMBERBSD_CLANG_TABLEGEN=/absolute/new-clang-host-work/native/bin/clang-tblgen
EMBERBSD_CROSS_BUILD_PYTHON=/absolute/host-python3.15
EMBERBSD_CROSS_BUILD_PERL=/absolute/host-perl5.44
```

Clang and LLD find the target LLVM with a build-host llvm-config.
Before configure, `lang/llvm/cross-llvm-config.mk` makes it from the
lang/llvm build tree. The dependency order builds lang/llvm first; keep its
WRKDIR until Clang and LLD are configured. The step builds the native
generator tree with `build-llvm-native.py` and then runs
`scripts/build-llvm-config.py`. Both write below
`${WRKOBJDIR}/.emberbsd-cross/<target triple>`, and later builds reuse the
sealed result. Set `EMBERBSD_CROSS_LLVM_CONFIG` to use a different one.

That llvm-config is the native metadata executable derived from the
actual target LLVM build, following the
[metadata workflow](../../common-graphics/cross/llvm-config.md). It is neither
the target ELF executable nor the host LLVM installation's metadata.
The recipe rejects absent or incorrect TableGen versions. The explicit
`LLVM_TABLEGEN_EXE` setting is required by standalone Clang's CMake logic.

Build Perl executes only on the host. Installed scan-build tools retain a
normal target Perl >=5.44 dependency and `/usr/pkg/bin/perl` shebangs.
Do not bypass that runtime dependency to accept the final package.

## Native compiler defaults

The [runtime config helper](../../../pkgsrc/lang/clang/files/llvm-runtime-config.sh)
writes the native Clang configuration for the target triple reported by the
target LLVM metadata, in cross and native builds alike. It selects
compiler-rt, libunwind and libc++, the runtimes the SDK cross toolchain
uses; libc++, libunwind and the CRT files come from the base system and the
builtins from lang/compiler-rt. Native Clang needs no GCC.

These checks validate inputs and installed paths. They do not substitute for
running Clang on the target and checking actual C/C++ compilation, CRT/link
selection, dynamic loading and the existing SDK opt-out behavior.

## Checks and current boundary

The complete Clang 23.1.3 package passes cross-build and ordinary package
checks with matching LLVM 23.1.3 and was replaced normally in the build sysroot
on 2026-10-12. SHA256:
`e8f81bef5038ace7ca7c4dda5fe5cbb87c8a45e7e88a21f47a605c5c58ad22ce`.
The following 23.1.2 input-test receipt remains historical.


```sh
sh profiles/common-build-tools/tests/clang-runtime-config.sh /absolute/new-check /absolute/host/bin/clang
BMAKE=/absolute/host/bin/bmake \
    sh profiles/common-build-tools/tests/clang-cross-inputs.sh \
    /absolute/export /absolute/private-mk.conf /absolute/new-input-check
```

On 2026-10-12 the host generator built from the verified LLVM 23.1.2 archive.
The metadata helper passed with real GCC16 and target LLVM metadata. Fixture
checks reject wrong versions, ABI, missing files, escaped paths and duplicate
headers. Real pkgsrc evaluation passes valid inputs, rejects missing/wrong host
tools, and preserves target Perl, installed shebangs, static libclang and tests.
The complete target package also builds and passes ordinary dependency,
manifest, interpreter, permissions, PIE, RELRO, RPATH and work-reference checks.
It includes static libclang, the new scalable-analysis tools and libraries,
and explicitly enabled HLSL headers with the clang-dxc entry point.
The obsolete offload-packager alias is owned by LLVM, matching upstream.
Options.inc now belongs to clang/Options; generated Sema headers are preserved.
The source contract covers 119 Clang and 11 LLVM generated declarations.

Installed Clang execution remains pending. Full QtTools cross-packaging against
LLVM/Clang 23.1.3 passes; its installed GUI/runtime acceptance remains pending.
Cross-package success does not establish an accelerated Plasma session.
