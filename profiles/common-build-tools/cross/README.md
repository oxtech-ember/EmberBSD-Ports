# Cross-building common packages on macOS

This opt-in path builds EmberBSD/AArch64 pkgsrc packages with the
[GCC 16.2 cross compiler](../../development-toolchain/cross/README.md).
The retained NetBSD 11 ABI and `aarch64--netbsd` triplet identify compatibility,
not an upstream OS build. Follow the [sysroot provenance rules](sysroot.md).
The compiler and build tools execute on macOS; installed packages are tested
on EmberBSD. Python, Meson and Ninja are among the
[accepted target packages](validation.md). LLVM23 core also passes
[installed C API and JITLink acceptance](../llvm-family.md#cross-build-and-accepted-core)
on Zero 3W. A complete GCC16-built base userland and compiler-family
consumer migration remain pending.

Use the `common-build-tools` export from the parent profile. It preserves the
pinned pkgsrc revision and obtains original upstream archives with recipe
checksums. The cross fixes also compose into profiles based on common tools.

## Prerequisites

Prepare these separate directories, outside Git:

- A working GCC16 cross prefix targeting `aarch64--netbsd`.
- Host tools from the EmberBSD source tree, built on the Mac, including
  `aarch64--netbsd-install`.
- A pkgsrc unprivileged macOS bootstrap with BSD make, the patched package tools,
  mksh and digest. Use the exported `pkg_install-20260227nb1` recipe: it fixes
  alternate-root replacement and suppresses target deinstall scripts during
  cross updates. Its package database describes host executables only.
- A target sysroot with headers, complete base libraries and development
  files (including `libintl`), the complete accepted
  `gcc16-16.2.0nb1` package, its dependency files and target package database.
  Include base `/usr/bin/install-info` for packages shipping Info manuals.

Do not substitute a host package database for the target database. The
selected target GCC runtime needs its CRT files and `libstdc++.so.7`; a
compiler executable alone does not satisfy these prerequisites. This profile
rejects building `lang/gcc16` as a consumer: its Canadian-cross package recipe
is a separate, unfinished step.

Compose the existing tools without rebuilding them:

```sh
sh profiles/common-build-tools/cross/prepare-tools.sh \
    /absolute/gcc16-prefix /absolute/netbsd-tools /absolute/new-cross-tools
```

A private MAKECONF includes the host bootstrap configuration first:

```make
.include "/absolute/host/etc/mk.conf"
.if defined(BSD_PKG_MK)
EMBERBSD_CROSS_TOOLS=/absolute/new-cross-tools
EMBERBSD_CROSS_SYSROOT=/absolute/target-sysroot
EMBERBSD_CROSS_HOST_PREFIX=/absolute/host
WRKOBJDIR=/absolute/work
DISTDIR=/absolute/distfiles
MAKE_JOBS=4
# Optional when these host tools are already installed:
TOOLS_PLATFORM.makeinfo=/absolute/host-texinfo/bin/makeinfo
EMBERBSD_BUILD_MSGFMT=/absolute/host-gettext/bin/msgfmt
EMBERBSD_BUILD_CMAKE=/absolute/host-cmake/bin/cmake
# Optional matching host interpreter for the Python target package:
EMBERBSD_CROSS_BUILD_PYTHON=/absolute/python3.14
.include "/absolute/EmberBSD-Ports/profiles/common-build-tools/cross/mk.conf"
.endif
```

Use the host BSD make to build a target package, for example:

```sh
/absolute/host/bin/bmake -C /absolute/export/devel/pkgconf \
    MAKECONF=/absolute/cross.mk.conf package
```

Pkgsrc resolves native build dependencies separately from target runtime
packages. Add private paths for any required host tools through pkgsrc's tool
configuration. The EmberBSD target prefix remains `/usr/pkg`. Cross `install` populates
the private sysroot with package scripts disabled; actual `pkg_add` on the
target runs installation scripts, including Info registration.

Build-time C/C++ generators use `/usr/bin/cc` and `/usr/bin/c++` on macOS.
Override `EMBERBSD_CROSS_BUILD_CC` and `EMBERBSD_CROSS_BUILD_CXX` with absolute
host compiler paths when necessary. They reach upstream configure as
`CC_FOR_BUILD` and `CXX_FOR_BUILD`; target wrappers still compile the package.
The profile also sets pkgsrc's `NATIVE_CC` and `NATIVE_CXX`, because recipes
such as Bash append their generator compiler settings later. Conflicting
command-line overrides fail rather than silently selecting the target compiler.
The mDNSResponder version probe reads the target sysroot header during cross
builds and the host header during native dependency recursion.
Host tool dependencies read the host bootstrap MAKECONF, so interpreter and
tool choices needed by those dependencies belong there as well.
`EMBERBSD_BUILD_MSGFMT` accepts an existing absolute GNU gettext-tools 1.0+
executable whose version command succeeds. It breaks the native
Python → xz → gettext-tools → Python bootstrap cycle without disabling NLS
or changing the selected libintl. Without this opt-in, pkgsrc's original
msgfmt dependency choice is retained. Put the setting in the host bootstrap
MAKECONF too, so recursively built host packages see it.
`EMBERBSD_BUILD_CMAKE` similarly selects an existing CMake 4.4.4+ and matching
CPack alongside it. Both version commands must succeed, and all package
`CMAKE_REQD` floors still apply. The tools framework exposes the selected
pair through its normal wrappers. Keep this setting in the host MAKECONF
too. Clean a package's work directory after changing cached tool choices.
The [Python recipe](../python.md) validates the matching host interpreter and
keeps installed extension metadata on the target side. SQLite and zstd
receive explicit target platform settings during cross compilation.
Cross Ninja uses the matching native Ninja and Python to generate and build
for the target platform. Its normal native bootstrap is retained; the cross
build does not execute the newly linked target binary. The target package
declares its Python dependency for the installed browse tool.

## What the cross adaptation checks

Host dependency recursion drops cached target platform values. Target package
metadata uses cross `readelf` and sysroot libraries, never the macOS loader.
It rejects missing ELF files, failed inspection tools and unresolved DSOs.
Scripts and empty files are not ELF providers. Relative, absolute and directory
symlink aliases resolve inside the target staging tree and sysroot; loops fail. Existing package-owned DSO
filtering and `CHECK_SHLIBS_SKIP` shell patterns remain supported.

Compiler wrappers preserve the selected GCC16 CRT and runtime paths even
when Libtool reconstructs its link command. Packages retain normal pkgsrc
file, permission, RPATH and shared-library checks, and record root/wheel
ownership rather than the Mac user's UID.

The only cross runtime-tool exception is base `install-info`, verified
in the sysroot. Its build wrapper is a no-op and the installation script names
`/usr/bin/install-info` on the target. Other unsupported `:run` tools still
fail explicitly. Libtool declares GNU M4 as a target package dependency.

## Acceptance

Run `tests/cross-pkgsrc.sh` against a staged pkgconf package. It exercises real
pkgsrc parsing, native dependency recursion, ELF metadata and failure cases.
`tests/cross-tools.sh` checks tool composition, refusal of existing output,
missing host tools and the constrained target Info utility selection.
`tests/cross-libc.rb BMAKE NEW_WORK` exercises the actual pre-extract guard:
canonical aliases pass; four missing and four divergent libc paths fail.
That guard detects inconsistent copies, not the origin of an otherwise
consistent sysroot. See [the separate provenance requirement](sysroot.md).
`tests/host-msgfmt.sh` checks the opt-in on native/cross pkgsrc configurations,
preserved defaults and libintl, rejection of invalid tools and a real
translated plural/context catalog consumer on the Mac host.
`tests/host-cmake.sh` checks the native/cross selection, preserved defaults,
version and companion-tool guards, and a compiled/installed host C/C++ consumer.
`tests/host-gettext-xml.sh` checks installed XML translation after the direct
libxml2 link repair in gettext-tools 1.0nb1. Maintained and generated makefiles
carry the same change; the macOS host package retains its XML functionality.
`tests/ninja-cross.sh` checks native/target command separation and pkgsrc's
parallel-build limit, including an unset job count and `MAKE_JOBS_SAFE=no`.
`tests/cross-generators.sh` checks native/cross Libtool auxiliary selection
and executes C/C++ generators through the real configure environment. It
also rejects missing compiler exports and invalid compiler paths.
The separate `tests/pkg-add-sysroot.sh` compares original and repaired host
package tools. It checks replacement, same-version reinstall, shared-directory
ownership, partial-extraction rollback and native behavior.
These scripts print their required positional arguments when called without
arguments. Set `BMAKE` to the host bootstrap BSD make.

Target acceptance scripts in this directory require a new output directory:

- `run-pkgconf-tests.sh`: upstream API binaries and CLI fixtures, plus an
  installed C API consumer built with the selected GCC16.
- `run-m4-tests.sh`: upstream manual examples, stack-overflow test and Info
  registration through the installed package.
- `run-libtool-tests.sh`: C11/C++20 shared and static consumers, exceptions,
  actual runtime linkage, libtoolize, shlibtool and uninstall.
- `run-binutils-tests.sh`: GNU assembler/linker and archive consumers,
  DWARF5/64, split debug information, stripping, C++ DSO exceptions,
  GNU CTF and unresolved-symbol errors; see [Binutils](../binutils.md).
- `run-python-tests.sh`: installed C/C++ consumers, extension loading,
  build-details agreement and focused upstream Python suites.
- `run-meson-tests.sh`: installed Meson/Ninja with Python314, explicit GCC16
  and Binutils 2.47; C/C++ shared/static libraries, Python embedding,
  incremental builds, error propagation, browse interpreter and installed RPATH.

The Meson check retains `werror=true`. Base ld 2.42 emits compatibility
warnings for unused libc/libm symbols and fails the shared-library link;
installed GNU ld 2.47 passes the same object and flags. The test selects
current GNU as/ld through GCC specs; GCC's bootstrap defaults and collect2/LTO
remain separate migration gates. The upstream `unittests.internaltests`
group also runs in the VM with Python314; see [the validation record](validation.md).

Pkgconf builds its test binaries as upstream `noinst_PROGRAMS` during `all`.
Copy the actual `WRKSRC/.libs/test-api-*` and `.libs/test-runner` ELF files;
the similarly named files in WRKSRC itself are host Libtool shell wrappers.
Copy pristine upstream `tests/` and `t/` directories separately from those
cross-built binaries. For GNU M4, transfer upstream `checks/` and `examples/`.
On macOS, create transfer archives with
`COPYFILE_DISABLE=1 tar --no-xattrs --exclude '._*' ...`; AppleDouble files
otherwise become unintended test inputs on NetBSD. Do not count a host
execution or version string as target acceptance. The [Libtool record](../libtool.md)
explains source regeneration and target script conversion.
