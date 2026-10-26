# Current common build tools

The [Mach-O metadata resolver](macho-metadata.md) uses selected structural tools.
It does not require libmagic or create a file/libtool bootstrap cycle.

The [complete initial libnbcompat route](libnbcompat.md) uses the canonical
recipe, DB implementation, and selected SDK tools. It shares configure
diagnostics with GCC and retains a separate finite component acceptance.

The [common Brotli and c-ares sources](brotli-cares.md) select the current
1.2.1 and 1.34.9 security releases. They keep the inherited recipes and
CMake policy. Source checks pass; native packaging and consumer checks remain
separate.

The [common GNU utility sources](gnu-utilities.md) select diffutils 3.12 and
findutils 4.11.0 with ordinary NLS preserved. Finite initial source specifications
build only the tools needed before full package installation. Source and runtime
acceptance remain separate.

The [shared bmake source update](bmake.md) selects stable 20260912 in the
existing vendor owner. Bootstrap and the ordinary package retain one payload,
all upstream tests and the existing pkgsrc mode override. Source checks pass;
builds and installed tool acceptance remain separate.

The [shared libarchive source update](cross/libarchive.md) selects 3.8.10 for
libarchive, bsdtar and the package-tools vendor route. Original NetBSD source
imports preserve the complete upstream tests and the existing common-zlib delta.
Package builds and installed consumer acceptance remain separate.

The [Flex epsilon-closure repair](../../probes/flex-nfa/README.md) replaces
recursive graph traversal with a bounded worklist. Native GCC16 packaging,
all 114 upstream tests and installed scanner consumers pass. Instrumented
memory execution and cross-package acceptance remain separate.

The [ICU 78.3 package policy](cross/icu.md) keeps native packaging complete
and separates cross runtime files from an exact matching target SDK on the
development host. Both real 274-file payloads pass ownership and refusal
checks. Final split packages and installed target acceptance remain separate.

The [Boost cross roles](cross/boost.md) keep one canonical 1.92.0 provider.
Native b2 uses the selected target GCC wrappers and explicit NetBSD ABI
properties. Native engine and complete GCC16 AArch64 packages pass, including
ICU build integration, causal source graphs and three assembly objects. The
installed [API consumer](cross/boost-api/README.md) retains a separate target
execution gate.

The [CMake Xcode header check](tests/cmake-xcode/README.md) keeps the complete
Xcode generator and project-opening API available to native GCC16. The common
recipe uses the LaunchServices header without unrelated Apple Blocks headers.
Paired full-module compilation and its API reference pass. Full package and
generator acceptance remain separate.

On native Darwin, the CMake recipe also binds each selected pkgsrc libarchive,
libuv and curl header/library pair to its buildlink prefix. SDK or unrelated
framework discovery cannot replace half of a selected provider. Built-in
providers, cross builds and other hosts keep their existing search policy.
The repair is AI-assisted EmberBSD work, not submitted upstream.
The focused [provider check](tests/cmake-darwin-providers.py) replays the six
fields from a real failed cache, then applies the extracted recipe policy.
Use its `--help` for explicit CMake, GCC16, source, prefix and SDK inputs.
It checks native/built-in/cross policy, real Find modules, the missing-symbol
link failure and coherent header/runtime versions. A cache replay is not an
independent discovery baseline. No full-package or memory-safety claim follows.

Native CMake consumers and the CMake bootstrap use the selected pkgsrc
AR, RANLIB, NM, STRIP and LD roles. The common policy requires each real
input to be an existing absolute executable. It preserves compiler and
archive wrappers; their generated paths reach the corresponding CMake cache
entries. Cross builds retain their existing toolchain routing.
The AI-assisted [metadata check](tests/cmake-binutils.py) covers modern and
legacy CMake routes, both wrapper implementations, invalid inputs, export
patch order and bootstrap argument forwarding. It runs no compiler or CMake
configure command. Full builds and archive execution remain separate checks.
Native Darwin maps the selected `OSX_SDK_PATH` to `CMAKE_OSX_SYSROOT:PATH`.
The input must be an existing absolute directory. The SDK producer must set
the admitted path before pkgsrc reads metadata. Earlier raw pkgsrc SDK
discovery remains outside this binding. This keeps the final CMake
bootstrap configuration and ordinary consumers on the same selected SDK.
Upstream forwards that value to nested `try_compile` calls. Linux, NetBSD and
cross builds keep their current sysroot routing. Deployment flags stay under
the existing producer policy.

