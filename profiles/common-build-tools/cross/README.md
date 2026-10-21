# Cross-building common packages on macOS

Host controllers use Python 3.15 and the standard-library SDK API version 1.
Set `EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK`, or pass `--sdk-source` to
the controller. Run these host tools with `python3 -B`. Target run scripts
remain POSIX shell and do not require host Python on the device.
The host entrypoints handle INT, TERM and HUP. Signal exits use `128 + signal`.
Completed producer failures retain their exit status. Imports do not install
handlers. If the SDK cannot prove the producer session has stopped, it raises
`ProcessOwnershipError`. Preserve the affected work for a process audit.
The [LLVM reuse guard](llvm-reuse.md) also blocks another installation.

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

The common profiles select canonical Ruby 4.0.7 for packages and native
generators. Recursive host dependencies keep host compilers and paths.
`tests/ruby-selection.rb` in the parent profile verifies actual selection,
both target metadata modes, host recursion and the unchanged native barrier.
This metadata check does not establish Ruby package or target acceptance.

The [pkg-config environment](pkgconfig.md) roots target compile/link search
paths in the selected SDK. Runtime paths retain their installed target prefix.
Explicit C++ imports select the installed GCC16 runtime before the base runtime.
The real GCC16/CMake regressions also verify unchanged native discovery.

The [shared font roles](font-runtime-roles.md) keep native font compilers and
target runtime indexers separate in both package install frameworks. Actual
native/cross metadata checks retain the strict unsupported run-tool refusal.

## Prerequisites

Prepare these separate directories, outside Git:

- A working GCC16 cross prefix targeting `aarch64--netbsd` or `x86_64--netbsd`.
- Host tools from the EmberBSD source tree, built on the Mac, including
  the corresponding target `install` utility.
- A pkgsrc unprivileged macOS bootstrap with BSD make, the patched package tools,
  mksh and digest. Use the exported `pkg_install-20260227nb3` recipe: it fixes
  alternate-root replacement, successful dry runs and DESTDIR-aware pkg_admin
  add/rebuild operations. It suppresses target deinstall scripts during cross
  updates. Its package database describes host executables only.
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
  For Info manuals, use the target base `/usr/bin/install-info` when it is present. If the target base omits it, pkgsrc supplies `pkgtools/pkg_install-info` as a target run dependency. The cross profile writes `/usr/pkg/bin/pkg_install-info` into package lifecycle scripts; it never substitutes the build-host helper.

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

For OpenMP, also stage the matching GCC16 `omp.h` and `libgomp.spec`.
The C/C++ wrappers select that specs file through the runtime prefix.
The [real specs-selection regression](openmp-spec.md) compares the historical
base selection with GCC16 metadata and checks the resulting target ELF links.

Compose the existing tools without rebuilding them:

