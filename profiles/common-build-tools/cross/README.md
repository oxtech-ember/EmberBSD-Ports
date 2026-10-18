# Cross-building common packages on macOS

This opt-in path builds EmberBSD/AArch64 or amd64 pkgsrc packages with the
[GCC 16.2 cross compiler](../../development-toolchain/cross/README.md).
The retained NetBSD 11 ABI and target triplet identify compatibility,
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

- A working GCC16 cross prefix targeting `aarch64--netbsd` or `x86_64--netbsd`.
- Host tools from the EmberBSD source tree, built on the Mac, including
  the corresponding target `install` utility.
- A pkgsrc unprivileged macOS bootstrap with BSD make, the patched package tools,
  mksh and digest. Use the exported `pkg_install-20260227nb1` recipe: it fixes
  alternate-root replacement and suppresses target deinstall scripts during
  cross updates. Its package database describes host executables only.
  The bootstrap must also own native `libtool-base-2.6.2` and `m4-1.4.21`
  built from the same export (`bmake -C export/devel/libtool-base MAKECONF=`
  *host*`/etc/mk.conf package`, then `pkg_add` both). Recipes that run
  `autoreconf` — `devel/libusb1`, `pkgsrc/local-phone/gaster` — resolve
  `libtoolize` through the bootstrap prefix: invoke cross builds with the
  bootstrap `bin` on `PATH` and point `TOOLS_PLATFORM.gm4` at its own
  `bin/gm4` instead of an external package manager. `tests/host-libtool.sh`
  (in the parent profile) gates this: registered packages, real files rather
  than symlinks outside the prefix, a shared-library consumer built through
  `autoreconf -fi`, and a stripped `PATH` that still fails at `libtoolize`.
- A target sysroot with headers, complete base libraries and development
  files (including `libintl`), the complete accepted
  GCC16 development files, a coherent runtime provider and target package database.
  Include base `/usr/bin/install-info` for packages shipping Info manuals.

For AArch64 or amd64 application images, select `EMBERBSD_GCC16_RUNTIME_PROVIDER=runtime`.
The [runtime-only provider](../../development-toolchain/runtime/README.md)
ships only target shared libraries and licenses. Keep headers and CRT objects
in the build-host sysroot. This choice does not install a compiler in the VM.
The runtime-only recipe accepts both architectures and rejects mismatched
target triplets, ELF machines and package metadata. Native package creation
and isolated installation pass for both synthetic target fixtures. Actual
target runtime package execution remains a separate acceptance step.
The default `compiler` provider preserves existing full-package workflows.
The providers conflict; do not register both or fabricate full-package metadata.

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

The default remains AArch64. For amd64, pass `--target amd64` before paths.
Also set `EMBERBSD_CROSS_TARGET=amd64` in the cross MAKECONF. This selects
`MACHINE_ARCH=x86_64` and the `x86_64--netbsd` compiler and CRT paths.
Unknown targets and conflicting compiler or machine overrides fail.
The selector does not prove an amd64 package build or desktop session.

OpenSSL uses explicit upstream `BSD-x86_64` and `BSD-aarch64` Configure targets
for NetBSD cross builds. OpenSSL 3.6's automatic `config` path reads host
`POSIX::uname` and ignores the older target environment variables. Native
selection stays unchanged. Unsupported NetBSD cross architectures fail before
the build. Assembly, shared libraries and package checks remain enabled.
The [focused regression](../tests/openssl-target.rb) uses real pkgsrc metadata
and the verified upstream archive:

```sh
BMAKE=/absolute/host/bin/bmake GMAKE=/absolute/host/bin/gmake \
    ruby profiles/common-build-tools/tests/openssl-target.rb \
    /absolute/export /absolute/cross.mk.conf \
    /absolute/distfiles/openssl-3.6.4.tar.gz /absolute/new-check
```

Run this check on macOS with a genuine amd64 GCC16 compiler and sysroot.
It compares host detection with explicit targets, checks ARM and native
metadata, rejects unknown targets, and compiles one unchanged upstream C file
through its generated Makefile. ARM has configuration coverage only. These
checks do not establish a complete package, target execution or TLS acceptance.

A private MAKECONF includes the host bootstrap configuration first:

```make
.include "/absolute/host/etc/mk.conf"
.if defined(BSD_PKG_MK)
EMBERBSD_CROSS_TOOLS=/absolute/new-cross-tools
EMBERBSD_CROSS_SYSROOT=/absolute/target-sysroot
EMBERBSD_CROSS_HOST_PREFIX=/absolute/host
# Optional: amd64 rather than the AArch64 default.
EMBERBSD_CROSS_TARGET=amd64
EMBERBSD_GCC16_RUNTIME_PROVIDER=runtime
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

Keep `mk.conf` and its executable `sort-c.sh` together. The profile uses
one executable path to preserve C collation in pkgsrc's `TOOLS_SORT`.
An `env LC_ALL=C sort` command loses its arguments in libtool PLIST expansion.
The prepared export includes both files. Check the exported helper with
`BMAKE=/absolute/host/bin/bmake sh scripts/tests/cross-export-sort.sh /absolute/pkgsrc`.
The check reads the actual exported profile and executes its selected sort path.

The cross profile defaults `CROSS_SYSCONFBASE` to `/etc` for base `rc.subr`
and `rc.conf`. `PKG_SYSCONFBASE` keeps pkgsrc's separate `${PREFIX}/etc` default.
`RCD_SCRIPTS_DIR` defaults to `/etc/rc.d`. Explicit overrides remain supported.
The `../tests/cross-rcd-path.rb` check queries the actual D-Bus recipe and
runs pkgsrc's unmodified rc-script generator. It reproduces the wrong base
path and old service-directory path. It also checks three explicit overrides
and unchanged native output:

```sh
BMAKE=/absolute/host/bin/bmake ruby ../tests/cross-rcd-path.rb \
  /absolute/pkgsrc/sysutils/dbus /absolute/cross.mk.conf /absolute/new-checks
