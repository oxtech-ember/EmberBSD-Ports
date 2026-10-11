# Cross-building the current Clang package

The Clang 23.1.2 recipe uses target LLVM headers, libraries and CMake exports
from the common EmberBSD sysroot. Only generators and build interpreters run
on the development host. This path supports the complete QtTools dependency;
it does not replace QDoc or remove Qt Designer from the package.

## Matching host tools

First build the native LLVM tools with `build-llvm-native.sh`, as described in
[the LLVM family](../llvm-family.md#cross-build-and-accepted-core). Then build
only the matching native Clang generator from the same verified archive:

```sh
HOST_PYTHON=/absolute/host-python3.14 JOBS=3 \
    sh profiles/common-build-tools/cross/build-clang-native.sh \
    /absolute/llvm-project-23.1.2.src.tar.xz /absolute/native-llvm \
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
EMBERBSD_CROSS_LLVM_CONFIG=/absolute/target-metadata/bin/llvm-config
EMBERBSD_CROSS_BUILD_PYTHON=/absolute/host-python3.14
EMBERBSD_CROSS_BUILD_PERL=/absolute/host-perl5.44
```

The llvm-config here is the native metadata executable derived from the
actual target LLVM build, following the
[metadata workflow](../../common-graphics/cross/llvm-config.md). It is neither
the target ELF executable nor the host LLVM installation's metadata.
The recipe rejects absent or incorrect TableGen versions. The explicit
`LLVM_TABLEGEN_EXE` setting is required by standalone Clang's CMake logic.

Build Perl executes only on the host. Installed scan-build tools retain a
normal target Perl >=5.44 dependency and `/usr/pkg/bin/perl` shebangs.
Do not bypass that runtime dependency to accept the final package.

## Native compiler defaults

The [cross metadata helper](../recipes/lang/clang/files/cross-gcc-config.sh)
queries the real cross GCC16 and target LLVM metadata. It verifies target ABI,
all selected CRT/runtime files and three distinct C++ include directories.
Paths must resolve within the installed target GCC16 prefix. It removes the
physical sysroot prefix from the generated native Clang configuration.
Native builds retain the existing executable-based metadata helper.

These checks validate inputs and installed paths. They do not substitute for
running Clang on the target and checking actual C/C++ compilation, CRT/link
selection, dynamic loading and the existing SDK opt-out behavior.

## Checks and current boundary

```sh
sh profiles/common-build-tools/tests/clang-cross-config.sh /absolute/new-check
BMAKE=/absolute/host/bin/bmake \
    sh profiles/common-build-tools/tests/clang-cross-inputs.sh \
    /absolute/export /absolute/private-mk.conf /absolute/new-input-check
```

On 2026-10-12 the host generator built from the verified LLVM 23.1.2 archive.
The metadata helper passed with real GCC16 and target LLVM metadata. Fixture
checks reject wrong versions, ABI, missing files, escaped paths and duplicate
headers. Real pkgsrc evaluation passes valid inputs, rejects missing/wrong host
tools, and preserves target Perl, installed shebangs, static libclang and tests.
Target CMake configuration also succeeds with the selected generators.

The full target build, normal dependency resolution, package-file checks and
installed Clang execution are still pending. Perl's target cross-package path
and the complete QtTools consumer require separate acceptance. Preparation
checks do not establish an accelerated Plasma session.