Native Darwin also requires `EMBERBSD_DARWIN_INSTALL_NAME_TOOL` and
`EMBERBSD_DARWIN_TAPI` to select existing absolute executable files.
`EMBERBSD_DARWIN_TAPI_KIND` must be `apple` or `llvm-readtapi`. The SDK producer
selects and qualifies these tools. Recipes do not duplicate its provenance
or acceptance policy. An initial scoped bootstrap can select copied Apple
tools. The final SDK can select its own `llvm-install-name-tool` and
`llvm-readtapi` from the common LLVM recipe.

CMake 4.4.4nb4 retains its text-stub feature. The common Darwin rule uses
fixed Apple or LLVM arguments. Apple TAPI receives `stubify -isysroot`;
`llvm-readtapi` receives `--stubify`. Both receive the explicit output and
input paths. The selected cache entries prevent implicit TAPI or install-name
program discovery. No arbitrary command string is accepted.
Native policy appends the selected tools and TAPI kind to
`CMAKE_TRY_COMPILE_PLATFORM_VARIABLES`. It preserves package-added entries
and forwards the list itself for deeper children. `CMP0137` defaults to `NEW`
so project signatures also receive these values. A preset
`CMAKE_TRY_COMPILE_NO_PLATFORM_VARIABLES` causes an explicit error. Packages
that later set `CMP0137` to `OLD` or disable platform forwarding are outside
this contract and need separate repair.
The [Darwin tool check](tests/cmake-darwin-tools.py) covers quoted paths,
missing and invalid files, finite kinds, native/cross guards and source patch
replay. It does not execute either stub generator. Actual dylib and framework
checks remain required after LLVM builds. Other binary utilities and
compiler-specific IPO archivers need separate qualification.

The paired [Tcl/Tk 9.1 recipes](cross/tcltk.md) retain bundled extensions,
system SQLite and ZipFS. Tcl's ordinary native GCC16 package and host
generator contract pass. Platform branches, metadata and SQLite symbol
ownership pass causal checks. Full upstream tests and strict memory checks
retain documented failures; target GUI acceptance remains separate.

The [cwrappers archive repair](cross/cwrappers-unwrap.md) preserves sibling
directory paths in installed Libtool metadata. Actual native GCC16 wrapper
checks and bounded module memory checks pass; package integration is separate.

The [explicit Mach-O RPATH contract](cross/cwrappers-macho-rpath.md) keeps
only explicitly mapped loader tokens. Paired real wrapper controls preserve
ordinary path filtering. D-Bus package tests remain a separate gate.

The [RELRO link rule](cross/cwrappers-relro.md) adds the selected RELRO
flags to every wrapped executable and shared link. Recipes that ignore
`LDFLAGS` pass `check-relro` without recipe changes.

The [pkg-config sysroot contract](cross/pkgconfig.md) maps target dependency
headers and link paths to the SDK. Actual GCC16/CMake imported-target checks
preserve target runtime paths and unchanged native provider selection. Explicit
C++ imports retain the installed GCC16 runtime ABI.

The [mDNSResponder build contract](cross/mdns-build-tools.md) selects Apple's
current 2881.120.11 source and preserves the complete DNS-SD package. Target OS
selection, generator roles and a private-only logging operand are corrected.
Ordinary native/AArch64 GCC16 packages and 518 native API cases pass, including
strict Memcheck. Installed discovery and CUPS integration remain separate.