```sh
python3 -B profiles/common-build-tools/cross/prepare-tools.py \
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
    /absolute/distfiles/openssl-3.6.5.tar.gz /absolute/new-check
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
EMBERBSD_BUILD_AUTOCONF=/absolute/host-autoconf/bin/autoconf
# Optional matching host interpreter for the Python target package:
EMBERBSD_CROSS_BUILD_PYTHON=/absolute/python3.15
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
and `NATIVE_CXX` are compiler commands. On Darwin and Linux, they append `-B/usr/bin/`
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

`tests/cross-ncurses-native.rb` checks the Linux counterpart with native GCC16.
Pass the exported pkgsrc, cross MAKECONF, existing ncurses 6.6 work directory,
historical profile, current profile and a new output directory, in that order.
Set `BMAKE` to the native pkgsrc make executable. The work directory supplies
the real cwrappers, upstream configure check and recorded `confdefs.h`.
The test copies wrapper configuration and redirects logs into its own output.
It reproduces the target linker's `elf_x86_64` refusal before the fix, then
compiles and executes the unchanged upstream native-compiler check afterward.
It checks the complete ncurses `BUILD_CC` assignment, both native GCC16 command
versions, and the unchanged AArch64 target ELF route. The x86-64 Linux-host
check passed on 2026-10-18; this is not a complete ncurses package or VM test.

The mDNSResponder version probe reads the target sysroot header during cross
builds and the host header during native dependency recursion.
The [mDNSResponder build contract](mdns-build-tools.md) selects Apple's current
2881.120.11 source and passes the target OS as a GNU Make argument. Its complete
NetBSD graph needs no lexer/parser generator. Darwin retains Flex and Bison.
Ordinary native/AArch64 GCC16 packages and 518 native public API cases pass,
including strict Memcheck. Installed DNS-SD and CUPS acceptance remain separate.
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

For cross builds, the common profile also sets CMake's target system,
processor and sysroot. Program lookup stays on the host. Header, library and
package lookup searches the pkgsrc buildlink root before the target sysroot.
This order retains the selected package when base has the same library name.
Base-only dependencies remain available through the sysroot. Native tool
dependency recursion receives none of these cross settings. This corrects
host-system detection even when the selected compiler already emits target
objects. `tests/cmake-cross.rb EXPORTED_PKGSRC MAKECONF NEW_WORK` checks the
actual pkgsrc arguments and CMake identity/search behavior for AArch64 and
amd64, plus unchanged native recursion. Its compiler-free fixture establishes
configuration behavior; actual compiler and installed-consumer checks remain
separate. It also checks LLVM's final recipe arguments, so its local settings
cannot override the shared package-first order.

`tests/cmake-dependency-roots.rb EXPORTED_PKGSRC MAKECONF PREPARED_WRKOBJDIR NEW_WORK`
uses the real prepared protobuf buildlink stage, pkgsrc flags and environment.
Its GCC16 control finds base zlib 1.3.1 with the previous root order, then
the selected package's zlib 1.3.2 with buildlink first. Both API links pass.
Base `execinfo` fallback remains unchanged, as do native configuration and
provider hashes. This check configures and links; it does not execute target code.
Existing CMake build directories retain cached dependency paths. Reconfigure
them with the corrected profile and clear only the affected dependency cache
entries before the normal dependency rebuild and package checks.

`EMBERBSD_BUILD_AUTOCONF` selects an existing native Autoconf 2.73+ for plain
`USE_TOOLS+=autoconf` build dependencies. Its version command must succeed.
All `AUTOCONF_REQD` floors apply. The same directory must contain executable
`autoheader`, `autom4te`, `autoreconf`, `autoscan`, `autoupdate` and `ifnames`
with the same version. Invalid selections fail through `PKG_FAIL_REASON`.
The seven tools use normal pkgsrc wrappers without a redundant native package
dependency. This does not register an installed package or provide Automake.
Explicit 2.13/2.69 requests and `autoconf:run` or `autoconf:test` retain their
normal package dependencies and paths. A build-host path never substitutes
for those runtime or test providers. With no opt-in, the original choice stays.
Remove earlier `TOOLS_PATH`/`TOOLS_DEPENDS` overrides and put this setting in
the host MAKECONF too. Use a normally configured installation; relocation
environment variables that point at another Autoconf release must be removed.

Run the regression with an export that does not yet contain this patch:

```sh
BMAKE=/absolute/host/bin/bmake ruby profiles/common-build-tools/tests/host-autoconf.rb \
    /absolute/prepared-pkgsrc /absolute/native.mk.conf /absolute/cross.mk.conf \
    /absolute/autoconf-2.73/bin/autoconf /absolute/new-autoconf-results
