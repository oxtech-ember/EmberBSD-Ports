# Native GCC16 on macOS AArch64

Build-host programs need a native GCC 16.
Upstream GCC 16.2.0 does not support `aarch64-apple-darwin`.

## Source and licence

The Darwin port is maintained by Iain Sandoe in the
[gcc-16-branch](https://github.com/iains/gcc-16-branch) repository.
Homebrew publishes the difference between that branch and the GCC 16.2.0
release as a source diff:

| Field | Value |
| --- | --- |
| Upstream branch | https://github.com/iains/gcc-16-branch |
| Published diff | homebrew-core commit `4a334d2f90f786c3fc86cbc9cf72b2f13961b078` ("gcc 16.2.0"), `Patches/gcc/gcc-16.2.0.diff` |
| Size | 205825 bytes, 73 files |
| SHA256 | `578a78ae0bc62a02f260b6a20c7f23e71deee16ed644e9cb5619247be4df5a71` |

The diff is GCC source. It has the GCC licence: GPLv3 or later with the GCC
Runtime Library Exception 3.1. Ports uses only this source diff. It does not
use Homebrew binaries or bottles. [sources.tsv](sources.tsv) pins the URL and
SHA256; the recipe `distinfo` pins BLAKE2s, SHA512 and the size.

## Recipe change

[gcc-darwin-host.patch](patches/gcc-darwin-host.patch) prepares the shared source for `lang/gcc16`. Native tool and bootstrap
selection remains conditional on Darwin:

- `PATCHFILES` applies the diff with `-p1` before the pkgsrc patches.
  The diff also adds Darwin COBOL support in `libgcobol/configure.tgt`. That
  hunk conflicts with `patch-libgcobol_configure.tgt`, and the recipe does not
  build COBOL. `PATCH_DIST_CAT` drops that one file section.
- Darwin requires an accepted SDK GCC16 bootstrap seed. The recipe rejects
  `PKGSRC_COMPILER=clang` and missing seed inputs. GCC builds stage 1,
  rebuilds itself, and compares stages 2 and 3.
- The recipe selects explicit LLVM MC, Mach-O LLD, dsymutil and
  `llvm-lipo` paths. libgcc creates `libgcc_s` with `LIPO_FOR_TARGET`; its
  default is a bare `lipo`, which no Ports package provides.
  libstdc++ `scripts/make_exports.pl` runs a bare `c++filt -_`, so the recipe
  creates the `c++filt` tool from `llvm-cxxfilt`.
  [gcc-darwin-llvm-mc.patch](patches/gcc-darwin-llvm-mc.patch) adds
  `--with-darwin-assembler=llvm-mc` to GCC. It changes the driver assembler
  arguments and the configure assembler probes together.
- [gcc-darwin-xpc-choose.patch](patches/gcc-darwin-xpc-choose.patch) adds
  the `darwin_xpc_choose` fixincludes hack. macOS `<xpc/base.h>` pastes the
  value of `__has_attribute` onto `_XPC_CHOOSE_` and defines only the 0 and
  1 cases. GCC reports standard versions for `deprecated` and `noreturn`
  (202311 in C, 200809 and 201309 in C++), so every GCC translation unit
  that includes `<xpc/xpc.h>` failed, for example Python's `_scproxy`.
  The patch carries `fixincl.x` regenerated with AutoGen 5.18.16 and a
  `make check` baseline.
- Darwin target libraries use the macOS iconv, not a GNU libiconv in
  `${LOCALBASE}`. `COMPILER_RPATH_FLAG` is `-L` on Darwin, so the common
  `LDFLAGS_FOR_TARGET` filter passed `-L${LOCALBASE}/lib` to the target
  libraries. libstdc++ configure then selected GNU libiconv and its
  `libiconv_open` names. The Darwin recipe passes only `-Wl,-z` options to
  the target libraries. `BOOT_LDFLAGS` for the stage 2 and 3 compilers is
  unchanged.
  The target C and C++ flags also drop `-I${LOCALBASE}` and buildlink
  include paths, because the GNU `iconv.h` there renames `iconv_open`.
  iconv is not part of libSystem.
  [gcc-darwin-libstdcxx-iconv.patch](patches/gcc-darwin-libstdcxx-iconv.patch)
  records `-liconv` in the libstdc++ `format.o` object (`LC_LINKER_OPTION`).
  A `-static-libstdc++` link that uses `std::format` locale conversion then
  needs no extra library option.

NetBSD and cross builds also apply the pinned source diff: the common LLVM-MC
patch references Darwin files absent from the release archive. The Python
source preparer uses the same prerequisite and COBOL exclusion.
The new assembler mode is opt-in and accepts only AArch64 Darwin targets.
The current source draft is a default-CPU pilot. It does not establish a
qualified native toolset or an accepted Darwin GCC package.

## Producer inputs

The SDK owns seed acceptance, the producer plan and native ABI inputs.
The shared Ports recipe owns the GCC source and command language.
The SDK must validate its accepted seed before it starts pkgsrc metadata.
It must bind these make variables in the initial producer environment:

| Make variable | Accepted SDK value |
| --- | --- |
| `EMBERBSD_GCC16_SEED_CC` | GCC seed C command, with its fixed binding and ABI arguments |
| `EMBERBSD_GCC16_SEED_CXX` | GCC seed C++ command, with its fixed binding and ABI arguments |
| `EMBERBSD_GCC16_SEED_CPP` | GCC seed preprocessor command, with its fixed binding and ABI arguments |
| `EMBERBSD_GCC16_LLVM_MC` | Qualified `llvm-mc` executable path |
| `EMBERBSD_GCC16_LD64_LLD` | Qualified Mach-O linker path invoked as `ld64.lld` |
| `EMBERBSD_GCC16_DSYMUTIL` | Qualified `dsymutil` executable path |
| `EMBERBSD_GCC16_AR`, `EMBERBSD_GCC16_RANLIB` | Qualified archive tool paths |
| `EMBERBSD_GCC16_NM`, `EMBERBSD_GCC16_STRIP` | Qualified symbol tool paths |
| `OSX_SDK_PATH` | Explicit accepted native ABI sysroot path |
| `EMBERBSD_GCC16_DARWIN_SDK_VERSION` | SDK version from that accepted native ABI metadata |

The producer also sets `PKGSRC_COMPILER=gcc` before pkgsrc reads the recipe.
These values are inputs to an accepted SDK plan. A make variable name or a
successful version query does not qualify a seed. The recipe does not create
another descriptor format. It does not search `PATH` for a missing compiler.

The recipe passes `--with-as`, `--with-ld` and `--with-dsymutil` to GCC.
Fresh GCC embeds these exact paths. It uses its source-owned MC mode.
The recipe also sets `--with-darwin-sdk-version` from the accepted ABI metadata.
In MC mode, the default linker receives `-platform_version macos MIN SDK`.
This does not require a user `-fuse-ld` option. Cctools mode stays unchanged.
The generic configure default `0.0` means an unknown SDK version. It is not
a claim about the SDK. A producer with known metadata must pass its real version.
It does not require an external specs override for ordinary use.
The recipe now depends on common `devel/lld`, which depends on matching `lang/llvm`.
It embeds `${LOCALBASE}/bin/llvm-mc`, `ld64.lld` and `dsymutil` from those packages.
Seed compiler commands retain their separate accepted bootstrap routes.
Choose the permanent common SDK prefix before building GCC.
Do not move this prefix or replace its tools with initial binary inputs.

The scoped Darwin bootstrap profile links initial C++ providers with
`-static-libstdc++ -static-libgcc -nodefaultrpaths`.
These are producer link options, not ABI flags.
The last option suppresses GCC's default compiler-library runpaths.
The GCC recipe preserves this option only for the scoped bootstrap profile.
Other Darwin callers retain the existing wrapper removal rule.
Explicit package runtime search paths remain unchanged.
This policy still needs native C++ exception and final runtime-closure acceptance.
The compiler's ordinary user-link defaults remain unchanged.

CMake uses the existing common binutils fragment for its own bootstrap and consumers.
The SDK selects native `libtool_darwin`, `install_name_tool` and `llvm_readtapi` roles.
The last role fixes `EMBERBSD_DARWIN_TAPI_KIND=llvm-readtapi`.
The same pinned resource launcher runs C/C++ final links and reaches `try_compile` children.
It does not wrap compilation or archive creation.

Run `tests/darwin-native-provider.py --gcc-source /absolute/patched-gcc-source`
with Python for the finite source checks. This does not compile or qualify GCC.
Run `tests/darwin-libstdcxx-iconv.py --cxx /absolute/gcc16/bin/g++
--objdump /absolute/bin/llvm-objdump --work /absolute/new-dir` against an
installed GCC. It links a `std::format` program with `-static-libstdc++` and no
iconv option, runs it, and checks that it loads only system libraries.
GCC built by the previous recipe fails with undefined `libiconv_*` symbols.
It must provide the other configure and build tools from its accepted closure.

Use the [initial make binding](../common-build-tools/bootstrap/README.md)
when a seed make has external makefile or shell defaults. It retains the
complete upstream rules and binds an explicit shell before metadata reads.
It does not qualify an initial make binary as an ordinary native tool.

## Shared link resource

[gcc-host-link-launcher.patch](patches/gcc-host-link-launcher.patch) adds
an optional `GCC_HOST_LINKER_LAUNCHER` prefix to GCC's `LINKER` and
`LINKER_FOR_BUILD` assignments. An absent or empty prefix preserves their
original command text. The patch does not change `CC`, `CXX`, `COMPILER`,
compiler flags or archive commands. It retains each bootstrap stage's
selected compiler and the existing `HOST_LIBS` branch.

The Darwin recipe exports the accepted `EMBERBSD_GCC16_LINKER_LAUNCHER`
as `GCC_HOST_LINKER_LAUNCHER` in the make environment. GNU make retains this
environment input through recursive bootstrap stages. The SDK constructs
the complete prefix from its pinned control-plane Python, its existing
`scripts/link-launcher.py`, and the common lock root and resource context.
The command ends with `--`. It does not introduce a compiler wrapper or
a new native Python provider.

`LLINKER` inherits `LINKER`. This route covers the C, C++, Objective-C,
Objective-C++, Fortran and LTO frontend links, GCC drivers and tools,
native build generators, and `libgdiagnostics`. Keep GCC's optional local
frontend mutex unchanged. The SDK launcher owns the common heavy-link
resource for each foreground link. The outer parallel build must retain
its source/input and work leases without holding this same exclusive
resource. Otherwise the nested launcher cannot proceed.

Target runtime libraries, including `libgcc` and `libstdc++`, use separate
make or libtool link rules. This hook does not serialize those smaller
links. The SDK must retain its accepted worker budget and memory-pressure
control. This source route does not establish their runtime memory use.

Use [the finite route check](tests/gcc-native-link-route.py) with the exact
patched GCC Makefile before and after this patch. It checks the three
driver assignments, exact empty-prefix behavior and unchanged compilation.
It can prepare make fixtures with surrogate Python work commands for a
separate accepted native make/launcher test. That test must show parallel
compile work and serialized link work. A source-only pass does not prove
the full GCC build graph, bootstrap comparison or a native SDK result.

```sh
python3 profiles/development-toolchain/tests/gcc-native-link-route.py \
  source BEFORE_MAKEFILE AFTER_MAKEFILE \
  --new-fixtures /absolute/new-fixtures
```

Run the prepared fixtures only through the accepted SDK execution context.
Bind `CC`, `CXX` and `CXX_FOR_BUILD` to the same SDK control-plane Python,
this test script and its `record` subcommand. Bind `EVENTS` to a new owned
event file. Use the accepted GNU make command with four workers and its
selected shell. Set `GCC_HOST_LINKER_LAUNCHER` to the SDK's exact resource
prefix. The `after.mk` events must pass this script's `verify` subcommand.
The `before.mk` control must fail verification because its links overlap.
Use a separate new work directory for each case. The surrogate commands
do not compile sources or qualify a native tool provider.

## Fixed bootstrap binding

An existing seed can have Apple assembler arguments in its built-in specs.
The bounded input
[darwin-llvm-mc-seed.specs.in](bootstrap/darwin-llvm-mc-seed.specs.in)
adapts that seed without replacing its linker command.
The selector is `ports-gcc16-darwin-llvm-mc-seed-v1`.
It is bootstrap-only. It does not admit arbitrary `-specs` files.

An accepted plan pins the Ports revision, template path and SHA256.
It pins a deployment value and the exact instantiated file SHA256.
The only template substitution is `@DEPLOYMENT@`.
The initial pilot uses `26.0`.
The SDK compiler command must contain all four arguments in this order:

```text
/absolute/selected/gcc
-B/absolute/selected/driver-prefix/
-specs=/absolute/pinned/seed.specs
-mmacosx-version-min=26.0
```

Use the corresponding selected driver for C++ and preprocessing.
Append the separately accepted native ABI arguments.
The explicit deployment argument is required. The SDK must reject its absence.
A template alone cannot distinguish an explicit value from a driver default.
The specs reject any explicit `-fuse-ld` option. They insert `-fuse-ld=lld`.
They reject a conflicting deployment, CPU, architecture or tuning request
before the frontend starts. The pilot supports the default `apple-m1`
CPU only. Unsupported requests fail. They are not silently removed.

The assembler receives `--filetype=obj`, a deployment-qualified
`--triple=arm64-apple-macosx26.0` and `--mcpu=apple-m1`.
The normal C, C++, assembly, preprocessed assembly and pipe paths still use
the GCC assembler command. `collect2` still controls the final link.
The binding preserves the library, start-file, constructor and LTO specs.
It does not prove that the emitted assembly or GCC LTO objects work with MC.

## Mach-O LLD platform binding

The initial v1 template above preserves the seed's legacy platform option.
LLVM 23 Mach-O LLD recognizes that option, but derives its target only from
`-platform_version`. Use the fixed v2 template
[darwin-llvm-mc-lld-seed.specs.in](bootstrap/darwin-llvm-mc-lld-seed.specs.in)
for this linker. The selector is `ports-gcc16-darwin-llvm-mc-seed-v2`.
Keep the v1 file for existing pinned inputs.

The only v2 substitutions are `@DEPLOYMENT@` and `@SDK_VERSION@`.
The deployment is `26.0`. The SDK version is the installed macOS SDK, which
is currently `27.0`. The SDK accepts only versions that it records with an
exact instantiation hash, currently `27.0` and `26.5`; see its
`docs/bootstrap-seed.md`. Bind the SDK version to the exact accepted ABI
metadata, such as its inventoried `SDKSettings.json` Version.
Do not query Xcode tools or infer a version from a directory name.
Pin the template and instantiated hashes in the accepted SDK plan.
Keep the four-argument driver prefix shown above.

V2 appends `-platform_version macos MIN SDK` to the inherited `link` spec.
It keeps the complete upstream `link_command`, `collect2`, library, start-file,
constructor, LTO and dsymutil selection. The inherited legacy platform option
has the same deployment value. LLD parses it without deriving a platform.
No linker diagnostics or verification options are disabled.

Driver `-###` controls compare C and C++ executable, static, shared, relocatable,
no-standard-library, no-default-library, LTO and debug plans. Removing the one
modern platform tuple must restore the previous `collect2` argv exactly.
Deployment, explicit linker selection and unsupported CPU requests must fail.
These are metadata checks. They do not establish a successful link or runtime.
Real static and relocatable Mach-O support remain separate checks.

## Linker identity and feature probes

In this GCC16 Darwin port, `collect2 -fuse-ld=lld` selects `ld64.lld`.
An accessible compiled-in `DEFAULT_LINKER` can take precedence over `-B`.
Inspect the exact seed. Do not assume that every seed permits this binding.
GCC16's `-print-prog-name=ld` query does not apply the `lld` suffix in the
same way as `collect2`. A bounded seed receipt can therefore record a nominal
`driver-prefix/ld` query and a selected `driver-prefix/ld64.lld` executable.
The former is query evidence only. Do not put it in `LD` or `LD_FOR_TARGET`.
Require an actual child-execution record for the latter before accepting a
completed seed pilot or an ordinary output toolset. The first bounded pilot
can start from explicitly accepted scoped seed inputs and a pinned plan.
That input acceptance does not claim a successful pilot or ordinary toolset.
Matching canonical files or hashes does not prove the selected LLD flavor.
LLD uses its invocation name: `ld` selects ELF; `ld64.lld` selects Mach-O.
Fresh GCC's explicit `--with-ld=/absolute/ld64.lld` removes this ambiguity.

The source patch gives configure probes the MC object-file arguments too.
It tests `.build_version` independently from Apple's
`-mmacosx-version-min` assembler option. It does not force capability results.
It keeps the source and shipped configure script changes together.
The shipped script was adapted directly; regeneration with GCC's required
Autoconf version remains a source-consistency check before package acceptance.

The command mapping follows primary sources:

- [GCC16 Darwin port](https://github.com/iains/gcc-16-branch).
- [LLVM MC 23.1.4 command source](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.4/llvm/tools/llvm-mc/llvm-mc.cpp).
- [LLVM MC command flags](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.4/llvm/lib/MC/MCTargetOptionsCommandFlags.cpp).
- [Darwin assembly parser](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.4/llvm/lib/MC/MCParser/DarwinAsmParser.cpp).
- [Mach-O LLD options](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.4/lld/MachO/Options.td)
  and [LLD invocation dispatch](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.4/lld/Common/DriverDispatcher.cpp).

## Verification

The metadata regression needs no build. It checks the Darwin diff, its
checksums, the COBOL filter, the GCC-only seed gate and the explicit tool
selection. It checks that the cross recipe receives the same prerequisite diff without
the native Darwin command selection:

```sh
BMAKE=/absolute/bmake sh profiles/development-toolchain/tests/darwin-host.sh \
    /absolute/prepared-pkgsrc /absolute/darwin-mk.conf \
    /absolute/cross-mk.conf /absolute/new-work
```

The `<xpc/base.h>` regression builds `fixincl` from the patched source tree
with GCC 16, fixes the SDK header and compiles `<xpc/xpc.h>` as C (with
`-fanalyzer`) and C++ under `-Wall -Wextra -Werror`. The unfixed header must
fail. With AutoGen installed it also runs the fixincludes `make check`:

```sh
GCC_CC=/absolute/gcc GCC_CXX=/absolute/g++ OSX_SDK_PATH=/absolute/MacOSX.sdk \
    sh profiles/development-toolchain/tests/darwin-xpc-fixincludes.sh \
    /absolute/patched-gcc-16.2.0 /absolute/new-work
```

The build checks:

1. Export the recipes. `bmake -C lang/gcc16 patch` on macOS applies the diff
   and all pkgsrc patches without rejects.
2. Accept the seed's bounded compile, link and run pilot. Check its actual
   assembler, linker, LTO wrapper and dsymutil execution paths. Check the
   native headers, library search paths, DSOs and selected deployment.
3. Build the package on macOS AArch64 with the accepted GCC16 seed.
   The build log must show a successful stage 2/3 comparison.
4. The installed `gcc` and `g++` must report 16.2.0, define `__GNUC__ 16` and
   no `__clang__`, and compile, link and run C and C++ test programs.
5. Check plain and GCC LTO links, C++ constructors, exceptions across a DSO,
   TLS, threads, debug information and dsymutil. Keep requested diagnostics.
   Complete CPU/extension mapping and upstream compiler tests are separate
   gates. Do not accept the default-CPU pilot as full compiler coverage.

Current checks cover driver `-###` plans and exact source-patch application.
They do not execute a frontend, assembler, linker or generated program.
They do not establish an accepted seed, package or native toolset.

The five linked LLVM MC and Mach-O interface files are byte-identical in
23.1.3 and 23.1.4. This source comparison does not qualify new native tools.

### Shared source prerequisite check

The common source change advances `gcc16` to nb6, `gcc16-libs` to nb7,
and `gcc16-libjit` to nb1. The separate C/C++ runtime advances to nb7;
Fortran runtime/devel advance to nb1 with matching exact dependency pins.
Previous installed-package results remain historical.
The source preparation check applies the complete recipe series and rejects
a corrupt prerequisite. It also races four first writers against a read-only
archive directory. Downloads use the writable output workspace and publish
only complete, hash-checked files. Existing archive-side inputs are read only.

```sh
python3 profiles/development-toolchain/tests/gcc-source-prerequisite.py \
  /absolute/prepared-pkgsrc /absolute/gcc-16.2.0.tar.xz \
  --sdk-source /absolute/EmberBSD-SDK
```

This check does not qualify a native compiler package or SDK toolset.