The [sysroot import contract](cross/sysroot.md#pinned-aarch64-base-and-comp-imports)
provides a pinned-manifest importer for OS-owned AArch64 `base` and `comp`
releases. It verifies provenance and hashes before isolated extraction.
The GCC16 compiler and target package remain separate inputs.

This profile prepares one common Python 3.15.1, Meson 1.12.1 and matching
LLVM/Clang/LLD 23.1.4 with upstream lit and [Perl 5.44](cross/perl.md) for the
GCC 16 / LLVM 23 / Mesa 26 dependency closure. The [Python package](python.md)
cross-builds on macOS. The earlier Python 3.14.8 package passed installed AArch64
VM consumers and 21 selected upstream suites. These results do not establish
Python 3.15 acceptance. Meson/Ninja also pass installed C/C++ consumers and focused
upstream tests in that VM. The installed [LLVM 23.1.3 core](cross/llvm-api-tests.md) passes C API, bitcode and four ORC JITLink lifecycles on CM5. Its rebuilt [Mesa consumer](../common-graphics/cross/mesa-llvm2313.md) also passes V3D/llvmpipe rendering and all 38 upstream invocations there. Full Clang/LLD cross packages pass ordinary staging checks; their target execution remains separate. The export itself installs no packages.

The [Linux/GCC16 runtime and SDK split](cross/llvm-linux-aarch64.md) passes both
full builds, exact installed payload checks and C API/ORC package lifecycle
acceptance in E34 VM. Its sealed host metadata helper agrees with all 16 target
query groups and passes Mesa's production LLVM guards. The
[Mesa26 consumer](../common-graphics/cross/mesa-linux-aarch64.md) passes installed
llvmpipe rendering, all 39 target invocations and package removal/reinstallation.

The native and cross profiles select the current canonical Ruby 4.0.7 provider.
Recursive host generators use native Ruby and `ruby40-asciidoctor`.
The [selection check](tests/ruby-selection.rb) queries actual pkgsrc metadata
for native, AArch64, amd64 and host recursion. It preserves compiler routing,
native-only barriers and the unrelated pkgsrc default. Ruby package builds
and target execution remain separate checks.

The common [SWIG 4.5.1 provider](cross/swig.md) retains all language backends,
839 templates and compressed CCache support. Its ordinary native GCC16 package,
upstream Python 3.15 example and closed-stderr compiler regression pass.
Strict memory checks retain upstream allocation findings; target packaging
and complete KiCad bindings remain pending.

The shared [zlib 1.3.2nb2 recipe](../../pkgsrc/devel/zlib/README.md) replaces the
vendored 1.3.1 sources with the verified current release. It preserves pkgsrc
Libtool naming and the complete gzip API. Two writer-seek repairs pass native
GCC16 regression and strict Memcheck checks. The ordinary AArch64 cross package
also passes installed VM compression, gzip, writer-seek, integrity and
removal/reinstallation checks with the runtime-only GCC16 provider.

The [bootstrap integration](cross/bsdtar-zlib.md) selects this registered zlib
package for bsdtar and pkg_install, including ordinary bootstrap. It removes
the obsolete embedded-source route. Export and native metadata checks pass.
Earlier bsdtar common-profile runtime evidence does not accept this dependency
change. Its ordinary bootstrap build and target execution remain separate.

The [ncurses 6.6nb3 cross roles](cross/ncurses-native-headers.md) separate
native generator headers and produce the target terminfo filename layout.
Full GCC16 AArch64 packaging and exact installed SDK readback pass.
Target `infocmp` reads the original database leaf and refuses damaged data.
All 15 numeric boundary values pass; paired target UBSan trap checks reject
the upstream reader and accept the repair. GUI and complete KiCad acceptance
remain separate.

Ordinary [FFTW and Readline packages](cross/README.md#installed-fftw-readline-and-ncurses)
also pass GCC16 AArch64 VM numerical, terminal input/history and package
removal/reinstallation checks. FFTW covers both precisions with pthread
and OpenMP. Readline uses ncurses 6.6; all 2899 installed terminfo entries,
including 1038 aliases, match the package and SDK. The cross-build Libtool
metadata repair remains pending. These checks do not establish KiCad acceptance.

The [protobuf 36.2 and Abseil 20260817.0 recipes](cross/protobuf.md) keep one
common runtime/SDK source provider and a separate native generator for cross
consumers. The cross protobuf runtime installs no target generator; the SDK
retains the complete development interface. Native packaging stays complete.
Source, host-tool and CMake metadata regressions pass. Abseil's ordinary package
passes both installed SDK consumers on AArch64, all 816 payload checks and
normal removal/reinstallation. The protobuf runtime package passes normal checks
and all twelve SDK payload entries; SDK packaging and target acceptance remain pending.
A bounded AArch64
source-probe regression verifies Abseil's NetBSD stack-trace repair: the same
consumer changes from zero frames to three non-null frames.

[Groff 1.24.2](../../pkgsrc/textproc/groff/README.md) includes a C23 function-prototype repair.
Its native macOS build renders the three Enchant manual pages as HTML.
The focused source check passes ASan/UBSan and preserves all errno cases.
The complete target package and graphical HTML pipeline remain unaccepted.

The common [Node24 recipe](node.md) uses Node.js 24.22.1 LTS. It retains the
existing shared-library configuration and portability patches. Native and cross
package acceptance remain separate.

The shared [Rust 1.99 host package](rust.md) keeps upstream runpaths and gives
its bundled Darwin LLVM a private name. It checks actual Mach-O imports for
cargo-c/librsvg builds. Its
[target std package](rust-target-std.md) installs into the same host sysroot and passes AArch64 VM consumers.

The [macOS cross-package path](cross/README.md) uses GCC16 and ordinary pkgsrc
packaging. Pkgconf 3.0.7, GNU M4 1.4.21, Libtool 2.6.2 and
[Binutils 2.47nb1](binutils.md) pass package checks
and [installed AArch64 VM acceptance](cross/validation.md). Cross package
metadata, alternate-root updates and target script paths have regressions.
The cross-tools check also queries pkgsrc's `archivers/gzip` recipe to keep
`INFO_FILES` enabled and select the target `install-info` provider.
The [common gzip 1.15 recipe](gzip.md) keeps that
interface and all helpers. Source and export checks do not accept native execution.
Binutils includes a tested DWARF32/64 line-table repair. Its acceptance
explicitly selects GNU as/ld; migration of the bootstrap GCC16 package's
hardcoded base-tool paths remains pending.
OpenSSL cross builds select complete upstream BSD targets instead of the
build host's uname; the [cross checks](cross/README.md) keep package and runtime acceptance separate.

The NSS 3.132 and NSPR 4.40 source pins use the common providers. The NSS
cross recipe selects the NetBSD target OS, architecture, release and
CPU. It builds nsinstall with the native compiler. Its narrow link branch removes target
linker flags and libraries only for that host helper. The
[host-tool regression](tests/nss-cross-host-tools.py) checks both target CPU mappings,
the native recipe path and a real Darwin link before and after the patch. It evaluates
the upstream `freebl/config.mk` Darwin guard with native and cross OS settings. It also
copies a binary payload with `nsinstall` and checks its bytes, hash, file type and mode.
It does not build or accept target NSS libraries. The upstream cross .chk skip remains;
this does not establish shlibsign or FIPS acceptance.
The [NSS runtime consumer](tests/nss-runtime/README.md) adds a bounded no-database
API check. Earlier NSS 3.129nb2 amd64 packaging and a staged physical NetBSD 11 run pass,
including checked module loading and consumer-only UBSan. Target package
installation, TLS, FIPS and a complete library memory check remain separate.
Current NSS 3.132 and NSPR 4.40 package and target acceptance remain pending.


The [cross Libtool path check](cross/libtool-runtime-paths.md) repairs an SDK
runtime path leak through pkgsrc passthrough directories. A genuine GCC16 C++
shared-library consumer verifies target RPATH and installed Libtool metadata.
Header and link-time search paths, native mappings and ABI remain unchanged.

The [LLVM Python migration](cross/llvm-python315.md) keeps one lit provider and
updates installed Clang helper interpreters. It records package changes separately
from the original compiler build.

The profile owns full Python, Meson and
[LLVM family recipes](llvm-family.md), based on
pkgsrc `fff4deb639a1a640476203c80f752fb77b6cb14b`. It composes the established
[development toolchain](../development-toolchain/README.md) export without
changing GCC bootstrap options. The common MAKECONF selects
the prepared GCC16 package for new native builds. LLVM family recipes also
prepare scoped native Clang defaults. The default
export and `development-toolchain` mode retain their common GCC16 selection.
Standard profiles preserve the complete pinned gmake and dtc providers.
The incomplete [board-firmware toolchain checkpoint](../development-toolchain/README.md#source-and-preparation)
requires an explicit opt-in and does not affect these exports.
The lit recipe now selects shared Python315 for native and cross packages.
Its [selection and source checks](llvm-family.md#upstream-lit-and-focused-checks)
pass on the host; target wheel installation remains separate.

The [common graphics profile](../common-graphics/README.md) composes these
tools with canonical MesaLib/libdrm source recipes. It does not change this
profile's exported package set or establish an installed graphics stack.

This MAKECONF selects an installed native target compiler. For compilation
on macOS, use the [cross-package configuration](cross/README.md) with the
[GCC16 cross recipe](../development-toolchain/cross/README.md). Its host tools
and target sysroot are separate from this native pkgsrc selection policy.

The common CMake provider uses stable 4.4.4 from [NetBSD pkgsrc commit
`5cd745c4794fcf99c8a789dfc750df5b89be35c8`](https://github.com/NetBSD/pkgsrc/commit/5cd745c4794fcf99c8a789dfc750df5b89be35c8).
The release, checksums and module file list apply to native and cross builds.
The uniform nb1 revision repairs GCC16 compilation of the Mach-O architecture
reader. Header and API selection use the same macOS deployment-target guard.
The [module regression](tests/cmake-macho/README.md) checks both deployment
branches and independent Mach-O fixtures. Full packaging remains a separate gate.

Native Darwin defaults use the common Mach-O load-command checker for package
requirements. It resolves each image's own runpaths to concrete providers.
This records concrete GCC16 runtime paths for ordinary `pkg_add` checks.
Unresolved inherited runpaths remain errors. Other host and cross defaults
retain their existing selection. The selected tools must provide `file`,
`lipo` and `otool`.

`tests/macho-native-metadata.py` checks the actual default selection with
BSD make. Its optional package-stage check verifies real `REQUIRES` values
without installing a package. It does not qualify a native toolset.

The [shared bundled nawk](nawk.md) keeps one tagged source and one parser
payload for bootstrap and ordinary packages. Its source and metadata gates
remain separate from compiler and runtime acceptance.

## Prepare and select

```sh
git submodule update --init --depth 1 upstream/pkgsrc
# Provide a verified source-data export at /absolute/new-pkgsrc. See the root README.
```

The destination must be new. The export rejects missing or changed patches
before it creates the destination. Original archive URLs and SHA256 are in
[sources.tsv](sources.tsv); recipes record BLAKE2s, SHA512, size and pkgsrc's
RCS-filtered patch SHA1. Meson uses its release asset, not GitHub's generated
source tarball. No archives, build outputs or local machine settings belong
in Git.

A later native build's private MAKECONF includes the exported
`EMBERBSD-COMMON-TOOLS-MK.CONF`. Include `EMBERBSD-DEVELOPMENT-MK.CONF` only
when its documented C/C++ options are also intended. The common-tools file
requires Python 315, Meson >=1.12.1 and pkgsrc GCC for native NetBSD 11/AArch64,
with final `LOCALBASE=PREFIX=/usr/pkg` and one worker. It sets `GCC_REQD+=16.2`,
`PKGSRC_COMPILER=gcc`, `USE_PKGSRC_GCC=yes` and `USE_NATIVE_GCC=no`.
`GCC_REQD` is a major.minor floor, not an exact installed-version check;
the prepared recipe supplies `gcc16-16.2.0nb1`. The standard
`BUILDLINK_API_DEPENDS.gcc16+=gcc16>=16.2.0nb1` dependency requires the
[C++ modules allocation repair](../development-toolchain/modules-portability.md). The pinned pkgsrc comparison
uses the same major.minor format for a detected GCC version. The prepared
pkgsrc overlay keeps `16.2.0` from becoming an unsupported patch-level floor.
Request `GCC_REQD=16.2`. Compatible command-line floors
and `ccache gcc` / `distcc gcc` chains remain supported. Incompatible compiler,
native-compiler, runtime and dependency-method overrides fail explicitly.

The complete compiler package must already be bootstrapped with
`EMBERBSD-DEVELOPMENT-MK.CONF` and native GCC12. Do not include common tools
while building GCC16 or its bootstrap closure. After installation, include
common tools for new consumers; pkgsrc obtains `/usr/pkg/gcc16` from the
installed package's file metadata. Missing metadata retains the normal GCC16
dependency and does not prove a compiler executable exists.

The package includes its own runtime through `always-libgcc`.
`BUILDLINK_DEPMETHOD.gcc16=full` keeps that complete package as a consumer
runtime dependency, including C-only consumers. The public
`.MAKEFLAGS: USE_PKGSRC_GCC_RUNTIME=no` setting is intentional: pinned
`gcc.mk` otherwise forces this knob to `yes` on NetBSD, adding a separate
`gcc16-libs` dependency and custom runtime specs. Here the selected driver
and pkgsrc RPATH select the complete package's own runtime. `no` disables
that separate provider; it does not select the base GCC12 runtime.
Native compile/link/runtime checks must verify the actual loaded libraries.
The original [native selection fixture](tests/native-compiler-selection/README.md) passes
on physical Orange Pi Zero 3W: actual pkgsrc wrappers compile and package C/C++,
and the installed consumer loads the selected GCC16 runtime. The updated
fixture passes with installed nb1 through the durable
`/etc/mk.conf` default on the same board. The
[compiler validation](../development-toolchain/native-validation.md) records
current math dependencies, focused LTO checks and remaining compiler limits.
The [reversible development defaults](development-defaults.md) now select
installed nb1 in fresh login/SSH sessions and ordinary pkgsrc builds on that
board. The durable common include is copied from this committed profile.
Base `/usr/bin/cc` remains available through the explicit private bootstrap
configuration. Existing GUI consumer migration and fresh-image acceptance
remain separate gates.

The opt-in `lang/python/pyversion.mk` guard rejects unsupported consumers
and older command-line interpreter overrides. Repair those consumers through
Ports; do not select an old interpreter or install another one beside this
stack. This source stage does not install those interpreter packages. Later
package migration must check their reverse dependencies.

Run the focused metadata gate against a prepared common-media export:

```sh
BMAKE=/absolute/bmake sh profiles/common-build-tools/tests/compiler-selection.sh \
    EXPORTED_PKGSRC NEW_WORK
```

It executes complete pinned pkgsrc compiler/buildlink/dependency metadata
with declared target and installed-package receipts. It checks ordinary C/C++
consumers, LLVM/graphics/media composition, policy overrides and native GCC12
bootstrap boundaries. It does not execute a target compiler or accept native
packages. Missing BSD make fails this gate.

Use the separate native fixture after installing the documented prerequisites;
it exercises real target compilation and removes only its own test package.

The [Vala array copy contract](cross/vala.md) repairs a missing NULL slot
for copied nullable value arrays. Paired host GCC16 generators and the
unchanged upstream regression pass ASan/UBSan after the repair. Cross package
and target acceptance remain separate.

## Patch decisions

Original pkgsrc identifiers, ownership and upstream licenses are preserved.
Local adaptations and shell/C contracts are AI-assisted EmberBSD work;
these adaptations have not been submitted or accepted upstream.

| Python patch | Decision and reason |
| --- | --- |
| `Include_pymacro.h` | Retain NetBSD/SunOS assertion; keep the C11 branch an integer constant expression on GCC16 hosts. |
| `Lib___pyrepl_terminfo.py` | Retain NetBSD terminfo.cdb via ctypes and tmux alias. |
| `Lib_ctypes_util.py` | Retain PREFIX/X11 clang search and conditional SunOS lookup. |
| `Lib_sysconfig_____init____.py` | Retain coupled platform-only sysconfig and config-directory naming. |
| `Makefile.pre.in` | Retain install ordering, optimization levels 0/1, naming and suppression of generic libpython3.so; correct the policy description. |
| `Modules_faulthandler.c` | Drop the inherited manual-count workaround after eight actual native GCC16 initializer variants and pointer rejection pass; retain the upstream array-derived count. |
| `Modules_readline.c` | Retain selected readline portability; editline is not accepted here. |
| `Modules_socketmodule.c` | Retain conditional SunOS declaration. |
| `Misc_python-config.in` | Include the shared-library search directory for installed embedding, matching the shell script. |
| `Lib_test_test__sysconfig.py` | Check retained pkgsrc `.so` naming and actual loader acceptance on NetBSD/Linux; retain tagged loader ABI and priority checks. |
| `configure` / `configure.ac` | Retain packaging/UUID hunks; recognize NetBSD/AArch64 in both cross-host checks, preserving unknown-host rejection. |
| `Tools_build_generate-build-details.py` | Describe the target NetBSD platform, version, ABI, loader suffixes and installed static library. |

The Python PLIST adds the two upstream test modules `test_capi/test_slice`
and `test_free_threading/test_context`, each with source and optimization
levels 0/1, and removes the obsolete `idle_test/test_zzdummy_user` entries.
Buildlink's config directory matches the installed
`config-3.14` directory. No generic libpython SONAME alias is created.
The recipe uses upstream's shipped `configure`, without autoreconf;
the new cross-host cases are also maintained in `configure.ac`. Regeneration
of the inherited pkgsrc changes still needs a separate synchronized review.
The [Python cross recipe](python.md) explains the host interpreter, OpenSSL
sysroot and installed metadata adaptations. NetBSD still selects pkgsrc libuuid instead
of its system's UUIDv4-only interface.

| Meson patch | Decision and reason |
| --- | --- |
| `compilers_detect.py` | Retain only `cython-3.14`; upstream already supplies stdin language, so drop the suffix heuristics. |
| `compilers_mixins_gnu.py` | Retain conditional SunOS as-needed handling. |
| `dependencies_dev.py` | Explicit LLVM config-tool selection fails closed and cannot fall back through CMake. |
| `linkers_linkers.py` | Retain SunOS thin-archive restriction; drop unconditional rpath-link override. |
| `modules_pkgconfig.py` | Retain foreign pkg-config directory placement. |
| `scripts_depfixer.py` | Drop NetBSD ELF-fixup bypass; retain upstream install RPATH processing. |

Machine-file `llvm-config` entries retain upstream precedence over the
`LLVM_CONFIG_PATH` environment variable, including failure. Without a
machine entry, an explicit environment path must be absolute and must meet
the requested version. Missing, invalid or wrong-version tools cannot fall
back to suffixed/default tools or CMake. Native/build-machine selection may
use that environment path; a cross target uses its own machine file and
never imports the native environment selection. With no explicit selection,
upstream automatic dependency discovery remains available.

## Reproducible source checks

Save original archives in a private directory, using the URLs in sources.tsv.
The source check requires a C/C++ compiler, Python >=3.10 to run upstream
Meson, and an OpenSSL implementation with BLAKE2s support. Set `PYTHON`,
`CC`, `CXX`, `OPENSSL` or `BMAKE` explicitly when necessary.

```sh
sh profiles/common-build-tools/tests/source-profile.sh \
    /absolute/verified-distfiles /absolute/new-source-check
```

The test verifies archives and all 19 patches through actual pkgsrc
`checksum.awk`, rejects corrupted archives, unfiltered patch hashes,
missing patches and repeated application, and applies the full series
forward with zero fuzz. It checks PLIST additions and restored upstream
ELF fixup, exports exact recipes, compares unchanged GCC recipe composition,
and rejects existing destinations and unknown profiles. Logs and extracted
sources remain in the private output directory.

The shared work-reference check opens one append stream after the first
retained file. It preserves skip patterns, existing list entries, diagnostics
and failure status. Empty and fully skipped inputs do not create a new list.
Run the real BSD make and mksh regression with a stock pkgsrc input:

```sh
BMAKE=/absolute/bin/bmake MKSH=/absolute/bin/mksh python3 -B \
    profiles/common-build-tools/tests/check-wrkref.py \
    /absolute/stock-pkgsrc /absolute/new-wrkref-check
```

The regression compares actual file lists and grep diagnostics. Descriptor
offsets distinguish repeated opens from one shared append description. Printing
comments keep stdout. A pre-opened parent descriptor stays unchanged. It also
checks empty inputs, duplicate and spaced paths, skip globs, pre-existing lists,
and open/read/write failures. The inherited left-pipeline read-failure status
is recorded as it is. The test does not add a new failure-propagation policy.

The named `llvm-source` third argument checks the LLVM family, metadata,
Clang command traces and upstream lit, while comparing unchanged common
recipes. Its source/native boundaries are documented in [llvm-family.md](llvm-family.md).

The named `python-source` third argument limits a follow-up to Python archive,
canonical patch series, negative checksum/application cases, target metadata and
exact exported recipe. Set `PYTHON` to the selected SDK Python (3.12 or newer).
It explicitly excludes unchanged Meson/GCC/native contracts from its result;
omitted tests are not counted as passed. The default `all` path calls the same
current Python gate with its normal common pkgsrc export.

Actual Meson CLI fixtures exercise C++20 through a compiler proxy and ten
LLVM selection cases. Fake LLVM metadata proves tool choice/error handling;
it does not prove LLVM headers, libraries, ELF linkage or execution.
`MESON_SELECTION_CASE=missing` isolates the causal baseline: the original
pkgsrc patch accepts a missing path using `llvm-config-64`; the new patch
refuses it. The fixture preserves the actual configure statuses.

`tests/python-selection.sh EXPORTED_PKGSRC NEW_WORK` parses the actual
pkgsrc selection block with BSD make. It checks default 315, rejected old
CLI selection and unsupported/incompatible consumers. If BSD make is absent,
the source check prints an explicit SKIP. Native NetBSD BSD make has passed
the five selection cases; full package parsing/builds remain required.

The faulthandler compile gate is independently usable by a native parent:

```sh
CC=/absolute/current-cc sh profiles/common-build-tools/tests/faulthandler-macro.sh \
    /absolute/fully-patched-python /absolute/pristine-python /absolute/new-macro-check
```

It extracts the actual record/handler array and upstream count initializer,
includes the patched production pymacro header, covers optional SIGBUS/SIGILL
combinations with both actual HAVE_SIGACTION layouts, and requires pointer
misuse to fail compilation. The signal typedefs are extracted from upstream;
only the declaration-only visibility macro for unrelated prototypes is supplied.

The Darwin os_log gate checks the CPython 3.15 Apple system log guard:

```sh
GCC_CC=/absolute/gcc16 sh profiles/common-build-tools/tests/python-darwin-os-log.sh \
    /absolute/fully-patched-python /absolute/pristine-python /absolute/new-os-log-check
```

`os/log.h` uses the Clang-only `__builtin_os_log_format`. The recipe patch
disables the Apple system log when the compiler lacks that builtin. The gate
extracts the actual guard and builds the upstream call shape with GCC,
`-Werror` and `-fanalyzer`. It requires the pristine guard to fail. It prints
SKIP on hosts other than Darwin.
Host builds select the NetBSD
macro branch after their system headers; they are not NetBSD execution proof.
The sole suppressed warning covers intentionally omitted trailing record
fields, as in the production initializer. Native GCC16 passed all eight
variants and pointer rejection, allowing removal of the manual count.
LLVM23 should check the same contract. See [native evidence](native-evidence.md)
for the bounded result; this is not a native Python package acceptance.

## Initial Darwin archive tools

`EMBERBSD_DARWIN_TOOL_PHASE` defaults to `full` for native Darwin.
The explicit `initial` phase permits absent Darwin libtool, install-name-tool and TAPI selectors.
Provided selectors still require existing absolute executable files.
It preserves the selected five binutils, sysroot and compiler routes.
Linux, NetBSD and cross routes remain unchanged.

The complete CMake build keeps its normal static-library AR/RANLIB rules.
Initial mode suppresses discovery of the three future Darwin tool outputs.
An actual install-name or RPATH update without its selected tool fails during generation.
Shared-library `ENABLE_EXPORTS` without TAPI also fails, including the global initializer.
Executable exports keep their upstream behavior.
The phase and existing package platform variables propagate through both `try_compile` signatures.
The existing default CMP0137 NEW policy and preset opt-out refusal remain required.
A later package override to OLD or platform-variable opt-out is outside this acceptance boundary.

LLVM initial mode selects `LLVM_DARWIN_ARCHIVE_TOOL=ar` and static LLVM linkage.
The upstream libtool route remains the default.
Backends, options, dependencies and PLIST remain complete.
The SDK controller owns the fixed five-target operation and exact LLVM dependency closure.
This profile does not qualify the uninstalled LLVM package or future graph nodes.

Run `tests/cmake-initial-source.py` with `--cmake-source` and `--llvm-source`
pointing to fully patched sources, and `--pkgsrc` to the same prepared export.
It checks the installed module's PLIST entry. It executes no CMake or compiler.
`tests/cmake-initial-metadata.py --help` describes the explicit owned make tuple,
contained environment, private MAKECONF and exact command-record interface.
It checks the common helper through standalone BSD make queries.
It does not run a package target or qualify the fixture as an ordinary provider.
`tests/cmake-initial/` retains operation fixtures for the later native configure gate.
Native CMake, nested configure, installation, LLVM output, analysis and memory gates remain pending.

Origin: EmberBSD contributors. AI assistance was used for this common source change and its checks.

## Native acceptance still required

Use staged packages and normal pkgsrc checks; do not bypass missing files,
WRKREF, RPATH, checksum, dependency or upstream test failures.

- Meson: remaining upstream groups, explicit native/cross selection against
  installed LLVM23 and a shared-library fixture with transitive PREFIX dependencies.
  Installed C/C++ consumers, basic install-RPATH and the focused upstream group
  are [accepted in the AArch64 VM](cross/validation.md).
- Common consumers: current setuptools/wheel/Cython dependencies and LLVM23
  generators. Installed Mesa26 passes the graphics profile's package/runtime
  checks; desktop consumer migration remains in that profile.

Native libpython and all C++ consumers must use the selected common runtimes.
Source/host checks do not establish those package, ELF or Mesa gates.

The [common SQLite 3.54.1 recipe](../../pkgsrc/databases/sqlite3/README.md)
replaces both the older pkgsrc provider and the former robotics-only recipe.
All consumers use `databases/sqlite3`; release selection and source-family
checksums move together. See its checks for the current acceptance boundary.
