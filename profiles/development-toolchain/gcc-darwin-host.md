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

[gcc-darwin-host.patch](patches/gcc-darwin-host.patch) changes only Darwin
native builds of `lang/gcc16`:

- `PATCHFILES` applies the diff with `-p1` before the pkgsrc patches.
  The diff also adds Darwin COBOL support in `libgcobol/configure.tgt`. That
  hunk conflicts with `patch-libgcobol_configure.tgt`, and the recipe does not
  build COBOL. `PATCH_DIST_CAT` drops that one file section.
- Darwin requires an accepted SDK GCC16 bootstrap seed. The recipe rejects
  `PKGSRC_COMPILER=clang` and missing seed inputs. GCC builds stage 1,
  rebuilds itself, and compares stages 2 and 3.
- The recipe selects explicit LLVM MC, Mach-O LLD and dsymutil paths.
  [gcc-darwin-llvm-mc.patch](patches/gcc-darwin-llvm-mc.patch) adds
  `--with-darwin-assembler=llvm-mc` to GCC. It changes the driver assembler
  arguments and the configure assembler probes together.

NetBSD and cross builds have `OPSYS=NetBSD` and keep their current recipes.
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

The producer also sets `PKGSRC_COMPILER=gcc` before pkgsrc reads the recipe.
These values are inputs to an accepted SDK plan. A make variable name or a
successful version query does not qualify a seed. The recipe does not create
another descriptor format. It does not search `PATH` for a missing compiler.

The recipe passes `--with-as`, `--with-ld` and `--with-dsymutil` to GCC.
Fresh GCC embeds these exact paths. It uses its source-owned MC mode.
It does not require an external specs override for ordinary use.
The producer must keep the embedded tools available in the final bundle.
It must provide the other configure and build tools from its accepted closure.

Use the [initial make binding](../common-build-tools/bootstrap/README.md)
when a seed make has external makefile or shell defaults. It retains the
complete upstream rules and binds an explicit shell before metadata reads.
It does not qualify an initial make binary as an ordinary native tool.

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
The initial values are `26.0` and `26.5`. Bind the SDK version to the exact
accepted ABI metadata, such as its inventoried `SDKSettings.json` Version.
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
selection. It checks that the cross recipe does not get the Darwin diff:

```sh
BMAKE=/absolute/bmake sh profiles/development-toolchain/tests/darwin-host.sh \
    /absolute/prepared-pkgsrc /absolute/darwin-mk.conf \
    /absolute/cross-mk.conf /absolute/new-work
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
