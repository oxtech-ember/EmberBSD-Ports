# Cross-build the complete LLD package

LLD 23.1.3 uses the same verified monorepo archive and installed LLVM
provider as [the compiler family](../llvm-family.md). The build keeps
COFF, Common, ELF, MachO, MinGW and Wasm development archives, all linker
entry points, public headers and CMake exports. Upstream tests stay enabled.

Cross configuration selects the matching native `llvm-tblgen`, upstream
`llvm-lit` and Python interpreter explicitly. Target LLVM CMake metadata
comes from the selected EmberBSD sysroot. Missing host inputs or mismatched
tool versions fail configuration; they are not replaced by target executables.
The matching libunwind source headers supply Mach-O constants. No additional
libunwind runtime provider is installed.

CMake resolves symlinked sysroots before exposing LLVM's GTest include
directories. The original compiler wrapper discarded those physical paths,
causing both upstream test executables to fail at `gmock/gmock.h`. A narrow
buildlink mapping now redirects that sysroot spelling into the consumer's
declared dependencies. It does not admit arbitrary host headers.

```sh
BMAKE=/absolute/host/bin/bmake READELF=/absolute/target-readelf \
    sh profiles/common-build-tools/tests/lld-cross-inputs.sh \
    /absolute/prepared-pkgsrc /absolute/cross.mk /absolute/new-check
```

On 2026-10-12, the complete macOS-to-EmberBSD/AArch64 cross-package passed
normal manifest, interpreter, permission, PIE, RELRO, RPATH and work-path
checks. Normal package installation into the build sysroot also passed.
Package SHA256:
`746e2b748585e6cfb2891e6df573cfb14db464c30faf5ce318b83c7610c3261b`.
The real recipe check rejects missing generators, retains all six libraries
and verifies both unchanged upstream test executables as AArch64 ELF linked
to canonical shared LLVM. Their compilation passed after the include repair.
Executing LLD and those tests on the target remains a separate pending gate.
No full installed LLVM/Clang/LLD runtime or Plasma session is claimed here.
