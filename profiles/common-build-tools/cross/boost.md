# Boost cross build roles

The common profiles retain the canonical Boost 1.92.0 provider. They use a
native `boost-jam` package to run b2 and the selected GCC16 wrappers to build
target libraries. The source archive is
[`boost_1_92_0.tar.bz2`](https://archives.boost.io/release/1.92.0/source/boost_1_92_0.tar.bz2),
SHA256 `5c1d40cb8e19adbf740a4ec2da35b3e58f3f5804b1dce44deb53df72193cbc6c`.
Upstream code retains the Boost Software License 1.0.

The [pkgsrc patch](../patches/pkgsrc-boost-cross-target.patch) supplies
NetBSD target properties to the native engine. Upstream's GCC toolset does
not recognize `netbsd` in its target-triplet OS inference. On Linux, the
unmodified Context graph therefore uses `<target-os>linux` and adds `-lrt`.
The corrected graph uses `<target-os>netbsd` and its NetBSD linker branch.

The cross recipe names pkgsrc's C++ and archive wrappers in a generated
site configuration. It passes the selected C, C++ and preprocessor flags.
AArch64 uses ARM, 64-bit, AAPCS and ELF properties. amd64 uses x86, 64-bit,
SysV and ELF properties. Other NetBSD cross architectures fail explicitly.
Native builds and recursive native tool dependencies keep their original
properties. Every library selected by the existing package stays selected.
The library package is `boost-libs-1.92.0nb1`.

The export installs every recipe first, including the canonical Boost recipes
in `pkgsrc/`, and then applies the repair. Every consumer gets the same library
revision and cross roles.
The patch does not add an application-specific Boost provider.

## Reproduce the native engine

Prepare a normal `common-media` export and a native MAKECONF that selects
GCC 16.2.0. Set its final prefix to the native pkgsrc bootstrap. Keep its
work and package directories separate from target work.

```sh
bmake -C export/devel/boost-jam MAKECONF=/absolute/native.conf \
    MAKE_JOBS=1 package
```

The ordinary Linux/GCC16 package passes file, permission, RELRO, runtime-path
and work-reference checks. Its engine reports `B2 5.5.3 (OS=LINUX)`.
Use `b2 -v` to query the standalone engine. Framework options such as
`--version` need the matching Boost.Build source files in the search path.

## Build the engine with GCC on Darwin

pkgsrc selects the b2 toolset `darwin` for GCC on Darwin when `GCCBASE` is not
set. The Ports GCC16 compiler does not set it. The engine script `build.sh` of
Boost 1.92.0 has no `darwin` toolset, so the boost-jam build stopped with
`Toolset 'darwin' does not appear to support C++11`. The
[engine patch](../patches/pkgsrc-boost-jam-darwin-engine.patch) builds the
engine with the `gcc` toolset in that case. Consumers of `bjam.mk` still pass
`--toolset=darwin` to b2, which provides `darwin.jam`.

The [toolset regression](../tests/boost-jam-engine-toolset.py) evaluates the
real `toolset.mk` and the real boost-jam `do-build` target with bmake. It
fails when the engine script gets a toolset that its usage text does not list.
`--engine-script` names `tools/build/src/engine/build.sh` from the extracted
Boost source.

```sh
python3.15 -B profiles/common-build-tools/tests/boost-jam-engine-toolset.py \
    --pkgsrc /absolute/export --bmake /absolute/host/bin/bmake \
    --shell /absolute/host/bin/mksh \
    --engine-script /absolute/work/boost_1_92_0/tools/build/src/engine/build.sh \
    --work /absolute/new-work
```

## Select the Darwin archive tool

The shared [wrapper patch](../patches/pkgsrc-boost-darwin-libtool.patch)
retains `EMBERBSD_DARWIN_LIBTOOL` in Boost's `post-wrapper` hook. The SDK
maps its `libtool_darwin` role to this existing variable for both `initial`
and `full` tool phases. A declared selection, Darwin bootstrap or selected
native prefix requires an absolute executable; an absent or invalid input
fails before replacing the wrapper. Ordinary pkgsrc Darwin defaults outside
that explicit selection and non-Darwin hooks remain available.

The [regression](../tests/boost-darwin-libtool.py) executes the actual
Boost headers, jam and libraries hooks. Its baseline demonstrates the old
selection replacement. The repaired hooks create six archives through the
selected initial and full Darwin tools, with symbols checked by LLVM.
Twelve invalid-input cases preserve the old wrapper; Linux and NetBSD
metadata fixtures execute no Darwin replacement. This does not establish
a complete Boost build or target runtime acceptance.

Pass the complete native bmake tuple through repeated `--make-arg`, including
its MAKECONF and any bootstrap flags. `--environment` is the corresponding
JSON environment mapping. `--llc` supplies the tiny Darwin object without
requiring a Clang frontend.

```sh
python3.15 -B profiles/common-build-tools/tests/boost-darwin-libtool.py \
    --pkgsrc /absolute/export --bmake /absolute/host/bin/bmake \
    --environment /absolute/native-environment.json \
    --patch /absolute/host/bin/nbpatch \
    --llc /absolute/host/bin/llc --nm /absolute/host/bin/llvm-nm \
    --initial-libtool /absolute/initial/bin/libtool \
    --full-libtool /absolute/host/bin/llvm-libtool-darwin \
    --make-arg=-m --make-arg=/absolute/host/share/mk \
    --make-arg=SHELL=/absolute/host/bin/mksh \
    --make-arg=MAKECONF=/absolute/native.conf \
    --make-arg=EMBERBSD_DARWIN_BOOTSTRAP=yes \
    --work /absolute/new-work
```

## Check the cross graph

Run the [source regression](../tests/boost-cross-target.py) with Python 3.15
and SDK host API 1. `--source` names the extracted Boost source from normal
pkgsrc preparation. The selected compiler must be GCC16 for AArch64.

```sh
python3.15 -B profiles/common-build-tools/tests/boost-cross-target.py \
    --sdk-source /absolute/EmberBSD-SDK \
    --pkgsrc /absolute/export \
    --archive /absolute/distfiles/boost_1_92_0.tar.bz2 \
    --source /absolute/work/boost_1_92_0 \
    --native-makeconf /absolute/native.conf \
    --cross-makeconf /absolute/cross.conf \
    --bmake /absolute/host/bin/bmake --b2 /absolute/host/bin/b2 \
    --cxx /absolute/cross/bin/aarch64--netbsd-g++ \
    --ar /absolute/cross/bin/aarch64--netbsd-ar \
    --readelf /absolute/cross/bin/aarch64--netbsd-readelf \
    --work /absolute/new-result
```

The regression checks actual before/after pkgsrc metadata for native,
AArch64, amd64, recursive native and unsupported architecture cases. It
executes the real make hook that writes the site configuration. The real
Context graphs retain shared and static outputs and all three ARM64/AAPCS
assembly sources. Real target header preprocessing identifies NetBSD,
AArch64 and GCC16. The same compiler produces three AArch64 ELF objects.
The amd64 result covers metadata only; it does not qualify an amd64 toolchain.

## Complete target package

The ordinary GCC 16.2.0 AArch64 `boost-headers-1.92.0` and
`boost-libs-1.92.0nb1` packages pass the normal pkgsrc checks. The libraries
retain every component selected by the canonical recipe, shared and static.
The real build reports ICU support and completes 2343 b2 targets. All 39
shared ELF files in the library archive identify AArch64.

The [installed API consumer](boost-api/README.md) passes a real GCC16 cross
build through the installed CMake packages for locale, filesystem, thread
and Boost.Test. It also checks the header-only System API. Normal packages
are installed in an isolated sysroot for this check. All 18 runtime providers
match either the existing SDK or the normal Boost archive. The target RPATH
selects the common GCC16 runtime and package libraries.
Its native header companion passes strict Memcheck. The full target source
passes Clang static analysis.

On 2026-10-19, the API consumer was run against the installed GCC16 package in
a clean NetBSD 11.0 AArch64 VM. Four ordinary-user cycles passed,
covering five API cases and 33 assertions per cycle, provider inventory checks,
and the deliberate Boost.Test failure control. The package-specific target
`pkg_admin check` verified all 296 package files. The package archive used for
this run has SHA256
`902701a047a59a8c987d96576e76ce9a4c0f7e394a30fdfcb4f0aefb5b08644f`.
The full package database scan after reinstall was not completed. Complete
upstream suites and KiCad remain separate acceptance work.

## Acceptance boundary

These results qualify source selection, native and complete AArch64 packages,
ICU build integration, the focused target objects and the installed consumer
run. Complete upstream suites and KiCad remain separate acceptance work.

Strict native Memcheck passes the engine's `-v` query with zero live blocks
and zero errors. A real raw-Jam file action produces the expected bytes but
retains one upstream 24-byte reachable allocation at exit. It has no lost
blocks or invalid-access reports. This remains a Boost.Build engine memory
finding; it is not a clean whole-engine memory result. No C/C++ implementation
is changed by the cross-role patch.
Clang is the primary cross compiler. The same repair selects the b2 `clang`
toolset and writes its site configuration with the cross `CXX` and `AR`.
Run the [Clang regression](../tests/boost-cross-clang.py) with a Clang cross
make configuration:

```sh
python3.15 -B profiles/common-build-tools/tests/boost-cross-clang.py \
    --pkgsrc /absolute/export \
    --cross-makeconf /absolute/cross.conf \
    --bmake /absolute/host/bin/bmake-wrapper
```

The wrapper must pass `-m` with the host `share/mk` directory. The
regression applies the repair to the pinned upstream recipes and checks
the actual boost-headers metadata and the real `pre-build` hook.
