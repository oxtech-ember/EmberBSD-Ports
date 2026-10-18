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

The exporter applies the repair after complete toolkit recipes. This keeps
the same library revision and cross roles in each composed common profile.
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
passes Clang static analysis. Installed target execution remains separate.

## Acceptance boundary

These results qualify source selection, native and complete AArch64 packages,
ICU build integration and the focused target objects. Installed target API
execution, complete upstream suites and KiCad remain separate acceptance work.

Strict native Memcheck passes the engine's `-v` query with zero live blocks
and zero errors. A real raw-Jam file action produces the expected bytes but
retains one upstream 24-byte reachable allocation at exit. It has no lost
blocks or invalid-access reports. This remains a Boost.Build engine memory
finding; it is not a clean whole-engine memory result. No C/C++ implementation
is changed by the cross-role patch.
