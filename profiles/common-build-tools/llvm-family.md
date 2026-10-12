# LLVM 23 common family

This profile prepares matching LLVM 23.1.3, Clang, LLD and upstream
Python314 lit for the common Mesa26/TinyGo dependency closure. It extends
[the common profile](README.md), based on pkgsrc
`fff4deb639a1a640476203c80f752fb77b6cb14b`. The previously accepted LLVM 23.1.2 core package
cross-builds on macOS and passes installed C API and ORC JITLink acceptance
on Zero 3W. [Mesa consumers](../common-graphics/cross/mesa-package.md) also pass
installed runtime checks. Clang 23.1.2 cross-packaging also passes; installed Clang/LLD and TinyGo remain separate gates;
core acceptance does not establish an installed compiler family.
The `llvm-23.1.2nb1` revision also carries the shared
[DWARF32/64 DWP package-index repair](cross/llvm-dwp-tests.md), with mixed-width,
type-unit, live-debugger and malformed-input checks in the AArch64 VM.
Its installed 104-case matrix and the existing C API/ORC consumers pass
without loader overrides; package integrity covers all 2,789 payload entries.

## Current 23.1.3 migration

The [official stable 23.1.3 archive](https://github.com/llvm/llvm-project/releases/tag/llvmorg-23.1.3) was published on 2026-10-06. All four
recipes now share its version and digests. Zero-fuzz patches, generated-header
contracts, negative-input checks and the exported version selection pass.
The DWP repair remains applied once. Matching native generators execute on
macOS; the actual host metadata helper reports target AArch64, shared LLVM
and RTTI. QDoc also passes a C++ documentation consumer with the official
native LLVM/Clang SDK. The full LLVM 23.1.3 core now passes cross-package checks
and installation into the common build sysroot. Its staged metadata helper
passes 15 query/refusal checks. The package SHA256 is
`052b4a4e7afd291c21ee78f9c2cbd5e9c125164ff1faad44bbfb27d922793cfe`.
The complete Clang and [LLD](cross/lld.md) 23.1.3 packages also pass normal
cross-package checks and sysroot installation. Installed 23.1.3 target
execution and renewed Mesa/Qt runtime
acceptance are still in progress. The dated 23.1.2 receipts below are historical
evidence and must not be relabeled as 23.1.3 results.

## One family and development payload

All four recipes use the official monorepo archive and matching distinfo.
[sources.tsv](sources.tsv) records its URL and SHA256. Shared version selection
rejects unprepared recipes: compiler-rt, libc++, libc++abi, libunwind, MLIR,
Flang, OpenMP, extra tools and wasi runtimes cannot silently combine an LLVM21
recipe with this archive. Repair consumers through Ports; do not install a
second LLVM. Legacy independent pkgsrc recipes are not migrated here.

Core keeps shared libLLVM, RTTI and static development components together:
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
common Python314 and ordinary wheel machinery. LLVM no longer installs a
source/build-tree-dependent stub. Build-tree lit remains for upstream tests.
Upstream reports 23.1.3dev; expected wheel metadata is 23.1.3.dev0, not silently
relabeled. No project Python helper is added. Wheel payload/shebang/PLIST checks
await native staging.

```sh
sh profiles/common-build-tools/tests/source-profile.sh \
    /absolute/verified-distfiles /absolute/new-work llvm-source
```

The named gate verifies all four distinfo records and the complete patch set through actual
pkgsrc checksum.awk, full zero-fuzz forward series, corrupt/raw-RCS/missing/
reversed/repeated failures, exact exports and refused existing/unknown/missing-patch
exports. Accepted Python/Meson/GCC recipe bytes are compared without rerunning
unrelated suites. Target/PLIST declarations are source contracts, not builds.
The default source gate includes LLVM; python-source preserves its narrow scope.

The generated-header gate is independently usable with the verified pristine tree:

```sh
sh profiles/common-build-tools/tests/llvm-generated-headers.sh \
    /absolute/llvm-project-23.1.3.src \
    profiles/common-build-tools/recipes /absolute/new-header-check
```

It reads actual Config configure outputs, Analysis tablegen, Extension generation,
Clang Basic tablegen/diagnostic macros and binary-tree install declarations.
Source-file existence alone cannot prove generated headers. config.h is excluded
by upstream; Basic JSON outputs do not match its *.inc install rule. This named
source contract does not execute CMake/TableGen or replace package-file checks.

llvm-selection.sh parses the real exported version block with BSD make:
four allowed paths and thirteen rejected consumers. Missing BSD make prints SKIP;
all 17 cases now pass with native BSD make. A bounded native metadata check also
generates the config with actual GCC16 and existing Clang21.1.8; it does not prove
LLVM23 driver/link behavior. See [native evidence](native-evidence.md).
Full native recipe parsing is separate. clang-config.sh uses fixture metadata and
a real available Clang driver's traces, including causal no-config RED, C/C++, CRT
search order, cross/SDK optout, static and no-default-library modes. Dummy CRT
files are never linked. AppleClang21 is comparative evidence, not native LLVM23.
llvm-lit.sh stages actual upstream modules in a private Python314 environment,
renames the source tree away and runs upstream shell-format PASS/FAIL without
PYTHONPATH. FAIL must return 1. The subsequent installed
`py314-llvm-lit-23.1.2` package passed wheel metadata, launcher/module and
upstream shell-format PASS/XFAIL/FAIL checks in AArch64 UTM. The
[installed runner](cross/run-llvm-lit-tests.sh) requires the failure exit code;
it uses the shared Python3.14 provider, without PYTHONPATH overrides.

## Cross-build and accepted core

Use the [common cross composition](cross/README.md) and the
[host LLVM metadata workflow](../common-graphics/cross/llvm-config.md).
`cross/build-llvm-native.sh` builds matching native TableGen generators;
`EMBERBSD_LLVM_NATIVE_TOOLS` selects their absolute directory. The recipe
checks each executable's exact version and keeps host generators separate
from target LLVM headers and libraries. It includes upstream libc utilities
needed by LLVM23; these are build sources, not a second installed libc.

The llvm-config CMake adaptation removes only the build sysroot from reported
target linker search paths. It does not change actual compiler/linker flags.
Source-causal CMake and real pkgsrc selection tests cover this boundary.
The host metadata executable uses the generated target build metadata.
Its stage proof reproduces CMake's exact target strip operation and requires
byte-identical output; normal install-strip remains enabled. All 16 query
groups agree with llvm-config executed on the actual target.

On 2026-10-08 the complete LLVM23.1.2 package passed ordinary pkgsrc file,
dependency, interpreter, PIE, RELRO, RPATH and work-directory checks. Two
inherited opt-viewer permission warnings remain; there were no check errors.
The package retains all selected normal/experimental backends, RTTI, the
shared library, static archives and test-development support.

Installed normally on Orange Pi Zero 3W (A733), it passed
[C API/bitcode and four default ORC JITLink lifecycles](cross/llvm-api-tests.md).
The tests verify shared-library RTTI, real generated-function results,
resource removal and typed missing-symbol errors. They use ordinary target
loader paths without global PaX changes or a private LLVM runtime. This is
focused AArch64 execution evidence, not the full LLVM upstream suite or
acceptance of other backends, concurrent JIT or arbitrary external relocations.

The [Clang cross workflow](cross/clang.md) provides matching host generators,
target-only installed paths and checked GCC16 metadata. Its preparation checks
pass. Full LLVM, Clang and LLD 23.1.3 packages now pass ordinary cross-package
checks and installation into the build sysroot. On 2026-10-12, installed
LLVM 23.1.3 also passes the same C API/bitcode and four ORC lifecycles on CM5,
16 actual target metadata queries and 21 sealed-tool integrity checks.
Installed Clang/LLD and renewed downstream consumer acceptance remain separate.

## Remaining native gates

Use normal package/check-files, WRKREF, RPATH, dependency and upstream checks.
Verify exact CMake/compiler provenance, shared/static consumers, RTTI, installed
lit and native C/C++ CRT traces for PIE/non-PIE/shared/static. Check foreign triples,
same-triple SDK optout, incomplete dependencies and actual ELF/load bindings.
Prove startup pthread, dlopen/threads/TLS, JIT RW-to-RX and unload without weakening
PaX/global settings or hiding existing libc helper failures. TinyGo's LLVM22-tagged
binding/fork needs its own LLVM23 API/target/static-component gates, without an
LLVM22 fallback. Mesa26 and GPU acceleration retain separate unaccepted gates.
