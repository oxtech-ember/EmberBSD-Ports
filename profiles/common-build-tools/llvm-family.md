# LLVM 23 common family

This profile prepares matching LLVM 23.1.4, Clang, LLD and upstream
Python315 lit for the common Mesa26/TinyGo dependency closure.
It extends [the common profile](README.md), based on pkgsrc
`fff4deb639a1a640476203c80f752fb77b6cb14b`.
## Current 23.1.4 source update

The [official stable 23.1.4 release](https://github.com/llvm/llvm-project/releases/tag/llvmorg-23.1.4)
was published on 2026-10-20. All five package roles share its source version.
The four distinfo records use the verified 179,272,572-byte monorepo archive.
Its SHA256 is `819ecf7351f1a66f76b2d701d8942faaf5faeb324cb90c9d5b090de142434bb2`.
The existing seven LLVM patches and one Clang patch apply with zero fuzz.
The DWP repair remains applied once. All normal and experimental backends,
platform rules, options and runtime/SDK partitions remain unchanged.

Active Clang, lit, Mesa, metadata helpers and native generator consumers select
23.1.4. Upstream lit reports `23.1.4dev`; its wheel name is `lit-23.1.4.dev0`.
The pinned llvm-config source and the five Darwin MC/Mach-O interface sources
are unchanged from 23.1.3. This is source compatibility evidence.
It does not establish native tool execution or a new GCC16 producer.
The historical macOS binary pin remains in `sources.tsv`; the new pin is separate.
No 23.1.4 binary archive was downloaded for this source update.

The current source gate requires an explicit SDK `DIGEST` executable.
It compares unaffected Python, Meson and GCC exports through the production
export graph from HEAD. It does not maintain a second GCC patch list.
LLVM 23.1.4 full builds, package checks, installed runtime and downstream
consumer acceptance remain pending. The receipts below retain their original versions.

## Previous runtime acceptance

The [Linux/GCC16 runtime and SDK receipt](cross/llvm-linux-aarch64.md)
records full LLVM 23.1.3 builds, installed C API/ORC checks and package lifecycle
acceptance. Its [Mesa consumer](../common-graphics/cross/mesa-linux-aarch64.md)
passes installed llvmpipe rendering and all 39 target invocations.
Earlier [CM5 and Zero 3W API checks](cross/llvm-api-tests.md) and the
[DWP matrix](cross/llvm-dwp-tests.md) retain their recorded versions and scope.
Full Clang/LLD staging passed; installed Clang/LLD, TinyGo and renewed Qt
acceptance remain separate. These results do not accept LLVM 23.1.4.

## One family and development payload

All five package roles use the official monorepo archive and matching distinfo.
[sources.tsv](sources.tsv) records its URL and SHA256. Shared version selection
rejects unprepared recipes: compiler-rt, libc++, libc++abi, libunwind, MLIR,
Flang, OpenMP, extra tools and wasi runtimes cannot silently combine an LLVM21
recipe with this archive. Repair consumers through Ports; do not install a
second LLVM. Legacy independent pkgsrc recipes are not migrated here.

Core builds shared libLLVM, RTTI and static development components together:
LLVM_BUILD_LLVM_DYLIB/LLVM_LINK_LLVM_DYLIB on, RTTI on, BUILD_SHARED_LIBS off,
libc++ off and LLVM_INSTALL_TOOLCHAIN_ONLY off. Clang requests static libclang
alongside shared libraries. LLD retains COFF/Common/ELF/MachO/MinGW/Wasm archives.
All upstream normal/experimental backend options remain available and selected
by default. SPIRV is now normal. The stack is not restricted to AArch64.

PLIST candidates refresh source/resource headers and restore the Config/Extension
definitions and replacement Analysis/Clang Basic generated includes. A source-derived
contract checks 119 Clang and 11 LLVM outputs in these directly related generation/install rules;
the preceding PLIST fails on 17 missing entries. llvm_gtest support, libclang.a,
clangAnalysisLifetimeSafety and LLVMDTLTO are declared. Other generated/tool/archive
payloads were subsequently checked against the complete LLVM core stage:
2,789 installed entries, with conditional backend/gtest components preserved.
Removed bugpoint and DirectXPointerTypeAnalysis entries were replaced by the
actual LLVM23 tool/header/archive payload. Clang and LLD now pass complete package staging; installed execution remains pending.
Missing or unexpected files remain failures; package checks are not weakened.

Standalone Clang/LLD use matching installed LLVM CMake exports and check
llvm-config's exact version before configure. Their tests require core tests
with LLVM_INSTALL_GTEST on: upstream needs the llvm_gtest target, not an unrelated
googletest package. LLD's second LLVM test archive and unused libunwind buildlink
are removed. C/C++ builds use pkgsrc wrappers with GCC_REQD16.2 and common Python.
Native cache, RTTI, dependency and ELF evidence remains required.

NetBSD cross builds now use the [runtime/SDK package split](cross/llvm-runtime.md).
The execution-only image receives `llvm-23.1.4nb1`; the build-host target sysroot
also needs `llvm-devel-23.1.4nb2`. Native LLVM remains a full package.
## Inherited patch decisions

NetBSD RCS identifiers, authorship and licenses are preserved. These recipes,
adaptations and shell contracts are AI-assisted EmberBSD work, not submitted
or accepted upstream. Removed patches remain in the pinned pkgsrc history.

| Core patch | Decision |
| --- | --- |
| CMakeLists.txt (RCSv1.2) | Adapt Solaris workaround disabling; source DataTypes supplies the fix. |
| cmake/config-ix.cmake (v1.8) | Adapt pthread override before upstream CMAKE_REQUIRED_LIBRARIES append. |
| cmake/modules/AddLLVM.cmake (v1.9) | Drop upstream-covered Darwin SONAME hunk; retain absolute install-name policy. |
| include/llvm-c/DataTypes.h | Preserve conditional Solaris regset inclusion and macro cleanup. |
| tools/llvm-shlib/CMakeLists.txt | Preserve Solaris extraction/Bsymbolic handling. |
| RDFGraph.h, RDFRegisters.h, RDFLiveness.cpp | Drop comparator fixes already upstream. |
| MachOLayoutBuilder.cpp, MachOWriter.cpp | Drop alignment/raw-size fixes already upstream. |
| Hexagon RDFCopy.cpp/RDFCopy.h | Drop comparator fixes, including their RDFCopyBase.h location. |
| utils/llvm-lit/CMakeLists.txt | Drop installed build-launcher hunk; package upstream lit separately. |
| lib/DWP/DWP.cpp | Correct unit/string widths and indexed type contributions; bound malformed metadata reads. |

Clang Gnu.cpp RCSv1.5 retains Solaris's configured GCC prefix substitution in
GCCInstallationDetector::AddDefaultGCCPrefixes. It does not select GCC16 on
NetBSD, which uses a different toolchain class.
Five Clang shebang-replacement entries for upstream-deleted scripts are removed;
the remaining replacement paths were checked against the pristine release.
Both LLD 835769 patches are removed: Config.h v1.10 added an unused field;
Options.td v1.5 accepted a dummy flag with misleading mitigation help text.
There is no upstream 835769 implementation. The flag now fails instead of
silently promising a hardware fix. GCC can emit it for an explicit erratum
scenario; that scenario remains unsupported. Real upstream 843419 stays intact.

## Native Clang defaults

Native Darwin LLVM and Clang require `EMBERBSD_DARWIN_LIBTOOL`.
Select an existing absolute executable with the Darwin archive interface.
The shared [selector](../../pkgsrc/lang/llvm/darwin.mk) forwards `CMAKE_LIBTOOL` without PATH lookup.
LLVM probes `-V`, then uses `-static ... -o TARGET` for archive creation.
SDK qualification or the initial scoped seed belongs to the producer.
Other native hosts and cross builds do not consume this selector.
The [metadata regression](tests/llvm-darwin-libtool.py) covers selection and refusals without compilation.

LLD installs `libexec/lld/ld` as a relative link to `../../bin/lld`.
An absolute link would escape a staged or relocated prefix, and the SDK
inventory refuses it. The [link regression](tests/lld-relative-libexec-link.py)
runs the real `post-install` target for a staged and a direct prefix.

NetBSD's normal libstdc++ search uses base headers/CRT paths; selecting only
the stdlib name is insufficient. The package generates a supported effective
native-triple config from actual common GCC16 metadata. No generic Driver patch
or per-application wrapper is introduced. Generation rejects wrong GCC version,
missing compilers/CRT/runtime, escaped real paths, ambiguous CRT/runtime
locations, duplicate headers, failed preprocessing and target ABI mismatch.
NetBSD version suffix differences are allowed; architecture/vendor/ABI must agree.

The config supplies C++-only -stdlib++-isystem paths and libstdc++ selection,
-B for exact GCC16 CRT, ordinary linker-only -L before NetBSD's /usr/lib and
$-Wl runtime RPATH in the linking tail. Available Clang21 command traces show
that $-L tail options are not rendered by NetBSD's early argument path;
$-Wl,-L in the tail would put the base directory first. LLVM23 NetBSD source
also renders regular -L before AddFilePathLibArgs. Only RPATH uses the tail.
No C++ library is unconditionally added to C or no-default-library modes.

Driver::GetFilePath searches -B before base file paths: -L/RPATH cannot select
crtbegin/end. Generation checks actual GCC16 files; OS crt0/crti/crtn retain
normal ownership/search. NetBSD's architecture switch controls explicit libgcc
insertion; --rtlib=libgcc alone does not establish AArch64 runtime selection.
Native linking must prove GCC16 CRT and one actual stdc++7/libgcc_s1.
Config generation is not runtime evidence or protection against later manual
removal of package files. No fake SONAME or static C++ runtime workaround is used.

The config names only the effective native triple, never generic clang.cfg or
clang++.cfg. Different target triples must not inherit these paths. A same-triple
SDK must use standard --no-default-config with --sysroot; sysroot alone does not
disable native defaults. Projects retain -nostdinc++, -nostdlib, -nodefaultlibs,
-nostdlib++ and static modes. This is not arbitrary cross SDK acceptance.

## Upstream lit and focused checks

The new py-llvm-lit recipe uses upstream lit's module/setup.py and lit.py launcher,
common Python315 and ordinary wheel machinery. LLVM no longer installs a
source/build-tree-dependent stub. Build-tree lit remains for upstream tests.
Upstream reports 23.1.4dev; expected wheel metadata is 23.1.4.dev0, not silently
relabeled. Wheel payload, shebang and PLIST checks await native staging.

```sh
export EMBERBSD_SDK_SOURCE=/absolute/EmberBSD-SDK
export DIGEST=/absolute/sdk/bin/digest
sh profiles/common-build-tools/tests/source-profile.sh \
    /absolute/verified-distfiles /absolute/new-work llvm-source
```

The named gate verifies all four distinfo records and the complete patch set through actual
pkgsrc checksum.awk, full zero-fuzz forward series, corrupt/raw-RCS/missing/
reversed/repeated failures, exact exports and refused existing/unknown/missing-patch
exports. Accepted Python/Meson/GCC recipe bytes are compared without rerunning
unrelated suites. Target/PLIST declarations are source contracts, not builds.

The generated-header gate is independently usable with the verified pristine tree:

```sh
sh profiles/common-build-tools/tests/llvm-generated-headers.sh \
    /absolute/llvm-project-23.1.4.src \
    pkgsrc /absolute/new-header-check
```

It reads actual Config configure outputs, Analysis tablegen, Extension generation,
Clang Basic tablegen/diagnostic macros and binary-tree install declarations.
Source-file existence alone cannot prove generated headers. config.h is excluded
by upstream; Basic JSON outputs do not match its *.inc install rule. This named
source contract does not execute CMake/TableGen or replace package-file checks.

llvm-selection.sh parses the real exported version block with BSD make:
five allowed paths and thirteen rejected consumers. Missing BSD make prints SKIP.
Full native recipe parsing remains separate. clang-config.sh uses fixture metadata
and real available Clang driver traces. Dummy CRT files are never linked.
See [native evidence](native-evidence.md) for its original tool versions and scope.
llvm-lit.sh stages actual upstream modules in a private Python315 environment,
renames the source tree away and runs upstream shell-format PASS/XFAIL/FAIL without
PYTHONPATH. FAIL must return 1. A missing or older interpreter is an error.
LLVM 23.1.4 requires Python >=3.8 for its tests. Its lit package metadata has
no upper Python bound, and its resource-limit fixture handles Python 3.15.
The earlier source passed this bounded launcher contract on host Python 3.15.0.
The 23.1.4 launcher check requires the matching common Python315 producer.
This does not establish target wheel installation or the full LLVM test suite.

`llvm-lit-selection.py` queries the complete recipe with real BSD make:

```sh
python3 -B profiles/common-build-tools/tests/llvm-lit-selection.py \
    /absolute/normal-export \
    /absolute/source/pkgsrc/devel/py-llvm-lit/Makefile \
    /absolute/bmake /absolute/native.mk.conf /absolute/cross.mk.conf \
    /absolute/new-selection-output
```

It checks native, amd64 cross and recursive-host selection on Python315.
Requests for Python314 and unsupported Python316 must fail. The candidate
Makefile is parsed over the normal export; no package phase or database
mutation runs. Verify the shared archive through normal pkgsrc `checksum.awk`
and the unchanged recipe `distinfo` before the launcher test.

## Cross-build and accepted core

Use the [common cross composition](cross/README.md) and the
[host LLVM metadata workflow](../common-graphics/cross/llvm-config.md).
`cross/build-llvm-native.py` builds matching native TableGen generators;
`EMBERBSD_LLVM_NATIVE_TOOLS` selects their absolute directory. The recipe
checks each executable's exact version and keeps host generators separate
from target LLVM headers and libraries. It includes upstream libc utilities
needed by LLVM23; these are build sources, not a second installed libc.

The llvm-config CMake adaptation removes the build sysroot from reported target
`-L` paths. It omits the two common build-only `rpath-link` arguments from
reported flags. Actual compiler/linker flags keep those transitive searches.
Runtime RPATHs, other link arguments and native/no-sysroot metadata stay intact.
Source-causal CMake and real pkgsrc selection tests cover this boundary.
The host metadata executable uses the generated target build metadata.
Its stage proof reproduces CMake's exact target strip operation and requires
byte-identical output; normal install-strip remains enabled. All 16 query
groups agree with llvm-config executed on the actual target.

Use the [Clang cross workflow](cross/clang.md) for matching host generators,
target-only installed paths and checked GCC16 metadata.
The earlier runtime receipts cover focused AArch64 execution, shared-library
RTTI, resource removal and missing-symbol errors with normal loader paths.
They do not cover the full upstream suite, all backends, concurrent JIT or
arbitrary relocations. Two inherited opt-viewer permission warnings remain.

## Remaining native gates

Use normal package/check-files, WRKREF, RPATH, dependency and upstream checks.
Verify exact CMake/compiler provenance, shared/static consumers, RTTI, installed
lit and native C/C++ CRT traces for PIE/non-PIE/shared/static. Check foreign triples,
same-triple SDK optout, incomplete dependencies and actual ELF/load bindings.
Prove startup pthread, dlopen/threads/TLS, JIT RW-to-RX and unload without weakening
PaX/global settings or hiding existing libc helper failures. TinyGo's LLVM22-tagged
binding/fork needs its own LLVM23 API/target/static-component gates, without an
LLVM22 fallback. Mesa26 and GPU acceleration retain separate unaccepted gates.