```
pkgsrc defaults `PKG_RCD_SCRIPTS` to `NO`; installation does not start services.
See the [Xwayland lifecycle](../../../probes/plasma-mobile/toolkit/recipes/wayland/xwayland/README.md#shared-socket-directories).

Package scripts substitute target `/usr/bin/sort` through `_CROSS_FILES_SUBST`.
The host wrapper path must never enter the installed scripts.
The regression runs the real helper and checks every library entry:

```sh
BMAKE=/absolute/host/bin/bmake ruby profiles/common-build-tools/tests/cross-sort.rb \
    /absolute/export/sysutils/attr /absolute/cross.mk.conf /absolute/new-results
```

After packaging attr, exercise its actual serialized installation helpers:

```sh
ruby profiles/common-build-tools/tests/cross-install-scripts.rb \
    /absolute/attr-2.6.0nb1.tgz /absolute/new-install-results
```

This check rejects host tool paths before execution. It unpacks the actual
`+INSTALL` script and runs directory/configuration helpers in a private prefix.
It checks creation, permissions, removal, and preservation of modified config.
It does not replace installation on the target system.

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
The raw provider inputs remain absolute executable paths. Pkgsrc's `NATIVE_CC`
and `NATIVE_CXX` are compiler commands. On Darwin, they append `-B/usr/bin/`
so compiler subprocesses select the native assembler and linker despite the
cross wrapper PATH. Recipes must preserve the complete command, including its
arguments. Bash, libX11, libXt and FreeType receive this same native command.
Conflicting command-line overrides fail. Target compiler flags, wrappers and
sysroot selection remain unchanged. Native dependency recursion does not acquire
these cross-only command settings.

`tests/cross-native-routing.rb` takes a prepared pkgsrc tree, cross MAKECONF,
failed libX11 work directory, FreeType source directory and a new work path.
This Darwin/amd64 regression copies the actual cwrapper configuration into its private fixture and records
commands and results. It links and runs native C/C++, the upstream makekeys
source, and FreeType's unchanged native suffix probe under the polluted PATH.
It also checks libXt's final configure command and a target ELF link.
These checks do not establish full package or target runtime acceptance.
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
ICU uses native generators from the same upstream release. Its installed
`icu-config`, Makefile and pkgdata settings refer to the target shell, GCC16
and base tools; build-host paths must not enter those development interfaces.
Set the package revision before building: pkgsrc cleans its work directory
when the extraction cookie names a different complete package version.
The ICU metadata regression is `tests/icu-cross-metadata.sh` (relative to
common-build-tools). `tests/icu-cross-consumer.sh` builds its executable on
the development host; copy the result to the target and run `sh run.sh .`.
The board runs Unicode conversion, collation, resource generation and the
prebuilt consumer without invoking a compiler. On CM5, ICU 78.3nb1 passed
these checks before and after package removal/reinstallation on 2026-10-11.
Package SHA256: `328a62398f4c1231bd2511d0f2b3a2d9780b1f68323f314cdd978b8946737fed`.
Cppcheck and GCC16 `-fanalyzer` reported no diagnostics for the consumer.
This verifies ICU; target Qt and the remote desktop remain separate gates.

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
`ruby tests/cross-targets.rb BMAKE` checks both target tool compositions,
real make variable expansion, runtime-provider selection and mixed-target rejection.
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

## Cached file-check recovery

The common export makes each file-check result depend on its output directory.
`error-clean` can remove `.error` while the before/after file lists remain cached.
The check then recreates that directory through the existing pkgsrc target.
File, prefix, configuration-directory and variable-data checks remain enabled.

Run this check from the repository root:

```sh
BMAKE=/absolute/bmake sh profiles/common-build-tools/tests/check-error-dir.sh \
    /absolute/unpatched-pkgsrc /absolute/new-results
```

The regression uses real pkgsrc make fragments. It reproduces the original
failure, accepts a valid payload and rejects five invalid payloads.
It also checks all four direct writer targets and preserves the build cookie.

The cross profile exports `LC_ALL=C` and selects `/usr/bin/sort` directly.
pkgsrc passes `TOOLS_SORT` as one executable to its libtool PLIST expander.
An `env` command in the tool path drops shared and static library entries.
This check exercises the actual PLIST target under a non-C caller locale:

```sh
BMAKE=/absolute/host/bin/bmake ruby profiles/common-build-tools/tests/cross-sort.rb \
    /absolute/prepared-pkgsrc /absolute/cross.mk.conf /absolute/new-sort-results
```

Its staged files test PLIST processing; they are not target ELF evidence.