```

The test copies the real pkgsrc tool rules and consumer recipe. It checks
native and cross metadata, creates seven actual wrappers in private work
directories, and regenerates and executes a small configure/header contract.
Default, legacy, runtime and test routes remain unchanged. Invalid paths,
failed version commands, old versions, required-version floors and missing
or mismatched companions are rejected. This checks host generators, not an
installed target package or a complete `autoreconf`/Automake workflow.

The [Python recipe](../python.md) validates the matching host interpreter and
keeps installed extension metadata on the target side. SQLite and zstd
receive explicit target platform settings during cross compilation.
The [ICU runtime and SDK split](icu.md) keeps matching native generators on
the host. Cross runtime images contain shared libraries and user commands.
The exact SDK dependency retains `icu-config`, headers, generators and build
metadata in the host sysroot. The metadata regression remains
`tests/icu-cross-metadata.sh`; resource fixtures are now generated on the host.
The earlier full ICU 78.3nb1 package passed CM5 conversion, collation, resource
generation and package lifecycle checks. Its SHA256 is
`328a62398f4c1231bd2511d0f2b3a2d9780b1f68323f314cdd978b8946737fed`.
Those results do not establish acceptance of the new 78.3nb2 split packages.

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
when Libtool reconstructs its link command. They also add the sysroot
`/usr/lib` as a link search path. GNU ld needs it to resolve base libraries,
such as `libm.so.0`, that package libraries require. The profile rejects a
sysroot whose GCC16 C++ headers do not define `_GLIBCXX_HAVE_TLS`. Packages retain normal pkgsrc
file, permission, RPATH and shared-library checks, and record root/wheel
ownership rather than the Mac user's UID.

For Info manuals, cross package scripts use the target base
`/usr/bin/install-info` when it is present. If the base sysroot omits it,
pkgsrc adds `pkgtools/pkg_install-info` as a target runtime dependency and
records `/usr/pkg/bin/pkg_install-info` for the target. The build wrapper is a
no-op in both cases. A Perl runtime tool is allowed only when the target Perl
package is staged at `/usr/pkg/bin/perl`. Pkgsrc retains Perl as a target
runtime dependency and writes the target path into Perl script shebangs. Other
unsupported `:run` tools still fail explicitly. Libtool declares GNU M4 as a
target package dependency.

## Acceptance

Run `tests/cross-pkgsrc.sh` against a staged pkgconf package. It exercises real
pkgsrc parsing, native dependency recursion, ELF metadata and failure cases.
`tests/cross-tools.py` checks tool composition, refusal of existing output,
missing host tools, target Info utility routing and the pkgsrc runtime
dependency. It does not execute target binaries on the host.
`tests/cross-runtime-perl.py` checks staged target Perl dependency and shebang
selection, refusal when Perl is absent, and unchanged native behavior.
`python3 -B tests/prepare-tools-target.py --sdk-source SDK NEW_WORK` runs the real
helper with fake amd64 tools. It needs no compiler or pkgsrc export. It checks the
imports, every composed link, a wrong compiler and existing output.
In this helper, the GCC16 `host.py` resolves `sdk_source` to the LLVM module.
That module therefore defines the same `PRODUCER_QUARANTINE`; the test compares both values.
`python3 -B tests/cross-targets.py BMAKE` checks both target tool compositions,
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
The [Go discovery repair](gettext-go-detection.md) rejects unrelated programs
named `go` and preserves compiler preference and explicit overrides.
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
The separate `tests/pkg-admin-destdir.sh ORIGINAL_PKG_ADMIN FIXED_PKG_ADMIN NEW_WORK`
checks `pkg_admin rebuild` and `add` against a staged tree. It verifies that
file checks use DESTDIR while B-tree keys retain target paths.
The cross package tools also carry the OS replacement dry-run repair from
EmberBSD `c22fa34ebe0`. A successful simulated deletion returns zero. Real
deletion results and metadata errors retain their original return values.
Run `python3 -B tests/pkg-add-dryrun.py --sdk-source SDK --source PERFORM_C
--work NEW_WORK` from this profile to check both complete source functions.
The fixture adapts the OS contract for alternate-root script selection.
It checks 69 cases, including all `Fake`, `Destdir` and `NoInstall` combinations.
Use `--extract-only` for separate target compilation and analysis. Use
`--compiler` and repeated `--cflag=FLAG` options for native memory checks.
The test uses private metadata directories. It launches no package tools.
A passing source fixture does not qualify an installed package transaction.

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

The ncurses 6.6 export inventories both regular terminfo files and symbolic
aliases. A native `tic` can use relative symbolic links during a cross install.
The original recipe lists only regular files, so normal `check-files` rejects
those installed aliases. The patch does not follow links or change `tic`.

Run the regression against an unpatched ncurses recipe and an actual installed
stage. It copies the stage into new private directories and invokes the normal
`post-install`, `plist` and `check-files` targets:

```sh
BMAKE=/absolute/host/bin/bmake ruby profiles/common-build-tools/tests/ncurses-terminfo.rb \
    /absolute/prepared-pkgsrc /absolute/cross.mk.conf \
    /absolute/ncurses-work/.destdir /absolute/new-terminfo-results
```

The AArch64 stage checked on 2026-10-18 contains 1861 regular entries and 1038
aliases. The original check rejects exactly those aliases; the patched check
accepts all 2899 entries. Extra-file and missing-alias controls still fail.
The test verifies that input aliases resolve within the staged database.
This is a packing-list check, not package installation or target execution.

The cross profile exports `LC_ALL=C` and selects `/usr/bin/sort` directly.
pkgsrc passes `TOOLS_SORT` as one executable to its libtool PLIST expander.
An `env` command in the tool path drops shared and static library entries.
This check exercises the actual PLIST target under a non-C caller locale:

```sh
BMAKE=/absolute/host/bin/bmake ruby profiles/common-build-tools/tests/cross-sort.rb \
    /absolute/prepared-pkgsrc /absolute/cross.mk.conf /absolute/new-sort-results
```

Its staged files test PLIST processing; they are not target ELF evidence.

## Installed FFTW, Readline and ncurses

On 2026-10-18 the ordinary `math/fftw`, `devel/ncurses` and `devel/readline`
recipes cross-built `fftw-3.3.11`, `ncurses-6.6` and `readline-8.3nb1`
with GCC 16.2.0 for the pinned E34 AArch64 sysroot. The packages retain
normal pkgsrc ownership and dependencies on the runtime-only GCC16 package.
Use the cross configuration above and each recipe's normal `package` target;
install the resulting archives with target `pkg_add`, with ncurses before
Readline. Host tool installation and target installation are separate.
For an archive rebuilt under the same package version, use `pkg_add -U`.
An ordinary `pkg_add -u` can return success without replacing that version.

The installed [FFTW contract](../../../probes/fftw/README.md#numerical-contract)
passes for double/float and pthread/OpenMP: four consumers, each checking
analytical spectra, inverse recovery, real transforms and two workers.
The upstream double and float `bench` verification sets also pass.
Deleting FFTW makes two consumers fail with the expected missing-library
diagnostic. Reinstallation restores all four and passes package integrity.

The unchanged Readline 8.3 `examples/rltest.c` runs against installed
`libreadline.so.8` and `libncurses.so.6`. Pipe input and an actual SSH PTY
pass input/history checks. In the PTY, backspace changes `betx` to `beta`,
Ctrl-P recalls it, and the upstream history listing reports both entries.
Deleting Readline produces the expected loader refusal; reinstalling ncurses
and Readline restores the consumer. All three packages pass `pkg_admin check`.
All 3976 package payload entries match the archives, SDK and installed VM:
regular-file SHA256 hashes, symbolic-link targets and permission modes.
The six FFTW DSOs, Readline/history, five ncurses DSOs and GCC16
`libgomp.so.1`/`libgcc_s.so.1` also pass a separate 15-library hash comparison.

The fresh ordinary ncurses archive contains 1861 regular terminfo entries
and 1038 relative aliases. All 2899 entries match the SDK and installed VM.
The earlier archive omitted those aliases and failed `nxterm` lookup.
The replacement passes `infocmp nxterm`; `tput -Tnxterm colors` returns eight.
Readline PTY editing and history also pass with this replacement.
The full packing-list and installed-package checks retain their distinct scope.

The FFTW, ncurses and Readline `.la` files still contain absolute SDK search paths.
Repairing that cross-build metadata and producing portable replacement
archives remain pending; the ELF runtime checks above do not verify `.la`
portability. Full ncurses terminal coverage, upstream library suites,
physical-board performance and KiCad integration remain separate.
